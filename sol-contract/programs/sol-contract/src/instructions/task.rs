use crate::constants::*;
use crate::state::*;
use crate::error::ErrorCode;
use anchor_lang::prelude::*;
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
        seeds = [REACH_STATE_SEED],
        bump,
    )]
    pub reach_state: Account<'info, ReachState>,

    #[account(
        init_if_needed,
        payer = creator,
        seeds = [b"fee_vault", stable_coin_mint.key().as_ref()],
        bump,
        token::mint = stable_coin_mint,
        token::authority = reach_state,
    )]
    pub fee_vault: Account<'info, TokenAccount>,

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
    let fee_pct = ctx.accounts.reach_state.creation_fee_pct as u64;
    let creation_fee = (total_escrow as u128)
        .checked_mul(fee_pct as u128).unwrap()
        .checked_div(10000).unwrap() as u64;

    let cpi_accounts = anchor_spl::token::TransferChecked {
        from: ctx.accounts.creator_token_account.to_account_info(),
        to: ctx.accounts.task_vault.to_account_info(),
        authority: ctx.accounts.creator.to_account_info(),
        mint: ctx.accounts.stable_coin_mint.to_account_info(),
    };

    let cpi_context = CpiContext::new(
        ctx.accounts.token_program.key(),
        cpi_accounts,
    );

    anchor_spl::token::transfer_checked(cpi_context, total_escrow, ctx.accounts.stable_coin_mint.decimals)?;

    msg!("Escrow locked for task:{}", task_id);

    if creation_fee > 0 {
        let fee_cpi_accounts = anchor_spl::token::TransferChecked {
            from: ctx.accounts.creator_token_account.to_account_info(),
            to: ctx.accounts.fee_vault.to_account_info(),
            authority: ctx.accounts.creator.to_account_info(),
            mint: ctx.accounts.stable_coin_mint.to_account_info(),
        };

        let fee_cpi_context = CpiContext::new(
            ctx.accounts.token_program.key(),
            fee_cpi_accounts,
        );

        anchor_spl::token::transfer_checked(fee_cpi_context, creation_fee, ctx.accounts.stable_coin_mint.decimals)?;
        msg!("Protocol creation fee paid: {}", creation_fee);
    }

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

#[derive(Accounts)]
#[instruction(task_id:u64,provider:Pubkey)]
pub struct AcceptApplication<'info> {
    pub owner: Signer<'info>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump
    )]
    pub task: Account<'info, Task>,

    #[account(
        mut,
        seeds = [APPLICATION_SEED, provider.as_ref(), task.key().as_ref()],
        bump
    )]
    pub application: Account<'info, ProviderApplication>,
}

#[allow(unused_variables)]
pub fn accept_application(ctx: Context<AcceptApplication>, task_id: u64, provider: Pubkey) -> Result<()> {
    let application = &mut ctx.accounts.application;
    let task = &mut ctx.accounts.task;
    task.provider = Some(provider);
    
    if task.terms.required_provider_collateral > 0 {
        application.status = ProviderApplicationStatus::AcceptedPendingCollateral;
        task.status = TaskStatus::AwaitingEscrow;
    }else{
        application.status = ProviderApplicationStatus::Accepted;
        task.status = TaskStatus::InProgress;
    }
    Ok(())
}

#[derive(Accounts)]
#[instruction(task_id: u64)]
pub struct CancelTask<'info> {
    #[account(mut)]
    pub creator: Signer<'info>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump,
        constraint = task.creator == creator.key() @ ErrorCode::NotOwner,
    )]
    pub task: Account<'info, Task>,

    #[account(
        mut,
        seeds = [TASK_SEED, task.key().as_ref()],
        bump,
    )]
    pub task_vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
    )]
    pub reach_state: Account<'info, ReachState>,

    #[account(
        init_if_needed,
        payer = creator,
        seeds = [b"fee_vault", stable_coin_mint.key().as_ref()],
        bump,
        token::mint = stable_coin_mint,
        token::authority = reach_state,
    )]
    pub fee_vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        token::mint = stable_coin_mint,
    )]
    pub creator_token_account: Account<'info, TokenAccount>,

    pub stable_coin_mint: Account<'info, Mint>,

    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn cancel_task(ctx: Context<CancelTask>, task_id: u64) -> Result<()> {
    let task = &mut ctx.accounts.task;

    require!(
        task.status == TaskStatus::Open || task.status == TaskStatus::AwaitingEscrow,
        ErrorCode::CannotCancelTask
    );

    let total_escrow = task.escrow.creator_locked_balance;
    let fee_pct = ctx.accounts.reach_state.cancellation_fee_pct as u64;
    let cancellation_fee = (total_escrow as u128)
        .checked_mul(fee_pct as u128).unwrap()
        .checked_div(10000).unwrap() as u64;

    let refund_amount = total_escrow.checked_sub(cancellation_fee).unwrap();

    let task_id_bytes = task_id.to_le_bytes();
    let seeds: &[&[u8]] = &[TASK_SEED, task_id_bytes.as_ref(), &[ctx.bumps.task]];
    let signer_seeds = &[seeds];

    // Transfer refund to creator
    if refund_amount > 0 {
        let cpi_accounts = anchor_spl::token::TransferChecked {
            from: ctx.accounts.task_vault.to_account_info(),
            to: ctx.accounts.creator_token_account.to_account_info(),
            authority: task.to_account_info(),
            mint: ctx.accounts.stable_coin_mint.to_account_info(),
        };

        let cpi_context = CpiContext::new_with_signer(
            ctx.accounts.token_program.key(),
            cpi_accounts,
            signer_seeds,
        );

        anchor_spl::token::transfer_checked(cpi_context, refund_amount, ctx.accounts.stable_coin_mint.decimals)?;
    }

    // Transfer cancellation fee to fee vault
    if cancellation_fee > 0 {
        let fee_cpi_accounts = anchor_spl::token::TransferChecked {
            from: ctx.accounts.task_vault.to_account_info(),
            to: ctx.accounts.fee_vault.to_account_info(),
            authority: task.to_account_info(),
            mint: ctx.accounts.stable_coin_mint.to_account_info(),
        };

        let fee_cpi_context = CpiContext::new_with_signer(
            ctx.accounts.token_program.key(),
            fee_cpi_accounts,
            signer_seeds,
        );

        anchor_spl::token::transfer_checked(fee_cpi_context, cancellation_fee, ctx.accounts.stable_coin_mint.decimals)?;
    }

    task.status = TaskStatus::Refunded;
    task.escrow.creator_locked_balance = 0;

    msg!("Task {} cancelled. Refunded: {}, Fee paid: {}", task_id, refund_amount, cancellation_fee);

    Ok(())
}

#[derive(Accounts)]
#[instruction(task_id: u64)]
pub struct CompleteTask<'info> {
    #[account(mut)]
    pub provider: Signer<'info>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump,
        constraint = task.provider == Some(provider.key()) @ ErrorCode::NotTaskProvider,
    )]
    pub task: Account<'info, Task>,
}

pub fn complete_task(ctx: Context<CompleteTask>, _task_id: u64) -> Result<()> {
    let task = &mut ctx.accounts.task;
    require!(task.status == TaskStatus::InProgress, ErrorCode::InvalidTaskStatus);
    task.status = TaskStatus::AwaitingApproval;
    Ok(())
}

#[derive(Accounts)]
#[instruction(task_id: u64)]
pub struct ApproveWork<'info> {
    #[account(mut)]
    pub creator: Signer<'info>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump,
        constraint = task.creator == creator.key() @ ErrorCode::NotOwner,
    )]
    pub task: Box<Account<'info, Task>>,

    #[account(
        mut,
        seeds = [TASK_SEED, task.key().as_ref()],
        bump,
    )]
    pub task_vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        constraint = provider_token_account.owner == task.provider.unwrap() @ ErrorCode::NotTaskProvider,
    )]
    pub provider_token_account: Account<'info, TokenAccount>,

    pub stable_coin_mint: Account<'info, Mint>,
    pub token_program: Program<'info, Token>,
}

pub fn approve_work(ctx: Context<ApproveWork>, task_id: u64) -> Result<()> {
    let task = &mut ctx.accounts.task;
    require!(task.status == TaskStatus::AwaitingApproval, ErrorCode::InvalidTaskStatus);

    let provider_locked_balance = task.escrow.provider_locked_balance.unwrap_or(0);
    let mut advance_amount = 0;
    if task.escrow.advanced_disbursed && task.terms.upfront_release_pct > 0 {
        let pct = task.terms.upfront_release_pct as u64;
        advance_amount = task.terms.material_cost
            .checked_mul(pct).unwrap()
            .checked_div(100).unwrap();
    }

    let remaining_creator_escrow = task.escrow.creator_locked_balance.checked_sub(advance_amount).unwrap();
    let payout_amount = remaining_creator_escrow.checked_add(provider_locked_balance).unwrap();

    if payout_amount > 0 {
        let task_id_bytes = task_id.to_le_bytes();
        let seeds: &[&[u8]] = &[TASK_SEED, task_id_bytes.as_ref(), &[ctx.bumps.task]];
        let signer_seeds = &[seeds];

        let cpi_accounts = anchor_spl::token::TransferChecked {
            from: ctx.accounts.task_vault.to_account_info(),
            to: ctx.accounts.provider_token_account.to_account_info(),
            authority: task.to_account_info(),
            mint: ctx.accounts.stable_coin_mint.to_account_info(),
        };

        let cpi_context = CpiContext::new_with_signer(
            ctx.accounts.token_program.key(),
            cpi_accounts,
            signer_seeds,
        );

        anchor_spl::token::transfer_checked(cpi_context, payout_amount, ctx.accounts.stable_coin_mint.decimals)?;
    }

    task.status = TaskStatus::Completed;
    task.escrow.creator_locked_balance = 0;
    task.escrow.provider_locked_balance = None;

    msg!("Task {} approved. Payout of {} made to provider.", task_id, payout_amount);
    Ok(())
}

#[derive(Accounts)]
#[instruction(task_id: u64)]
pub struct RaiseDispute<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump,
        constraint = caller.key() == task.creator || Some(caller.key()) == task.provider @ ErrorCode::InvalidDisputeCaller,
    )]
    pub task: Account<'info, Task>,
}

pub fn raise_dispute(ctx: Context<RaiseDispute>, _task_id: u64) -> Result<()> {
    let task = &mut ctx.accounts.task;
    require!(
        task.status == TaskStatus::InProgress || task.status == TaskStatus::AwaitingApproval,
        ErrorCode::InvalidDisputeStatus
    );
    task.status = TaskStatus::Disputed;
    msg!("Task {} placed in Dispute status", task.id);
    Ok(())
}

