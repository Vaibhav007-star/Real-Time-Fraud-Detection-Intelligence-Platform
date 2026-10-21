from typing import Any, Dict, List, Optional
from pydantic import Field, validator
from app.schemas.transaction import CompatBaseModel

VALID_ALERT_STATUSES = {"OPEN", "ACKNOWLEDGED", "IN_REVIEW", "RESOLVED"}
VALID_RESOLUTIONS = {"UNRESOLVED", "CONFIRMED_FRAUD", "LEGITIMATE", "INCONCLUSIVE"}
VALID_SEVERITIES = {"MEDIUM", "HIGH", "CRITICAL"}


class AlertStatusUpdate(CompatBaseModel):
    status: str = Field(..., description="New status: OPEN, ACKNOWLEDGED, IN_REVIEW, RESOLVED")
    assigned_to: Optional[str] = Field(None, max_length=64, description="Analyst username or ID")
    resolution_outcome: Optional[str] = Field(None, description="UNRESOLVED, CONFIRMED_FRAUD, LEGITIMATE, INCONCLUSIVE")
    note: Optional[str] = Field(None, max_length=1000, description="Investigation note to append")
    actor: str = Field("senior.analyst", max_length=64, description="Investigator performing the update")

    @validator("status")
    def check_status(cls, v: str) -> str:
        s = v.upper().strip()
        if s not in VALID_ALERT_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_ALERT_STATUSES)}")
        return s

    @validator("resolution_outcome")
    def check_resolution(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        r = v.upper().strip()
        if r not in VALID_RESOLUTIONS:
            raise ValueError(f"resolution_outcome must be one of {sorted(VALID_RESOLUTIONS)}")
        return r


class AlertNoteCreate(CompatBaseModel):
    author: str = Field("senior.analyst", min_length=2, max_length=64)
    note: str = Field(..., min_length=2, max_length=2000)


class AlertRecord(CompatBaseModel):
    alert_id: str
    transaction_id: str
    account_id: str
    merchant_id: Optional[str] = None
    transaction_amount: float
    currency: str = "USD"
    detection_timestamp: str
    risk_score: float
    risk_percentage: float
    ml_score: float
    graph_score: float
    rule_score: float
    severity: str
    risk_category: str
    detection_method: str
    triggered_rules: List[str] = []
    model_explanation: List[Dict[str, Any]] = []
    graph_relationships: List[str] = []
    investigation_status: str = "OPEN"
    assigned_to: Optional[str] = None
    resolution_outcome: str = "UNRESOLVED"
    is_demo: bool = False
    scenario_tag: Optional[str] = None
    notes: List[Dict[str, Any]] = []
    audit_history: List[Dict[str, Any]] = []
