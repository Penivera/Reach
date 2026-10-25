use pinocchio::{
    error::ProgramError,
    sysvars::{clock::Clock, Sysvar},
    AccountView, Address, ProgramResult,
};

use crate::{
    constants::{TASK_DISCM, TASK_SEED},
    cpi::{
        cpi_task_transfer_checked, cpi_task_transfer_checked_pair,
        cpi_user_transfer_checked_pair, create_pda_account, create_pda_token_account,
    },
    error::ReachError,
    instructions::admin::require_admin,
    math::{get_mint_decimals, get_token_balance, mul_div_64},
    state::{const_data, mut_data, FinancialTerms, ReachState, Task, TaskStatus},
};

#[inline(never)]
pub fn create_task(
    program_id: &Address,
    accounts: &[AccountView],
    task_id: u64,
    terms: FinancialTerms,
    metadata_hash: [u8; 32],
) -> ProgramResult {
    if accounts.len() < 8 {
        return Err(ProgramError::NotEnoughAccountKeys);
    }
    let creator = &accounts[0];
    let stable_coin_mint = &accounts[1];
    let supported_token_check = &accounts[2];
    let reach_state = &accounts[3];
    let fee_vault = &accounts[4];
    let task = &accounts[5];
    let task_vault = &accounts[6];
    let creator_token_account = &accounts[7];

    if !creator.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    // Verify supported token account is owned by program and initialized for this mint
    if !supported_token_check.owned_by(program_id) || supported_token_check.data_len() != 56 {
        return Err(ProgramError::InvalidAccountOwner);
    }
    let supported_token = unsafe { const_data::<crate::state::SupportedStable>(supported_token_check) };
    if supported_token.mint != *stable_coin_mint.address() {
        return Err(ProgramError::InvalidAccountData);
    }

    let total_escrow = terms
        .labor_fee
        .checked_add(terms.material_cost)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    let state = unsafe { mut_data::<ReachState>(reach_state) };
    let creation_fee = mul_div_64(total_escrow, state.creation_fee_pct as u64, 10_000)?;

    // Create Task PDA: [b"task", task_id.to_le_bytes()]
    let task_id_bytes = task_id.to_le_bytes();
    let task_space = core::mem::size_of::<Task>() as u64;
    let task_bump = create_pda_account(
        creator,
        task,
        &[TASK_SEED, &task_id_bytes],
        task_space,
        program_id,
        program_id,
    )?;

    // Create Task Vault PDA and initialize token account
    create_pda_token_account(
        creator,
        task_vault,
        &[TASK_SEED, task.address().as_ref()],
        program_id,
        stable_coin_mint,
        task.address(),
    )?;

    let decimals = get_mint_decimals(stable_coin_mint);

    // Transfer escrow and creation fee from creator
    cpi_user_transfer_checked_pair(
        creator_token_account,
        stable_coin_mint,
        creator,
        task_vault,
        total_escrow,
        fee_vault,
        creation_fee,
        decimals,
    )?;

    let task_data = unsafe { mut_data::<Task>(task) };
    let now = Clock::get()?.unix_timestamp;

    task_data.discriminator = TASK_DISCM;
    task_data.id = task_id;
    task_data.creator = *creator.address();
    task_data.bump = task_bump;
    task_data.stable_coin_mint = *stable_coin_mint.address();
    task_data.metadata_hash = metadata_hash;
    task_data.terms = terms;
    task_data.escrow.creator_locked_balance = total_escrow;
    task_data.created_at = now;
    task_data.updated_at = now;

    state.task_count += 1;

    Ok(())
}

#[inline(never)]
pub fn cancel_task(
    accounts: &[AccountView],
) -> ProgramResult {
    let [creator, task, task_vault, reach_state, fee_vault, creator_token_account, stable_coin_mint, _system_program, _token_program, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !creator.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let task_data = unsafe { mut_data::<Task>(task) };
    if &task_data.creator != creator.address() {
        return Err(ReachError::NotOwner.into());
    }

    if task_data.status != TaskStatus::Open as u8 && task_data.status != TaskStatus::AwaitingEscrow as u8 {
        return Err(ReachError::CannotCancelTask.into());
    }

    let state = unsafe { const_data::<ReachState>(reach_state) };
    let total_escrow = task_data.escrow.creator_locked_balance;
    let cancellation_fee = mul_div_64(total_escrow, state.cancellation_fee_pct as u64, 10_000)?;
    let refund_amount = total_escrow.checked_sub(cancellation_fee).ok_or(ProgramError::ArithmeticOverflow)?;

    cpi_task_transfer_checked_pair(
        task_vault,
        stable_coin_mint,
        task,
        creator_token_account,
        refund_amount,
        fee_vault,
        cancellation_fee,
    )?;

    task_data.status = TaskStatus::Refunded as u8;
    task_data.escrow.creator_locked_balance = 0;

    Ok(())
}

#[inline(never)]
pub fn complete_task(
    accounts: &[AccountView],
) -> ProgramResult {
    let [provider, task, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !provider.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let task_data = unsafe { mut_data::<Task>(task) };
    if task_data.has_provider == 0 || &task_data.provider != provider.address() {
        return Err(ReachError::NotTaskProvider.into());
    }

    if task_data.status != TaskStatus::InProgress as u8 {
        return Err(ReachError::InvalidTaskStatus.into());
    }

    task_data.status = TaskStatus::AwaitingApproval as u8;
    Ok(())
}

#[inline(never)]
pub fn approve_work(
    accounts: &[AccountView],
) -> ProgramResult {
    let [creator, task, task_vault, provider_token_account, stable_coin_mint, _token_program, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !creator.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let task_data = unsafe { mut_data::<Task>(task) };
    if &task_data.creator != creator.address() {
        return Err(ReachError::NotOwner.into());
    }

    if task_data.status != TaskStatus::AwaitingApproval as u8 {
        return Err(ReachError::InvalidTaskStatus.into());
    }

    let provider_locked = if task_data.escrow.has_provider_locked_balance != 0 {
        task_data.escrow.provider_locked_balance
    } else {
        0
    };

    let advance_amount = if task_data.escrow.advanced_disbursed != 0 && task_data.terms.upfront_release_pct > 0 {
        mul_div_64(task_data.terms.material_cost, task_data.terms.upfront_release_pct as u64, 100)?
    } else {
        0
    };

    let remaining_creator_escrow = task_data
        .escrow
        .creator_locked_balance
        .checked_sub(advance_amount)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    let payout_amount = remaining_creator_escrow
        .checked_add(provider_locked)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    cpi_task_transfer_checked(
        task_vault,
        stable_coin_mint,
        provider_token_account,
        task,
        payout_amount,
    )?;

    task_data.status = TaskStatus::Completed as u8;
    task_data.escrow.creator_locked_balance = 0;
    task_data.escrow.provider_locked_balance = 0;
    task_data.escrow.has_provider_locked_balance = 0;

    Ok(())
}

#[inline(never)]
pub fn raise_dispute(
    accounts: &[AccountView],
) -> ProgramResult {
    let [caller, task, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !caller.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let task_data = unsafe { mut_data::<Task>(task) };
    let is_caller = caller.address() == &task_data.creator
        || (task_data.has_provider != 0 && caller.address() == &task_data.provider);

    if !is_caller {
        return Err(ReachError::InvalidDisputeCaller.into());
    }

    if task_data.status != TaskStatus::InProgress as u8 && task_data.status != TaskStatus::AwaitingApproval as u8 {
        return Err(ReachError::InvalidDisputeStatus.into());
    }

    task_data.status = TaskStatus::Disputed as u8;
    Ok(())
}

#[inline(never)]
pub fn resolve_dispute(
    accounts: &[AccountView],
    creator_refund_pct: u8,
    provider_payment_pct: u8,
) -> ProgramResult {
    let [caller, reach_state, task, task_vault, creator_token_account, provider_token_account, stable_coin_mint, _token_program, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_admin(reach_state, caller)?;

    let task_data = unsafe { mut_data::<Task>(task) };
    if task_data.status != TaskStatus::Disputed as u8 {
        return Err(ReachError::InvalidTaskStatus.into());
    }

    if (creator_refund_pct as u16 + provider_payment_pct as u16) != 100 {
        return Err(ReachError::InvalidDisputeSplit.into());
    }

    let total_funds = get_token_balance(task_vault);
    let creator_refund = mul_div_64(total_funds, creator_refund_pct as u64, 100)?;
    let provider_payment = total_funds.checked_sub(creator_refund).ok_or(ProgramError::ArithmeticOverflow)?;

    cpi_task_transfer_checked_pair(
        task_vault,
        stable_coin_mint,
        task,
        creator_token_account,
        creator_refund,
        provider_token_account,
        provider_payment,
    )?;

    task_data.status = TaskStatus::Refunded as u8;
    task_data.escrow.creator_locked_balance = 0;
    task_data.escrow.provider_locked_balance = 0;
    task_data.escrow.has_provider_locked_balance = 0;

    Ok(())
}
