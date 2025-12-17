import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from .auth import SpotifyPKCEAuth
from .token_manager import TokenInfo, TokenManager


SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"


class SpotifyClient:
    """Thin Spotify Web API client (stdlib-only).

    This client expects an OAuth access token (Authorization Code w/ PKCE).

    Design goals:
    - Centralize retry + rate limiting (429 Retry-After)
    - Provide high-level helpers that return *fully paged* lists
    """

    def __init__(self, config: Dict[str, Any], *, token_manager: Optional[TokenManager] = None):
        self.config = config or {}
        self.token_manager = token_manager or TokenManager()
        self._token: Optional[TokenInfo] = None

    # -----------------
    # Token management
    # -----------------

    def set_token(self, token: TokenInfo) -> None:
        self._token = token
        self.token_manager.save(self.config, token)

    def get_token(self) -> TokenInfo:
        if self._token is None:
            self._token = self.token_manager.load(self.config)

        if self._token is None:
            raise RuntimeError("No Spotify token available. Run the OAuth PKCE flow first.")

        if not self.token_manager.is_expired(self._token):
            return self._token

        if not bool(self.config.get("spotify_auto_refresh", True)):
            raise RuntimeError("Spotify token expired and spotify_auto_refresh is disabled.")

        if not self._token.refresh_token:
            raise RuntimeError("Spotify token expired and no refresh_token is available.")

        auth = SpotifyPKCEAuth(self.config, token_manager=self.token_manager)
        refreshed = auth.refresh_access_token(refresh_token=self._token.refresh_token)
        self._token = refreshed
        return refreshed

    # -----------------
    # HTTP helpers
    # -----------------

    def _sleep_with_jitter(self, seconds: float) -> None:
        # Avoid synchronized retries when running concurrent calls.
        seconds = float(max(0.0, seconds))
        jitter = float(self.config.get("spotify_retry_jitter", 0.25))
        time.sleep(seconds + (jitter * (time.time() % 1.0)))

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        retry_429: bool = True,
        retry_5xx: bool = True,
        retry_401_refresh: bool = True,
    ) -> Dict[str, Any]:
        """Make a Spotify Web API request and return parsed JSON.

        Retry behavior:
        - 429: honors Retry-After (Spotify rate limiting)
        - 5xx: exponential backoff retries (best effort)
        - 401: one refresh attempt if possible
        """

        max_retries = int(self.config.get("spotify_max_retries", 5))
        backoff_base = float(self.config.get("spotify_backoff_base", 1.0))

        attempt = 0
        while True:
            attempt += 1
            token = self.get_token()

            url = f"{SPOTIFY_API_BASE_URL}{path}"
            if params:
                url = f"{url}?{urllib.parse.urlencode({k: str(v) for k, v in params.items() if v is not None})}"

            req = urllib.request.Request(
                url=url,
                method=method.upper(),
                headers={
                    "Authorization": f"{token.token_type} {token.access_token}",
                    "Accept": "application/json",
                },
            )

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8")
                    status = getattr(resp, "status", 200)
                    headers = dict(resp.headers)
            except urllib.error.HTTPError as e:
                status = e.code
                headers = dict(getattr(e, "headers", {}) or {})
                body = (e.read().decode("utf-8") if hasattr(e, "read") else "")

                # 401: token invalid/expired (server-side); try refresh once.
                if status == 401 and retry_401_refresh and attempt <= max_retries:
                    if self._token and self._token.refresh_token and bool(self.config.get("spotify_auto_refresh", True)):
                        try:
                            auth = SpotifyPKCEAuth(self.config, token_manager=self.token_manager)
                            refreshed = auth.refresh_access_token(refresh_token=self._token.refresh_token)
                            self._token = refreshed
                            retry_401_refresh = False
                            continue
                        except Exception:
                            # fall through to raise
                            pass

                # 429: rate limited.
                if status == 429 and retry_429 and attempt <= max_retries:
                    retry_after = headers.get("Retry-After")
                    try:
                        delay = float(retry_after) if retry_after is not None else 1.0
                    except Exception:
                        delay = 1.0
                    self._sleep_with_jitter(max(1.0, delay))
                    continue

                # 5xx: transient errors.
                if status >= 500 and retry_5xx and attempt <= max_retries:
                    delay = backoff_base * (2 ** max(0, attempt - 1))
                    self._sleep_with_jitter(min(60.0, delay))
                    continue

                raise RuntimeError(f"Spotify API error {status}: {body}") from e
            except Exception as e:
                if attempt <= max_retries:
                    delay = backoff_base * (2 ** max(0, attempt - 1))
                    self._sleep_with_jitter(min(30.0, delay))
                    continue
                raise RuntimeError(f"Spotify API request failed: {e}") from e

            if not body:
                return {}

            try:
                return json.loads(body)
            except Exception as e:
                raise RuntimeError(f"Spotify API response was not JSON (status {status}): {body}") from e

    def _paginate(self, path: str, *, params: Optional[Dict[str, Any]] = None, page_key: str = "items") -> List[Dict[str, Any]]:
        """Fetch all pages for an endpoint that returns {items, total, limit, offset}."""

        out: List[Dict[str, Any]] = []
        limit = int((params or {}).get("limit") or 50)
        offset = int((params or {}).get("offset") or 0)

        while True:
            page = self.request_json("GET", path, params={**(params or {}), "limit": limit, "offset": offset})
            items = page.get(page_key) or []
            if isinstance(items, list):
                out.extend([x for x in items if isinstance(x, dict)])

            total = page.get("total")
            if total is None:
                break

            got = len(items) if isinstance(items, list) else 0
            offset += got
            if got <= 0 or offset >= int(total):
                break

        return out

    # -----------------
    # Convenience endpoints
    # -----------------

    def me(self) -> Dict[str, Any]:
        return self.request_json("GET", "/me")

    def current_user_playlists(self, *, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        return self.request_json("GET", "/me/playlists", params={"limit": limit, "offset": offset})

    def playlist_items(self, playlist_id: str, *, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        return self.request_json(
            "GET",
            f"/playlists/{playlist_id}/tracks",
            params={"limit": limit, "offset": offset, "additional_types": "track"},
        )

    def current_user_saved_tracks(self, *, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        return self.request_json("GET", "/me/tracks", params={"limit": limit, "offset": offset})

    def audio_features(self, ids: List[str]) -> Dict[str, Any]:
        """Return audio features for up to 100 track ids."""

        ids = [str(i).strip() for i in (ids or []) if str(i).strip()]
        if not ids:
            return {"audio_features": []}
        return self.request_json("GET", "/audio-features", params={"ids": ",".join(ids)})

    # -----------------
    # High-level helpers (fully paged)
    # -----------------

    def get_user_playlists(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        return self._paginate("/me/playlists", params={"limit": min(50, int(limit))}, page_key="items")

    def get_playlist_tracks(self, playlist_id: str, *, limit: int = 100) -> List[Dict[str, Any]]:
        # Endpoint shape: {items: [{added_at, track: {...}}], total, ...}
        return self._paginate(
            f"/playlists/{playlist_id}/tracks",
            params={"limit": min(100, int(limit)), "additional_types": "track"},
            page_key="items",
        )

    def get_liked_songs(self, *, limit: int = 50) -> List[Dict[str, Any]]:
        # Endpoint shape: {items: [{added_at, track: {...}}], total, ...}
        return self._paginate("/me/tracks", params={"limit": min(50, int(limit))}, page_key="items")
