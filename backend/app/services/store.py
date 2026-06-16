from app.models import CustomerRequest, RuntimeDecision, Receipt

REQUESTS: dict[str, CustomerRequest] = {}
DECISIONS: dict[str, RuntimeDecision] = {}
RECEIPTS: dict[str, Receipt] = {}
