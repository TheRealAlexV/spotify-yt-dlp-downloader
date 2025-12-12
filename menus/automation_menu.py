import questionary
from managers.resume_manager import resume_batch
from managers.schedule_manager import schedule_download
from managers.sync_manager import run_sync_once, get_sync_status, schedule_sync, clear_sync_state
from managers.backup_manager import backup_all, list_backups, get_backup_stats
from managers.cleanup_manager import cleanup_after_download, get_cleanup_preview
from utils.logger import log_info, log_success, log_error


def automation_menu(config):
    """
    Displays the Automation Menu and runs automation tasks.
    """
    while True:
        choice = questionary.select(
            "🤖 Automation Menu — Choose an option:",
            choices=[
                "Resume paused batch download",
                "Schedule a download job",
                "Sync exportify folder now",
                "Schedule automatic sync",
                "Run cleanup",
                "Backup all data files",
                "View backup status",
                "Clear sync state (force re-sync)",
                "Back"
            ]
        ).ask()

        if choice == "Resume paused batch download":
            resume_batch(config)

        elif choice == "Schedule a download job":
            schedule_download(config)

        elif choice == "Sync exportify folder now":
            sync_now(config)

        elif choice == "Schedule automatic sync":
            schedule_sync_menu(config)

        elif choice == "Run cleanup":
            run_cleanup_menu(config)

        elif choice == "Backup all data files":
            backup_now(config)

        elif choice == "View backup status":
            view_backup_status()

        elif choice == "Clear sync state (force re-sync)":
            clear_sync_menu()

        elif choice == "Back":
            break


def sync_now(config):
    """Run a sync operation immediately."""
    log_info("Starting sync...")
    
    # Show current status first
    status = get_sync_status(config)
    if status["pending_count"] == 0:
        log_info("No new files to sync")
        return
    
    log_info(f"Found {status['pending_count']} file(s) to sync: {', '.join(status['pending_files'])}")
    
    confirm = questionary.confirm("Proceed with sync?", default=True).ask()
    if not confirm:
        return
    
    results = run_sync_once(config)
    
    if results.get("new_tracks", 0) > 0:
        log_success(f"Sync complete: {results['new_tracks']} new tracks added")
    else:
        log_info("Sync complete: no new tracks added")
    
    if results.get("errors"):
        log_error(f"Errors during sync: {len(results['errors'])}")
        for error in results["errors"]:
            log_error(f"  - {error}")


def schedule_sync_menu(config):
    """Start the scheduled sync process."""
    status = get_sync_status(config)
    
    print(f"\nCurrent sync interval: {status['sync_interval']} seconds")
    print(f"Auto-sync enabled: {'Yes' if status['auto_sync_enabled'] else 'No'}")
    print(f"Last sync: {status['last_sync'] or 'Never'}")
    
    confirm = questionary.confirm(
        f"Start scheduled sync (every {status['sync_interval']}s)? This will run until you press Ctrl+C.",
        default=False
    ).ask()
    
    if confirm:
        log_info("Starting scheduled sync... Press Ctrl+C to stop.")
        try:
            schedule_sync(config)
        except KeyboardInterrupt:
            log_info("Scheduled sync stopped")


def run_cleanup_menu(config):
    """Run cleanup with preview option."""
    # Show preview first
    preview = get_cleanup_preview(config)
    
    total_items = (
        len(preview["temp_files"]) + 
        len(preview["empty_dirs"]) + 
        len(preview["partial_files"])
    )
    
    if total_items == 0:
        log_info("Nothing to clean up!")
        return
    
    print("\n📋 Cleanup Preview:")
    
    if preview["temp_files"]:
        print(f"\nTemp files to remove ({len(preview['temp_files'])}):")
        for f in preview["temp_files"][:5]:
            print(f"  - {f}")
        if len(preview["temp_files"]) > 5:
            print(f"  ... and {len(preview['temp_files']) - 5} more")
    
    if preview["empty_dirs"]:
        print(f"\nEmpty directories to remove ({len(preview['empty_dirs'])}):")
        for d in preview["empty_dirs"][:5]:
            print(f"  - {d}")
        if len(preview["empty_dirs"]) > 5:
            print(f"  ... and {len(preview['empty_dirs']) - 5} more")
    
    if preview["partial_files"]:
        print(f"\nPartial/corrupted files to remove ({len(preview['partial_files'])}):")
        for f in preview["partial_files"][:5]:
            print(f"  - {f}")
        if len(preview["partial_files"]) > 5:
            print(f"  ... and {len(preview['partial_files']) - 5} more")
    
    print()
    
    confirm = questionary.confirm(
        f"Remove {total_items} item(s)?",
        default=True
    ).ask()
    
    if confirm:
        results = cleanup_after_download(config)
        total_removed = (
            results.get("temp_files_removed", 0) +
            results.get("empty_dirs_removed", 0) +
            results.get("partial_files_removed", 0)
        )
        log_success(f"Cleanup complete: removed {total_removed} items")


def backup_now(config):
    """Run backup of all data files."""
    confirm = questionary.confirm("Backup all data files now?", default=True).ask()
    
    if confirm:
        results = backup_all(config)
        
        if results.get("skipped"):
            log_info(f"Backup skipped: {results['reason']}")
            return
        
        successful = sum(1 for v in results.values() if v not in ["failed", "not_found"])
        log_success(f"Backup complete: {successful} file(s) backed up")


def view_backup_status():
    """Display backup statistics."""
    stats = get_backup_stats()
    
    print("\n" + "=" * 50)
    print("📦 Backup Status")
    print("=" * 50)
    
    print(f"\nTotal backups: {stats['total_backups']}")
    print(f"Total size: {stats['total_size'] / 1024:.1f} KB")
    
    if stats['newest']:
        print(f"Newest backup: {stats['newest']}")
    if stats['oldest']:
        print(f"Oldest backup: {stats['oldest']}")
    
    if stats['by_file']:
        print("\nBackups by file:")
        for filename, info in stats['by_file'].items():
            print(f"  {filename}: {info['count']} backups ({info['size'] / 1024:.1f} KB)")
    
    # Show recent backups
    backups = list_backups()
    if backups:
        print("\nRecent backups:")
        for backup in backups[:5]:
            print(f"  - {backup['filename']} ({backup['size'] / 1024:.1f} KB)")
    
    print("\n" + "=" * 50)
    input("\nPress Enter to continue...")


def clear_sync_menu():
    """Clear sync state to force re-sync of all files."""
    confirm = questionary.confirm(
        "Clear sync state? This will cause all exportify files to be re-synced on next run.",
        default=False
    ).ask()
    
    if confirm:
        clear_sync_state()
        log_success("Sync state cleared")
