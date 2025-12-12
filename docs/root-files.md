# Root Files Documentation

This document describes the main entry points and configuration files at the root of the project.

## Files Overview

### `main.py`
**Purpose**: The main entry point of the application. Initializes logging, loads configuration, and manages the main menu loop.

**How it works**:
1. Sets up logging using `setup_logging()` from `utils.logger`
2. Loads configuration from `config.json` using `load_config()`
3. Creates the output directory if it doesn't exist
4. Runs an infinite loop that displays the main menu and routes to sub-menus based on user selection
5. Handles menu navigation between Downloads, Management, Automation, and Tools menus

**Key Functions**:
- Main execution loop that processes user menu choices
- Routes to appropriate menu handlers based on selection

**Dependencies**:
- `config.py` - Configuration loading
- `utils.logger` - Logging setup
- All menu modules from `menus/`

**Usage**: Run `python main.py` to start the application.

---

### `config.py`
**Purpose**: Loads and parses the `config.json` configuration file.

**How it works**:
1. Defines the path to `config.json` as a constant
2. `load_config()` function:
   - Checks if the config file exists
   - Raises `FileNotFoundError` if missing
   - Reads and parses JSON configuration
   - Returns the configuration dictionary

**Key Functions**:
- `load_config()` - Loads configuration from JSON file

**Dependencies**:
- `json` - JSON parsing
- `os` - File existence checking

**Configuration Structure**:
```json
{
  "tracks_file": "data/tracks.json",
  "playlists_file": "data/playlists.json",
  "output_dir": "music",
  "audio_format": "mp3",
  "sleep_between": 5,
  "average_download_time": 20
}
```

**Usage**: Imported by `main.py` and other modules that need configuration.

---

### `constants.py`
**Purpose**: Defines application-wide constants including dependencies, audio formats, bitrate options, and file paths.

**How it works**:
- Contains lists and dictionaries of constants used throughout the application
- No functions, just constant definitions

**Key Constants**:
- `PYTHON_DEPENDENCIES` - List of required Python packages
- `SYSTEM_DEPENDENCIES` - List of required system binaries (e.g., ffmpeg)
- `VALID_AUDIO_EXTENSIONS` - Set of supported audio file extensions
- `AUDIO_BITRATE_OPTIONS` - Dictionary mapping bitrates to quality descriptions
- `FAILED_FILE` - Path to failed downloads JSON file
- `PROGRESS_FILE` - Path to download progress JSON file
- `LOG_FILE` - Path to application log file

**Dependencies**: None (pure constants)

**Usage**: Imported by modules that need to reference these constants (e.g., `utils.logger`, `tools.dependency_check`).

---

### `config.json`
**Purpose**: User-configurable settings file that controls application behavior.

**How it works**:
- JSON file read by `config.py`
- Contains paths to data files, output directory, audio format preferences, and timing settings

**Configuration Options**:
- `tracks_file`: Path to the tracks JSON file
- `playlists_file`: Path to the playlists JSON file
- `output_dir`: Directory where downloaded music is saved
- `audio_format`: Default audio format (mp3, wav, flac, etc.)
- `sleep_between`: Seconds to wait between downloads (rate limiting)
- `average_download_time`: Estimated average download time per track (for progress estimation)

**Usage**: Modified by users to customize application behavior. Also updated programmatically by some tools (e.g., `choose_audio_format.py`).

---

### `requirements.txt`
**Purpose**: Lists all Python package dependencies required for the application.

**How it works**:
- Standard Python requirements file format
- Used by `pip install -r requirements.txt` to install dependencies

**Usage**: Install dependencies with `pip install -r requirements.txt`.

---

### `readme.md`
**Purpose**: Main project documentation and user guide.

**How it works**:
- Contains project overview, features, installation instructions, usage examples, and configuration details
- Includes screenshots, project structure, and dependency information

**Usage**: Read by users to understand and use the application.

---

### `changelog.md`
**Purpose**: Tracks version history and changes made to the application.

**Usage**: Documents updates, bug fixes, and new features over time.

---

### `todo.md`
**Purpose**: Development notes and planned features.

**Usage**: Tracks development tasks and ideas for future improvements.

