from dataclasses import dataclass


@dataclass(frozen=True)
class AdminGrant:
    id: str
    action: str
    expires_at: float


@dataclass(frozen=True)
class LoginSession:
    id: str
    revision: int
