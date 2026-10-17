from dataclasses import dataclass


@dataclass(frozen=True)
class AdminGrant:
    id: str
    action: str
    expires_at: float
