from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class RejectionReason(str, Enum):
    """Enumeration of possible rejection reasons based on adjudication rules"""

    # Eligibility & Policy
    POLICY_INACTIVE = "Policy not active"
    WAITING_PERIOD = "Waiting period not satisfied"
    MEMBER_NOT_COVERED = "Member not covered"

    # Documentation
    INCOMPLETE_INFORMATION = "Incomplete information in documents"
    INVALID_DOCUMENTS = "Invalid or unreadable documents"
    INVALID_PRESCRIPTION = "Invalid prescription or doctor registration"
    DOCTOR_REG_INVALID = "Doctor registration invalid/missing"
    DATE_MISMATCH = "Document dates do not match"
    PATIENT_MISMATCH = "Patient details do not match"

    # Coverage
    SERVICE_NOT_COVERED = "Service not covered"
    EXCLUDED_CONDITION = "Condition excluded"
    PRE_EXISTING_CONDITION = "Pre-existing condition not covered"
    PRE_AUTH_MISSING = "Pre-authorization missing"
    NON_COVERED_PROCEDURE = "Non-covered procedure"

    # Limits
    ANNUAL_LIMIT_EXCEEDED = "Annual limit exceeded"
    SUB_LIMIT_EXCEEDED = "Sub-limit exceeded"
    PER_CLAIM_EXCEEDED = "Amount exceeds per-claim limit"
    INVALID_AMOUNT = "Invalid claim amount"

    # Medical
    NOT_MEDICALLY_NECESSARY = "Not medically necessary"
    EXPERIMENTAL_TREATMENT = "Experimental treatment"
    COSMETIC_PROCEDURE = "Cosmetic procedure"

    # Process
    LATE_SUBMISSION = "Late submission"
    CLAIM_PERIOD_EXPIRED = "Claim period expired (beyond 90 days)"
    DUPLICATE_CLAIM = "Duplicate claim"
    INVALID_DATE = "Invalid treatment date"
    SYSTEM_ERROR = "System error during processing"


class ClaimSubmissionSchema(BaseModel):
    """Schema for claim submission request"""

    member_id: str = Field(..., description="Member ID")
    member_name: str = Field(..., description="Member name")
    treatment_date: str = Field(..., description="Treatment date in YYYY-MM-DD format")
    # NEW: Required for calculating waiting periods (e.g., Diabetes 90 days)
    member_join_date: Optional[str] = Field(
        None, description="Member join date (YYYY-MM-DD)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "member_id": "EMP001",
                "member_name": "John Doe",
                "treatment_date": "2024-01-15",
                "member_join_date": "2023-01-01",
            }
        }


class ExtractedDataSchema(BaseModel):
    """Schema for extracted data from documents"""

    patient_name: Optional[str] = None
    patient_age: Optional[str] = None
    patient_gender: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    clinic_hospital_name: Optional[str] = None
    treatment_date: Optional[str] = None
    diagnosis: Optional[str] = None
    chief_complaints: Optional[List[str]] = None
    medicines_prescribed: Optional[List[Dict]] = None
    diagnostic_tests: Optional[List[str]] = None
    procedures_performed: Optional[List[str]] = None
    consultation_fee: Optional[float] = None
    diagnostic_charges: Optional[float] = None
    medicine_charges: Optional[float] = None
    procedure_charges: Optional[float] = None
    total_amount: Optional[float] = None
    bill_number: Optional[str] = None
    payment_mode: Optional[str] = None
    extraction_confidence: Optional[float] = None


class AdjudicationResultSchema(BaseModel):
    """Schema for adjudication result"""

    claim_id: str = Field(..., description="Generated claim ID")
    decision: str = Field(
        ..., description="APPROVED, REJECTED, PARTIAL, or MANUAL_REVIEW"
    )
    approved_amount: float = Field(..., description="Approved claim amount")
    confidence_score: float = Field(..., description="AI confidence score (0.0-1.0)")
    rejection_reasons: Optional[List[RejectionReason]] = Field(
        None, description="Reasons for rejection"
    )
    rejected_items: Optional[List[str]] = Field(
        default=[], description="List of rejected items"
    )
    deductions: Optional[Dict[str, float]] = Field(
        default={}, description="Deductions applied"
    )
    notes: str = Field(..., description="Additional notes about the decision")
    next_steps: str = Field(..., description="Next steps for the claimant")
    processed_at: datetime = Field(
        default_factory=datetime.now, description="Processing timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "claim_id": "CLM-20240115-ABC123",
                "decision": "APPROVED",
                "approved_amount": 4500.0,
                "confidence_score": 0.95,
                "rejection_reasons": None,
                "rejected_items": [],
                "deductions": {"copay": 500.0},
                "notes": "Claim approved with standard copay deduction",
                "next_steps": "Amount will be credited within 3-5 business days",
                "processed_at": "2024-01-15T10:30:00",
            }
        }


class ClaimHistorySchema(BaseModel):
    """Schema for claim history record"""

    id: int
    claim_id: str
    member_id: str
    member_name: str
    treatment_date: str
    submission_date: datetime
    decision: str
    approved_amount: float
    total_amount: Optional[float]
    confidence_score: float
    notes: str

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Schema for error responses"""

    error: str
    detail: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Processing failed",
                "detail": "Document extraction error: Invalid file format",
            }
        }
