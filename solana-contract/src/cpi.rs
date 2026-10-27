use pinocchio::{
    cpi::{invoke_signed_unchecked, CpiAccount, Seed, Signer},
    error::ProgramError,
    instruction::{InstructionAccount, InstructionView},
    AccountView, Address, ProgramResult,
};

use crate::{
    constants::TASK_SEED,
    math::{get_mint_decimals, rent_exempt_minimum},
};

pub const SYSTEM_PROGRAM_ID: Address = Address::new_from_array([0u8; 32]);
pub const TOKEN_PROGRAM_ID: Address = Address::new_from_array([
    6, 221, 246, 225, 215, 101, 161, 147, 217, 203, 225, 70, 206, 235, 121, 172, 28, 180, 133, 237,
    95, 91, 55, 145, 58, 140, 245, 133, 126, 255, 0, 169,
]);

#[inline(never)]
fn init_cpi_account<'a>(view: &'a AccountView, out: &mut core::mem::MaybeUninit<CpiAccount<'a>>) {
    CpiAccount::init_from_account_view(view, out);
}

#[repr(C, packed)]
struct CreateAccountIx {
    instruction: u32,
    lamports: u64,
    space: u64,
    owner: Address,
}

#[repr(C, packed)]
struct InitAccount3Ix {
    instruction: u8,
    owner: Address,
}

#[repr(C, packed)]
struct TransferCheckedIx {
    instruction: u8,
    amount: u64,
    decimals: u8,
}

#[inline(always)]
pub fn cpi_create_account(
    payer: &AccountView,
    new_account: &AccountView,
    space: u64,
    lamports: u64,
    owner: &Address,
    signer_seeds: &[Signer],
) -> ProgramResult {
    let data = CreateAccountIx {
        instruction: 0,
        lamports,
        space,
        owner: *owner,
    };
    let data_bytes = unsafe {
        core::slice::from_raw_parts(
            &data as *const _ as *const u8,
            core::mem::size_of::<CreateAccountIx>(),
        )
    };
    let ix_accounts = [
        InstructionAccount::writable_signer(payer.address()),
        InstructionAccount::writable_signer(new_account.address()),
    ];
    let instruction = InstructionView {
        program_id: &SYSTEM_PROGRAM_ID,
        accounts: &ix_accounts,
        data: data_bytes,
    };

    let mut accounts = [const { core::mem::MaybeUninit::<CpiAccount>::uninit() }; 2];
    init_cpi_account(payer, &mut accounts[0]);
    init_cpi_account(new_account, &mut accounts[1]);

    unsafe {
        invoke_signed_unchecked(
            &instruction,
            core::slice::from_raw_parts(accounts.as_ptr() as *const CpiAccount, 2),
            signer_seeds,
        );
    }
    Ok(())
}

#[inline(always)]
pub fn cpi_init_token_account(
    account: &AccountView,
    mint: &AccountView,
    owner: &Address,
) -> ProgramResult {
    let data = InitAccount3Ix {
        instruction: 18,
        owner: *owner,
    };
    let data_bytes = unsafe {
        core::slice::from_raw_parts(
            &data as *const _ as *const u8,
            core::mem::size_of::<InitAccount3Ix>(),
        )
    };

    let ix_accounts = [
        InstructionAccount::writable(account.address()),
        InstructionAccount::readonly(mint.address()),
    ];
    let instruction = InstructionView {
        program_id: &TOKEN_PROGRAM_ID,
        accounts: &ix_accounts,
        data: data_bytes,
    };

    let mut accounts = [const { core::mem::MaybeUninit::<CpiAccount>::uninit() }; 2];
    init_cpi_account(account, &mut accounts[0]);
    init_cpi_account(mint, &mut accounts[1]);

    unsafe {
        invoke_signed_unchecked(
            &instruction,
            core::slice::from_raw_parts(accounts.as_ptr() as *const CpiAccount, 2),
            &[],
        );
    }
    Ok(())
}

#[inline(never)]
pub fn cpi_transfer_checked(
    from: &AccountView,
    mint: &AccountView,
    to: &AccountView,
    authority: &AccountView,
    amount: u64,
    decimals: u8,
    signer_seeds: &[Signer],
) -> ProgramResult {
    if amount == 0 {
        return Ok(());
    }
    let data = TransferCheckedIx {
        instruction: 12,
        amount,
        decimals,
    };
    let data_bytes = unsafe {
        core::slice::from_raw_parts(
            &data as *const _ as *const u8,
            core::mem::size_of::<TransferCheckedIx>(),
        )
    };

    let ix_accounts = [
        InstructionAccount::writable(from.address()),
        InstructionAccount::readonly(mint.address()),
        InstructionAccount::writable(to.address()),
        InstructionAccount::readonly_signer(authority.address()),
    ];
    let instruction = InstructionView {
        program_id: &TOKEN_PROGRAM_ID,
        accounts: &ix_accounts,
        data: data_bytes,
    };

    let mut accounts = [const { core::mem::MaybeUninit::<CpiAccount>::uninit() }; 4];
    init_cpi_account(from, &mut accounts[0]);
    init_cpi_account(mint, &mut accounts[1]);
    init_cpi_account(to, &mut accounts[2]);
    init_cpi_account(authority, &mut accounts[3]);

    unsafe {
        invoke_signed_unchecked(
            &instruction,
            core::slice::from_raw_parts(accounts.as_ptr() as *const CpiAccount, 4),
            signer_seeds,
        );
    }
    Ok(())
}

#[inline(never)]
pub fn cpi_user_transfer_checked_pair(
    from: &AccountView,
    mint: &AccountView,
    authority: &AccountView,
    dest1: &AccountView,
    amount1: u64,
    dest2: &AccountView,
    amount2: u64,
    decimals: u8,
) -> ProgramResult {
    cpi_transfer_checked(from, mint, dest1, authority, amount1, decimals, &[])?;
    cpi_transfer_checked(from, mint, dest2, authority, amount2, decimals, &[])
}

#[inline(never)]
pub fn cpi_task_transfer_checked(
    task_vault: &AccountView,
    mint: &AccountView,
    destination: &AccountView,
    task: &AccountView,
    amount: u64,
) -> ProgramResult {
    if amount == 0 {
        return Ok(());
    }
    let data_ptr = task.data_ptr();
    let task_id_bytes = unsafe { core::slice::from_raw_parts(data_ptr.add(8), 8) };
    let bump_bytes = unsafe { core::slice::from_raw_parts(data_ptr.add(82), 1) };
    let seeds = [
        Seed::from(TASK_SEED),
        Seed::from(task_id_bytes),
        Seed::from(bump_bytes),
    ];
    let signers = [Signer::from(&seeds)];
    let decimals = get_mint_decimals(mint);
    cpi_transfer_checked(
        task_vault,
        mint,
        destination,
        task,
        amount,
        decimals,
        &signers,
    )
}

#[inline(never)]
pub fn cpi_task_transfer_checked_pair(
    task_vault: &AccountView,
    mint: &AccountView,
    task: &AccountView,
    dest1: &AccountView,
    amount1: u64,
    dest2: &AccountView,
    amount2: u64,
) -> ProgramResult {
    cpi_task_transfer_checked(task_vault, mint, dest1, task, amount1)?;
    cpi_task_transfer_checked(task_vault, mint, dest2, task, amount2)
}

#[cfg(target_os = "solana")]
extern "C" {
    fn sol_create_program_address(
        seeds_addr: *const u8,
        seeds_len: u64,
        program_id_addr: *const u8,
        address_addr: *mut u8,
    ) -> u64;
}

#[inline(never)]
pub fn create_pda_account(
    payer: &AccountView,
    new_account: &AccountView,
    prefix_seeds: &[&[u8]],
    space: u64,
    program_id: &Address,
    owner_id: &Address,
) -> Result<u8, ProgramError> {
    let n = prefix_seeds.len();
    if n > 4 {
        return Err(ProgramError::MaxSeedLengthExceeded);
    }

    let mut seeds_raw: [&[u8]; 5] = [&[]; 5];
    for i in 0..n {
        seeds_raw[i] = prefix_seeds[i];
    }

    let mut bump = 255u8;
    let bump_ptr = &mut bump as *mut u8;
    let bump_slice = unsafe { core::slice::from_raw_parts(bump_ptr, 1) };
    seeds_raw[n] = bump_slice;
    let mut expected_pda = Address::default();

    loop {
        #[cfg(target_os = "solana")]
        let res = unsafe {
            sol_create_program_address(
                seeds_raw.as_ptr() as *const u8,
                (n + 1) as u64,
                program_id.as_ref().as_ptr(),
                expected_pda.as_mut().as_mut_ptr(),
            )
        };
        #[cfg(not(target_os = "solana"))]
        let res = match Address::create_program_address(&seeds_raw[..n + 1], program_id) {
            Ok(addr) => {
                expected_pda = addr;
                0
            }
            Err(_) => 1,
        };

        if res == 0 {
            break;
        }
        if bump == 0 {
            return Err(ProgramError::InvalidSeeds);
        }
        unsafe {
            *bump_ptr -= 1;
        }
    }

    if new_account.address() != &expected_pda {
        return Err(ProgramError::InvalidAccountOwner);
    }

    let seed_slice: &[Seed] =
        unsafe { core::slice::from_raw_parts(seeds_raw.as_ptr() as *const Seed, n + 1) };
    let signers = [Signer::from(seed_slice)];
    let lamports = rent_exempt_minimum(space);

    cpi_create_account(payer, new_account, space, lamports, owner_id, &signers)?;

    Ok(bump)
}

#[inline(never)]
pub fn create_pda_token_account(
    payer: &AccountView,
    vault: &AccountView,
    seeds: &[&[u8]],
    program_id: &Address,
    mint: &AccountView,
    owner: &Address,
) -> ProgramResult {
    create_pda_account(payer, vault, seeds, 165, program_id, &TOKEN_PROGRAM_ID)?;
    cpi_init_token_account(vault, mint, owner)
}

#[inline(never)]
pub fn close_account(mut source: AccountView, mut destination: AccountView) -> ProgramResult {
    let source_lamports = source.lamports();
    let new_dest_lamports = destination
        .lamports()
        .checked_add(source_lamports)
        .ok_or(ProgramError::ArithmeticOverflow)?;

    destination.set_lamports(new_dest_lamports);
    source.set_lamports(0);

    let len = source.data_len();
    if len > 0 {
        unsafe {
            core::ptr::write_bytes(source.data_mut_ptr(), 0, len);
        }
    }

    Ok(())
}
