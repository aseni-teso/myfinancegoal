import json
from pathlib import Path
from typing import Any, Dict

DATA_DIR = Path.cwd() / "myfinancegoal" / "data"
CONFIG_PATH = DATA_DIR / "config.json"
STATE_PATH = DATA_DIR / "state.json"

def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path: Path, default: Any) -> Any:
    ensure_data_dir()
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, content: Any) -> None:
    ensure_data_dir()
    # simple atomic write
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

def load_config() -> Dict:
    default = {
      "isFirstLaunch": True,
      "currency": "RUB",
      "tithe_enabled": True,
      "daily_default": 1000.0,
      "initial_balance": 0.0,
      "base_date": None,
      "base_amount": None
    }
    return load_json(CONFIG_PATH, default)

def save_config(cfg: Dict) -> None:
    save_json(CONFIG_PATH, cfg)

def load_state() -> Dict:
    default = {
        "transactions": [],
        "goals": []
    }
    return load_json(STATE_PATH, default)

def save_state(state: Dict) -> None:
    save_json(STATE_PATH, state)

def backup_state() -> Path:
    ensure_data_dir()
    import datetime
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = DATA_DIR / f"state_backup_{stamp}.json"
    state = load_state()
    save_json(backup_path, state)
    return backup_path

