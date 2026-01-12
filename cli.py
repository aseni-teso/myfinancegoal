import sys
import datetime
import json
from pathlib import Path
from storage import load_config, save_config, load_state, save_state, backup_state, CONFIG_PATH, STATE_PATH
from finance import add_transaction, compute_balance, compute_tithe_total, last_transactions, projected_daily_table, format_projected_table, spend_tithe

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

    # save both (defensive: ensure correct types)
    if not isinstance(cfg, dict):
        raise TypeError("cfg must be dict")
    if not isinstance(state, dict):
        raise TypeError("state must be dict")
    save_config(cfg)
    save_state(state)
    print("Инициализация завершена. Файлы сохранены.")
    return cfg, state

def print_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))

def cmd_add(argv):
    # argv: [amount, -d desc, -t tag1,tag2]
    cfg = load_config()
    state = load_state()
    if len(argv) < 1:
        print("Usage: add <amount> [-d description] [-t tag1,tag2]")
        return
    try:
        amount = float(argv[0])
    except:
        print("Неверная сумма.")
        return
    desc = ""
    tags = []
    # simple parsing
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "-d" and i+1 < len(argv):
            desc = argv[i+1]
            i += 2
        elif a == "-t" and i+1 < len(argv):
            tags = [s.strip() for s in argv[i+1].split(",") if s.strip()]
            i += 2
        else:
            i += 1

    cfg, state = add_transaction(cfg, state, amount, desc, tags)
    print("Добавлено. Баланс:", compute_balance(cfg, state))

def cmd_show_tithe(argv):
    cfg = load_config()
    state = load_state()
    total = compute_tithe_total(state)
    print(f"Текущая сумма десятины: {total}")

def cmd_history(argv):
    state = load_state()
    limit = 10
    if argv:
        try:
            limit = int(argv[0])
        except:
            pass
    tx = last_transactions(state, limit)
    print_json(tx)

def cmd_spend_tithe(argv):
    cfg = load_config()
    state = load_state()
    if not argv:
        print("Usage: spend-tithe <amount> [-d description]")
        return
    try:
        amount = float(argv[0])
        if amount >= 0:
            print("Сумма должна быть отрицательной.")
            return
    except ValueError:
        print("Неверная сумма.")
        return

    desc = ""
    if len(argv) >= 3 and argv[1] == "-d":
        desc = argv[2]
    try:
        cfg, state = spend_tithe(cfg, state, amount, desc or "tithe spend")
        print("Списано. Текущая десятина:", compute_tithe_total(state))
    except Exception as e:
        print("Error:", str(e))

def main():
    cfg = load_config()
    state = load_state()
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cfg.get("isFirstLaunch", True) and cmd != "init":
        print("Первый запуск не завершён. Выполните: python cli.py init")
        return


    if not cmd:
        print("Запустите с командой: init / add / show-tithe / history / show-config / show-savings / spend-tithe")
        return

    if cmd == "init":
        cfg, state = init_flow(cfg, state)
        print("Инициализация завершена.")
        return

    if cmd == "add":
        cmd_add(sys.argv[2:])
        return

    if cmd == "show-tithe":
        cmd_show_tithe(sys.argv[2:])
        return

    if cmd == "history":
        cmd_history(sys.argv[2:])
        return

    if cmd == "show-config":
        print_json(cfg)
        return

    if cmd == "show-savings":
        cfg = load_config()
        state = load_state()
        tbl = projected_daily_table(cfg, state, days=365)
        print(format_projected_table(tbl, show_days=14, currency=cfg.get("currency","RUB")))
        return

    if cmd == "spend-tithe":
        cmd_spend_tithe(sys.argv[2:])
        return

    if cmd == "backup":
        p = backup_state()
        print("Бэкап сохранён", p)
        return

    print("Unknown command:", cmd)

if __name__ == "__main__":
    main()
