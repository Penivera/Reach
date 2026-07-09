use anchor_lang::prelude::*;

#[error_code]
pub enum ErrorCode {
    #[msg("Cannot Provide Collateral Until Application is Accepted")]
    ApplicationNotAccepted,
    #[msg("Must Be An Admin")]
    NotAnAdmin,
}

#[error_code]
pub enum TaskError {
    #[msg("Task does not require collateral lock")]
    NoCollateralRequired,
}