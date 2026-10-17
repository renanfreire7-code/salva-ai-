from dataclasses import dataclass
from datetime import date,datetime
from decimal import Decimal


@dataclass(frozen=True)
class MonthlyResult:
    revenue_cents: int
    cogs_cents: int
    fees_cents: int
    operating_cents: int
    das_cents: int
    product_result_cents: int
    delivery_revenue_cents: int
    delivery_cost_cents: int
    total_result_cents: int
    warnings: list[str]


@dataclass(frozen=True)
class ProductResult:
    product_id: int
    name: str
    qty: int
    revenue_cents: int
    cogs_cents: int
    fees_cents: int
    contribution_cents: int
    allocated_cents: int
    profit_cents: int
    margin: Decimal | None


@dataclass(frozen=True)
class PurchaseSuggestion:
    product_id: int
    name: str
    available: int
    needed_units: int
    packs: int
    estimated_cents: int


@dataclass(frozen=True)
class HistoryFilter:
    start: date
    end: date
    object_id: str | None = None
    include_deleted: bool = True


@dataclass(frozen=True)
class HistoryRow:
    id: str
    occurred_at: datetime
    kind: str
    object_id: str
    description: str


@dataclass(frozen=True)
class ReportBundle:
    start: date
    end: date
    filters: dict
    sheets: dict[str,list[list]]
    warnings: list[str]


@dataclass(frozen=True)
class CashReport:
    session_id: int
    opening_cents: int
    expected_cents: int
    counted_cents: int
    variance_cents: int
    reason: str | None
    payments: dict[str,int]
    entries: list[dict]
