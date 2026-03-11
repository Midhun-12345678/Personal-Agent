"""Configuration loading utilities."""

import json
import os
from pathlib import Path

from nanobot.config.schema import Config


def get_config_path() -> Path:
    """Get the default configuration file path."""
    return Path.home() / ".nanobot" / "config.json"


def get_example_config_path() -> Path:
    """Get the example config file path (in repo root)."""
    return Path(__file__).parent.parent.parent / "config.example.json"


def get_data_dir() -> Path:
    """Get the nanobot data directory."""
    from nanobot.utils.helpers import get_data_path
    return get_data_path()


def load_config(config_path: Path | None = None) -> Config:
    """
    Load configuration from file or create default.
    
    Priority: config.json → config.example.json → defaults → env overrides

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        Loaded configuration object.
    """
    path = config_path or get_config_path()
    example_path = get_example_config_path()

    # Try config.json first, then fall back to config.example.json
    config_file = None
    if path.exists():
        config_file = path
    elif example_path.exists():
        config_file = example_path
        print(f"Using example config from {example_path}")

    if config_file:
        try:
            with open(config_file, encoding="utf-8") as f:
                data = json.load(f)
            data = _migrate_config(data)
            data = apply_env_overrides(data)
            return Config.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config from {config_file}: {e}")
            print("Using default configuration.")

    # Apply env overrides even for default config
    data = apply_env_overrides({})
    return Config.model_validate(data) if data else Config()


def save_config(config: Config, config_path: Path | None = None) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save.
        config_path: Optional path to save to. Uses default if not provided.
    """
    path = config_path or get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(by_alias=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _migrate_config(data: dict) -> dict:
    """Migrate old config formats to current."""
    # Move tools.exec.restrictToWorkspace → tools.restrictToWorkspace
    tools = data.get("tools", {})
    exec_cfg = tools.get("exec", {})
    if "restrictToWorkspace" in exec_cfg and "restrictToWorkspace" not in tools:
        tools["restrictToWorkspace"] = exec_cfg.pop("restrictToWorkspace")
    return data


def apply_env_overrides(config: dict) -> dict:
    """
    Override config values with environment variables if present.
    
    This allows sensitive values like API keys to be injected in production
    without hardcoding them in config.json.
    
    Supported environment variables:
        OPENAI_API_KEY: OpenAI provider API key
        GOOGLE_CLIENT_ID: Google OAuth client ID
        GOOGLE_CLIENT_SECRET: Google OAuth client secret
        SERP_API_KEY: SerpApi key for web search
        PORT: Gateway server port
        NANOBOT_WORKSPACE: Default workspace path
        GOOGLE_REDIRECT_URI: Google OAuth redirect URI
    
    Args:
        config: Configuration dictionary to modify.
        
    Returns:
        Modified configuration dictionary with env overrides applied.
    """
    # Override OpenAI API key
    if os.getenv("OPENAI_API_KEY"):
        config.setdefault("providers", {}).setdefault("openai", {})["apiKey"] = os.getenv("OPENAI_API_KEY")
    
    # Override Google OAuth settings
    if os.getenv("GOOGLE_CLIENT_ID"):
        config.setdefault("integrations", {}).setdefault("google", {})["clientId"] = os.getenv("GOOGLE_CLIENT_ID")
    
    if os.getenv("GOOGLE_CLIENT_SECRET"):
        config.setdefault("integrations", {}).setdefault("google", {})["clientSecret"] = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if os.getenv("GOOGLE_REDIRECT_URI"):
        config.setdefault("integrations", {}).setdefault("google", {})["redirectUri"] = os.getenv("GOOGLE_REDIRECT_URI")
    
    # Override SerpApi key for web search
    if os.getenv("SERP_API_KEY"):
        config.setdefault("tools", {}).setdefault("web", {}).setdefault("search", {})["serpApiKey"] = os.getenv("SERP_API_KEY")
    
    # Override gateway port
    if os.getenv("PORT"):
        config.setdefault("gateway", {})["port"] = int(os.getenv("PORT"))
    
    # Override workspace path
    if os.getenv("NANOBOT_WORKSPACE"):
        config.setdefault("agents", {}).setdefault("defaults", {})["workspace"] = os.getenv("NANOBOT_WORKSPACE")
    
    return config
