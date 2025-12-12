#!/usr/bin/env python3
"""TRAV-DJ song selection feature test runner.

Runs lightweight, local tests for:
- Song selection menu UI wiring (choices + default checked state)
- Existing-song auto-uncheck via folder scan + VALID_AUDIO_EXTENSIONS
- Integration paths in downloads menu for Exportify + legacy playlists

This runner intentionally avoids network calls and does NOT invoke yt-dlp.

Usage:
  cd spotify-yt-dlp-downloader
  python3 -m tests.run_song_selection_feature_tests

"""

from __future__ import annotations

import os
import types
import unittest
from dataclasses import dataclass
from typing import Any

# Ensure imports like `utils.*` and `menus.*` work even when executed from repo root.
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# -------------------------
# Simple questionary mocks
# -------------------------

@dataclass
class _Askable:
    """Mimic questionary prompt objects that return a value from .ask()."""

    value: Any

    def ask(self):
        return self.value


class _QuestionaryMock:
    """A minimal questionary stub that returns queued answers and captures args."""

    def __init__(self):
        # Preserve the real Choice constructor so production code can build choices.
        import questionary as _real_questionary

        self.Choice = _real_questionary.Choice

        self._queue: list[Any] = []
        self.last_checkbox_choices = None
        self.last_checkbox_message = None
        self.last_select_choices = None
        self.last_select_message = None
        self.last_confirm_message = None

    def queue(self, *answers: Any) -> None:
        self._queue.extend(list(answers))

    def _pop(self) -> Any:
        if not self._queue:
            raise AssertionError("QuestionaryMock queue exhausted")
        return self._queue.pop(0)

    def checkbox(self, message: str, choices: list[Any]):
        self.last_checkbox_message = message
        self.last_checkbox_choices = choices
        return _Askable(self._pop())

    def select(self, message: str, choices: list[Any]):
        self.last_select_message = message
        self.last_select_choices = choices
        return _Askable(self._pop())

    def confirm(self, message: str, default: bool = True):
        self.last_confirm_message = message
        return _Askable(self._pop())


class _PatchModuleAttr:
    """Context manager to temporarily patch module attributes."""

    def __init__(self, module: types.ModuleType, attr: str, value: Any):
        self.module = module
        self.attr = attr
        self.value = value
        self._old = None

    def __enter__(self):
        self._old = getattr(self.module, self.attr)
        setattr(self.module, self.attr, self.value)

    def __exit__(self, exc_type, exc, tb):
        setattr(self.module, self.attr, self._old)


# -------------------------
# Helpers
# -------------------------


def _choice_checked(choice: Any) -> bool | None:
    """Best-effort extraction of Choice.checked across questionary versions."""

    # questionary.Choice is usually a dataclass-like object with .checked.
    for attr in ("checked", "_checked"):
        if hasattr(choice, attr):
            return bool(getattr(choice, attr))
    return None


def _choice_title(choice: Any) -> str:
    for attr in ("title", "name"):
        if hasattr(choice, attr):
            return str(getattr(choice, attr))
    return str(choice)


def _choice_value(choice: Any) -> Any:
    for attr in ("value",):
        if hasattr(choice, attr):
            return getattr(choice, attr)
    return choice


# -------------------------
# Tests
# -------------------------


class TestTrackChecker(unittest.TestCase):
    def test_existing_track_keys_respects_extensions(self):
        from utils.track_checker import existing_track_keys_in_dir

        base_dir = os.path.join("music", "Electro")
        self.assertTrue(os.path.isdir(base_dir), f"Expected dir to exist: {base_dir}")

        keys = existing_track_keys_in_dir(base_dir)

        # Should include valid audio extensions
        self.assertIn(
            "tritonal, dylan matthew, au5|happy where we are",
            keys,
        )
        self.assertIn(
            "selena gomez, marshmello|wolves",
            keys,
        )

        # Should NOT include invalid extension entries
        self.assertNotIn("not audio|ignore", keys)


class TestSongSelectionMenu(unittest.TestCase):
    def test_menu_builds_choices_and_auto_unchecks_existing(self):
        import menus.song_selection_menu as ssm

        # Tracks include two that exist (we created dummy files) and one that does not.
        tracks = [
            {"artist": "Tritonal, Dylan Matthew, Au5", "track": "Happy Where We Are"},
            {"artist": "Selena Gomez, Marshmello", "track": "Wolves"},
            {"artist": "David Guetta, Brooks, Loote", "track": "Better When You're Gone"},
        ]

        q = _QuestionaryMock()
        # Return a non-empty selection to exit the loop.
        q.queue(["david guetta, brooks, loote|better when you're gone"])

        with _PatchModuleAttr(ssm, "questionary", q):
            selected = ssm.select_songs_for_playlist(
                playlist_name="Electro",
                tracks=tracks,
                playlist_dir=os.path.join("music", "Electro"),
            )

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["track"], "Better When You're Gone")

        # Verify the menu lists only the individual songs (no action rows).
        titles = [_choice_title(c) for c in q.last_checkbox_choices]
        self.assertTrue(any("Happy Where We Are" in t for t in titles))
        self.assertTrue(any("Wolves" in t for t in titles))
        self.assertTrue(any("Better When You're Gone" in t for t in titles))
        self.assertFalse(any("Select All" in t for t in titles))
        self.assertFalse(any("Deselect All" in t for t in titles))

        # Verify existing songs are shown as "(exists)" and start unchecked.
        # Note: (exists) is appended to the title, not to the stored value.
        exists_titles = [t for t in titles if "(exists)" in t]
        self.assertGreaterEqual(len(exists_titles), 2)

        # checked state should be False for existing tracks and True for non-existing.
        checked_map = {_choice_value(c): _choice_checked(c) for c in q.last_checkbox_choices}
        self.assertFalse(checked_map.get("tritonal, dylan matthew, au5|happy where we are"))
        self.assertFalse(checked_map.get("selena gomez, marshmello|wolves"))
        self.assertTrue(checked_map.get("david guetta, brooks, loote|better when you're gone"))


class TestDownloadsMenuIntegration(unittest.TestCase):
    def test_exportify_flow_calls_song_picker_and_uses_playlist_folder(self):
        import menus.downloads_menu as dm

        q = _QuestionaryMock()
        # downloads_menu main selection
        q.queue(
            "Download from Exportify CSV folder",
            # playlist checkbox selection
            ["Electro"],
            # confirm download
            True,
        )

        calls = {"picker": [], "download": []}

        def fake_picker(playlist_name: str, tracks: list, playlist_dir: str) -> list:
            calls["picker"].append((playlist_name, len(tracks), playlist_dir))
            # Return only one track to avoid long run
            return tracks[:1]

        async def fake_download_playlist(playlist_name, tracks, output_dir, audio_format, sleep_between):
            calls["download"].append((playlist_name, len(tracks), output_dir, audio_format, sleep_between))

        with (
            _PatchModuleAttr(dm, "questionary", q),
            _PatchModuleAttr(dm, "select_songs_for_playlist", fake_picker),
            _PatchModuleAttr(dm, "download_playlist", fake_download_playlist),
        ):
            dm.downloads_menu(
                {
                    "output_dir": "music",
                    "audio_format": "mp3",
                    "sleep_between": 0,
                    "exportify_watch_folder": "data/exportify",
                    "playlists_file": "data/playlists.json",
                    "tracks_file": "data/tracks.json",
                    "primary_input_source": "csv",
                    "primary_csv_file": "../_WORKING/Electro.csv",
                }
            )

        self.assertEqual(len(calls["picker"]), 1)
        pl_name, track_count, pl_dir = calls["picker"][0]
        self.assertEqual(pl_name, "Electro")
        self.assertTrue(pl_dir.endswith(os.path.join("music", "Electro")))
        self.assertGreater(track_count, 0)

        self.assertEqual(len(calls["download"]), 1)
        dl_name, dl_count, out_dir, fmt, sleep = calls["download"][0]
        self.assertEqual(dl_name, "Electro")
        self.assertEqual(out_dir, "music")
        self.assertEqual(fmt, "mp3")
        self.assertEqual(sleep, 0)
        self.assertEqual(dl_count, 1)

    def test_legacy_flow_calls_song_picker_and_uses_playlist_folder(self):
        import menus.downloads_menu as dm

        q = _QuestionaryMock()
        q.queue(
            "Download from playlists file (legacy Spotify export)",
            "Pick which playlists to download",
            ["Simon vol.93"],
            True,
        )

        calls = {"picker": [], "download": []}

        def fake_picker(playlist_name: str, tracks: list, playlist_dir: str) -> list:
            calls["picker"].append((playlist_name, len(tracks), playlist_dir))
            return tracks[:2]

        async def fake_download_playlist(playlist_name, tracks, output_dir, audio_format, sleep_between):
            calls["download"].append((playlist_name, len(tracks), output_dir, audio_format, sleep_between))

        with (
            _PatchModuleAttr(dm, "questionary", q),
            _PatchModuleAttr(dm, "select_songs_for_playlist", fake_picker),
            _PatchModuleAttr(dm, "download_playlist", fake_download_playlist),
        ):
            dm.downloads_menu(
                {
                    "output_dir": "music",
                    "audio_format": "mp3",
                    "sleep_between": 0,
                    "exportify_watch_folder": "data/exportify",
                    "playlists_file": "data/playlists.json",
                    "tracks_file": "data/tracks.json",
                    "primary_input_source": "csv",
                    "primary_csv_file": "../_WORKING/Electro.csv",
                }
            )

        self.assertEqual(len(calls["picker"]), 1)
        pl_name, track_count, pl_dir = calls["picker"][0]
        self.assertEqual(pl_name, "Simon vol.93")
        self.assertTrue(pl_dir.endswith(os.path.join("music", "Simon vol.93")))
        self.assertGreater(track_count, 0)

        self.assertEqual(len(calls["download"]), 1)
        dl_name, dl_count, out_dir, fmt, sleep = calls["download"][0]
        self.assertEqual(dl_name, "Simon vol.93")
        self.assertEqual(out_dir, "music")
        self.assertEqual(fmt, "mp3")
        self.assertEqual(sleep, 0)
        self.assertEqual(dl_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
