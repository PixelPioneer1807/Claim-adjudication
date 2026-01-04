import json
from pathlib import Path
from typing import Dict
from .config import settings


def load_policy_terms() -> Dict:
    """
    Load policy terms from JSON file.

    Returns:
        Dict containing policy terms and rules
    """
    policy_file = Path(settings.POLICY_FILE)

    if not policy_file.exists():
        print(f"⚠️  Policy file not found: {policy_file}")
        print("   Using default policy terms")
        return get_default_policy()

    try:
        with open(policy_file, "r", encoding="utf-8") as f:
            policy = json.load(f)
        print(f"✅ Loaded policy terms from {policy_file}")
        return policy
    except Exception as e:
        print(f"❌ Error loading policy file: {e}")
        print("   Using default policy terms")
        return get_default_policy()


def get_default_policy() -> Dict:
    """
    Get default policy terms if file is not available.

    Returns:
        Dict with default policy configuration
    """
    return {
        "policy_name": "Standard OPD Policy",
        "policy_version": "1.0",
        "coverage_limits": {
            "per_claim_limit": 5000,
            "annual_limit": 50000,
            "consultation_limit": 1000,
            "diagnostic_limit": 3000,
            "medicine_limit": 2000,
        },
        "deductibles_copay": {"deductible": 0, "copay_percentage": 10},
        "exclusions": {
            "pre_existing_conditions": ["Diabetes", "Hypertension", "Heart Disease"],
            "non_covered_procedures": [
                "Cosmetic Surgery",
                "Dental Treatment",
                "Alternative Medicine",
            ],
        },
        "waiting_periods": {
            "general_waiting_period_days": 30,
            "specific_conditions_days": 90,
        },
        "claim_submission": {
            "max_days_after_treatment": 90,
            "required_documents": [
                "Prescription",
                "Bills/Invoices",
                "Diagnostic Reports",
            ],
        },
    }
