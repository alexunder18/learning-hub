import json
from pathlib import Path

APP_DIR = Path(__file__).parent.parent.resolve()
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_CONFIG = {
    "school_name": "Home School",
    "mode": "cli",
    "provider": "claude-code",
    "model": "claude-opus-4-6",
    "api_key": "",
    "api_base": "",
    "initial_lessons": 3,
    "topics_dir": "./topics",
}


def load_config():
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        return {**DEFAULT_CONFIG, **cfg}
    except (json.JSONDecodeError, IOError):
        return None


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def get_topics_dir():
    cfg = load_config()
    td = cfg.get("topics_dir", "./topics") if cfg else "./topics"
    p = Path(td)
    if not p.is_absolute():
        p = APP_DIR / p
    p.mkdir(parents=True, exist_ok=True)
    return p
