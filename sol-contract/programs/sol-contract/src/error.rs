use anchor_lang::prelude::*;

#[error_code]
pub enum ErrorCode {
    #[msg("Cannot Provide Collateral Until Application is Accepted")]
    ApplicationNotAccepted,
    #[msg("Must Be An Admin")]
    NotAnAdmin,
    #[msg("Only the owner can perform this action")]
    NotOwner,
    #[msg("Fee percentage cannot exceed 100 (10000 basis points)")]
    FeeTooHigh,
    #[msg("No owner proposal is currently active")]
    NoOwnerProposal,
    #[msg("An owner proposal is already active")]
    OwnerProposalAlreadyActive,
    #[msg("Admin has already voted for this proposal")]
    AlreadyVoted,
    #[msg("Task does not require collateral lock")]
    NoCollateralRequired,
    #[msg("Task is not awaiting escrow")]
    NotAwaitingEscrow,
    #[msg("Advance has already been disbursed")]
    AdvanceAlreadyDisbursed,
    #[msg("No upfront advance configured for this task")]
    NoAdvanceToClaim,
    #[msg("Only the assigned provider can perform this action")]
    NotTaskProvider,
    #[msg("Task cannot be cancelled in its current state")]
    CannotCancelTask,
    #[msg("Application cannot be cancelled in its current state")]
    CannotCancelApplication,
    #[msg("Provider has cancelled with debt and cannot apply to tasks")]
    ProviderHasDebt,
    #[msg("Dispute split percentages must sum to 100")]
    InvalidDisputeSplit,
    #[msg("Cannot add more than 10 admins")]
    TooManyAdmins,
    #[msg("Task is not in the correct state for this action")]
    InvalidTaskStatus,
    #[msg("Only the creator or provider can perform this action")]
    InvalidDisputeCaller,
    #[msg("Task must be in InProgress or AwaitingApproval state to dispute")]
    InvalidDisputeStatus,
}