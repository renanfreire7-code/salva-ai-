from dataclasses import dataclass


@dataclass(frozen=True)
class CashPosition:
    expected_cents: int

