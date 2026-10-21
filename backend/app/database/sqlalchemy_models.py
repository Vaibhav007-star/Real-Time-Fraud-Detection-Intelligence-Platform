"""SQLAlchemy ORM schema definitions for PostgreSQL / relational deployments.

When SQLAlchemy is installed and DATABASE_URL points to PostgreSQL, these declarative
models define the relational schema. For zero-dependency local execution, `db.py`
maintains the exact same relational tables, foreign keys, and indexes via sqlite3.
"""

try:
    from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey, Index
    from sqlalchemy.orm import declarative_base

    Base = declarative_base()

    class AccountModel(Base):
        __tablename__ = "accounts"
        account_id = Column(String(64), primary_key=True)
        created_at = Column(String(40), nullable=False)
        last_seen_at = Column(String(40), nullable=False)
        tx_count = Column(Integer, default=0)
        total_amount = Column(Float, default=0.0)
        risk_tier = Column(String(24), default="LOW_RISK")

    class MerchantModel(Base):
        __tablename__ = "merchants"
        merchant_id = Column(String(64), primary_key=True)
        category = Column(String(64), nullable=False)
        created_at = Column(String(40), nullable=False)
        tx_count = Column(Integer, default=0)

    class DeviceModel(Base):
        __tablename__ = "devices"
        device_id = Column(String(64), primary_key=True)
        first_seen_at = Column(String(40), nullable=False)
        last_ip = Column(String(64), nullable=True)
        account_count = Column(Integer, default=0)

    class TransactionModel(Base):
        __tablename__ = "transactions"
        transaction_id = Column(String(128), primary_key=True)
        event_timestamp = Column(String(40), nullable=False, index=True)
        ingestion_timestamp = Column(String(40), nullable=False)
        scoring_timestamp = Column(String(40), nullable=False)
        source_account_id = Column(String(64), ForeignKey("accounts.account_id"), nullable=False, index=True)
        destination_account_id = Column(String(64), nullable=True, index=True)
        merchant_id = Column(String(64), nullable=True, index=True)
        merchant_category = Column(String(64), nullable=True)
        device_id = Column(String(64), ForeignKey("devices.device_id"), nullable=False, index=True)
        ip_address = Column(String(64), nullable=False)
        transaction_amount = Column(Float, nullable=False)
        currency = Column(String(8), nullable=False)
        transaction_type = Column(String(32), nullable=False)
        location = Column(String(64), nullable=True)
        transaction_status = Column(String(32), nullable=False)
        fraud_label = Column(Integer, nullable=True)
        is_demo = Column(Boolean, default=False)
        scenario_tag = Column(String(64), nullable=True)
        is_late_event = Column(Boolean, default=False)
        late_by_seconds = Column(Float, default=0.0)
        ml_score = Column(Float, nullable=False)
        graph_score = Column(Float, nullable=False)
        rule_score = Column(Float, nullable=False)
        combined_score = Column(Float, nullable=False, index=True)
        risk_category = Column(String(24), nullable=False, index=True)
        predicted_class = Column(Integer, nullable=False)
        model_version = Column(String(64), nullable=False)
        scoring_method = Column(String(64), nullable=False)
        triggered_rules_json = Column(Text, nullable=False)
        top_risk_factors_json = Column(Text, nullable=False)
        graph_explanations_json = Column(Text, nullable=False)
        features_json = Column(Text, nullable=False)
        processing_latency_ms = Column(Float, default=0.0)

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
