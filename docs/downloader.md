# Downloader Module Documentation

The `downloader/` folder contains all core downloading functionality. It handles downloading music from YouTube using yt-dlp, managing playlists, embedding metadata, and retrying failed downloads.

## Folder Overview

This module is the heart of the application's download functionality. It provides:
- Single and batch track downloads
- Playlist downloading with folder organization
- Direct YouTube link/playlist downloads
- Metadata embedding for downloaded files
- Retry mechanisms for failed downloads

---

## Files

### `base_downloader.py`
**Purpose**: Core download functions for single tracks and batch downloads using yt-dlp.

**How it works**:

1. **`download_track(artist, track, output_dir, audio_format, sleep_between)`**:
   - Constructs a YouTube search query: `"{artist} - {track}"`
   - Sanitizes filename by replacing "/" with "-"
   - Executes yt-dlp command with `ytsearch1:` prefix to search YouTube
   - Uses `-x` flag to extract audio only
   - Formats output filename with `%(ext)s` placeholder
   - Waits for process completion and logs success/failure
   - Sleeps between downloads to avoid rate limiting

2. **`_download_worker(artist, track, output_dir, audio_format)`**:
   - Internal worker function for batch downloads
   - Similar to `download_track` but runs quietly (`--quiet` flag)
   - Used by async batch downloader

3. **`batch_download(tracks, output_dir, audio_format, max_workers=4)`**:
   - Async batch downloader using `asyncio` and `ThreadPoolExecutor`
   - Processes multiple tracks concurrently (default: 4 workers)
   - Uses `tqdm` for progress bar display
   - Creates tasks for each track and executes them in parallel
   - Updates progress bar as each download completes

**Key Features**:
- YouTube search integration via yt-dlp
- Concurrent batch downloads for efficiency
- Progress tracking with tqdm
- Error handling and logging

**Dependencies**:
- `os`, `subprocess`, `time`, `asyncio`, `concurrent.futures`
- `tqdm` - Progress bars
- `utils.logger` - Logging functions

**Usage**: Imported by menu handlers and other download modules.

---

### `playlist_download.py`
**Purpose**: Downloads entire playlists, organizing tracks into playlist-specific folders.

**How it works**:

1. **`download_playlist(playlist_name, tracks, output_dir, audio_format, sleep_between)`**:
   - Sanitizes playlist name (replaces "/" with "-")
   - Creates a dedicated folder for the playlist: `{output_dir}/{playlist_name}/`
   - Formats tracks into the structure expected by `batch_download`
   - Calls `batch_download` to download all tracks concurrently
   - Logs progress and completion

**Key Features**:
- Automatic folder creation per playlist
- Batch processing of playlist tracks
- Name sanitization for filesystem compatibility

**Dependencies**:
- `os`, `json`
- `utils.logger` - Logging
- `downloader.base_downloader.batch_download` - Core download function

**Usage**: Called from `menus.downloads_menu` when downloading playlists.

---

### `metadata.py`
**Purpose**: Embeds metadata (artist, title, album art) into downloaded MP3 files.

**How it works**:

1. **`embed_metadata(output_dir)`**:
   - Recursively walks through the output directory
   - Processes only `.mp3` files
   - Parses filename format: `"Artist - Title.mp3"`
   - Uses `mutagen` library to:
     - Create or update ID3 tags
     - Set artist and title metadata
     - Optionally embed album art if a matching `.jpg` file exists
   - Handles files that don't have existing ID3 tags
   - Logs success/failure for each file

**Key Features**:
- Automatic metadata extraction from filenames
- ID3 tag creation and updating
- Optional album art embedding
- Error handling for malformed filenames

**Dependencies**:
- `os`
- `mutagen.easyid3` - Easy ID3 tag manipulation
- `mutagen.id3` - Advanced ID3 operations (for album art)
- `utils.logger` - Logging

**Usage**: Called from `menus.management_menu` to add metadata to downloaded files.

---

### `retry_manager.py`
**Purpose**: Retries downloads that previously failed.

**How it works**:

1. **`retry_failed(config)`**:
   - Checks if `data/failed_downloads.json` exists
   - Loads the list of failed tracks
   - Handles empty or corrupted JSON files gracefully
   - Iterates through failed tracks and attempts download again
   - Uses `download_track` from `base_downloader`
   - Tracks which tracks still fail after retry
   - Updates `failed_downloads.json` with remaining failures

**Key Features**:
- Graceful handling of missing/corrupted files
- Tracks persistent failures
- Updates failure list after retry attempts

**Dependencies**:
- `os`, `json`
- `downloader.base_downloader.download_track` - Core download function
- `utils.logger` - Logging
- `constants.FAILED_FILE` - Path to failed downloads file

**Usage**: Called from `menus.management_menu` to retry failed downloads.

---

### `youtube_link_downloader.py`
**Purpose**: Downloads music directly from YouTube URLs (single videos or playlists).

**How it works**:

1. **`get_youtube_info(url)`**:
   - Uses yt-dlp with `-j` and `--flat-playlist` flags to fetch metadata
   - Returns JSON data containing video/playlist information
   - Handles both single videos and playlists
   - Returns `None` on failure

2. **`download_from_link(url, output_dir, audio_format)`**:
   - Fetches video metadata using `get_youtube_info`
   - Displays video title to user for confirmation
   - Uses `questionary.confirm` for user approval
   - Downloads single video as audio using yt-dlp
   - Outputs file with original title from YouTube

3. **`download_from_playlist(url, output_dir, audio_format, sleep_between)`**:
   - Fetches playlist metadata
   - Displays playlist name and preview of tracks (first 10)
   - Shows total track count
   - Requests user confirmation before downloading
   - Downloads entire playlist using yt-dlp
   - All videos saved to output directory

**Key Features**:
- Direct YouTube URL support
- User confirmation before downloading
- Playlist preview and confirmation
- Automatic title extraction

**Dependencies**:
- `os`, `subprocess`, `json`
- `questionary` - Interactive prompts
- `utils.logger` - Logging

**Usage**: Called from `menus.downloads_menu` when user selects "Download from YouTube link/playlist".

---

### `__init__.py`
**Purpose**: Makes the downloader folder a Python package.

**How it works**: Empty or contains package-level imports/exports.

**Usage**: Allows importing modules from the downloader package.

