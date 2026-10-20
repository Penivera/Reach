from decimal import Decimal


class AmountError(ValueError):
    pass


def to_kobo(value) -> int:
    try:
        amount = Decimal(str(value)) * 100
    except Exception as exc:
        raise AmountError("Invalid amount") from exc

    if amount != amount.to_integral_value():
        raise AmountError("Amount cannot have sub-kobo precision")

    return int(amount)


def to_ngn(kobo: int) -> int:
    if kobo <= 0:
        raise AmountError("Amount must be positive")

    if kobo % 100 != 0:
        raise AmountError("FossaPay checkout requires a whole naira amount")

    return kobo // 100


def commission_kobo(amount_kobo: int, basis_points: int) -> int:
    """Commission rounded down to a whole naira."""
    return (amount_kobo * basis_points // 10000) // 100 * 100
