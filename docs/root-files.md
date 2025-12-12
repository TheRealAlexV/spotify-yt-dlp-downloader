# Root Files Documentation

This document describes the main entry points and configuration files at the root of the project.

## Files Overview

### `main.py`

**Purpose**: The main entry point of the application. Initializes logging, loads configuration, and manages the main menu loop.

**How it works**:

1. Sets up logging using `setup_logging()` from `utils.logger`
2. Loads configuration from `config.json` using `load_config()`
3. Creates the output directory if it doesn't exist
4. Runs startup sync if `auto_sync_enabled` is true in config
5. Runs an infinite loop that displays the main menu and routes to sub-menus based on user selection
6. Handles menu navigation between Downloads, Management, Automation, Tools, and Config menus
7. Updates config object when Config Menu returns modified configuration

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

**Purpose**: Comprehensive configuration management system with validation, profiles, and automated settings.

**How it works**:

1. **Configuration Loading**:

   - `load_config()` loads configuration from `config.json`
   - Automatically applies default values for missing fields
   - Raises `FileNotFoundError` if config file doesn't exist

2. **Configuration Validation**:

   - `validate_config()` validates configuration against `CONFIG_SCHEMA`
   - Checks required fields, data types, value ranges, and valid choices
   - Returns validation status and list of errors

3. **Configuration Profiles**:

   - Pre-defined profiles: `light`, `advanced`, `minimal`
   - Each profile sets multiple related settings at once
   - `apply_config_profile()` applies a profile and updates config file
   - `list_profiles()` returns all available profiles and their settings

4. **Configuration Updates**:

   - `update_config()` updates a single setting with validation
   - Validates the change before saving
   - Returns success status and message

5. **Default Configuration**:
   - `DEFAULT_CONFIG` defines all default values
   - `reset_to_defaults()` resets entire configuration to defaults

**Key Functions**:

- `load_config()` - Loads configuration from JSON file with defaults
- `save_config()` - Saves configuration to JSON file
- `validate_config()` - Validates configuration against schema
- `update_config()` - Updates a single config field with validation
- `apply_config_profile()` - Applies a configuration profile
- `list_profiles()` - Returns all available profiles
- `get_profile_info()` - Gets settings for a specific profile
- `reset_to_defaults()` - Resets configuration to defaults
- `get_config_value()` - Gets a single config value with optional default

**Dependencies**:

- `json` - JSON parsing
- `os` - File existence checking
- `typing` - Type hints

**Configuration Schema** (`CONFIG_SCHEMA`):
The schema defines validation rules for each configuration field:

- **Type checking**: Validates data types (str, int, float, bool)
- **Required fields**: Marks fields that must be present
- **Choices**: Restricts values to a predefined list
- **Range validation**: Min/max values for numeric fields

**Configuration Profiles** (`CONFIG_PROFILES`):

- **light**: Minimal retries (1 attempt), quick delays (3s), basic backup (5 max)
- **advanced**: Maximum retries (5 attempts), longer delays (10s), extensive backup (20 max)
- **minimal**: No retries, no backups, fastest settings (2s delay)

**Default Configuration Structure**:

```json
{
	"tracks_file": "data/tracks.json",
	"playlists_file": "data/playlists.json",
	"output_dir": "music",
	"audio_format": "mp3",
	"sleep_between": 5,
	"average_download_time": 20,
	"retry_attempts": 3,
	"retry_delay": 5,
	"auto_cleanup": false,
	"auto_backup": true,
	"max_backups": 10,
	"profile": "light",
	"exportify_watch_folder": "data/exportify",
	"auto_sync_enabled": false,
	"auto_sync_interval": 3600
}
```

**Configuration Fields**:

- **File Paths**:

  - `tracks_file`: Path to tracks JSON file
  - `playlists_file`: Path to playlists JSON file
  - `output_dir`: Directory where downloaded music is saved
  - `exportify_watch_folder`: Folder to watch for Exportify CSV files

- **Download Settings**:

  - `audio_format`: Default audio format (mp3, wav, flac, aac, ogg, m4a)
  - `sleep_between`: Seconds to wait between downloads (0-60)
  - `average_download_time`: Estimated average download time per track (1-300 seconds)

- **Retry Settings**:

  - `retry_attempts`: Number of retry attempts for failed downloads (0-10)
  - `retry_delay`: Seconds to wait between retry attempts (0-60)

- **Automation Settings**:

  - `auto_cleanup`: Automatically clean up after downloads (boolean)
  - `auto_backup`: Automatically backup JSON files (boolean)
  - `max_backups`: Maximum number of backups to keep (0-100)
  - `auto_sync_enabled`: Enable automatic Exportify folder sync (boolean)
  - `auto_sync_interval`: Interval between sync checks in seconds (60-86400)

- **Profile**:
  - `profile`: Current configuration profile name (light, advanced, minimal)

**Usage**: Imported by `main.py`, `menus/config_menu.py`, and other modules that need configuration.

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

- JSON file read and written by `config.py`
- Contains all application settings including file paths, download preferences, retry settings, and automation features
- Automatically validated against schema when loaded or updated
- Missing fields are filled with default values from `DEFAULT_CONFIG`

**Configuration Options**:

**File Paths**:

- `tracks_file`: Path to the tracks JSON file (default: "data/tracks.json")
- `playlists_file`: Path to the playlists JSON file (default: "data/playlists.json")
- `output_dir`: Directory where downloaded music is saved (default: "music")
- `exportify_watch_folder`: Folder to watch for Exportify CSV files (default: "data/exportify")

**Download Settings**:

- `audio_format`: Default audio format - one of: mp3, wav, flac, aac, ogg, m4a (default: "mp3")
- `sleep_between`: Seconds to wait between downloads for rate limiting (0-60, default: 5)
- `average_download_time`: Estimated average download time per track in seconds (1-300, default: 20)

**Retry Settings**:

- `retry_attempts`: Number of retry attempts for failed downloads (0-10, default: 3)
- `retry_delay`: Seconds to wait between retry attempts (0-60, default: 5)

**Automation Settings**:

- `auto_cleanup`: Automatically clean up after downloads (default: false)
- `auto_backup`: Automatically backup JSON files (default: true)
- `max_backups`: Maximum number of backups to keep (0-100, default: 10)
- `auto_sync_enabled`: Enable automatic Exportify folder sync (default: false)
- `auto_sync_interval`: Interval between sync checks in seconds (60-86400, default: 3600)

**Profile**:

- `profile`: Current configuration profile name - one of: light, advanced, minimal (default: "light")

**Usage**:

- Modified by users to customize application behavior
- Updated programmatically by `config.py` functions and tools (e.g., `choose_audio_format.py`)
- Can be managed through the Config Menu (see `menus/config_menu.py`)
- Automatically validated when loaded or updated

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
