import os
import json
import time
from downloader.base_downloader import download_track
from utils.logger import log_info, log_error, log_warning
from constants import FAILED_FILE


def retry_failed(config):
    """
    Retry failed downloads using configurable retry rules from config.
    
    Config options used:
    - retry_attempts: Maximum number of retry attempts per track
    - retry_delay: Base delay between retries (uses exponential backoff)
    - auto_backup: Whether to backup before modifying failed_downloads.json
    """
    if not os.path.exists(FAILED_FILE):
        log_info("No failed downloads to retry.")
        return

    # Get retry configuration
    max_attempts = config.get("retry_attempts", 3)
    base_delay = config.get("retry_delay", 5)
    auto_backup = config.get("auto_backup", True)
    
    if max_attempts == 0:
        log_info("Retry is disabled (retry_attempts=0).")
        return

    try:
        with open(FAILED_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                log_info("No failed downloads.")
                return
            failed_tracks = json.loads(content)
    except json.JSONDecodeError:
        log_error("Failed downloads file is corrupted or invalid JSON.")
        return

    if not failed_tracks:
        log_info("No failed downloads.")
        return

    # Auto-backup before modifying
    if auto_backup:
        try:
            from managers.backup_manager import backup_json_file
            backup_json_file(FAILED_FILE)
        except ImportError:
            pass  # Backup manager not yet available

    log_info(f"Retrying {len(failed_tracks)} failed downloads (max {max_attempts} attempts each)...")
    still_failed = []

    for t in failed_tracks:
        track_attempts = t.get("attempt_count", 0)
        
        if track_attempts >= max_attempts:
            log_warning(f"Skipping {t['artist']} - {t['track']} (exceeded max attempts: {track_attempts})")
            still_failed.append(t)
            continue
        
        success = False
        
        for attempt in range(1, max_attempts - track_attempts + 1):
            # Exponential backoff delay
            delay = base_delay * (2 ** (attempt - 1))
            
            log_info(f"Retry attempt {attempt}/{max_attempts - track_attempts} for: {t['artist']} - {t['track']}")
            
            try:
                download_track(
                    t["artist"], 
                    t["track"], 
                    config["output_dir"], 
                    config["audio_format"], 
                    config["sleep_between"]
                )
                success = True
                log_info(f"Successfully downloaded on retry: {t['artist']} - {t['track']}")
                break
            except Exception as e:
                log_error(f"Retry attempt {attempt} failed: {t['artist']} - {t['track']} - {e}")
                
                if attempt < max_attempts - track_attempts:
                    log_info(f"Waiting {delay}s before next attempt...")
                    time.sleep(delay)
        
        if not success:
            # Update attempt count
            t["attempt_count"] = t.get("attempt_count", 0) + (max_attempts - track_attempts)
            still_failed.append(t)

    # Save remaining failed tracks
    with open(FAILED_FILE, "w", encoding="utf-8") as f:
        json.dump(still_failed, f, indent=2)
    
    # Summary
    retried_count = len(failed_tracks) - len(still_failed)
    log_info(f"Retry complete: {retried_count} succeeded, {len(still_failed)} still failed.")


def add_failed_track(artist: str, track: str, error: str = None, config: dict = None):
    """
    Add a track to the failed downloads list with retry tracking.
    """
    failed_tracks = []
    
    if os.path.exists(FAILED_FILE):
        try:
            with open(FAILED_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    failed_tracks = json.loads(content)
        except (json.JSONDecodeError, IOError):
            failed_tracks = []
    
    # Check if track already exists
    for t in failed_tracks:
        if t["artist"] == artist and t["track"] == track:
            t["attempt_count"] = t.get("attempt_count", 0) + 1
            t["last_error"] = error
            break
    else:
        failed_tracks.append({
            "artist": artist,
            "track": track,
            "attempt_count": 1,
            "last_error": error
        })
    
    # Auto-backup before modifying
    if config and config.get("auto_backup", True):
        try:
            from managers.backup_manager import backup_json_file
            backup_json_file(FAILED_FILE)
        except ImportError:
            pass
    
    with open(FAILED_FILE, "w", encoding="utf-8") as f:
        json.dump(failed_tracks, f, indent=2)


def clear_failed_tracks():
    """Clear all failed tracks from the list."""
    if os.path.exists(FAILED_FILE):
        with open(FAILED_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        log_info("Cleared failed downloads list.")


def get_failed_count() -> int:
    """Get the count of failed downloads."""
    if not os.path.exists(FAILED_FILE):
        return 0
    
    try:
        with open(FAILED_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return 0
            return len(json.loads(content))
    except (json.JSONDecodeError, IOError):
        return 0
