from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from datetime import datetime
from .database import Base


class Claim(Base):
    """Database model for insurance claims"""

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, unique=True, index=True, nullable=False)

    # Member information
    member_id = Column(String, index=True, nullable=False)
    member_name = Column(String, nullable=False)

    # Claim details
    treatment_date = Column(String, nullable=False)
    submission_date = Column(DateTime, default=datetime.now, nullable=False)

    # Adjudication results
    decision = Column(
        String, nullable=False
    )  # APPROVED, REJECTED, PARTIAL, MANUAL_REVIEW
    approved_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=True)
    confidence_score = Column(Float, default=0.0)

    # Additional information
    rejection_reasons = Column(JSON, nullable=True)
    rejected_items = Column(JSON, nullable=True)
    deductions = Column(JSON, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    # Document paths
    document_paths = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Claim(claim_id='{self.claim_id}', decision='{self.decision}', approved_amount={self.approved_amount})>"
