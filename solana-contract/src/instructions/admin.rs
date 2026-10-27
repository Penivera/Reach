use pinocchio::{
    cpi::{Seed, Signer},
    error::ProgramError,
    AccountView, Address, ProgramResult,
};

use crate::{
    constants::{MAX_ADMINS, REACH_STATE_DISCM, REACH_STATE_SEED},
    cpi::{cpi_transfer_checked, create_pda_account},
    error::ReachError,
    math::get_mint_decimals,
    state::{const_data, mut_data, AdminEntry, ReachState},
};

#[inline(never)]
pub fn require_admin(reach_state: &AccountView, caller: &AccountView) -> ProgramResult {
    if !caller.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }
    let state = unsafe { const_data::<ReachState>(reach_state) };
    let count = (state.admin_count as usize).min(MAX_ADMINS);
    for i in 0..MAX_ADMINS {
        if i >= count {
            break;
        }
        if state.admins[i].active != 0 && &state.admins[i].address == caller.address() {
            return Ok(());
        }
    }
    Err(ReachError::NotAnAdmin.into())
}

#[inline(never)]
pub fn require_owner(reach_state: &AccountView, caller: &AccountView) -> ProgramResult {
    if !caller.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }
    let state = unsafe { const_data::<ReachState>(reach_state) };
    if &state.owner != caller.address() {
        return Err(ReachError::NotOwner.into());
    }
    Ok(())
}

#[inline(never)]
pub fn initialize(
    program_id: &Address,
    accounts: &[AccountView],
    owner_name: [u8; 10],
) -> ProgramResult {
    let [owner, reach_state, _system_program, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };

    if !owner.is_signer() {
        return Err(ProgramError::MissingRequiredSignature);
    }

    let space = core::mem::size_of::<ReachState>() as u64;
    let bump = create_pda_account(
        owner,
        reach_state,
        &[REACH_STATE_SEED],
        space,
        program_id,
        program_id,
    )?;

    let state = unsafe { mut_data::<ReachState>(reach_state) };
    state.discriminator = REACH_STATE_DISCM;
    state.owner = *owner.address();
    state.cancellation_fee_pct = 1000;
    state.admin_count = 1;
    state.bump = bump;
    state.admins[0].name = owner_name;
    state.admins[0].active = 1;
    state.admins[0].address = *owner.address();

    Ok(())
}

#[inline(never)]
pub fn set_fee_pct(accounts: &[AccountView], fee_pct: u16, is_cancellation: bool) -> ProgramResult {
    let [caller, reach_state, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_admin(reach_state, caller)?;

    if fee_pct > 10_000 {
        return Err(ReachError::FeeTooHigh.into());
    }

    let state = unsafe { mut_data::<ReachState>(reach_state) };
    if is_cancellation {
        state.cancellation_fee_pct = fee_pct;
    } else {
        state.creation_fee_pct = fee_pct;
    }
    Ok(())
}

#[inline(never)]
pub fn propose_owner_update(accounts: &[AccountView], new_owner: Address) -> ProgramResult {
    let [owner, reach_state, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_owner(reach_state, owner)?;

    let state = unsafe { mut_data::<ReachState>(reach_state) };
    if state.has_owner_proposal != 0 {
        return Err(ReachError::OwnerProposalAlreadyActive.into());
    }

    state.owner_proposal = new_owner;
    state.has_owner_proposal = 1;
    state.vote_count = 0;

    Ok(())
}

#[inline(never)]
pub fn vote_owner_update(accounts: &[AccountView]) -> ProgramResult {
    let [caller, reach_state, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_admin(reach_state, caller)?;

    let state = unsafe { mut_data::<ReachState>(reach_state) };
    if state.has_owner_proposal == 0 {
        return Err(ReachError::NoOwnerProposal.into());
    }

    let count = (state.vote_count as usize).min(MAX_ADMINS);
    for i in 0..count {
        if &state.owner_votes[i] == caller.address() {
            return Err(ReachError::AlreadyVoted.into());
        }
    }

    if count < MAX_ADMINS {
        state.owner_votes[count] = *caller.address();
        state.vote_count += 1;
    }

    let admin_count = (state.admin_count as usize).min(MAX_ADMINS);
    let mut active_admins = 0;
    for i in 0..admin_count {
        if state.admins[i].active != 0 {
            active_admins += 1;
        }
    }

    if (state.vote_count as usize) > active_admins / 2 {
        state.owner = state.owner_proposal;
        state.has_owner_proposal = 0;
        state.vote_count = 0;
    }

    Ok(())
}

#[inline(never)]
pub fn withdraw_protocol_fees(accounts: &[AccountView], amount: u64) -> ProgramResult {
    let [owner, reach_state, stable_coin_mint, fee_vault, receiver, _token_program, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_owner(reach_state, owner)?;

    let state = unsafe { const_data::<ReachState>(reach_state) };
    let bump_bytes = [state.bump];
    let seeds = [Seed::from(REACH_STATE_SEED), Seed::from(&bump_bytes)];
    let signers = [Signer::from(&seeds)];

    let decimals = get_mint_decimals(stable_coin_mint);

    cpi_transfer_checked(
        fee_vault,
        stable_coin_mint,
        receiver,
        reach_state,
        amount,
        decimals,
        &signers,
    )
}

#[inline(never)]
pub fn add_admin(accounts: &[AccountView], name: [u8; 10], address: Address) -> ProgramResult {
    let [owner, reach_state, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_owner(reach_state, owner)?;

    let state = unsafe { mut_data::<ReachState>(reach_state) };
    let count = state.admin_count as usize;
    if count >= MAX_ADMINS {
        return Err(ReachError::TooManyAdmins.into());
    }

    state.admins[count] = AdminEntry {
        name,
        active: 1,
        _pad: [0; 5],
        address,
    };
    state.admin_count += 1;

    Ok(())
}

#[inline(never)]
pub fn remove_admin(accounts: &[AccountView], address: Address) -> ProgramResult {
    let [owner, reach_state, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_owner(reach_state, owner)?;

    let state = unsafe { mut_data::<ReachState>(reach_state) };
    let admin_count = (state.admin_count as usize).min(MAX_ADMINS);
    for i in 0..MAX_ADMINS {
        if i >= admin_count {
            break;
        }
        if state.admins[i].address == address {
            state.admins[i].active = 0;
        }
    }

    Ok(())
}
