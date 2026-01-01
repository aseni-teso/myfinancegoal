from datetime import date, timedelta, datetime
from typing import Dict, List, Tuple
from models import Transaction
from storage import load_config, save_config, load_state, save_state
import math

def compute_balance(cfg: Dict, state: Dict) -> float:
    init = float(cfg.get("initial_balance", 0.0))
    total = init + sum(t["amount"] for t in state.get("transactions", []))
    return round(total, 2)

def compute_tithe_total(state: Dict) -> float:
    # tithe transactions stored as type == "tithe" with negative amounts
    total = sum(-t["amount"] for t in state.get("transactions", []) if t.get("type") == "tithe")
    return round(total, 2)

def add_transaction(cfg: Dict, state: Dict, amount: float, description: str = "", tags: List[str] = None) -> Tuple[Dict, Dict]:
    """
    Добавляет транзакцию. Если cfg.tithe_enabled и amount>0: выделяет 10% в tithe.
    Возвращает (cfg, state) после сохранения.
    """
    if tags is None:
        tags = []
    tithe_enabled = bool(cfg.get("tithe_enabled", False))
    if amount > 0 and tithe_enabled:
        t_full = Transaction.create(amount, description, tags, ttype="income")
        state.setdefault("transactions", []).append(t_full.to_dict())
        tithe_amount = round(amount * 0.10, 2)
        if tithe_amount != 0:
            t_tithe = Transaction.create(-tithe_amount, f"tithe for {t_full.id}", [], ttype="tithe")
            state.setdefault("transactions", []).append(t_tithe.to_dict())
    else:
        ttype = "income" if amount > 0 else "expense"
        t = Transaction.create(amount, description, tags, ttype=ttype)
        state.setdefault("transactions", []).append(t.to_dict())

    save_state(state)
    save_config(cfg)
    return cfg, state

def last_transactions(state: Dict, limit: int = 10) -> List[Dict]:
    tx = state.get("transactions", [])[-limit:]
    return list(reversed(tx))
    
def _parse_base_goal(cfg: Dict, state: Dict):
    """
    Возвращает кортеж (base_date: date, base_amount: float).
    Берёт из cfg.base_date/base_amount если есть, иначе из state.goal[0], иначе None.
    """
    bd = cfg.get("base_date")
    ba = cfg.get("base_amount")
    if bd and ba is not None:
        try:
            return date.fromisoformat(bd), float(ba)
        except:
            pass
    goals = state.get("goals, []")
    if goals:
        try:
            return date.fromisoformat(goals[0]["date"]), float(goals[0]["amount"])
        except:
            pass
        return None, None

def projected_daily_table(cfg: Dict, state: Dict, days: int = 30):
    today = date.today()
    daily = float(cfg.get("daily_default", 0.0))
    current = compute_balance(cfg, state)

    base_date, base_amount = _parse_base_goal(cfg, state)
    if base_date is None:
        base_date = today
        base_amount = current

    rows = []
    for d in range(0, days):
        dt = base_date + timedelta(days=d)
        expected = round(base_amount + daily * d, 2)
        rows.append((dt.isoformat(), expected))

    ahead_days = None
    ahead_date = None
    for d in range (0, days):
        dt = today + timedelta(days=d)
        delta = (dt - base_date).days
        expected = base_amount + daily * delta
        if current < expected:
            ahead_days = d - 1
            break
    else:
        ahead_days = days

    if ahead_days is None:
        ahead_days = 0
    if ahead_days >=0:
        ahead_date = today + timedelta(days=ahead_days)

    return {
        "today": today.isoformat(),
        "current_balance": round(current, 2),
        "base_date": base_date.isoformat(),
        "base_amount": round(base_amount, 2),
        "daily": round(daily, 2),
        "rows": rows,
        "ahead_days": int(ahead_days),
        "ahead_date": ahead_date.isoformat() if ahead_date else None
    }

def format_projected_table(tbl: Dict, show_days: int = 14):
    lines = []
    lines.append(f"Today {tbl['today']}   Current balance: {tbl['current_balance']} {('' if 'currency' not in tbl else tbl.get('currency', ''))}")
    lines.append(f"Base: {tbl['base_date']} -> {tbl['base_amount']}")
    lines.append(f"Daily expected (clean): {tbl['daily']}")
    lines.append("")
    # header
    lines.append(f"{'Date':10} | {'Expected':>12}")
    lines.append("-" * 25)
    for date_iso, expected in tbl["rows"][:show_days]:
        lines.append(f"{date_iso:10} | {expected:12.2f}")
    lines.append("")
    lines.append(f"Вы накопили на {tbl['ahead_days']} дней вперёд, на {tbl['ahead_date']}.")
    return "\n".join(lines)
