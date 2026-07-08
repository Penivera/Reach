use near_sdk::{AccountId, Timestamp, near};
use near_sdk::json_types::U128;


#[derive(Clone, Debug, PartialEq)]
#[near(serializers=[borsh, json])]
pub enum TaskStatus {
    Pending,     // Awaiting provider assignment
    InProgress,  // Escrow locked, work started
    AwaitingEscrow, // An application accepted but waiting on escrow
    Completed,   // Work confirmed, escrow released
    Disputed,    // Raised for admin review
    Refunded,    // Cancelled or ruled in favor of creator
}

#[derive(Clone, Debug, PartialEq)] 
#[near(serializers=[borsh, json])]
pub enum ProviderApplicationStatus {
    Pending,
    Accepted,
    Rejected
}


#[derive(Clone)]
#[near(serializers=[borsh, json])]
pub struct FinancialTerms {
    pub labor_fee: U128,             // Payment for the provider's time/effort
    pub material_cost: U128,         // Capital needed to execute the gig (e.g., buying gas)
    pub upfront_release_pct: u8,     // % of material_cost released to provider immediately upon acceptance (0-100)
    pub required_provider_collateral: Option<U128>,   // Amount the provider must deposit to accept the task (slashed if they abandon)
}


#[derive(Clone)]
#[near(serializers=[borsh, json])]
pub struct EscrowState {
    pub creator_locked_balance: U128,  // Total currently held from the creator
    pub provider_locked_balance: Option<U128>, // Defaults to None if no collateral is required; Total collateral currently held from the provider
    pub advance_disbursed: bool,       // Tracks if the upfront_release_pct was already paid out
}

#[derive(Clone)]
#[near(serializers=[borsh, json])]
pub struct Task {
    pub creator_id: AccountId,
    pub provider_id: Option<AccountId>, // Option handles the 'Pending' state before assignment
    pub desc: Option<String>,
    pub tag: Option<String>,
    pub stablecoin: AccountId,
    pub status: TaskStatus,
    pub terms: FinancialTerms,
    pub escrow: EscrowState,
    pub created_at: Timestamp,
    pub updated_at: Timestamp
}




#[near(serializers=[borsh, json])]
pub enum TransferAction {
    CreateTask{
        desc: Option<String>,
        tag: Option<String>,
        stablecoin: AccountId,
        terms: FinancialTerms,
    },
    ProvideCollateral{
        task_id: u64,
        application_id: u64
    }
}

#[derive(Clone)]
#[near(serializers=[borsh, json])]
pub struct ProviderApplication{
    pub provider_id: AccountId,
    pub task_id: u64,
    pub status:ProviderApplicationStatus,
    pub created_at: Timestamp,
    pub expires_at: Timestamp
}