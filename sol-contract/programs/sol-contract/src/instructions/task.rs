use crate::constants::*;
use crate::state::*;
pub use anchor_lang::prelude::*;
use anchor_spl::token::{Mint, Token, TokenAccount};

#[derive(Accounts)]
#[instruction(task_id:u64)]
pub struct CreateTask<'info> {
    #[account(mut)]
    pub creator: Signer<'info>,

    pub stable_coin_mint: Account<'info, Mint>,

    #[account(
        seeds = [STABLE_COIN_SEED, stable_coin_mint.key().as_ref()],
        bump,
    )]
    pub supported_token_check: Account<'info, SupportedStable>,

    #[account(
        init,
        payer = creator,
        space = 8 + Task::INIT_SPACE,
        seeds = [TASK_SEED,task_id.to_le_bytes().as_ref()],
        bump
    )]
    pub task: Account<'info, Task>,

    #[account(
        init,
        payer = creator,
        seeds = [TASK_SEED, task.key().as_ref()],
        token::mint = stable_coin_mint,
        token::authority = task,
        bump,
    )]
    pub task_vault: Account<'info, TokenAccount>,
    #[account(
            mut,
            associated_token::mint = stable_coin_mint,
            associated_token::authority = creator
        )]
    pub creator_token_account: Account<'info, TokenAccount>,

    // System programs required by Solana to initialize accounts
    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn create_task(
    ctx: Context<CreateTask>,
    task_id: u64,
    terms: FinancialTerms,
    tag: Option<String>,
    desc: Option<String>,
) -> Result<()> {
    let total_escrow = terms.labor_fee.checked_add(terms.material_cost).unwrap();

    let cpi_accounts = anchor_spl::token::Transfer {
        from: ctx.accounts.creator_token_account.to_account_info(),
        to: ctx.accounts.task_vault.to_account_info(),
        authority: ctx.accounts.creator.to_account_info(),
    };

    let cpi_context = CpiContext::new(
        ctx.accounts.token_program.key(),
        cpi_accounts,
    );

    anchor_spl::token::transfer(cpi_context, total_escrow)?;

    msg!("Escrow locked for task:{}", task_id);

    let task = &mut ctx.accounts.task;
    let clock = Clock::get()?;

    task.id = task_id;
    task.creator = ctx.accounts.creator.key();
    task.status = TaskStatus::Open;
    task.created_at = clock.unix_timestamp;
    task.updated_at = clock.unix_timestamp;
    task.terms = terms.clone();
    task.tag = tag;
    task.desc = desc;
    task.escrow = EscrowState {
        creator_locked_balance: total_escrow,
        provider_locked_balance: None,
        advanced_disbursed: false,
    };
    msg!("Task created: {}", task_id);

    Ok(())
}
