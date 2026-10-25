use pinocchio::program_error::ProgramError;

#[repr(u32)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReachError {
    ApplicationNotAccepted = 6000,
    NotAnAdmin = 6001,
    NotOwner = 6002,
    FeeTooHigh = 6003,
    NoOwnerProposal = 6004,
    OwnerProposalAlreadyActive = 6005,
    AlreadyVoted = 6006,
    NoCollateralRequired = 6007,
    NotAwaitingEscrow = 6008,
    AdvanceAlreadyDisbursed = 6009,
    NoAdvanceToClaim = 6010,
    NotTaskProvider = 6011,
    CannotCancelTask = 6012,
    CannotCancelApplication = 6013,
    ProviderHasDebt = 6014,
    InvalidDisputeSplit = 6015,
    TooManyAdmins = 6016,
    InvalidTaskStatus = 6017,
    InvalidDisputeCaller = 6018,
    InvalidDisputeStatus = 6019,
    InvalidInstruction = 6020,
    InvalidAccountData = 6021,
}

impl From<ReachError> for ProgramError {
    #[inline(always)]
    fn from(e: ReachError) -> Self {
        ProgramError::Custom(e as u32)
    }
}
