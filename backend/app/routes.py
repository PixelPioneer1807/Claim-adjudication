from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime
from pathlib import Path

from .database import get_db
from .models import Claim
from .schemas import (
    ClaimSubmissionSchema,
    AdjudicationResultSchema,
    ClaimHistorySchema,
    ErrorResponse,
)
from .adjudication_engine import adjudication_engine
from .config import settings
from .utils import sanitize_filename

router = APIRouter(prefix="/api/v1", tags=["claims"])

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.post("/claims/submit", response_model=AdjudicationResultSchema)
async def submit_claim(
    member_id: str = Form(...),
    member_name: str = Form(...),
    treatment_date: str = Form(...),
    documents: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Submit a new insurance claim with medical documents.

    Args:
        member_id: Member ID
        member_name: Member name
        treatment_date: Treatment date (YYYY-MM-DD)
        documents: List of medical document files
        db: Database session

    Returns:
        AdjudicationResultSchema with decision and details
    """
    print(f"\n{'=' * 60}")
    print(f"📋 New Claim Submission")
    print(f"   Member: {member_name} ({member_id})")
    print(f"   Treatment Date: {treatment_date}")
    print(f"   Documents: {len(documents)}")
    print(f"{'=' * 60}\n")

    # Validate documents
    if not documents or len(documents) == 0:
        raise HTTPException(status_code=400, detail="No documents uploaded")

    # Save uploaded documents
    document_paths = []
    try:
        for doc in documents:
            # Validate file extension
            file_ext = Path(doc.filename).suffix.lower()
            if file_ext not in settings.ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type {file_ext} not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
                )

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = sanitize_filename(doc.filename)
            unique_filename = f"{timestamp}_{safe_filename}"
            file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(doc.file, buffer)

            document_paths.append(file_path)
            print(f"✅ Saved document: {unique_filename}")

        print(f"✅ Saved {len(document_paths)} documents\n")

        # Create claim submission object
        claim_submission = ClaimSubmissionSchema(
            member_id=member_id, member_name=member_name, treatment_date=treatment_date
        )

        # Process claim through adjudication engine
        if adjudication_engine is None:
            raise HTTPException(
                status_code=500, detail="Adjudication engine not initialized"
            )

        result = await adjudication_engine.process_claim(
            claim_submission, document_paths
        )

        # Save to database
        claim_record = Claim(
            claim_id=result.claim_id,
            member_id=member_id,
            member_name=member_name,
            treatment_date=treatment_date,
            submission_date=datetime.now(),
            decision=result.decision,
            approved_amount=result.approved_amount,
            confidence_score=result.confidence_score,
            rejection_reasons=[r.value for r in result.rejection_reasons]
            if result.rejection_reasons
            else None,
            rejected_items=result.rejected_items,
            deductions=result.deductions,
            notes=result.notes,
            document_paths=document_paths,
        )

        db.add(claim_record)
        db.commit()
        db.refresh(claim_record)

        print(f"\n✅ Claim saved to database: {result.claim_id}\n")

        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Error processing claim: {str(e)}\n")
        import traceback

        traceback.print_exc()

        # Cleanup uploaded files on error
        for path in document_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass

        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")


@router.get("/claims/history", response_model=List[ClaimHistorySchema])
async def get_claim_history(
    member_id: str = None, limit: int = 50, db: Session = Depends(get_db)
):
    """
    Get claim history for a member or all claims.

    Args:
        member_id: Optional member ID to filter by
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of claim history records
    """
    query = db.query(Claim)

    if member_id:
        query = query.filter(Claim.member_id == member_id)

    claims = query.order_by(Claim.submission_date.desc()).limit(limit).all()

    return claims


@router.get("/claims/{claim_id}", response_model=ClaimHistorySchema)
async def get_claim_by_id(claim_id: str, db: Session = Depends(get_db)):
    """
    Get a specific claim by ID.

    Args:
        claim_id: Claim ID
        db: Database session

    Returns:
        Claim record
    """
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()

    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    return claim


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "OPD Claim Adjudication API",
        "timestamp": datetime.now().isoformat(),
    }
