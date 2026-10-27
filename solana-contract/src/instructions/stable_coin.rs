use pinocchio::{error::ProgramError, AccountView, Address, ProgramResult};

use crate::{
    constants::{FEE_VAULT_SEED, STABLE_COIN_SEED, SUPPORTED_STABLE_DISCM},
    cpi::{close_account, create_pda_account, create_pda_token_account},
    instructions::admin::require_admin,
    state::{mut_data, SupportedStable},
};

#[inline(never)]
pub fn add_supported_stable(
    program_id: &Address,
    accounts: &[AccountView],
    name: [u8; 10],
) -> ProgramResult {
    let [caller, reach_state, stable_coin_mint, supported_token, fee_vault, _system_program, _token_program, ..] =
        accounts
    else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_admin(reach_state, caller)?;

    // Initialize supported_token PDA
    let token_space = core::mem::size_of::<SupportedStable>() as u64;
    let token_bump = create_pda_account(
        caller,
        supported_token,
        &[STABLE_COIN_SEED, stable_coin_mint.address().as_ref()],
        token_space,
        program_id,
        program_id,
    )?;

    let token_data = unsafe { mut_data::<SupportedStable>(supported_token) };
    token_data.discriminator = SUPPORTED_STABLE_DISCM;
    token_data.mint = *stable_coin_mint.address();
    token_data.name = name;
    token_data.bump = token_bump;
    token_data._pad = [0; 5];

    // Ensure fee_vault PDA is initialized
    if fee_vault.is_data_empty() {
        create_pda_token_account(
            caller,
            fee_vault,
            &[FEE_VAULT_SEED, stable_coin_mint.address().as_ref()],
            program_id,
            stable_coin_mint,
            reach_state.address(),
        )?;
    }

    Ok(())
}

#[inline(never)]
pub fn remove_supported_stable(accounts: &[AccountView]) -> ProgramResult {
    let [caller, reach_state, _stable_coin_mint, supported_token, ..] = accounts else {
        return Err(ProgramError::NotEnoughAccountKeys);
    };
    require_admin(reach_state, caller)?;

    close_account(*supported_token, *caller)
}
