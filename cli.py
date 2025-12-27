import sys
import datetime
from pathlib import Path
from storage import load_config, save_config, load_state, save_state, backup_state, CONFIG_PATH, STATE_PATH

def ask(prompt: str, default: str = "") -> str:
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    val = input(prompt).strip()
    return val if val != "" else default

def parse_bool(s: str) -> bool:
    return s.lower() in ("y", "yes", "1", "true", "t")

def init_flow(cfg: dict, state: dict) -> (dict, dict):
    print("Первый запуск - задаём начальные параметры.")
    # initial balance
    ib = ask("Текущая общая сумма (например: 65000)")
    try:
        cfg["initial_balance"] = float(ib)
    except:
        cfg["initial_balance"] = 0.0
    # desired daily default
    dd = ask("Желаемый чистый доход в день (daily_default)", str(cfg.get("daily_default", 1000.0)))
    try:
        cfg["daily_default"] = float(dd)
    except:
        cfg["daily_default"] = 1000.0
    # period (optional) - store raw string
    period = ask("Период для цели (описание/строка, необязательно)", "")
    cfg["period"] = period or None
    # currency
    cur = ask("Валюта", cfg.get("currency", "RUB"))
    cfg["currency"] = cur
    # tithe
    t = ask("Десятина? (y/n)", "y" if cfg.get("tithe_enabled", True) else "n")
    cfg["tithe_enabled"] = parse_bool(t)
    # base date/amount pair (optional)
    base_date = ask("Сумма-соотношение: дата (YYYY-MM-DD) - leave empty for today", "")
    base_amount = ask("Сумма-соотношение: сумма (число) - leave empty for initial balance", "")
    if base_date:
        try:
            # validate date
            datetime.date.fromisoformat(base_date)
            cfg["base_date"] = base_date
        except Exception:
            print("Неверная дата, игнорируем.")
            cfg["base_date"] = None
    else:
        cfg["base_date"] = datetime.date.today().isoformat()
    if base_amount:
        try:
            cfg["base_amount"] = float(base_amount)
        except:
            cfg["base_amount"] = cfg["initial_balance"]
    else:
        cfg["base_amount"] = cfg["initial_balance"]

    cfg["isFirstLaunch"] = False

    # ensure empty state
    if "transactions" not in state:
        state["transactions"] = []
    if "goals" not in state:
        state["goals"] = []
    # add base goal entry if provided
    if cfg.get("base_date") and cfg.get("base_amount") is not None:
        state["goals"].append({
            "date": cfg["base_date"],
            "amount": cfg["base_amount"]
        })

    # save both
    save_config(cfg)
    save_state(state)
    print("Инициализация завершена. Файлы сохранены.")
    return cfg, state

def main():
    cfg = load_config()
    state = load_state()
    if cfg.get("isFirstLaunch", True):
        cfg, state = init_flow(cfg, state)

    # simple CLI handling for MVP: support a few commands
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if not cmd:
        print("Запустите с командой: add / show-savings / show-tithe / history / init")
        return

    if cmd == "init":
        cfg["isFirstLaunch"] = True
        save_config(cfg)
        print("Флаг isFirstLaunch сброшен. Запустите снова.")
        return
    if cmd == "show-config":
        print("CONFIG:")
        import json
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return
    if cmd == "backup":
        p = backup_state()
        print("Бэкап сохранён", p)
        return

    print("Команда не распознана в MVP.")

if __name__ == "__main__":
    main()
