from datetime import date, timedelta, datetime
from typing import Dict, List, Tuple
from models import Transaction
from storage import load_config, save_config, load_state, save_state
import math

def compute_balance(cfg: Dict, state: Dict) -> float:
    init = float(cfg.get("initial_balance", 0.0))
    total = init + sum(
        t["amount"] for t in state.get("transactions", [])
        if t.get("type") != "tithe_spend"
    )
    return round(total, 2)

def compute_tithe_total(state: Dict) -> float:
    total = 0.0

    for t in state.get("transactions", []):
        if t.get("type") == "tithe":
            total += -t["amount"]
        elif t.get("type") == "tithe_spend":
            total += t["amount"]

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
    bd = cfg.get("base_date")
    ba = cfg.get("base_amount")
    if bd and ba is not None:
        try:
            return date.fromisoformat(bd), float(ba)
        except:
            pass
    goals = state.get("goals", [])
    if goals:
        try:
            return date.fromisoformat(goals[0]["date"]), float(goals[0]["amount"])
        except:
            pass
        return None, None

def projected_daily_table(cfg: Dict, state: Dict, days: int = 90):
    today = date.today()
    daily = float(cfg.get("daily_default", 0.0))
    current = compute_balance(cfg, state)

    base_date, base_amount = _parse_base_goal(cfg, state)

    if base_date is None:
        base_date = today
        base_amount = current

    if base_date == today:
        base_amount = current

    rows = []
    for d in range(0, days):
        dt = base_date + timedelta(days=d)
        expected = round(base_amount + daily * d, 2)
        rows.append((dt.isoformat(), expected))

    if daily == 0:
        ahead_days = None
    else:
        delta_days_from_base_to_today = (today - base_date).days
        expected_today = base_amount + daily * delta_days_from_base_to_today
        diff = round(current - expected_today, 2)
        ahead_days = math.floor(diff / daily)
        
    ahead_date = today + timedelta(days=int(ahead_days))

    return {
        "today": today.isoformat(),
        "current_balance": round(current, 2),
        "base_date": base_date.isoformat(),
        "base_amount": round(base_amount, 2),
        "daily": round(daily, 2),
        "rows": rows,
        "ahead_days": int(ahead_days),
        "ahead_date": ahead_date.isoformat()
    }

def format_projected_table(tbl: Dict, show_days: int = 14, currency: str = "RUB"):
    rows_map = {d: v for d, v in tbl.get("rows", [])}

    today = date.fromisoformat(tbl["today"])
    ahead = date.fromisoformat(tbl["ahead_date"])
    base_date = date.fromisoformat(tbl["base_date"])
    daily = tbl["daily"]
    base_amount = tbl["base_amount"]

    def expected_for(d: date) -> float:
        iso = d.isoformat()
        if iso in rows_map:
            return rows_map[iso]
        delta = (d - base_date).days
        return round(base_amount + daily * delta, 2)

    def fmt_line(d: date):
        iso = d.isoformat()
        exp = expected_for(d)
        mark = ""
        if d == today:
            mark = " <today"
        if d == ahead:
            mark = (mark + ",ahead") if mark else " <ahead"
        return f"{iso:10} | {exp:12.2f}{mark}"

    delta = (ahead - today).days
    lines = []
    lines.append(f"Today {tbl['today']}   Current balance: {tbl['current_balance']} {currency}")
    lines.append(f"Base: {tbl['base_date']} -> {tbl['base_amount']}")
    lines.append(f"Daily expected (clean): {tbl['daily']}")
    lines.append("")
    lines.append(f"{'Date':10} | {'Expected':>12}")
    lines.append("-" * 27)

    def append_range(start_day: date, count: int):
        cur = start_day
        for _ in range(count):
            lines.append(fmt_line(cur))
            cur += timedelta(days=1)

    if delta <= -14:
        append_range(ahead, show_days)
        lines.append("...".rjust(11))
        lines.append(fmt_line(today))
    elif -14 < delta < 0:
        append_range(ahead, show_days)
    elif 0 <= delta <= 13:
        append_range(today, show_days)
    else: # delta >= 14
        append_range(today, show_days)
        lines.append("...".rjust(11))
        lines.append(fmt_line(ahead))

    lines.append("")
    lines.append(f"Вы накопили на {tbl['ahead_days']} дней вперёд, на {tbl['ahead_date']}.")
    return "\n".join(str(x) for x in lines)

def spend_tithe(cfg: Dict, state: Dict, amount: float, description: str = "") -> Tuple[Dict, Dict]:
    if amount >= 0:
        raise ValueError("Сумма должна быть отрицательной.")

    current_tithe = compute_tithe_total(state)

    spend_amount = abs(amount)

    if spend_amount > current_tithe:
        raise ValueError(f"Недостаточно средств для списания: текущая сумма десятины: {current_tithe}.")

    t = Transaction.create(amount, description or "tithe spend", [], ttype="tithe_spend")
    state.setdefault("transactions", []).append(t.to_dict())

    save_state(state)
    save_config(cfg)

    return cfg, state
