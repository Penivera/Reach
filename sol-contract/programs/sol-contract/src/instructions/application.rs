use anchor_lang::prelude::*;
use anchor_spl::token::TokenAccount;
use anchor_spl::token_2022::spl_token_2022::extension::scaled_ui_amount::UnixTimestamp;
use crate::state::*;
use crate::constants::*;

#[derive(Accounts)]
#[instruction(task_id:u64)]
pub struct ProvideCollateral<'info> {
    #[account(mut)]
    pub provider: Signer<'info>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump
    )]
    task: Account<'info, Task>,
    application: Account<'info, ProviderApplication>,

    #[account(
        mut,
        seeds = [TASK_SEED, task.key().as_ref()],
        bump
    )]
    pub task_vault: Account<'info, TokenAccount>,
    pub provider_token_account: Account<'info,TokenAccount>,
}

#[derive(Accounts)]
#[instruction(task_id:u64)]
pub struct CreateApplication<'info> {
    #[account(mut)]
    pub provider: Signer<'info>,
    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump
    )]
    task: Account<'info, Task>,
    #[account(
        init,
        payer = provider,
        space = 8 + ProviderApplication::INIT_SPACE,
        seeds = [APPLICATION_SEED,provider.key().as_ref()],
        bump
    )]
    pub application: Account<'info, ProviderApplication>,
    pub system_program: Program<'info, System>    
}

pub fn apply(ctx:Context<CreateApplication>,task_id:u64,expires_at:UnixTimestamp)->Result<()>{
    let application = &mut ctx.accounts.application;
    let clock = Clock::get()?;

    application.provider = ctx.accounts.provider.key();
    application.task_id = task_id;
    application.created_at = clock.unix_timestamp;
    application.expires_at = expires_at.into();
    application.status = ProviderApplicationStatus::Pending;
    Ok(())
}