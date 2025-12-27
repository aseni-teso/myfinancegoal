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
    # если доход положительный и десятина включена
    tithe_enabled = bool(cfg.get("tithe_enabled"), False))
    if amount > 0 and tithe_enabled:
        tithe_amount = round(amount * 0.10, 2)
        main_amount = round(amount - tithe_amount, 2)
        t_main = Transaction.create(main_amount, description, tags, ttype="income")
        t_tithe = Transaction.create(-tithe_amount, f"tithe for {t_main.id}", [], ttype="tithe")
        state.setdefault("transactions", []).append(t_main.to_dict())
        state.setdefault("transactions", []).append(t_tithe.to_dict())
    else:
        ttype = "income" if amount > 0 else "expense"
        t = Transaction.create(amount, description, tags, ttype=ttype)
        state.setdefault("transactions", []).append(t.to_dict())

    save_config(state)
    # cfg might be unchanged but save for consistency
    save_state(cfg)
    return cfg, state

def last_transactions(state: Dict, limit: int = 10) -> List[Dict]:
    tx = state.get("transactions", [])[-limit:]
    # return reversed so newest first
    return list(reversed(tx))
    
