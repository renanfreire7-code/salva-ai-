from dataclasses import dataclass


@dataclass(frozen=True)
class PriceCondition:
    unit_cents: int
    group_qty: int | None = None
    group_cents: int | None = None


@dataclass(frozen=True)
class PriceQuote:
    total_cents: int
    savings_cents: int

