import questionary
from config import (
    load_config, save_config, validate_config, update_config,
    apply_config_profile, list_profiles, get_profile_info, reset_to_defaults,
    CONFIG_SCHEMA
)
from utils.logger import log_info, log_error, log_success


def config_menu(config: dict) -> dict:
    """
    Display the configuration menu and handle user selections.
    Returns the potentially updated config dict.
    """
    while True:
        choice = questionary.select(
            "⚙️ Config Menu — What would you like to do?",
            choices=[
                "View current config",
                "Update a setting",
                "Switch config profile",
                "Toggle automation features",
                "Reset to defaults",
                "Validate configuration",
                "Back"
            ]
        ).ask()
        
        if choice == "View current config":
            view_config(config)
        
        elif choice == "Update a setting":
            config = update_setting_menu(config)
        
        elif choice == "Switch config profile":
            config = switch_profile_menu(config)
        
        elif choice == "Toggle automation features":
            config = toggle_automation_menu(config)
        
        elif choice == "Reset to defaults":
            config = reset_config_menu(config)
        
        elif choice == "Validate configuration":
            validate_config_menu(config)
        
        elif choice == "Back":
            break
    
    return config


def view_config(config: dict):
    """Display the current configuration in a readable format."""
    print("\n" + "=" * 50)
    print("📋 Current Configuration")
    print("=" * 50)
    
    # Group settings by category
    categories = {
        "File Paths": ["tracks_file", "playlists_file", "output_dir", "exportify_watch_folder"],
        "Download Settings": ["audio_format", "sleep_between", "average_download_time"],
        "Retry Settings": ["retry_attempts", "retry_delay"],
        "Automation": ["auto_cleanup", "auto_backup", "max_backups", "auto_sync_enabled", "auto_sync_interval"],
        "Profile": ["profile"]
    }
    
    for category, keys in categories.items():
        print(f"\n{category}:")
        for key in keys:
            if key in config:
                value = config[key]
                # Format boolean values
                if isinstance(value, bool):
                    value = "✓ Enabled" if value else "✗ Disabled"
                print(f"  {key}: {value}")
    
    print("\n" + "=" * 50)
    input("\nPress Enter to continue...")


def update_setting_menu(config: dict) -> dict:
    """Menu to update individual settings."""
    # Get list of editable settings
    editable_keys = list(CONFIG_SCHEMA.keys())
    editable_keys.append("Back")
    
    key = questionary.select(
        "Select setting to update:",
        choices=editable_keys
    ).ask()
    
    if key == "Back":
        return config
    
    schema = CONFIG_SCHEMA.get(key, {})
    current_value = config.get(key, "Not set")
    
    print(f"\nCurrent value: {current_value}")
    
    # Handle different types of inputs
    if "choices" in schema:
        new_value = questionary.select(
            f"Select new value for {key}:",
            choices=schema["choices"]
        ).ask()
    
    elif schema.get("type") == bool:
        new_value = questionary.confirm(
            f"Enable {key}?",
            default=current_value if isinstance(current_value, bool) else True
        ).ask()
    
    elif schema.get("type") in [int, (int, float)]:
        min_val = schema.get("min", 0)
        max_val = schema.get("max", 9999)
        new_value_str = questionary.text(
            f"Enter new value for {key} ({min_val}-{max_val}):",
            default=str(current_value) if current_value != "Not set" else ""
        ).ask()
        
        try:
            if schema.get("type") == int:
                new_value = int(new_value_str)
            else:
                new_value = float(new_value_str)
        except ValueError:
            log_error("Invalid number format")
            return config
    
    else:
        new_value = questionary.text(
            f"Enter new value for {key}:",
            default=str(current_value) if current_value != "Not set" else ""
        ).ask()
    
    # Update the config
    success, message = update_config(key, new_value)
    
    if success:
        log_success(message)
        config[key] = new_value
    else:
        log_error(message)
    
    return config


def switch_profile_menu(config: dict) -> dict:
    """Menu to switch between configuration profiles."""
    profiles = list_profiles()
    
    print("\n📋 Available Profiles:\n")
    
    for name, settings in profiles.items():
        current = " (current)" if config.get("profile") == name else ""
        print(f"  {name}{current}:")
        for key, value in settings.items():
            print(f"    - {key}: {value}")
        print()
    
    profile_choices = list(profiles.keys()) + ["Back"]
    
    choice = questionary.select(
        "Select profile to apply:",
        choices=profile_choices
    ).ask()
    
    if choice == "Back":
        return config
    
    # Confirm profile switch
    confirm = questionary.confirm(
        f"Apply '{choice}' profile? This will update several settings.",
        default=True
    ).ask()
    
    if confirm:
        success, message = apply_config_profile(choice)
        
        if success:
            log_success(message)
            # Reload config to get updated values
            config = load_config()
        else:
            log_error(message)
    
    return config


def toggle_automation_menu(config: dict) -> dict:
    """Menu to toggle automation features on/off."""
    automation_settings = [
        ("auto_cleanup", "Auto-cleanup after downloads"),
        ("auto_backup", "Auto-backup JSON files"),
        ("auto_sync_enabled", "Auto-sync exportify folder")
    ]
    
    while True:
        # Build choices with current status
        choices = []
        for key, label in automation_settings:
            status = "✓" if config.get(key, False) else "✗"
            choices.append(f"{status} {label}")
        choices.append("Back")
        
        choice = questionary.select(
            "Toggle automation features:",
            choices=choices
        ).ask()
        
        if choice == "Back":
            break
        
        # Find which setting was selected
        for key, label in automation_settings:
            if label in choice:
                new_value = not config.get(key, False)
                success, message = update_config(key, new_value)
                
                if success:
                    config[key] = new_value
                    status = "enabled" if new_value else "disabled"
                    log_success(f"{label} {status}")
                else:
                    log_error(message)
                break
    
    return config


def reset_config_menu(config: dict) -> dict:
    """Menu to reset configuration to defaults."""
    confirm = questionary.confirm(
        "⚠️ Reset all settings to defaults? This cannot be undone.",
        default=False
    ).ask()
    
    if confirm:
        success, message = reset_to_defaults()
        
        if success:
            log_success(message)
            config = load_config()
        else:
            log_error(message)
    
    return config


def validate_config_menu(config: dict):
    """Validate the current configuration and show any errors."""
    is_valid, errors = validate_config(config)
    
    print("\n" + "=" * 50)
    print("🔍 Configuration Validation")
    print("=" * 50)
    
    if is_valid:
        log_success("Configuration is valid! ✓")
    else:
        log_error("Configuration has errors:")
        for error in errors:
            print(f"  ✗ {error}")
    
    print("=" * 50)
    input("\nPress Enter to continue...")

