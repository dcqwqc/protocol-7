import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/whisper-flow")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "model_size": "tiny.en",
    "compute_type": "default",
    "language": "en",
    "auto_detect_language": True,
    "translate": False,
    "target_language": "en",
    "accent_color": "#00ffcc",
    "input_device": None,
    "hotkey_keycode": 29  # KEY_LEFTCTRL
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Merge with default config to ensure all keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
