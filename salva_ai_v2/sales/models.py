from dataclasses import dataclass
from ..inventory.models import CartLine


@dataclass(frozen=True)
class Payment:
    method: str
    tendered_cents: int | None = None


@dataclass(frozen=True)
class SaleResult:
    id: int
    total_cents: int
    change_cents: int
