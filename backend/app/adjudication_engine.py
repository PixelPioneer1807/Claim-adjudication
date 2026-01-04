import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import difflib

from .ai_service import ai_service
from .models import Claim
from .utils import validate_doctor_registration
from .schemas import ClaimSubmissionSchema, AdjudicationResultSchema, RejectionReason


class AdjudicationEngine:
    """Core engine for automated claim adjudication."""

    def __init__(self, policy_terms: Dict):
        self.policy = policy_terms
        print(f"✅ Adjudication Engine initialized: {policy_terms.get('policy_name')}")

    async def process_claim(
        self,
        claim_submission: ClaimSubmissionSchema,
        document_paths: List[str],
        db: Session,
    ) -> AdjudicationResultSchema:
        print(f"\n🔍 Processing Claim: {claim_submission.member_name}")

        try:
            # 1. FRAUD CHECK (Same Day Claims)
            if self._check_fraud_indicators(claim_submission, db):
                return self._create_rejection_result(
                    claim_submission,
                    [RejectionReason.DUPLICATE_CLAIM],
                    "Potential Fraud: Multiple claims submitted for same treatment date.",
                )

            # 2. Extract Data
            extraction = await ai_service.extract_data_from_documents(document_paths)
            if extraction.get("error"):
                return self._create_rejection_result(
                    claim_submission,
                    [RejectionReason.INVALID_DOCUMENTS],
                    extraction["error"],
                )

            data = extraction["extracted_data"]
            confidence = extraction["confidence_score"]

            # 3. Eligibility (Waiting Period)
            eligibility = self._check_eligibility(claim_submission, data)
            if not eligibility["is_eligible"]:
                return self._create_rejection_result(
                    claim_submission, eligibility["reasons"], eligibility["notes"]
                )

            # 4. Validation (Identity Check + Docs)
            validation = self._validate_extracted_data(data, claim_submission)
            if not validation["is_valid"]:
                return self._create_rejection_result(
                    claim_submission,
                    validation["reasons"],
                    "; ".join([r.value for r in validation["reasons"]]),
                )

            # 5. Coverage & Limits (Pre-auth + Annual Limit)
            coverage = self._check_policy_coverage_and_limits(
                data, claim_submission.member_id, db
            )

            # If rejected due to LIMITS, we might want to consider Partial Approval later
            # But for now, if it's an EXCLUSION or PRE-AUTH missing, we reject hard.
            # If it's just a LIMIT exceeded, we will try to cap it in calculation step.
            if not coverage["is_covered"]:
                # Check if the only reason is LIMIT EXCEEDED
                only_limits = all(
                    r
                    in [
                        RejectionReason.PER_CLAIM_EXCEEDED,
                        RejectionReason.ANNUAL_LIMIT_EXCEEDED,
                    ]
                    for r in coverage["reasons"]
                )

                if not only_limits:
                    # It has hard rejections (Exclusions/Pre-auth), so we reject.
                    return self._create_rejection_result(
                        claim_submission,
                        coverage["reasons"],
                        "; ".join([r.value for r in coverage["reasons"]]),
                    )
                else:
                    print(
                        "   ⚠️ Limit exceeded, but proceeding to Calculate for Partial Approval cap."
                    )

            # 6. Medical Necessity
            ai_assess = await ai_service.process_claim_with_ai(data, self.policy)
            if not ai_assess.get("is_medically_necessary", True):
                return self._create_rejection_result(
                    claim_submission,
                    [RejectionReason.NOT_MEDICALLY_NECESSARY],
                    ai_assess.get("reasoning", ""),
                )

            # 7. Calculate
            # Pass coverage reasons so we can cap the amount if needed
            calc = self._calculate_approved_amount(data, coverage["reasons"])

            # 8. Decide
            decision = self._determine_final_decision(
                calc["approved_amount"], confidence, validation, ai_assess, calc
            )

            return AdjudicationResultSchema(
                claim_id=self._generate_claim_id(),
                decision=decision,
                approved_amount=calc["approved_amount"],
                confidence_score=confidence,
                deductions=calc["deductions"],
                notes=self._generate_notes(
                    data, calc, ai_assess, eligibility, coverage
                ),
                next_steps=self._generate_next_steps(decision),
                rejected_items=calc["rejected_items"],
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return self._create_rejection_result(
                claim_submission, [RejectionReason.SYSTEM_ERROR], str(e)
            )

    # --- HELPER FUNCTIONS ---

    def _safe_get_lower(self, data: Dict, key: str) -> str:
        """Safely get string from dict and lower() it, handling None/Null."""
        val = data.get(key)
        if val is None:
            return ""
        return str(val).lower()

    def _check_fraud_indicators(
        self, submission: ClaimSubmissionSchema, db: Session
    ) -> bool:
        same_day_claims = (
            db.query(Claim)
            .filter(
                Claim.member_id == submission.member_id,
                Claim.treatment_date == submission.treatment_date,
            )
            .count()
        )
        if same_day_claims >= 2:
            print(f"   ⚠️ FRAUD ALERT: {same_day_claims} previous claims found")
            return True
        return False

    def _check_eligibility(self, submission: ClaimSubmissionSchema, data: Dict) -> Dict:
        reasons = []
        notes = []

        if not submission.member_join_date:
            return {"is_eligible": True, "reasons": [], "notes": ""}

        try:
            join = datetime.strptime(submission.member_join_date, "%Y-%m-%d")
            treat = datetime.strptime(submission.treatment_date, "%Y-%m-%d")
            days_active = (treat - join).days

            if days_active < 0:
                return {
                    "is_eligible": False,
                    "reasons": [RejectionReason.POLICY_INACTIVE],
                    "notes": "Inactive policy",
                }

            # FIX: Use safe getter
            diagnosis = self._safe_get_lower(data, "diagnosis")
            waiting = self.policy.get("waiting_periods", {})

            if days_active < waiting.get("initial_waiting", 30):
                reasons.append(RejectionReason.WAITING_PERIOD)
                notes.append(f"In initial waiting period (Day {days_active})")

            for ailment, days in waiting.get("specific_ailments", {}).items():
                if ailment in diagnosis and days_active < days:
                    reasons.append(RejectionReason.WAITING_PERIOD)
                    notes.append(f"{ailment.title()} waiting period not met")

        except ValueError:
            pass

        return {
            "is_eligible": len(reasons) == 0,
            "reasons": reasons,
            "notes": "; ".join(notes),
        }

    def _validate_extracted_data(
        self, data: Dict, submission: ClaimSubmissionSchema
    ) -> Dict:
        reasons = []

        # FIX: Handle None in amount
        amount = data.get("total_amount")
        if amount is None or amount <= 0:
            reasons.append(RejectionReason.INVALID_AMOUNT)

        # Identity Check
        doc_name = self._safe_get_lower(data, "patient_name")
        sub_name = submission.member_name.lower()

        if doc_name and sub_name:
            ratio = difflib.SequenceMatcher(None, doc_name, sub_name).ratio()
            if ratio < 0.6:
                print(
                    f"   ⚠️ Identity Mismatch: '{doc_name}' vs '{sub_name}' (Ratio: {ratio:.2f})"
                )
                reasons.append(RejectionReason.PATIENT_MISMATCH)

        return {"is_valid": len(reasons) == 0, "reasons": reasons}

    def _check_policy_coverage_and_limits(
        self, data: Dict, member_id: str, db: Session
    ) -> Dict:
        reasons = []
        amount = data.get("total_amount", 0) or 0  # Handle None

        # 1. Per Claim Limit
        if amount > self.policy["coverage_details"]["per_claim_limit"]:
            reasons.append(RejectionReason.PER_CLAIM_EXCEEDED)

        # 2. Annual Limit
        past_total = (
            db.query(func.sum(Claim.approved_amount))
            .filter(Claim.member_id == member_id, Claim.decision == "APPROVED")
            .scalar()
            or 0
        )

        if (past_total + amount) > self.policy["coverage_details"]["annual_limit"]:
            reasons.append(RejectionReason.ANNUAL_LIMIT_EXCEEDED)

        # 3. Exclusions
        diagnosis = self._safe_get_lower(data, "diagnosis")
        for excl in self.policy.get("exclusions", []):
            if excl.lower() in diagnosis:
                reasons.append(RejectionReason.EXCLUDED_CONDITION)

        # 4. Pre-Authorization (MRI/CT)
        # Handle None in lists
        tests = data.get("diagnostic_tests") or []
        procedures = data.get("procedures_performed") or []
        combined_services = str(tests) + str(procedures) + diagnosis

        needs_pre_auth = (
            "MRI" in combined_services.upper() or "CT SCAN" in combined_services.upper()
        )
        has_pre_auth = data.get("pre_authorization_number") is not None

        if needs_pre_auth and not has_pre_auth:
            if amount > 5000:
                reasons.append(RejectionReason.PRE_AUTH_MISSING)

        return {"is_covered": len(reasons) == 0, "reasons": reasons}

    def _calculate_approved_amount(
        self, data: Dict, coverage_reasons: List[str] = []
    ) -> Dict:
        total = data.get("total_amount", 0) or 0
        deductions = {}

        # CAP AMOUNT if Limit Exceeded
        per_claim_limit = self.policy["coverage_details"]["per_claim_limit"]

        capped_amount = total
        if RejectionReason.PER_CLAIM_EXCEEDED in coverage_reasons:
            print(f"   ⚠️ Capping claim at limit: {per_claim_limit}")
            deductions["limit_cap"] = round(total - per_claim_limit, 2)
            capped_amount = per_claim_limit

        # Network Discount
        hospital = self._safe_get_lower(data, "clinic_hospital_name")
        network_hospitals = self.policy.get("network_hospitals", [])
        is_network = any(h.lower() in hospital for h in network_hospitals)

        net_amount = capped_amount
        if is_network:
            disc = capped_amount * 0.20  # 20% discount
            deductions["network_discount"] = round(disc, 2)
            net_amount -= disc

        # Copay
        copay = net_amount * 0.10
        deductions["copay"] = round(copay, 2)

        approved = max(0, net_amount - copay)
        return {
            "approved_amount": round(approved, 2),
            "deductions": deductions,
            "rejected_items": [],
            "is_network": is_network,
        }

    def _determine_final_decision(self, amount, confidence, val, ai, calc) -> str:
        if confidence < 0.7 or ai.get("confidence", 1) < 0.6:
            return "MANUAL_REVIEW"
        if amount <= 0:
            return "REJECTED"

        # If we applied a "limit_cap", that counts as PARTIAL approval
        if "limit_cap" in calc.get("deductions", {}):
            return "PARTIAL"

        if calc.get("rejected_items"):
            return "PARTIAL"
        return "APPROVED"

    def _generate_notes(self, data, calc, ai, elig, cov) -> str:
        notes = []
        if elig.get("notes"):
            notes.append(elig["notes"])
        if cov.get("reasons"):
            # Only show reasons that didn't stop approval (like Limit Exceeded -> Partial)
            pass
        if calc.get("is_network"):
            notes.append("Network Hospital")
        if ai.get("reasoning"):
            notes.append(ai["reasoning"])

        # Explain deductions
        for k, v in calc.get("deductions", {}).items():
            notes.append(f"{k.replace('_', ' ').title()}: -₹{v}")

        return " | ".join(filter(None, notes))

    def _generate_next_steps(self, decision) -> str:
        if decision == "APPROVED" or decision == "PARTIAL":
            return "Payment processed within 3 days."
        return "Contact Support"

    def _create_rejection_result(self, sub, reasons, notes) -> AdjudicationResultSchema:
        return AdjudicationResultSchema(
            claim_id=self._generate_claim_id(),
            decision="REJECTED",
            approved_amount=0.0,
            confidence_score=1.0,
            rejection_reasons=reasons,
            notes=notes,
            next_steps="Contact Support",
        )

    def _generate_claim_id(self) -> str:
        import uuid

        return (
            f"CLM-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        )


# Global & Getter
adjudication_engine = None


def initialize_engine(policy_terms: Dict):
    global adjudication_engine
    adjudication_engine = AdjudicationEngine(policy_terms)
    return adjudication_engine


def get_engine():
    global adjudication_engine
    return adjudication_engine
