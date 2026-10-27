use crate::constants::MAX_ADMINS;
use pinocchio::{AccountView, Address};

#[repr(u8)]
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum TaskStatus {
    Open = 0,
    InProgress = 1,
    AwaitingEscrow = 2,
    AwaitingApproval = 3,
    Completed = 4,
    Disputed = 5,
    Refunded = 6,
}

#[repr(u8)]
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum ProviderApplicationStatus {
    Pending = 0,
    Accepted = 1,
    AcceptedPendingCollateral = 2,
    AcceptedAndCollateralProvided = 3,
    Rejected = 4,
    CancelledWithDebt = 5,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct FinancialTerms {
    pub labor_fee: u64,
    pub material_cost: u64,
    pub required_provider_collateral: u64,
    pub upfront_release_pct: u8,
    pub _padding: [u8; 7],
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct EscrowState {
    pub creator_locked_balance: u64,
    pub provider_locked_balance: u64,
    pub has_provider_locked_balance: u8,
    pub advanced_disbursed: u8,
    pub _padding: [u8; 6],
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct Task {
    pub discriminator: u8,
    pub _pad_discm: [u8; 7],
    pub id: u64,
    pub creator: Address,
    pub provider: Address,
    pub has_provider: u8,
    pub status: u8,
    pub bump: u8,
    pub _padding1: [u8; 5],
    pub stable_coin_mint: Address,
    pub metadata_hash: [u8; 32],
    pub terms: FinancialTerms,
    pub escrow: EscrowState,
    pub created_at: i64,
    pub updated_at: i64,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct AdminEntry {
    pub name: [u8; 10],
    pub active: u8,
    pub _pad: [u8; 5],
    pub address: Address,
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct ReachState {
    pub discriminator: u8,
    pub _pad_discm: [u8; 7],
    pub owner: Address,
    pub task_count: u64,
    pub application_count: u64,
    pub creation_fee_pct: u16,
    pub cancellation_fee_pct: u16,
    pub admin_count: u16,
    pub vote_count: u16,
    pub has_owner_proposal: u8,
    pub bump: u8,
    pub _pad: [u8; 6],
    pub owner_proposal: Address,
    pub owner_votes: [Address; MAX_ADMINS],
    pub admins: [AdminEntry; MAX_ADMINS],
    pub _pad_end: [u8; 8],
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct ProviderApplication {
    pub discriminator: u8,
    pub _pad_discm: [u8; 7],
    pub provider: Address,
    pub task_id: u64,
    pub status: u8,
    pub bump: u8,
    pub _pad: [u8; 6],
    pub created_at: i64,
    pub expires_at: i64,
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct SupportedStable {
    pub discriminator: u8,
    pub _pad_discm: [u8; 7],
    pub mint: Address,
    pub name: [u8; 10],
    pub bump: u8,
    pub _pad: [u8; 5],
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct ProviderDebt {
    pub discriminator: u8,
    pub _pad_discm: [u8; 7],
    pub provider: Address,
    pub has_debt: u8,
    pub bump: u8,
    pub _pad: [u8; 6],
}

const _: () = assert!(core::mem::size_of::<FinancialTerms>() == 32);
const _: () = assert!(core::mem::size_of::<EscrowState>() == 24);
const _: () = assert!(core::mem::size_of::<Task>() == 224);
const _: () = assert!(core::mem::size_of::<AdminEntry>() == 48);
const _: () = assert!(core::mem::size_of::<ReachState>() == 512);
const _: () = assert!(core::mem::size_of::<ProviderApplication>() == 72);
const _: () = assert!(core::mem::size_of::<SupportedStable>() == 56);
const _: () = assert!(core::mem::size_of::<ProviderDebt>() == 48);

#[inline(always)]
pub unsafe fn mut_data<T>(account: &AccountView) -> &mut T {
    &mut *(account.data_ptr() as *mut T)
}

#[inline(always)]
pub unsafe fn const_data<T>(account: &AccountView) -> &T {
    &*(account.data_ptr() as *const T)
}
