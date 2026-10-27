use pinocchio::error::ProgramError;

#[inline(always)]
pub fn mul_div_64(val: u64, num: u64, den: u64) -> Result<u64, ProgramError> {
    if den == 0 {
        return Err(ProgramError::InvalidArgument);
    }
    let prod = val
        .checked_mul(num)
        .ok_or(ProgramError::ArithmeticOverflow)?;
    Ok(prod / den)
}

#[inline(always)]
pub fn rent_exempt_minimum(space: u64) -> u64 {
    // 2-year rent exemption: (128 + space) * 3480 * 2
    (128 + space) * 6960
}

#[inline(always)]
pub fn get_token_balance(account: &pinocchio::AccountView) -> u64 {
    unsafe { *(account.data_ptr().add(64) as *const u64) }
}

#[inline(always)]
pub fn get_mint_decimals(mint: &pinocchio::AccountView) -> u8 {
    unsafe { *mint.data_ptr().add(44) }
}
