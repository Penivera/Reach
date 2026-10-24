"""Provider payout aliases.

The canonical provider cash-out implementation lives in ``/payments/offramp``.
These routes expose the same records under ``/payouts`` for the provider
dashboard, plus the bank-account resolution step the UI needs before creating
a payout.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.obiex import ObiexError, ObiexNotConfigured
from dependencies import get_current_user, get_db
from schemas import (
    BankResolveRequest,
    BankResolveResponse,
    OffRampBankResponse,
    OffRampWithdrawalResponse,
)
from services import offramp

router = APIRouter(prefix="/payouts", tags=["payouts"])


def _payout_error(exc: offramp.OffRampError) -> HTTPException:
    if isinstance(exc, offramp.OffRampDisabled):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, offramp.OffRampNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, offramp.OffRampConflict):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/me", response_model=list[OffRampWithdrawalResponse])
async def my_payouts(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """The provider's naira payout history."""
    return await offramp.list_withdrawals(db, user_id=current_user.id)


@router.get("/banks", response_model=list[OffRampBankResponse])
async def payout_banks(current_user=Depends(get_current_user)):
    """Nigerian banks available for a payout."""
    try:
        return await offramp.list_banks()
    except offramp.OffRampError as exc:
        raise _payout_error(exc)
    except (ObiexError, ObiexNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/banks/resolve", response_model=BankResolveResponse)
async def resolve_payout_account(
    data: BankResolveRequest,
    current_user=Depends(get_current_user),
):
    """Resolve the account name before the provider confirms a payout."""
    try:
        return await offramp.resolve_account(
            bank_code=data.bank_code,
            account_number=data.account_number,
        )
    except offramp.OffRampError as exc:
        raise _payout_error(exc)
    except (ObiexError, ObiexNotConfigured) as exc:
        raise HTTPException(status_code=503, detail=str(exc))
