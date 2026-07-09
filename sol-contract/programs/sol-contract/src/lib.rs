pub mod constants;
pub mod error;
pub mod instructions;
pub mod state;

use anchor_lang::prelude::*;

pub use constants::*;
#[allow(ambiguous_glob_reexports)]
pub use instructions::*;
pub use state::*;

declare_id!("5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY");

#[program]
pub mod sol_contract {
    use super::*;
    pub fn initialize(ctx: Context<Initialize>, owner_name: String) -> Result<()> {
        initialize::handler(ctx, owner_name)
    }

    pub fn update_creation_fee_pct(ctx: Context<AdminAction>, fee_pct: u16) -> Result<()> {
        admin::update_creation_fee_pct(ctx, fee_pct)
    }

    pub fn update_cancellation_fee_pct(ctx: Context<AdminAction>, fee_pct: u16) -> Result<()> {
        admin::update_cancellation_fee_pct(ctx, fee_pct)
    }

    pub fn propose_owner_update(ctx: Context<OwnerAction>, new_owner: Pubkey) -> Result<()> {
        admin::propose_owner_update(ctx, new_owner)
    }

    pub fn vote_owner_update(ctx: Context<AdminAction>) -> Result<()> {
        admin::vote_owner_update(ctx)
    }

    pub fn withdraw_protocol_fees(ctx: Context<WithdrawProtocolFees>, amount: u64) -> Result<()> {
        admin::withdraw_protocol_fees(ctx, amount)
    }

    pub fn create_task(
        ctx: Context<CreateTask>,
        task_id: u64,
        terms: FinancialTerms,
        tag: Option<String>,
        desc: Option<String>,
    ) -> Result<()> {
        task::create_task(ctx, task_id, terms, tag, desc)
    }

    pub fn apply(ctx: Context<CreateApplication>, task_id: u64, expires_at: i64) -> Result<()> {
        application::apply(ctx, task_id, expires_at)
    }

    pub fn accept(ctx: Context<AcceptApplication>, task_id: u64, provider:Pubkey) -> Result<()> {
        task::accept_application(ctx, task_id,provider)
    }

    pub fn provide_collateral(ctx: Context<ProvideCollateral>, task_id: u64) -> Result<()> {
        application::provide_collateral(ctx, task_id)
    }

    pub fn claim_advance(ctx: Context<ClaimAdvance>, task_id: u64) -> Result<()> {
        application::claim_advance(ctx, task_id)
    }

    pub fn cancel_task(ctx: Context<CancelTask>, task_id: u64) -> Result<()> {
        task::cancel_task(ctx, task_id)
    }

    pub fn cancel_approved_application(ctx: Context<CancelApprovedApplication>, task_id: u64) -> Result<()> {
        application::cancel_approved_application(ctx, task_id)
    }

    pub fn complete_task(ctx: Context<CompleteTask>, task_id: u64) -> Result<()> {
        task::complete_task(ctx, task_id)
    }

    pub fn approve_work(ctx: Context<ApproveWork>, task_id: u64) -> Result<()> {
        task::approve_work(ctx, task_id)
    }

    pub fn raise_dispute(ctx: Context<RaiseDispute>, task_id: u64) -> Result<()> {
        task::raise_dispute(ctx, task_id)
    }

    pub fn resolve_dispute(
        ctx: Context<ResolveDispute>,
        task_id: u64,
        creator_refund_pct: u8,
        provider_payment_pct: u8,
    ) -> Result<()> {
        admin::resolve_dispute(ctx, task_id, creator_refund_pct, provider_payment_pct)
    }

    pub fn withdraw_application(ctx: Context<WithdrawApplication>, task_id: u64) -> Result<()> {
        application::withdraw_application(ctx, task_id)
    }

    pub fn add_admin(ctx: Context<AddAdmin>, name: String, address: Pubkey) -> Result<()> {
        admin::add_admin(ctx, name, address)
    }

    pub fn remove_admin(ctx: Context<RemoveAdmin>, address: Pubkey) -> Result<()> {
        admin::remove_admin(ctx, address)
    }

    pub fn add_supported_stable(ctx: Context<AddSupportedStable>, stable_name: String) -> Result<()> {
        stable_coin::add_supported_stable(ctx, stable_name)
    }

    pub fn remove_supported_stable(ctx: Context<RemoveSupportedStable>) -> Result<()> {
        stable_coin::remove_supported_stable(ctx)
    }
}
