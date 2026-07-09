use crate::constants::*;
use crate::error::ErrorCode;
use crate::state::*;
use anchor_lang::prelude::*;
use anchor_spl::token::{Mint, TokenAccount, Token};

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
    #[account(
        mut,
        seeds = [APPLICATION_SEED, provider.key().as_ref(), task.key().as_ref()],
        bump,
        constraint = application.status == ProviderApplicationStatus::AcceptedPendingCollateral
        @ErrorCode::ApplicationNotAccepted
    )]
    application: Account<'info, ProviderApplication>,

    #[account(
        mut,
        seeds = [TASK_SEED, task.key().as_ref()],
        bump
    )]
    pub task_vault: Account<'info, TokenAccount>,
    #[account(mut)]
    pub provider_token_account: Account<'info, TokenAccount>,

    pub stable_coin_mint: Account<'info, Mint>,

    #[account(
        seeds = [STABLE_COIN_SEED, stable_coin_mint.key().as_ref()],
        bump,
    )]
    pub supported_token_check: Account<'info, SupportedStable>,

    //System Programs required
    pub token_program: Program<'info, Token>
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
        seeds = [APPLICATION_SEED,provider.key().as_ref(),task.key().as_ref()],
        bump
    )]
    pub application: Account<'info, ProviderApplication>,

    /// CHECK: Validated manually using seeds constraint
    #[account(
        seeds = [b"provider_debt", provider.key().as_ref()],
        bump
    )]
    pub provider_debt: UncheckedAccount<'info>,

    pub system_program: Program<'info, System>,
}

pub fn apply(
    ctx: Context<CreateApplication>,
    task_id: u64,
    expires_at: i64,
) -> Result<()> {
    if !ctx.accounts.provider_debt.data_is_empty() {
        let data = ctx.accounts.provider_debt.try_borrow_data()?;
        let mut data_slice: &[u8] = &data;
        let provider_debt_acc = ProviderDebt::try_deserialize(&mut data_slice)?;
        require!(!provider_debt_acc.has_debt, ErrorCode::ProviderHasDebt);
    }

    let application = &mut ctx.accounts.application;
    let clock = Clock::get()?;

    application.provider = ctx.accounts.provider.key();
    application.task_id = task_id;
    application.created_at = clock.unix_timestamp;
    application.expires_at = expires_at.into();
    application.status = ProviderApplicationStatus::Pending;
    Ok(())
}

#[allow(unused_variables)]
pub fn provide_collateral(
    ctx: Context<ProvideCollateral>,
    task_id: u64,
) -> Result<()> {
    let task = &mut ctx.accounts.task;
    let application = &mut ctx.accounts.application;

    require!(task.terms.required_provider_collateral > 0,ErrorCode::NoCollateralRequired);
    require!(task.status == TaskStatus::AwaitingEscrow,ErrorCode::NotAwaitingEscrow);

    let collateral_amount = task.terms.required_provider_collateral;
    
    let cpi_accounts = anchor_spl::token::TransferChecked {
        from: ctx.accounts.provider_token_account.to_account_info(),
        to: ctx.accounts.task_vault.to_account_info(),
        authority: ctx.accounts.provider.to_account_info(),
        mint: ctx.accounts.stable_coin_mint.to_account_info(),
    };

    let cpi_context = CpiContext::new(
        ctx.accounts.token_program.key(),
        cpi_accounts
    );
    anchor_spl::token::transfer_checked(cpi_context, collateral_amount, ctx.accounts.stable_coin_mint.decimals)?;
    msg!("Collateral deposisted for task:{}",task_id);
    
    application.status = ProviderApplicationStatus::AcceptedAndCollateralProvided;
    task.escrow.provider_locked_balance = Some(collateral_amount);
    task.status = TaskStatus::InProgress;
    
    if task.terms.upfront_release_pct > 0 {
        let pct = task.terms.upfront_release_pct as u64;
        let advance_release_amount = task.terms.material_cost
            .checked_mul(pct).unwrap()
            .checked_div(100).unwrap();
        let advance_cpi_accounts = anchor_spl::token::TransferChecked {
            from: ctx.accounts.task_vault.to_account_info(),
            to: ctx.accounts.provider_token_account.to_account_info(),
            authority: task.to_account_info(),
            mint: ctx.accounts.stable_coin_mint.to_account_info(),
        };

        let task_id_bytes = task_id.to_le_bytes();
        let seeds: &[&[u8]] = &[TASK_SEED, task_id_bytes.as_ref(), &[ctx.bumps.task]];
        let signer_seeds = &[seeds];

        let advance_cpi_context = CpiContext::new_with_signer(
            ctx.accounts.token_program.key(),
            advance_cpi_accounts,
            signer_seeds,
        );
        anchor_spl::token::transfer_checked(advance_cpi_context, advance_release_amount, ctx.accounts.stable_coin_mint.decimals)?;
        msg!("Advance release disbursed for task:{}",task_id);
        task.escrow.advanced_disbursed = true;
    }
    
    Ok(())
}

#[derive(Accounts)]
#[instruction(task_id:u64)]
pub struct ClaimAdvance<'info> {
    #[account(mut)]
    pub provider: Signer<'info>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump,
        constraint = task.provider == Some(provider.key()) @ ErrorCode::NotTaskProvider,
    )]
    pub task: Account<'info, Task>,

    #[account(
        mut,
        seeds = [TASK_SEED, task.key().as_ref()],
        bump
    )]
    pub task_vault: Account<'info, TokenAccount>,

    #[account(
        mut,
        token::authority = provider,
    )]
    pub provider_token_account: Account<'info, TokenAccount>,

    pub stable_coin_mint: Account<'info, Mint>,

    pub token_program: Program<'info, Token>,
}

pub fn claim_advance(ctx: Context<ClaimAdvance>, task_id: u64) -> Result<()> {
    let task = &mut ctx.accounts.task;

    require!(task.terms.upfront_release_pct > 0, ErrorCode::NoAdvanceToClaim);
    require!(!task.escrow.advanced_disbursed, ErrorCode::AdvanceAlreadyDisbursed);

    let pct = task.terms.upfront_release_pct as u64;
    let advance_amount = (task.terms.material_cost
        .checked_mul(pct).unwrap()
        .checked_div(100).unwrap()) as u64;

    // Fix 2: Include task.creator in the signer seeds
    let task_id_bytes = task_id.to_le_bytes();
    let signer_seeds: &[&[&[u8]]] = &[&[
        TASK_SEED,
        task.creator.as_ref(),
        task_id_bytes.as_ref(),
        &[ctx.bumps.task],
    ]];

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

    anchor_spl::token::transfer_checked(cpi_context, advance_amount, ctx.accounts.stable_coin_mint.decimals)?;
    task.escrow.advanced_disbursed = true;
    
    Ok(())
}

#[derive(Accounts)]
#[instruction(task_id: u64)]
pub struct CancelApprovedApplication<'info> {
    #[account(mut)]
    pub provider: Signer<'info>,

    #[account(
        mut,
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump,
        constraint = task.provider == Some(provider.key()) @ ErrorCode::NotTaskProvider,
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
        seeds = [APPLICATION_SEED, provider.key().as_ref(), task.key().as_ref()],
        bump,
        constraint = application.status == ProviderApplicationStatus::AcceptedAndCollateralProvided || 
                     application.status == ProviderApplicationStatus::AcceptedPendingCollateral @ ErrorCode::CannotCancelApplication,
    )]
    pub application: Account<'info, ProviderApplication>,

    #[account(
        mut,
        seeds = [REACH_STATE_SEED],
        bump,
    )]
    pub reach_state: Box<Account<'info, ReachState>>,

    #[account(
        init_if_needed,
        payer = provider,
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
    pub provider_token_account: Account<'info, TokenAccount>,

    pub stable_coin_mint: Account<'info, Mint>,

    #[account(
        init_if_needed,
        payer = provider,
        space = 8 + ProviderDebt::INIT_SPACE,
        seeds = [b"provider_debt", provider.key().as_ref()],
        bump
    )]
    pub provider_debt: Account<'info, ProviderDebt>,

    pub system_program: Program<'info, System>,
    pub token_program: Program<'info, Token>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn cancel_approved_application(ctx: Context<CancelApprovedApplication>, task_id: u64) -> Result<()> {
    let task = &mut ctx.accounts.task;
    let application = &mut ctx.accounts.application;

    let provider_locked_balance = task.escrow.provider_locked_balance.unwrap_or(0);
    
    let mut advance_amount = 0;
    if task.escrow.advanced_disbursed && task.terms.upfront_release_pct > 0 {
        let pct = task.terms.upfront_release_pct as u64;
        advance_amount = task.terms.material_cost
            .checked_mul(pct).unwrap()
            .checked_div(100).unwrap();
    }

    if advance_amount <= provider_locked_balance {
        let provider_refund = provider_locked_balance.checked_sub(advance_amount).unwrap();

        if provider_refund > 0 {
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

            anchor_spl::token::transfer_checked(cpi_context, provider_refund, ctx.accounts.stable_coin_mint.decimals)?;
        }
        
        ctx.accounts.provider_debt.provider = ctx.accounts.provider.key();
        ctx.accounts.provider_debt.has_debt = false;
    } else {
        let difference = advance_amount.checked_sub(provider_locked_balance).unwrap();
        let total_escrow = task.escrow.creator_locked_balance;
        
        let fee_pct = ctx.accounts.reach_state.cancellation_fee_pct as u64;
        let fee_amount = (total_escrow as u128)
            .checked_mul(fee_pct as u128).unwrap()
            .checked_div(10000).unwrap() as u64;

        if difference > 0 {
            let cpi_accounts = anchor_spl::token::TransferChecked {
                from: ctx.accounts.provider_token_account.to_account_info(),
                to: ctx.accounts.task_vault.to_account_info(),
                authority: ctx.accounts.provider.to_account_info(),
                mint: ctx.accounts.stable_coin_mint.to_account_info(),
            };

            let cpi_context = CpiContext::new(
                ctx.accounts.token_program.key(),
                cpi_accounts,
            );

            anchor_spl::token::transfer_checked(cpi_context, difference, ctx.accounts.stable_coin_mint.decimals)?;
        }

        if fee_amount > 0 {
            let cpi_accounts = anchor_spl::token::TransferChecked {
                from: ctx.accounts.provider_token_account.to_account_info(),
                to: ctx.accounts.fee_vault.to_account_info(),
                authority: ctx.accounts.provider.to_account_info(),
                mint: ctx.accounts.stable_coin_mint.to_account_info(),
            };

            let cpi_context = CpiContext::new(
                ctx.accounts.token_program.key(),
                cpi_accounts,
            );

            anchor_spl::token::transfer_checked(cpi_context, fee_amount, ctx.accounts.stable_coin_mint.decimals)?;
        }

        ctx.accounts.provider_debt.provider = ctx.accounts.provider.key();
        ctx.accounts.provider_debt.has_debt = true;
    }

    task.provider = None;
    task.status = TaskStatus::Open;
    task.escrow.provider_locked_balance = None;
    task.escrow.advanced_disbursed = false;

    if advance_amount > provider_locked_balance {
        application.status = ProviderApplicationStatus::CancelledWithDebt;
    } else {
        application.status = ProviderApplicationStatus::Rejected;
    }

    msg!("Approved application for task {} cancelled by provider", task_id);

    Ok(())
}

#[derive(Accounts)]
#[instruction(task_id: u64)]
pub struct WithdrawApplication<'info> {
    #[account(mut)]
    pub provider: Signer<'info>,

    #[account(
        seeds = [TASK_SEED, task_id.to_le_bytes().as_ref()],
        bump,
    )]
    pub task: Account<'info, Task>,

    #[account(
        mut,
        close = provider,
        seeds = [APPLICATION_SEED, provider.key().as_ref(), task.key().as_ref()],
        bump,
        constraint = application.status == ProviderApplicationStatus::Pending @ ErrorCode::CannotCancelApplication,
    )]
    pub application: Account<'info, ProviderApplication>,
}

pub fn withdraw_application(_ctx: Context<WithdrawApplication>, _task_id: u64) -> Result<()> {
    msg!("Application withdrawn by provider. Account closed.");
    Ok(())
}