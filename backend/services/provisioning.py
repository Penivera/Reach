from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.fossapay import FossaPayNotConfigured, get_fossapay_client
from DB import AsyncSessionLocal
from models import FossaPayCustomer, PaymentProfile, User
from schemas.enums import ProvisioningStatus
from payment_validation import (
    PaymentProfileValidationError,
    normalize_phone_number,
    validate_single_name,
)


class PaymentProfileIncomplete(Exception):
    pass


def build_customer_payload(user: User, profile: PaymentProfile) -> dict:
    try:
        first_name = validate_single_name(user.first_name, "first_name")
        last_name = validate_single_name(user.last_name, "last_name")
        mobile_number = normalize_phone_number(user.phone_number)
    except PaymentProfileValidationError as exc:
        raise PaymentProfileIncomplete(str(exc)) from exc

    payload = {
        "firstName": first_name,
        "lastName": last_name,
        "emailAddress": user.email,
        "mobileNumber": mobile_number,
        "dateOfBirth": profile.date_of_birth.isoformat(),
        "address": profile.address,
        "city": profile.city,
        "country": profile.country or "Nigeria",
        "type": "individual",
        "metadata": {"reach_user_id": user.id},
    }

    if profile.middle_name:
        payload["middleName"] = profile.middle_name

    return payload


async def ensure_customer_record(user_id: int, db: AsyncSession) -> FossaPayCustomer:
    result = await db.execute(
        select(FossaPayCustomer).where(FossaPayCustomer.user_id == user_id)
    )
    record = result.scalar_one_or_none()

    if record:
        return record

    record = FossaPayCustomer(user_id=user_id, status=ProvisioningStatus.PENDING)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def provision_user(user: User, db: AsyncSession) -> FossaPayCustomer:
    result = await db.execute(
        select(PaymentProfile).where(PaymentProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise PaymentProfileIncomplete("Complete your payment profile first")

    record = await ensure_customer_record(user.id, db)

    if record.status == ProvisioningStatus.PROVISIONED:
        return record

    if record.provider_customer_id and record.wallet_id:
        record.status = ProvisioningStatus.PROVISIONED
        record.last_error = None
        await db.commit()
        await db.refresh(record)
        return record

    try:
        client = get_fossapay_client()

        if not record.provider_customer_id:
            customer = await client.create_customer(build_customer_payload(user, profile))
            record.provider_customer_id = str(customer["id"])
            await db.commit()

        if not record.wallet_id:
            wallet = await client.create_fiat_wallet(
                customer_id=record.provider_customer_id,
                wallet_name=(
                    f"{user.first_name or ''} {user.last_name or ''}".strip()
                    or user.username
                ),
                wallet_reference=f"reach-user-{user.id}",
            )
            record.wallet_id = str(wallet["walletId"])
            record.account_number = wallet.get("accountNumber")
            record.account_name = wallet.get("accountName")
            record.bank_name = wallet.get("bankName")
            record.bank_code = wallet.get("bankCode")
            record.status = ProvisioningStatus.PROVISIONED
            record.last_error = None
            await db.commit()

    except FossaPayNotConfigured as exc:
        record.status = ProvisioningStatus.PENDING
        record.last_error = str(exc)
        await db.commit()

    except Exception as exc:
        record.status = ProvisioningStatus.FAILED
        record.last_error = str(exc)[:1000]
        await db.commit()

    await db.refresh(record)
    return record


async def provision_user_by_id(user_id: int) -> None:
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        if user:
            await provision_user(user, db)
