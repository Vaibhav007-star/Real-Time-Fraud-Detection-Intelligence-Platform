from typing import Any, Dict, List, Optional
from pydantic import Field
from app.schemas.transaction import CompatBaseModel


class StreamControlRequest(CompatBaseModel):
    tps: float = Field(2.0, ge=0.2, le=50.0, description="Transactions per second")
    fraud_rate: float = Field(0.15, ge=0.0, le=1.0, description="Injected synthetic fraud pattern probability")
    seed: Optional[int] = Field(42, description="Deterministic random seed for reproducible simulation")


class ScenarioTriggerRequest(CompatBaseModel):
    scenario_name: str = Field(
        ...,
        description="Scenario key: card_testing_burst | shared_device_ring | circular_money_mule | account_takeover_high_value | impossible_travel",
    )
    seed: int = Field(101, description="Deterministic seed")


class ScoringConfigUpdateRequest(CompatBaseModel):
    weight_ml_score: float = Field(0.45, ge=0.0, le=1.0)
    weight_graph_score: float = Field(0.30, ge=0.0, le=1.0)
    weight_rule_score: float = Field(0.25, ge=0.0, le=1.0)
    threshold_review: float = Field(0.45, gt=0.0, lt=1.0)
    threshold_high_risk: float = Field(0.72, gt=0.0, le=1.0)
    alert_cooldown_seconds: int = Field(120, ge=0, le=86400)


class DatasetMappingRequest(CompatBaseModel):
    column_mapping: Optional[Dict[str, str]] = None
    inject_synthetic_graph: bool = Field(
        True,
        description="When public dataset lacks device/IP/account relationships, synthesize clearly labeled DEMO graph entities separately from original features",
    )
    process_into_pipeline: bool = Field(
        False,
        description="Whether to stream rows through the scoring pipeline after validation",
    )
    max_rows_to_score: int = Field(200, ge=1, le=2000)
