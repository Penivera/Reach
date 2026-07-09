use anchor_lang::prelude::*;

#[derive(Debug, Clone, PartialEq, AnchorSerialize, AnchorDeserialize, InitSpace)]
pub enum TaskStatus {
    Open,        // Awaiting provider assignment
    InProgress,     // Escrow locked, work started
    AwaitingEscrow, // An application accepted but waiting on escrow
    Completed,      // Work confirmed, escrow released
    Disputed,       // Raised for admin review
    Refunded,       // Cancelled or ruled in favor of creator
}

#[derive(Debug, Clone, PartialEq, AnchorSerialize, AnchorDeserialize, InitSpace)]
pub enum ProviderApplicationStatus {
    Pending,
    Accepted,
    Rejected,
}

#[derive(Debug, Clone, PartialEq, AnchorSerialize, AnchorDeserialize, InitSpace)]
pub struct FinancialTerms {
    pub labor_fee: u64,
    pub material_cost: u64,
    pub upfront_release_pct: u8, //% of material cost to release upfront to provider
    pub required_provider_collateral: u128, //0 if no collateral is required
}

#[derive(Debug, Clone, PartialEq, AnchorSerialize, AnchorDeserialize, InitSpace)]
pub struct EscrowState {
    pub creator_locked_balance: u64,
    pub provider_locked_balance: Option<u64>,
    pub advanced_disbursed: bool,
}

#[account]
#[derive(InitSpace)]
pub struct Task {
    pub id: u64,
    pub creator: Pubkey,
    pub provider: Option<Pubkey>,
    pub stable_coin_mint: Pubkey,
    #[max_len(200)]
    pub desc: Option<String>,
    #[max_len(30)]
    pub tag: Option<String>,
    pub status: TaskStatus,
    pub terms: FinancialTerms,
    pub escrow: EscrowState,
    pub created_at: i64, // Unix timestamp
    pub updated_at: i64, // Unix timestamp
}

#[account]
#[derive(InitSpace)]
pub struct SupportedStable {
    pub mint: Pubkey,
    pub bump: u8,
    #[max_len(10)]
    pub name: String,
}

#[derive(InitSpace, Debug, Clone, PartialEq, AnchorSerialize, AnchorDeserialize)]
pub struct Admin {
    #[max_len(10)]
    pub name: String,
    pub address: Pubkey,
    pub active: bool,
}

#[account]
#[derive(InitSpace)]
pub struct ReachState {
    pub owner: Pubkey,
    pub task_count: u64,
    pub application_count: u64,
    #[max_len(10)]
    pub admins: Vec<Admin>,
}

#[account]
#[derive(InitSpace)]
pub struct ProviderApplication{
    pub provider: Pubkey,
    pub task_id:u64,
    pub status: ProviderApplicationStatus,
    pub created_at: i64, // Unix timestamp
    pub expires_at: i64, // Unix timestamp
}