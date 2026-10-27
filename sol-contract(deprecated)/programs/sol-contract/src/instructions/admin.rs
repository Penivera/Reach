use anchor_lang::prelude::*;
use anchor_spl::token::{Mint, Token, TokenAccount};

use crate::constants::*;
use crate::error::ErrorCode;
use crate::state::*;

// -- Shared account structs --

#[derive(Accounts)]
pub struct AdminAction<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
        constraint = reach_state.admins.iter().any(|a| a.address == caller.key() && a.active) @ ErrorCode::NotAnAdmin,
    )]
    pub reach_state: Account<'info, ReachState>,
}

#[derive(Accounts)]
pub struct OwnerAction<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
        constraint = reach_state.owner == owner.key() @ ErrorCode::NotOwner,
    )]
    pub reach_state: Account<'info, ReachState>,
}

// -- Handlers --

pub fn update_creation_fee_pct(ctx: Context<AdminAction>, fee_pct: u16) -> Result<()> {
    require!(fee_pct <= 10_000, ErrorCode::FeeTooHigh);
    ctx.accounts.reach_state.creation_fee_pct = fee_pct;
    Ok(())
}

pub fn update_cancellation_fee_pct(ctx: Context<AdminAction>, fee_pct: u16) -> Result<()> {
    require!(fee_pct <= 10_000, ErrorCode::FeeTooHigh);
    ctx.accounts.reach_state.cancellation_fee_pct = fee_pct;
    Ok(())
}

pub fn propose_owner_update(ctx: Context<OwnerAction>, new_owner: Pubkey) -> Result<()> {
    let state = &mut ctx.accounts.reach_state;
    require!(state.owner_proposal.is_none(), ErrorCode::OwnerProposalAlreadyActive);
    state.owner_proposal = Some(new_owner);
    state.owner_votes = Vec::new();
    Ok(())
}

pub fn vote_owner_update(ctx: Context<AdminAction>) -> Result<()> {
    let state = &mut ctx.accounts.reach_state;
    require!(state.owner_proposal.is_some(), ErrorCode::NoOwnerProposal);

    let voter = ctx.accounts.caller.key();
    require!(!state.owner_votes.contains(&voter), ErrorCode::AlreadyVoted);

    state.owner_votes.push(voter);

    // Transfer ownership once majority of active admins have voted
    let active_admin_count = state.admins.iter().filter(|a| a.active).count();
    let majority = (active_admin_count / 2) + 1;

    if state.owner_votes.len() >= majority {
        state.owner = state.owner_proposal.unwrap();
        state.owner_proposal = None;
        state.owner_votes = Vec::new();
    }

    Ok(())
}

#[derive(Accounts)]
pub struct WithdrawProtocolFees<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
        constraint = reach_state.owner == owner.key() @ ErrorCode::NotOwner,
    )]
    pub reach_state: Account<'info, ReachState>,

    pub stable_coin_mint: Account<'info, Mint>,

    #[account(
        mut,
        seeds = [b"fee_vault", stable_coin_mint.key().as_ref()],
        bump,
    )]
    pub fee_vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        token::mint = stable_coin_mint,
    )]
    pub receiver: Account<'info, TokenAccount>,

    pub token_program: Program<'info, Token>,
}

pub fn withdraw_protocol_fees(
    ctx: Context<WithdrawProtocolFees>,
    amount: u64,
) -> Result<()> {
    let bump = ctx.bumps.reach_state;
    let signer_seeds: &[&[&[u8]]] = &[&[
        REACH_STATE_SEED,
        &[bump],
    ]];

    let cpi_accounts = anchor_spl::token::TransferChecked {
        from: ctx.accounts.fee_vault.to_account_info(),
        to: ctx.accounts.receiver.to_account_info(),
        authority: ctx.accounts.reach_state.to_account_info(),
        mint: ctx.accounts.stable_coin_mint.to_account_info(),
    };

    let cpi_context = CpiContext::new_with_signer(
        ctx.accounts.token_program.key(),
        cpi_accounts,
        signer_seeds,
    );

    anchor_spl::token::transfer_checked(
        cpi_context,
        amount,
        ctx.accounts.stable_coin_mint.decimals,
    )?;

    Ok(())
}

#[derive(Accounts)]
pub struct AddAdmin<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
        constraint = reach_state.owner == owner.key() @ ErrorCode::NotOwner,
    )]
    pub reach_state: Account<'info, ReachState>,
}

pub fn add_admin(ctx: Context<AddAdmin>, name: String, address: Pubkey) -> Result<()> {
    let state = &mut ctx.accounts.reach_state;
    require!(state.admins.len() < 10, ErrorCode::TooManyAdmins);
    state.admins.push(Admin { name, address, active: true });
    Ok(())
}

#[derive(Accounts)]
pub struct RemoveAdmin<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
        constraint = reach_state.owner == owner.key() @ ErrorCode::NotOwner,
    )]
    pub reach_state: Account<'info, ReachState>,
}

pub fn remove_admin(ctx: Context<RemoveAdmin>, address: Pubkey) -> Result<()> {
    let state = &mut ctx.accounts.reach_state;
    state.admins.retain(|a| a.address != address);
    Ok(())
}

#[derive(Accounts)]
#[instruction(task_id: u64)]
pub struct ResolveDispute<'info> {
    #[account(mut)]
    pub caller: Signer<'info>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
        constraint = reach_state.admins.iter().any(|a| a.address == caller.key() && a.active) @ ErrorCode::NotAnAdmin,
    )]
    pub reach_state: Account<'info, ReachState>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump,
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
        constraint = creator_token_account.owner == task.creator @ ErrorCode::NotOwner,
    )]
    pub creator_token_account: Account<'info, TokenAccount>,

    #[account(
        mut,
        constraint = provider_token_account.owner == task.provider.unwrap() @ ErrorCode::NotTaskProvider,
    )]
    pub provider_token_account: Account<'info, TokenAccount>,

    pub stable_coin_mint: Account<'info, Mint>,
    pub token_program: Program<'info, Token>,
}

pub fn resolve_dispute(
    ctx: Context<ResolveDispute>,
    task_id: u64,
    creator_refund_pct: u8,
    provider_payment_pct: u8,
) -> Result<()> {
    let task = &mut ctx.accounts.task;
    require!(task.status == TaskStatus::Disputed, ErrorCode::InvalidTaskStatus);
    require!(creator_refund_pct + provider_payment_pct == 100, ErrorCode::InvalidDisputeSplit);

    let total_funds = ctx.accounts.task_vault.amount;
    let creator_refund = (total_funds as u128)
        .checked_mul(creator_refund_pct as u128).unwrap()
        .checked_div(100).unwrap() as u64;
    let provider_payment = total_funds.checked_sub(creator_refund).unwrap();

    let task_id_bytes = task_id.to_le_bytes();
    let seeds: &[&[u8]] = &[TASK_SEED, task_id_bytes.as_ref(), &[ctx.bumps.task]];
    let signer_seeds = &[seeds];

    // Transfer creator refund
    if creator_refund > 0 {
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

        anchor_spl::token::transfer_checked(cpi_context, creator_refund, ctx.accounts.stable_coin_mint.decimals)?;
    }

    // Transfer provider payment
    if provider_payment > 0 {
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

        anchor_spl::token::transfer_checked(cpi_context, provider_payment, ctx.accounts.stable_coin_mint.decimals)?;
    }

    task.status = TaskStatus::Refunded;
    task.escrow.creator_locked_balance = 0;
    task.escrow.provider_locked_balance = None;

    msg!("Dispute resolved for task {}. Creator refund: {}, Provider payment: {}", task_id, creator_refund, provider_payment);

    Ok(())
}

