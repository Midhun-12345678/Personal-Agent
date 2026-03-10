"""First-time setup — creates config file"""
import json
from pathlib import Path

config = {
  "providers": {
    "openai": {
      "apiKey": "YOUR_OPENAI_API_KEY_HERE"
    }
    },
    "agents": {
        "defaults": {
            "model": "gpt-4o",
            "provider": "openai"
        }
    },
    "auth_enabled": True,
    "server": {
        "host": "0.0.0.0",
        "port": 8765
    }
}

config_path = Path.home() / ".personal-agent" / "config.json"
config_path.parent.mkdir(parents=True, exist_ok=True)

if config_path.exists():
    print(f"Config already exists at {config_path}")
else:
    config_path.write_text(json.dumps(config, indent=2))
    print(f"Config created at {config_path}")
    print("Edit it and add your Anthropic API key before running.")
