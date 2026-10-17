from dataclasses import dataclass
from datetime import date,datetime


@dataclass(frozen=True)
class CommerceFilter:
    start: date
    end: date
    kind: str | None = None
    state: str | None = None
    text: str = ''


@dataclass(frozen=True)
class CommerceRow:
    key: str
    kind: str
    order_id: int
    sale_id: int | None
    customer: str
    occurred_at: datetime
    total_cents: int
    state: str
    paid_cents: int


@dataclass(frozen=True)
class CommerceItem:
    product_id: int
    name: str
    qty: int
    unit_cents: int
    group_qty: int | None
    group_cents: int | None
    total_cents: int
