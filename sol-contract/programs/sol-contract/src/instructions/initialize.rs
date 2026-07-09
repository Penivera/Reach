use anchor_lang::prelude::*;
use crate::state::*;
use crate::constants::*;

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,

    #[account(
        init,
        payer = owner,
        space = 8 + ReachState::INIT_SPACE,
        seeds = [REACH_STATE_SEED],
        bump
    )]
    pub reach_state: Account<'info, ReachState>,

    pub system_program: Program<'info, System>,    
}

pub fn handler(ctx: Context<Initialize>, owner_name: String) -> Result<()> {
    let state = &mut ctx.accounts.reach_state;
    state.owner = ctx.accounts.owner.key();
    state.task_count = 0;
    state.application_count = 0;
    state.admins = Vec::new();
    state.admins.push(Admin { name: owner_name, address: ctx.accounts.owner.key(), active: true });
    
    Ok(())
}