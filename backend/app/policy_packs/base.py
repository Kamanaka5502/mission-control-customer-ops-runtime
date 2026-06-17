from dataclasses import dataclass
from app.models import CustomerRequest, Outcome


@dataclass
class PolicyResult:
    outcome: Outcome
    protected_effect_status: str
    no_bind_status: bool
    reason_codes: list[str]


class PolicyPack:
    name = "base"
    description = "Base policy pack contract."

    def evaluate(self, req: CustomerRequest) -> PolicyResult:
        raise NotImplementedError
