use crate::constants::*;
use crate::error::ErrorCode;
use crate::state::*;
use anchor_lang::prelude::*;
use anchor_spl::token::Mint;

#[derive(Accounts)]
pub struct AddSupportedStable<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
        constraint = reach_state.admins.iter().any(|admin| admin.address == caller.key())
        @ErrorCode::NotAnAdmin
    )]
    pub reach_state: Account<'info, ReachState>,

    pub stable_coin_mint: Account<'info, Mint>,

    #[account(
            init,
            payer = caller,
            space = 8 + SupportedStable::INIT_SPACE,
            seeds = [STABLE_COIN_SEED, stable_coin_mint.key().as_ref()],
            bump
        )]
    pub supported_token: Account<'info, SupportedStable>,

    pub system_program: Program<'info, System>,
}

pub fn add_supported_stable(ctx: Context<AddSupportedStable>, stable_name: String) -> Result<()> {
    let supported_token = &mut ctx.accounts.supported_token;
    supported_token.mint = ctx.accounts.stable_coin_mint.key();
    supported_token.name = stable_name;

    Ok(())
}

#[derive(Accounts)]
pub struct RemoveSupportedStable<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,

    #[account(
        seeds = [REACH_STATE_SEED],
        bump,
        constraint = reach_state.admins.iter().any(|admin| admin.address == caller.key()) @ ErrorCode::NotAnAdmin
    )]
    pub reach_state: Account<'info, ReachState>,

    pub stable_coin_mint: Account<'info, Mint>,

    #[account(
        mut,
        close = caller,
        seeds = [STABLE_COIN_SEED, stable_coin_mint.key().as_ref()],
        bump,
    )]
    pub supported_token: Account<'info, SupportedStable>,
}

pub fn remove_supported_stable(_ctx: Context<RemoveSupportedStable>) -> Result<()> {
    msg!("Supported stablecoin removed and account closed.");
    Ok(())
}
