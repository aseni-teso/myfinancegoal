from dataclasses import asdict, dataclass
from typing import List, Optional
import datetime
import uuid

@dataclass
class Transaction:
    id: str
    amount: float
    timestamp: str  # ISO
    description: str
    tags: List[str]
    type: str   # "income" | "expense" | "tithe"

    @staticmethod
    def create(amount: float, description: str = "", tags: Optional[List[str]] = None, ttype: str = "income"):
        if tags is None:
            tags = []
        return Transaction(
            id=str(uuid.uuid4()),
            amount=round(float(amount), 2),
            timestamp=datetime.datetime.utcnow().isoformat(),
            description=description,
            tags=tags,
            type=ttype
        )
    def to_dict(self):
        return asdict(self)
