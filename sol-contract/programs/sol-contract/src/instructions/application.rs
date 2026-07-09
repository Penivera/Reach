use crate::constants::*;
use crate::error::{ErrorCode,TaskError};
use crate::state::*;
use anchor_lang::prelude::*;
use anchor_spl::token::{TokenAccount, Token};
use anchor_spl::token_2022::spl_token_2022::extension::scaled_ui_amount::UnixTimestamp;

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
        seeds = [APPLICATION_SEED, provider.key().as_ref()],
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
    pub provider_token_account: Account<'info, TokenAccount>,

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
    pub system_program: Program<'info, System>,
}

pub fn apply(
    ctx: Context<CreateApplication>,
    task_id: u64,
    expires_at: UnixTimestamp,
) -> Result<()> {
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

    require!(task.terms.required_provider_collateral > 0,TaskError::NoCollateralRequired);
    require!(task.status == TaskStatus::AwaitingEscrow,TaskError::NotAwaitingEscrow);

    let collateral_amount = task.terms.required_provider_collateral;
    
    let cpi_accounts = anchor_spl::token::Transfer {
        from: ctx.accounts.provider_token_account.to_account_info(),
        to: ctx.accounts.task_vault.to_account_info(),
        authority: ctx.accounts.provider.to_account_info(),
    };

    let cpi_context = CpiContext::new(
        ctx.accounts.token_program.key(),
        cpi_accounts
    );
    anchor_spl::token::transfer(cpi_context,collateral_amount)?;
    msg!("Collateral deposisted for task:{}",task_id);
    
    if task.terms.upfront_release_pct > 0 {
        let pct = task.terms.upfront_release_pct as u64;
        let advance_release_amount = task.terms.material_cost
            .checked_mul(pct).unwrap()
            .checked_div(100).unwrap();
        let advance_cpi_accounts = anchor_spl::token::Transfer {
            from: ctx.accounts.task_vault.to_account_info(),
            to: ctx.accounts.provider.to_account_info(),
            authority: task.to_account_info()
        };

        let advance_cpi_context = CpiContext::new(
            ctx.accounts.token_program.key(),
            advance_cpi_accounts
        );
        anchor_spl::token::transfer(advance_cpi_context, advance_release_amount)?;
        msg!("Advance release disbursed for task:{}",task_id);
        task.escrow.advanced_disbursed = true;
    }

    application.status = ProviderApplicationStatus::AcceptedAndCollateralProvided;
    task.escrow.provider_locked_balance = Some(collateral_amount);
    
    Ok(())
}
