import re
from datetime import date

from solders.pubkey import Pubkey


class PaymentProfileValidationError(ValueError):
    """Raised when a value cannot be sent to FossaPay as-is."""


def validate_solana_address(value: str) -> str:
    """Validate a Solana address and return its canonical form.

    The address is where a provider's escrow payout is released, so it has to
    be a real, canonical Solana public key.
    """
    if not isinstance(value, str) or not value.strip():
        raise PaymentProfileValidationError("onchain_address is required")

    cleaned = value.strip()

    # A canonical Solana address is 43 or 44 base58 characters. Anything
    # shorter would be a zero-padded key that nobody owns.
    if len(cleaned) not in (43, 44):
        raise PaymentProfileValidationError("That is not a valid Solana address")

    try:
        pubkey = Pubkey.from_string(cleaned)
    except Exception as exc:
        raise PaymentProfileValidationError(
            "That is not a valid Solana address"
        ) from exc

    if pubkey == Pubkey.default():
        raise PaymentProfileValidationError(
            "That is not a valid Solana address"
        )

    canonical = str(pubkey)
    if canonical != cleaned:
        # Reject non-canonical encodings (for example a truncated address).
        raise PaymentProfileValidationError("That is not a valid Solana address")

    return canonical


def validate_single_name(value: str, field: str) -> str:
    """FossaPay accepts exactly one name per field, with no spaces or digits."""
    if not isinstance(value, str):
        raise PaymentProfileValidationError(f"{field} must be a string")

    cleaned = value.strip()

    if not cleaned:
        raise PaymentProfileValidationError(f"{field} is required")

    if len(cleaned) < 2:
        raise PaymentProfileValidationError(f"{field} must be at least 2 characters")

    if len(cleaned) > 100:
        raise PaymentProfileValidationError(f"{field} must be at most 100 characters")

    if any(char.isdigit() for char in cleaned):
        raise PaymentProfileValidationError(f"{field} cannot contain numbers")

    if " " in cleaned:
        raise PaymentProfileValidationError(
            f"{field} must be a single name. Put additional names in middle_name."
        )

    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+", cleaned):
        raise PaymentProfileValidationError(f"{field} contains unsupported characters")

    return cleaned


def normalize_phone_number(value: str) -> str:
    """Normalize Nigerian numbers to E.164; accept other international numbers as-is."""
    if not isinstance(value, str) or not value.strip():
        raise PaymentProfileValidationError("phone_number is required")

    raw = value.strip()
    digits = re.sub(r"\D", "", raw)

    if not digits:
        raise PaymentProfileValidationError("phone_number is invalid")

    # +2348031234567 / 2348031234567
    if digits.startswith("234") and len(digits) == 13:
        return f"+{digits}"

    # 08031234567
    if digits.startswith("0") and len(digits) == 11:
        return f"+234{digits[1:]}"

    # 8031234567
    if len(digits) == 10:
        return f"+234{digits}"

    if 10 <= len(digits) <= 15:
        return f"+{digits}"

    raise PaymentProfileValidationError("phone_number must be a valid international number")


def validate_date_of_birth(value: date) -> date:
    today = date.today()

    if value >= today:
        raise PaymentProfileValidationError("date_of_birth must be in the past")

    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))

    if age < 18:
        raise PaymentProfileValidationError("You must be at least 18 years old")

    if age > 120:
        raise PaymentProfileValidationError("date_of_birth is not valid")

    return value
