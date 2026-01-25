"""
SQLAlchemy ORM models for database persistence.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AlertRecord(Base):
    """Stored alert records in the database."""
    
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    service = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    detector = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Store metric snapshot and context as JSON
    metric_snapshot = Column(JSON, nullable=False, default=dict)
    context = Column(JSON, nullable=False, default=dict)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)


class TriageResultRecord(Base):
    """Triage outcomes with agent decisions."""
    
    __tablename__ = "triage_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    alert_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Agent outputs
    logs_summary = Column(String, nullable=True)
    metrics_summary = Column(String, nullable=True)
    anomalies = Column(JSON, default=list)
    similar_incidents = Column(JSON, default=list)
    
    # Decision
    hypothesis = Column(String, nullable=True)
    recommended_action = Column(String, nullable=True)
    confidence = Column(Float, default=0.0)
    requires_approval = Column(Boolean, default=True)
    
    # Trace for Streamlit UI
    events = Column(JSON, default=list)
    
    # Status tracking
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class AuditLogRecord(Base):
    """Audit trail for all actions taken."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    triage_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    actor = Column(String(100), nullable=False)  # "agent" or "user:xxx"
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)
