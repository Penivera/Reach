use pinocchio::{
    error::ProgramError,
    sysvars::{clock::Clock, Sysvar},
    AccountView, Address, ProgramResult,
};

use crate::{
    constants::{APPLICATION_DISCM, APPLICATION_SEED, PROVIDER_DEBT_DISCM, PROVIDER_DEBT_SEED},
    cpi::{
        close_account, cpi_task_transfer_checked, cpi_transfer_checked,
        cpi_user_transfer_checked_pair, create_pda_account,
    },
    error::ReachError,
    math::{get_mint_decimals, mul_div_64},
    state::{
        const_data, mut_data, ProviderApplication, ProviderApplicationStatus, ProviderDebt,
        ReachState, Task, TaskStatus,
    },
};

#[inline(never)]
pub fn apply(
    program_id: &Address,
    accounts: &[AccountView],
    task_id: u64,
    expires_at: i64,
) -> ProgramResult {
    let [provider, task, application, provider_debt, _system_program, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !provider.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    if !provider_debt.is_data_empty() {
        let debt_data = unsafe { const_data::<ProviderDebt>(provider_debt) };
        if debt_data.has_debt != 0 {
            return Err(ReachError::ProviderHasDebt.into());
        }
    }

    let app_space = core::mem::size_of::<ProviderApplication>() as u64;
    let app_bump = create_pda_account(
        provider,
        application,
        &[
            APPLICATION_SEED,
            provider.address().as_ref(),
            task.address().as_ref(),
        ],
        app_space,
        program_id,
        program_id,
    )?;

    let app_data = unsafe { mut_data::<ProviderApplication>(application) };
    let now = Clock::get()?.unix_timestamp;

    app_data.discriminator = APPLICATION_DISCM;
    app_data.provider = *provider.address();
    app_data.task_id = task_id;
    app_data.status = ProviderApplicationStatus::Pending as u8;
    app_data.bump = app_bump;
    app_data._pad = [0; 6];
    app_data.created_at = now;
    app_data.expires_at = expires_at;

    Ok(())
}

#[inline(never)]
pub fn accept(accounts: &[AccountView], provider: Address) -> ProgramResult {
    let [owner, task, application, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !owner.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let task_data = unsafe { mut_data::<Task>(task) };
    if &task_data.creator != owner.address() {
        return Err(ReachError::NotOwner.into());
    }

    if task_data.status != TaskStatus::Open as u8 {
        return Err(ReachError::InvalidTaskStatus.into());
    }

    let app_data = unsafe { mut_data::<ProviderApplication>(application) };
    if app_data.status != ProviderApplicationStatus::Pending as u8 {
        return Err(ReachError::ApplicationNotAccepted.into());
    }

    task_data.provider = provider;
    task_data.has_provider = 1;

    if task_data.terms.required_provider_collateral > 0 {
        app_data.status = ProviderApplicationStatus::AcceptedPendingCollateral as u8;
        task_data.status = TaskStatus::AwaitingEscrow as u8;
    } else {
        app_data.status = ProviderApplicationStatus::Accepted as u8;
        task_data.status = TaskStatus::InProgress as u8;
    }

    Ok(())
}

#[inline(never)]
pub fn provide_collateral(accounts: &[AccountView]) -> ProgramResult {
    let [provider, task, application, task_vault, provider_token_account, stable_coin_mint, _supported_token_check, _token_program, ..] =
        accounts
    else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !provider.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let task_data = unsafe { mut_data::<Task>(task) };
    let app_data = unsafe { mut_data::<ProviderApplication>(application) };

    if task_data.terms.required_provider_collateral == 0 {
        return Err(ReachError::NoCollateralRequired.into());
    }

    if task_data.status != TaskStatus::AwaitingEscrow as u8 {
        return Err(ReachError::NotAwaitingEscrow.into());
    }

    if app_data.status != ProviderApplicationStatus::AcceptedPendingCollateral as u8 {
        return Err(ReachError::ApplicationNotAccepted.into());
    }

    let collateral_amount = task_data.terms.required_provider_collateral;
    let decimals = get_mint_decimals(stable_coin_mint);

    // Provider deposits collateral into task_vault
    cpi_transfer_checked(
        provider_token_account,
        stable_coin_mint,
        task_vault,
        provider,
        collateral_amount,
        decimals,
        &[],
    )?;

    app_data.status = ProviderApplicationStatus::AcceptedAndCollateralProvided as u8;
    task_data.escrow.provider_locked_balance = collateral_amount;
    task_data.escrow.has_provider_locked_balance = 1;
    task_data.status = TaskStatus::InProgress as u8;

    // Disburse advance if configured
    if task_data.terms.upfront_release_pct > 0 {
        disburse_advance(task, task_vault, stable_coin_mint, provider_token_account)?;
    }

    Ok(())
}

#[inline(never)]
fn disburse_advance(
    task: &AccountView,
    task_vault: &AccountView,
    stable_coin_mint: &AccountView,
    provider_token_account: &AccountView,
) -> ProgramResult {
    let task_data = unsafe { mut_data::<Task>(task) };
    let advance_amount = mul_div_64(
        task_data.terms.material_cost,
        task_data.terms.upfront_release_pct as u64,
        100,
    )?;
    cpi_task_transfer_checked(
        task_vault,
        stable_coin_mint,
        provider_token_account,
        task,
        advance_amount,
    )?;
    task_data.escrow.advanced_disbursed = 1;
    Ok(())
}

#[inline(never)]
pub fn claim_advance(accounts: &[AccountView]) -> ProgramResult {
    let [provider, task, task_vault, provider_token_account, stable_coin_mint, _token_program, ..] =
        accounts
    else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !provider.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let task_data = unsafe { const_data::<Task>(task) };
    if task_data.has_provider == 0 || &task_data.provider != provider.address() {
        return Err(ReachError::NotTaskProvider.into());
    }

    if task_data.terms.upfront_release_pct == 0 {
        return Err(ReachError::NoAdvanceToClaim.into());
    }

    if task_data.escrow.advanced_disbursed != 0 {
        return Err(ReachError::AdvanceAlreadyDisbursed.into());
    }

    disburse_advance(task, task_vault, stable_coin_mint, provider_token_account)
}

#[inline(never)]
pub fn cancel_approved_application(
    program_id: &Address,
    accounts: &[AccountView],
) -> ProgramResult {
    let [provider, task, task_vault, application, reach_state, fee_vault, provider_token_account, stable_coin_mint, provider_debt, _system_program, _token_program, ..] =
        accounts
    else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !provider.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let task_data = unsafe { mut_data::<Task>(task) };
    if task_data.has_provider == 0 || &task_data.provider != provider.address() {
        return Err(ReachError::NotTaskProvider.into());
    }

    let app_data = unsafe { mut_data::<ProviderApplication>(application) };
    let app_status = app_data.status;
    if app_status < 1 || app_status > 3 {
        return Err(ReachError::CannotCancelApplication.into());
    }

    let mut debt_bump = 0u8;
    if provider_debt.is_data_empty() {
        let debt_space = core::mem::size_of::<ProviderDebt>() as u64;
        debt_bump = create_pda_account(
            provider,
            provider_debt,
            &[PROVIDER_DEBT_SEED, provider.address().as_ref()],
            debt_space,
            program_id,
            program_id,
        )?;
    }

    let provider_locked_balance = if task_data.escrow.has_provider_locked_balance != 0 {
        task_data.escrow.provider_locked_balance
    } else {
        0
    };

    let advance_amount =
        if task_data.escrow.advanced_disbursed != 0 && task_data.terms.upfront_release_pct > 0 {
            mul_div_64(
                task_data.terms.material_cost,
                task_data.terms.upfront_release_pct as u64,
                100,
            )?
        } else {
            0
        };

    let decimals = get_mint_decimals(stable_coin_mint);

    let has_debt = if advance_amount <= provider_locked_balance {
        let provider_refund = provider_locked_balance
            .checked_sub(advance_amount)
            .ok_or(ProgramError::ArithmeticOverflow)?;

        cpi_task_transfer_checked(
            task_vault,
            stable_coin_mint,
            provider_token_account,
            task,
            provider_refund,
        )?;

        app_data.status = ProviderApplicationStatus::Rejected as u8;
        0
    } else {
        let difference = advance_amount
            .checked_sub(provider_locked_balance)
            .ok_or(ProgramError::ArithmeticOverflow)?;

        let state = unsafe { const_data::<ReachState>(reach_state) };
        let fee_amount = mul_div_64(
            task_data.escrow.creator_locked_balance,
            state.cancellation_fee_pct as u64,
            10_000,
        )?;

        cpi_user_transfer_checked_pair(
            provider_token_account,
            stable_coin_mint,
            provider,
            task_vault,
            difference,
            fee_vault,
            fee_amount,
            decimals,
        )?;

        app_data.status = ProviderApplicationStatus::CancelledWithDebt as u8;
        1
    };

    let debt = unsafe { mut_data::<ProviderDebt>(provider_debt) };
    debt.discriminator = PROVIDER_DEBT_DISCM;
    debt.provider = *provider.address();
    debt.has_debt = has_debt;
    if debt_bump != 0 {
        debt.bump = debt_bump;
    }

    task_data.provider = Address::default();
    task_data.has_provider = 0;
    task_data.status = TaskStatus::Open as u8;
    task_data.escrow.provider_locked_balance = 0;
    task_data.escrow.has_provider_locked_balance = 0;
    task_data.escrow.advanced_disbursed = 0;

    Ok(())
}

#[inline(never)]
pub fn withdraw_application(accounts: &[AccountView]) -> ProgramResult {
    if accounts.len() < 2 {
        return Err(ProgramError::NotEnoughAccountKeys);
    }
    let provider = &accounts[0];
    let application = if accounts.len() == 2 {
        &accounts[1]
    } else {
        &accounts[2]
    };

    if !provider.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let app_data = unsafe { const_data::<ProviderApplication>(application) };
    if app_data.status != ProviderApplicationStatus::Pending as u8 {
        return Err(ReachError::CannotCancelApplication.into());
    }

    close_account(*application, *provider)
}
