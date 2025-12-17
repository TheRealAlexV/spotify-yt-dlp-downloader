import logging
import secrets
import base64
import urllib.parse
import httpx
import pkg_resources # New: used to determine current package version
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes

from ..constants import APP_NAME
from ..config import get_spotify_config

logger = logging.getLogger(APP_NAME)


def _base64url_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def code_challenge_from_verifier(verifier: str) -> str:
    """Compute the PKCE S256 code_challenge from a code_verifier.

    Mirrors Exportify's implementation:
      base64url(sha256(verifier)) without padding.
    """

    digest = hashlib.sha256((verifier or "").encode("utf-8")).digest()
    return _base64url_no_pad(digest)


def get_effective_spotify_client_id(config: dict) -> str:
    """
    Returns the Spotify Client ID to use.
    Users *must* provide their own client ID; there is no longer a public fallback.
    """
    client_id = config.get("spotify_client_id")
    if not client_id:
        logger.error("Spotify Client ID is not configured. Please set 'spotify_client_id' in config.json. Visit https://developer.spotify.com/dashboard/applications to get one.")
        raise ValueError("Spotify Client ID not configured.")
    return str(client_id).strip()


def check_spotify_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """Check whether Spotify OAuth settings are present and provide user guidance.

    Returns a dict:
      {
        "ok": bool,
        "client_id": str,
        "client_id_source": "config"|"exportify_fallback",
        "redirect_uri": str,
        "scopes": list[str],
        "message": str,
      }
    """

    config = config or {}
    redirect_uri = str(config.get("spotify_redirect_uri", "")).strip()
    scopes = list(config.get("spotify_scopes", []) or [])

    client_id = get_effective_spotify_client_id(config)
    client_id_source = "config" if str(config.get("spotify_client_id", "")).strip() else "exportify_fallback"

    if not redirect_uri:
        return {
            "ok": False,
            "client_id": client_id,
            "client_id_source": client_id_source,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "message": (
                "Missing spotify_redirect_uri in config.json.\n"
                "Recommended default: http://localhost:8888/callback"
            ),
        }

    # We can technically proceed with the Exportify fallback, but we want to warn loudly.
    if client_id_source == "exportify_fallback":
        return {
            "ok": True,
            "client_id": client_id,
            "client_id_source": client_id_source,
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "message": (
                "spotify_client_id is not set. Falling back to Exportify's public client id.\n"
                "For reliability and to avoid breakage if Exportify rotates credentials, create your own Spotify app\n"
                "and set spotify_client_id in config.json (see spotify_app_setup_instructions())."
            ),
        }

    return {
        "ok": True,
        "client_id": client_id,
        "client_id_source": client_id_source,
        "redirect_uri": redirect_uri,
        "scopes": scopes,
        "message": "Spotify credentials look OK.",
    }


def spotify_app_setup_instructions(config: dict) -> str:
    """
    Provides instructions for setting up a Spotify app, with a dynamic redirect URI.
    """
    redirect_uri = config.get("spotify_redirect_uri", "http://localhost:8888/callback") # Safe fallback in case config loading fails
    scopes = config.get("spotify_scopes", [
        "user-library-read", # Access to a user's "Your Music" library
        "playlist-read-private", # Read access to a user's private playlists
        "playlist-read-collaborative" # Read access to a user's collaborative playlists
    ])

    # Dynamic package version for user-agent - fallback if not installed via pip
    try:
        package_version = pkg_resources.get_distribution(APP_NAME).version
    except pkg_resources.DistributionNotFound:
        package_version = "unknown"

    instructions = f"""
Spotify app setup (recommended):\n"
        "1) Go to https://developer.spotify.com/dashboard\n"
        "2) Create an app (or select an existing one)\n"
        f"3) Add this Redirect URI in the app settings: {redirect_uri}\n"
        "4) Copy the Client ID into spotify-yt-dlp-downloader/config.json as spotify_client_id\n"
        "5) Keep spotify_scopes as-is unless you know you need different permissions\n"
        "\n"
        "Notes:\n"
        "- This project uses Authorization Code + PKCE (no client secret required).\n"
        "- Redirect URI must match *exactly* what you configure in the Spotify dashboard.\n"
    """

    return instructions


def extract_code_from_redirect_url(redirect_url: str) -> Dict[str, str]:
    """Parse a redirect URL and return {"code": ..., "state": ...} (missing keys omitted)."""

    parsed = urllib.parse.urlparse(str(redirect_url or "").strip())
    qs = urllib.parse.parse_qs(parsed.query)
    out: Dict[str, str] = {}
    if qs.get("code"):
        out["code"] = str(qs["code"][0])
    if qs.get("state"):
        out["state"] = str(qs["state"][0])
    if qs.get("error"):
        out["error"] = str(qs["error"][0])
    return out


@dataclass(frozen=True)
class PKCEPair:
    code_verifier: str
    code_challenge: str


class SpotifyPKCEAuth:
    """Spotify OAuth (Authorization Code + PKCE).

    This module intentionally avoids external deps (requests).

    Typical flow:
      1) pkce = SpotifyPKCEAuth.generate_pkce_pair()
      2) url = auth.get_authorize_url(pkce.code_challenge, state=...)
      3) user completes login; you receive `code` at redirect URI
      4) token = auth.exchange_code_for_token(code=..., code_verifier=pkce.code_verifier)
    """

    def __init__(self, config: Dict[str, Any], *, token_manager: Optional[TokenManager] = None):
        self.config = config or {}
        self.token_manager = token_manager or TokenManager()

    @staticmethod
    def generate_pkce_pair() -> PKCEPair:
        """Generate a PKCE verifier + challenge."""
        # RFC 7636: verifier length 43-128 chars, characters from ALPHA / DIGIT / "-" / "." / "_" / "~"
        # token_urlsafe uses base64url alphabet, which is compatible (we strip padding)
        verifier = secrets.token_urlsafe(64).rstrip("=")
        verifier = verifier[:128]
        if len(verifier) < 43:
            verifier = (verifier + secrets.token_urlsafe(64)).rstrip("=")[:43]

        challenge = code_challenge_from_verifier(verifier)
        return PKCEPair(code_verifier=verifier, code_challenge=challenge)

    def get_authorize_url(
        self,
        *,
        code_challenge: str,
        state: Optional[str] = None,
        scopes: Optional[Iterable[str]] = None,
        show_dialog: bool = False,
    ) -> str:
        # Prefer user-provided client id; fall back to Exportify's client id.
        client_id = get_effective_spotify_client_id(self.config)
        redirect_uri = str(self.config.get("spotify_redirect_uri", "")).strip()
        if not client_id:
            raise ValueError("Missing config.spotify_client_id")
        if not redirect_uri:
            raise ValueError("Missing config.spotify_redirect_uri")

        scope_list = list(scopes if scopes is not None else self.config.get("spotify_scopes", []))
        scope_str = " ".join([str(s).strip() for s in scope_list if str(s).strip()])

        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
            "show_dialog": "true" if show_dialog else "false",
        }
        if scope_str:
            params["scope"] = scope_str
        if state:
            params["state"] = state

        return f"{SPOTIFY_ACCOUNTS_BASE_URL}/authorize?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, *, code: str, code_verifier: str) -> TokenInfo:
        payload = self._post_form(
            f"{SPOTIFY_ACCOUNTS_BASE_URL}/api/token",
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": str(self.config.get("spotify_redirect_uri", "")).strip(),
                "client_id": get_effective_spotify_client_id(self.config),
                "code_verifier": code_verifier,
            },
        )
        token = TokenInfo.from_spotify_token_response(payload)
        if not token.access_token:
            raise RuntimeError(f"Spotify token exchange failed: {payload}")

        self.token_manager.save(self.config, token)
        return token

    def refresh_access_token(self, *, refresh_token: str) -> TokenInfo:
        payload = self._post_form(
            f"{SPOTIFY_ACCOUNTS_BASE_URL}/api/token",
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": get_effective_spotify_client_id(self.config),
            },
        )

        token = TokenInfo.from_spotify_token_response(payload)
        # Spotify may omit refresh_token on refresh; keep existing.
        if not token.refresh_token:
            token = TokenInfo(
                access_token=token.access_token,
                token_type=token.token_type,
                expires_at=token.expires_at,
                refresh_token=refresh_token,
                scope=token.scope,
            )

        if not token.access_token:
            raise RuntimeError(f"Spotify token refresh failed: {payload}")

        self.token_manager.save(self.config, token)
        return token

    def load_cached_token(self) -> Optional[TokenInfo]:
        return self.token_manager.load(self.config)

    def begin_oauth_flow(self, *, show_dialog: bool = True) -> Dict[str, Any]:
        """Return {auth_url, pkce_pair, state} for starting the PKCE browser flow."""

        pkce = self.generate_pkce_pair()
        state = secrets.token_urlsafe(16).rstrip("=")
        url = self.get_authorize_url(code_challenge=pkce.code_challenge, state=state, show_dialog=show_dialog)
        return {"auth_url": url, "pkce_pair": pkce, "state": state}

    def _post_form(self, url: str, form: Dict[str, Any]) -> Dict[str, Any]:
        encoded = urllib.parse.urlencode({k: str(v) for k, v in form.items() if v is not None}).encode("utf-8")
        req = urllib.request.Request(
            url=url,
            data=encoded,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"Spotify token request failed: {e}") from e

        try:
            return json.loads(body)
        except Exception as e:
            raise RuntimeError(f"Spotify token response was not JSON: {body}") from e
