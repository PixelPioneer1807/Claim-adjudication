import re
from datetime import datetime, timedelta
from typing import Optional


def validate_doctor_registration(registration: str) -> bool:
    """
    Validate doctor registration number format.
    Expected format: STATE/NUMBER/YEAR (e.g., KA/45678/2015)
    """
    if not registration:
        return False
    pattern = r"^[A-Z]{2}/\d+/\d{4}$"
    return bool(re.match(pattern, registration))


def calculate_age_from_dob(dob: str) -> Optional[int]:
    """Calculate age from date of birth string."""
    try:
        birth_date = datetime.strptime(dob, "%Y-%m-%d")
        today = datetime.now()
        age = (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )
        return age
    except (ValueError, AttributeError):
        return None


def is_within_date_range(date: datetime, days: int = 90) -> bool:
    """Check if date is within specified number of days from today."""
    today = datetime.now()
    cutoff_date = today - timedelta(days=days)
    return cutoff_date <= date <= today


def format_currency(amount: float) -> str:
    """Format amount as Indian currency."""
    return f"₹{amount:,.2f}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove special characters."""
    sanitized = re.sub(r"[^\w\s\-\.]", "", filename)
    sanitized = sanitized.replace(" ", "_")
    return sanitized
