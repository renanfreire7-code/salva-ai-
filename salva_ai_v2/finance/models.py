from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ExpenseDraft:
    description: str
    category: str
    amount_cents: int
    incurred_on: date
    due_on: date


@dataclass(frozen=True)
class ExpenseFilter:
    start: date
    end: date
    date_basis: str
    category: str | None = None
    text: str = ""
    status: str | None = None
    include_deleted: bool = False


@dataclass(frozen=True)
class ExpenseRow:
    id: int
    draft: ExpenseDraft
    paid_cents: int
    paid_on: date | None
    status: str
    deleted_at: str | None
    source_type: str

    @property
    def due_on(self):
        return self.draft.due_on


@dataclass(frozen=True)
class ExpenseTotals:
    paid_cents: int
    pending_cents: int
    overdue_cents: int
    commitments_cents: int
    by_category: dict[str, int]
