#![no_std]

pub mod constants;
pub mod cpi;
pub mod error;
pub mod instructions;
pub mod math;
pub mod state;

use pinocchio::{error::ProgramError, AccountView, Address, ProgramResult};

use crate::{
    error::ReachError,
    instructions::{admin, application, stable_coin, task},
    state::FinancialTerms,
};

#[cfg(any(target_os = "solana", target_arch = "bpf"))]
#[no_mangle]
pub unsafe extern "C" fn entrypoint(mut input: *mut u8) -> u64 {
    const MAX_ACCOUNTS: usize = 12;
    let mut accounts = core::mem::MaybeUninit::<[AccountView; MAX_ACCOUNTS]>::uninit();
    let accounts_ptr = accounts.as_mut_ptr() as *mut AccountView;

    let num_accounts = *(input as *const u64) as usize;
    input = input.add(core::mem::size_of::<u64>());

    let to_process = if num_accounts > MAX_ACCOUNTS {
        MAX_ACCOUNTS
    } else {
        num_accounts
    };

    for i in 0..num_accounts {
        let is_dup = *input != 0xff;
        let account = input as *mut pinocchio::account::RuntimeAccount;
        input = input.add(core::mem::size_of::<u64>());

        if is_dup {
            let dup_index = (*account).borrow_state as usize;
            if i < to_process && dup_index < i {
                accounts_ptr.add(i).write(*accounts_ptr.add(dup_index));
            }
        } else {
            if i < to_process {
                accounts_ptr
                    .add(i)
                    .write(AccountView::new_unchecked(account));
            }
            let data_len = (*account).data_len as usize;
            input = input.add(10328 + data_len);
            let addr = input as usize;
            input = ((addr + 7) & !7) as *mut u8;
        }
    }

    let instruction_data_len = *(input as *const u64) as usize;
    input = input.add(core::mem::size_of::<u64>());
    let instruction_data = core::slice::from_raw_parts(input, instruction_data_len);
    input = input.add(instruction_data_len);
    let program_id = &*(input as *const Address);

    let accounts_slice = core::slice::from_raw_parts_mut(accounts_ptr, to_process);
    match process_instruction(program_id, accounts_slice, instruction_data) {
        Ok(()) => 0,
        Err(ProgramError::Custom(0)) => 1u64 << 32,
        Err(ProgramError::Custom(x)) => x as u64,
        Err(other) => {
            let tag = unsafe { *(core::ptr::addr_of!(other) as *const u32) };
            ((tag as u64) + 1) << 32
        }
    }
}

#[cfg(any(target_os = "solana", target_arch = "bpf"))]
pinocchio::no_allocator!();

#[cfg(any(target_os = "solana", target_arch = "bpf"))]
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    unsafe { pinocchio::syscalls::abort() }
}

#[inline(always)]
unsafe fn ptr_at<T: Copy>(input: &[u8], offset: usize) -> T {
    core::ptr::read_unaligned(input.as_ptr().add(offset) as *const T)
}

pub fn process_instruction(
    program_id: &Address,
    accounts: &mut [AccountView],
    instruction_data: &[u8],
) -> ProgramResult {
    if instruction_data.is_empty() {
        return Err(ProgramError::InvalidInstructionData);
    }

    let opcode = instruction_data[0];
    match opcode {
        // 0: Initialize (10 bytes owner_name)
        0 => {
            if instruction_data.len() < 11 {
                return Err(ProgramError::InvalidInstructionData);
            }
            let owner_name = unsafe { ptr_at::<[u8; 10]>(instruction_data, 1) };
            admin::initialize(program_id, accounts, owner_name)
        }
        // 1: UpdateCreationFeePct, 2: UpdateCancellationFeePct
        1 | 2 => {
            if instruction_data.len() < 3 {
                return Err(ProgramError::InvalidInstructionData);
            }
            let fee_pct = unsafe { ptr_at::<u16>(instruction_data, 1) };
            admin::set_fee_pct(accounts, fee_pct, opcode == 2)
        }
        // 3: ProposeOwnerUpdate
        3 => {
            if instruction_data.len() < 33 {
                return Err(ProgramError::InvalidInstructionData);
            }
            let new_owner = unsafe { ptr_at::<Address>(instruction_data, 1) };
            admin::propose_owner_update(accounts, new_owner)
        }
        // 4: VoteOwnerUpdate
        4 => admin::vote_owner_update(accounts),
        // 5: WithdrawProtocolFees
        5 => {
            if instruction_data.len() < 9 {
                return Err(ProgramError::InvalidInstructionData);
            }
            let amount = unsafe { ptr_at::<u64>(instruction_data, 1) };
            admin::withdraw_protocol_fees(accounts, amount)
        }
        // 6..=17: Task instructions with common task_id
        6..=17 => {
            if instruction_data.len() < 9 {
                return Err(ProgramError::InvalidInstructionData);
            }
            let task_id = unsafe { ptr_at::<u64>(instruction_data, 1) };
            match opcode {
                6 => {
                    if instruction_data.len() < 73 {
                        return Err(ProgramError::InvalidInstructionData);
                    }
                    let terms = unsafe { ptr_at::<FinancialTerms>(instruction_data, 9) };
                    let metadata_hash = unsafe { ptr_at::<[u8; 32]>(instruction_data, 41) };
                    task::create_task(program_id, accounts, task_id, terms, metadata_hash)
                }
                7 => {
                    if instruction_data.len() < 17 {
                        return Err(ProgramError::InvalidInstructionData);
                    }
                    let expires_at = unsafe { ptr_at::<i64>(instruction_data, 9) };
                    application::apply(program_id, accounts, task_id, expires_at)
                }
                8 => {
                    if instruction_data.len() < 41 {
                        return Err(ProgramError::InvalidInstructionData);
                    }
                    let provider = unsafe { ptr_at::<Address>(instruction_data, 9) };
                    application::accept(accounts, provider)
                }
                9 => application::provide_collateral(accounts),
                10 => application::claim_advance(accounts),
                11 => task::cancel_task(accounts),
                12 => application::cancel_approved_application(program_id, accounts),
                13 => task::complete_task(accounts),
                14 => task::approve_work(accounts),
                15 => task::raise_dispute(accounts),
                16 => {
                    if instruction_data.len() < 11 {
                        return Err(ProgramError::InvalidInstructionData);
                    }
                    let creator_refund_pct = instruction_data[9];
                    let provider_payment_pct = instruction_data[10];
                    task::resolve_dispute(accounts, creator_refund_pct, provider_payment_pct)
                }
                17 => application::withdraw_application(accounts),
                _ => unreachable!(),
            }
        }
        // 18: AddAdmin
        18 => {
            if instruction_data.len() < 43 {
                return Err(ProgramError::InvalidInstructionData);
            }
            let name = unsafe { ptr_at::<[u8; 10]>(instruction_data, 1) };
            let address = unsafe { ptr_at::<Address>(instruction_data, 11) };
            admin::add_admin(accounts, name, address)
        }
        // 19: RemoveAdmin
        19 => {
            if instruction_data.len() < 33 {
                return Err(ProgramError::InvalidInstructionData);
            }
            let address = unsafe { ptr_at::<Address>(instruction_data, 1) };
            admin::remove_admin(accounts, address)
        }
        // 20: AddSupportedStable
        20 => {
            if instruction_data.len() < 11 {
                return Err(ProgramError::InvalidInstructionData);
            }
            let name = unsafe { ptr_at::<[u8; 10]>(instruction_data, 1) };
            stable_coin::add_supported_stable(program_id, accounts, name)
        }
        // 21: RemoveSupportedStable
        21 => stable_coin::remove_supported_stable(accounts),
        _ => Err(ReachError::InvalidInstruction.into()),
    }
}
