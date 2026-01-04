import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .ai_service import ai_service
from .utils import (
    validate_doctor_registration,
    calculate_age_from_dob,
    is_within_date_range,
)
from .schemas import ClaimSubmissionSchema, AdjudicationResultSchema, RejectionReason


class AdjudicationEngine:
    """
    Core engine for automated claim adjudication.
    Processes claims using AI for document extraction and rule-based validation.
    """

    def __init__(self, policy_terms: Dict):
        """
        Initialize the adjudication engine with policy terms.

        Args:
            policy_terms: Dictionary containing policy rules and limits
        """
        self.policy = policy_terms
        print(f"✅ Adjudication Engine initialized")
        print(f"   Policy: {policy_terms.get('policy_name', 'Unknown')}")

    async def process_claim(
        self, claim_submission: ClaimSubmissionSchema, document_paths: List[str]
    ) -> AdjudicationResultSchema:
        """
        Process a claim submission through the complete adjudication pipeline.

        Steps:
        1. Extract data from documents using AI
        2. Validate extracted data
        3. Apply policy rules
        4. Calculate approved amount and deductions
        5. Generate decision with reasoning

        Args:
            claim_submission: Submitted claim data
            document_paths: List of uploaded document file paths

        Returns:
            AdjudicationResultSchema with decision and details
        """
        print(f"\n{'=' * 60}")
        print(f"🔍 Processing Claim for {claim_submission.member_name}")
        print(f"{'=' * 60}\n")

        try:
            # Step 1: Extract data from documents using AI
            print("📄 Step 1: Extracting data from documents...")
            extraction_result = await ai_service.extract_data_from_documents(
                document_paths
            )

            if extraction_result.get("error"):
                print(f"❌ Extraction failed: {extraction_result['error']}")
                return self._create_rejection_result(
                    claim_submission,
                    [RejectionReason.INVALID_DOCUMENTS],
                    f"Document extraction failed: {extraction_result['error']}",
                )

            extracted_data = extraction_result.get("extracted_data", {})
            confidence_score = extraction_result.get("confidence_score", 0.0)

            print(f"✅ Data extracted (confidence: {confidence_score:.2f})")

            # Step 2: Validate extracted data
            print("\n✓ Step 2: Validating extracted data...")
            validation_result = self._validate_extracted_data(extracted_data)

            if not validation_result["is_valid"]:
                print(f"❌ Validation failed: {validation_result['reasons']}")
                return self._create_rejection_result(
                    claim_submission,
                    validation_result["reasons"],
                    f"Validation failed: {', '.join([r.value for r in validation_result['reasons']])}",
                )

            print(f"✅ Validation passed")

            # Step 3: Check policy coverage
            print("\n🔍 Step 3: Checking policy coverage...")
            coverage_result = self._check_policy_coverage(extracted_data)

            if not coverage_result["is_covered"]:
                print(f"❌ Not covered: {coverage_result['reasons']}")
                return self._create_rejection_result(
                    claim_submission,
                    coverage_result["reasons"],
                    f"Not covered: {', '.join([r.value for r in coverage_result['reasons']])}",
                )

            print(f"✅ Coverage confirmed")

            # Step 4: Check medical necessity (using AI)
            print("\n🤖 Step 4: Checking medical necessity with AI...")
            ai_assessment = await ai_service.process_claim_with_ai(
                extracted_data, self.policy
            )

            if not ai_assessment.get("is_medically_necessary", True):
                print(f"❌ Not medically necessary: {ai_assessment.get('reasoning')}")
                return self._create_rejection_result(
                    claim_submission,
                    [RejectionReason.NOT_MEDICALLY_NECESSARY],
                    ai_assessment.get("reasoning", "Not medically necessary"),
                )

            print(f"✅ Medical necessity confirmed")

            # Step 5: Calculate approved amount
            print("\n💰 Step 5: Calculating approved amount...")
            calculation_result = self._calculate_approved_amount(extracted_data)

            approved_amount = calculation_result["approved_amount"]
            deductions = calculation_result["deductions"]

            print(f"✅ Approved amount: ₹{approved_amount}")
            print(f"   Deductions: {deductions}")

            # Step 6: Generate final decision
            print("\n✅ Step 6: Generating final decision...")
            decision = self._determine_final_decision(
                approved_amount, confidence_score, validation_result, ai_assessment
            )

            print(f"✅ Final decision: {decision}")

            # Create result
            result = AdjudicationResultSchema(
                claim_id=self._generate_claim_id(),
                decision=decision,
                approved_amount=approved_amount,
                confidence_score=confidence_score,
                deductions=deductions,
                notes=self._generate_notes(
                    extracted_data, calculation_result, ai_assessment
                ),
                next_steps=self._generate_next_steps(decision),
                rejection_reasons=None,
                rejected_items=calculation_result.get("rejected_items", []),
            )

            print(f"\n{'=' * 60}")
            print(f"✅ Claim Processing Complete")
            print(f"   Decision: {decision}")
            print(f"   Approved: ₹{approved_amount}")
            print(f"{'=' * 60}\n")

            return result

        except Exception as e:
            print(f"❌ Claim processing error: {str(e)}")
            import traceback

            traceback.print_exc()

            return self._create_rejection_result(
                claim_submission,
                [RejectionReason.SYSTEM_ERROR],
                f"System error during processing: {str(e)}",
            )

    def _validate_extracted_data(self, data: Dict) -> Dict:
        """
        Validate extracted data for completeness and correctness.

        Returns:
            Dict with is_valid flag and list of rejection reasons
        """
        reasons = []

        # Check for required fields
        required_fields = [
            "patient_name",
            "doctor_name",
            "treatment_date",
            "total_amount",
        ]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            reasons.append(RejectionReason.INCOMPLETE_INFORMATION)
            print(f"   ⚠️ Missing fields: {missing_fields}")

        # Validate doctor registration
        doctor_reg = data.get("doctor_registration")
        if doctor_reg and not validate_doctor_registration(doctor_reg):
            reasons.append(RejectionReason.INVALID_PRESCRIPTION)
            print(f"   ⚠️ Invalid doctor registration: {doctor_reg}")
        elif not doctor_reg:
            reasons.append(RejectionReason.INVALID_PRESCRIPTION)
            print(f"   ⚠️ Doctor registration missing")

        # Validate treatment date (not in future, within coverage period)
        treatment_date_str = data.get("treatment_date")
        if treatment_date_str:
            try:
                treatment_date = datetime.strptime(treatment_date_str, "%Y-%m-%d")
                if treatment_date > datetime.now():
                    reasons.append(RejectionReason.INVALID_DATE)
                    print(f"   ⚠️ Treatment date in future")

                # Check if within coverage period (last 90 days)
                if not is_within_date_range(treatment_date, days=90):
                    reasons.append(RejectionReason.CLAIM_PERIOD_EXPIRED)
                    print(f"   ⚠️ Treatment date outside coverage period")
            except ValueError:
                reasons.append(RejectionReason.INVALID_DATE)
                print(f"   ⚠️ Invalid date format: {treatment_date_str}")

        # Validate total amount
        total_amount = data.get("total_amount")
        if not total_amount or total_amount <= 0:
            reasons.append(RejectionReason.INVALID_AMOUNT)
            print(f"   ⚠️ Invalid total amount: {total_amount}")

        return {"is_valid": len(reasons) == 0, "reasons": reasons}

    def _check_policy_coverage(self, data: Dict) -> Dict:
        """
        Check if claim meets policy coverage requirements.

        Returns:
            Dict with is_covered flag and list of rejection reasons
        """
        reasons = []

        # Check per-claim limit
        total_amount = data.get("total_amount", 0)
        per_claim_limit = self.policy.get("coverage_limits", {}).get(
            "per_claim_limit", 5000
        )

        if total_amount > per_claim_limit:
            reasons.append(RejectionReason.PER_CLAIM_EXCEEDED)
            print(
                f"   ⚠️ Amount ₹{total_amount} exceeds per-claim limit ₹{per_claim_limit}"
            )

        # Check if diagnosis is covered
        diagnosis = data.get("diagnosis", "").lower()
        excluded_conditions = self.policy.get("exclusions", {}).get(
            "pre_existing_conditions", []
        )

        for excluded in excluded_conditions:
            if excluded.lower() in diagnosis:
                reasons.append(RejectionReason.PRE_EXISTING_CONDITION)
                print(f"   ⚠️ Pre-existing condition: {excluded}")
                break

        # Check if procedures are covered
        procedures = data.get("procedures_performed", [])
        excluded_procedures = self.policy.get("exclusions", {}).get(
            "non_covered_procedures", []
        )

        for procedure in procedures:
            if any(excl.lower() in procedure.lower() for excl in excluded_procedures):
                reasons.append(RejectionReason.NON_COVERED_PROCEDURE)
                print(f"   ⚠️ Non-covered procedure: {procedure}")
                break

        return {"is_covered": len(reasons) == 0, "reasons": reasons}

    def _calculate_approved_amount(self, data: Dict) -> Dict:
        """
        Calculate approved amount with deductions.

        Returns:
            Dict with approved_amount, deductions, and rejected_items
        """
        total_amount = data.get("total_amount", 0)
        deductions = {}
        rejected_items = []

        # Apply copayment
        copay_percentage = self.policy.get("deductibles_copay", {}).get(
            "copay_percentage", 10
        )
        copay_amount = total_amount * (copay_percentage / 100)
        deductions["copay"] = round(copay_amount, 2)

        # Apply deductible
        deductible = self.policy.get("deductibles_copay", {}).get("deductible", 0)
        if deductible > 0:
            deductions["deductible"] = deductible

        # Check medicine coverage (50% for non-generic)
        medicines = data.get("medicines_prescribed", [])
        if medicines:
            # Simple check: if medicine name contains "Brand" or is capitalized, consider non-generic
            non_generic_medicines = [
                med
                for med in medicines
                if isinstance(med, dict) and med.get("name", "").istitle()
            ]

            if non_generic_medicines:
                medicine_charges = data.get("medicine_charges", 0)
                non_generic_penalty = medicine_charges * 0.5
                deductions["non_generic_medicines"] = round(non_generic_penalty, 2)
                rejected_items.extend(
                    [med.get("name", "") for med in non_generic_medicines]
                )

        # Calculate final approved amount
        total_deductions = sum(deductions.values())
        approved_amount = max(0, total_amount - total_deductions)

        return {
            "approved_amount": round(approved_amount, 2),
            "deductions": deductions,
            "rejected_items": rejected_items,
        }

    def _determine_final_decision(
        self,
        approved_amount: float,
        confidence_score: float,
        validation_result: Dict,
        ai_assessment: Dict,
    ) -> str:
        """
        Determine final decision based on all factors.

        Returns:
            One of: APPROVED, REJECTED, PARTIAL, MANUAL_REVIEW
        """
        # If confidence is low, send for manual review
        if confidence_score < 0.7:
            return "MANUAL_REVIEW"

        # If AI confidence in medical necessity is low
        ai_confidence = ai_assessment.get("confidence", 1.0)
        if ai_confidence < 0.6:
            return "MANUAL_REVIEW"

        # If approved amount is 0, reject
        if approved_amount <= 0:
            return "REJECTED"

        # If there are rejected items, it's partial approval
        # This would be checked in the calculation result

        # Otherwise, approve
        return "APPROVED"

    def _generate_notes(
        self, extracted_data: Dict, calculation_result: Dict, ai_assessment: Dict
    ) -> str:
        """Generate human-readable notes about the decision."""
        notes = []

        # Add diagnosis info
        diagnosis = extracted_data.get("diagnosis")
        if diagnosis:
            notes.append(f"Diagnosis: {diagnosis}")

        # Add deduction info
        deductions = calculation_result.get("deductions", {})
        if deductions:
            deduction_str = ", ".join([f"{k}: ₹{v}" for k, v in deductions.items()])
            notes.append(f"Deductions applied: {deduction_str}")

        # Add AI reasoning
        ai_reasoning = ai_assessment.get("reasoning")
        if ai_reasoning:
            notes.append(f"AI Assessment: {ai_reasoning}")

        return " | ".join(notes) if notes else "Claim processed successfully"

    def _generate_next_steps(self, decision: str) -> str:
        """Generate next steps based on decision."""
        next_steps_map = {
            "APPROVED": "Your claim has been approved. Amount will be credited within 3-5 business days.",
            "REJECTED": "Please review the rejection reasons and submit a new claim with correct documentation if applicable.",
            "PARTIAL": "Partial approval granted. Some items were excluded. You may appeal for the excluded items.",
            "MANUAL_REVIEW": "Your claim requires manual review. Our team will contact you within 2 business days.",
        }
        return next_steps_map.get(
            decision, "Please contact customer support for more information."
        )

    def _create_rejection_result(
        self,
        claim_submission: ClaimSubmissionSchema,
        reasons: List[RejectionReason],
        notes: str,
    ) -> AdjudicationResultSchema:
        """Create a rejection result."""
        return AdjudicationResultSchema(
            claim_id=self._generate_claim_id(),
            decision="REJECTED",
            approved_amount=0.0,
            confidence_score=0.0,
            rejection_reasons=reasons,
            notes=notes,
            next_steps=self._generate_next_steps("REJECTED"),
        )

    def _generate_claim_id(self) -> str:
        """Generate unique claim ID."""
        import uuid

        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8]
        return f"CLM-{timestamp}-{unique_id.upper()}"


# Singleton instance will be created when policy is loaded
adjudication_engine = None


def initialize_engine(policy_terms: Dict):
    """Initialize the global adjudication engine instance."""
    global adjudication_engine
    adjudication_engine = AdjudicationEngine(policy_terms)
    return adjudication_engine
