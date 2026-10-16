from dataclasses import dataclass


@dataclass(frozen=True)
class StockPosition:
    product_id: int
    physical: int
    reserved: int
    available: int
    value_cents: int


@dataclass(frozen=True)
class CartLine:
    product_id: int
    qty: int


@dataclass(frozen=True)
class PurchaseLine:
    product_id: int
    qty: int
    total_cents: int

