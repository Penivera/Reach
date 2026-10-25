use pinocchio::{
    account_info::AccountInfo,
    instruction::{AccountMeta, Instruction, Signer},
    program::invoke_signed,
    program_error::ProgramError,
    Address,
};

#[inline(never)]
pub fn cpi_create_account<'a>(
    payer: &AccountInfo<'a>,
    new_account: &AccountInfo<'a>,
    space: u64,
    lamports: u64,
    program_id: &Address,
    signer_seeds: &[Signer],
) -> Result<(), ProgramError> {
    pinocchio_system::instructions::CreateAccount {
        from: payer,
        to: new_account,
        lamports,
        space,
        owner: program_id,
    }
    .invoke_signed(signer_seeds)
}

#[inline(never)]
pub fn cpi_init_token_account<'a>(
    account: &AccountInfo<'a>,
    mint: &AccountInfo<'a>,
    owner: &Address,
    rent_sysvar: &AccountInfo<'a>,
) -> Result<(), ProgramError> {
    // Token Program instruction 1: InitializeAccount(owner)
    let mut data = [0u8; 33];
    data[0] = 1; // InitializeAccount opcode
    data[1..33].copy_from_slice(owner.as_ref());

    let instruction = Instruction {
        program_id: &pinocchio_token::ID,
        accounts: &[
            AccountMeta::writable(account.key()),
            AccountMeta::readonly(mint.key()),
            AccountMeta::readonly(owner),
            AccountMeta::readonly(rent_sysvar.key()),
        ],
        data: &data,
    };

    pinocchio::program::invoke(&instruction, &[account, mint, rent_sysvar])
}

#[inline(never)]
pub fn cpi_transfer_checked<'a>(
    from: &AccountInfo<'a>,
    to: &AccountInfo<'a>,
    authority: &AccountInfo<'a>,
    mint: &AccountInfo<'a>,
    amount: u64,
    decimals: u8,
    signer_seeds: &[Signer],
) -> Result<(), ProgramError> {
    pinocchio_token::instructions::TransferChecked {
        from,
        to,
        authority,
        mint,
        amount,
        decimals,
    }
    .invoke_signed(signer_seeds)
}

#[inline(never)]
pub fn close_account<'a>(
    source: &AccountInfo<'a>,
    destination: &AccountInfo<'a>,
) -> Result<(), ProgramError> {
    let source_lamports = source.lamports();
    let mut dest_lamports = destination.try_borrow_mut_lamports()?;
    *dest_lamports = dest_lamports
        .checked_add(source_lamports)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    let mut src_lamports = source.try_borrow_mut_lamports()?;
    *src_lamports = 0;

    let mut data = source.try_borrow_mut_data()?;
    data.fill(0);

    Ok(())
}
