from dataclasses import dataclass
from ..inventory.models import CartLine


@dataclass(frozen=True)
class DeliveryDraft:
    customer: str
    phone: str
    address: str
    reference: str
    lines: list[CartLine]
    payment_method: str
    collection: str
    payment_timing: str = 'UNSPECIFIED'
    payment_channel: str | None = None
    change_for_cents: int | None = None
    link_reference: str = ''


@dataclass(frozen=True)
class DeliveryOrder:
    id: int
    state: str
    total_cents: int
    delivery_fee_cents: int
    courier_fee_cents: int
    paid_cents: int


@dataclass(frozen=True)
class Settlement:
    id: int
    handed_in_cents: int
    paid_out_cents: int
    offset_cents: int
