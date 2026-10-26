use {
    anchor_lang::{
        prelude::{Pubkey, sysvar::SysvarId},
        solana_program::{
            instruction::{AccountMeta, Instruction},
            system_instruction, system_program,
        },
    },
    litesvm::LiteSVM,
    solana_keypair::Keypair,
    solana_message::{Message, VersionedMessage},
    solana_signer::Signer,
    solana_transaction::versioned::VersionedTransaction,
};

const PROGRAM_ID: Pubkey = Pubkey::new_from_array([
    0x51, 0x72, 0x65, 0x61, 0x63, 0x68, 0x50, 0x69, 0x6e, 0x6f, 0x63, 0x63, 0x68, 0x69, 0x6f,
    0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31, 0x31,
    0x31, 0x31,
]);

fn setup_svm() -> (LiteSVM, Keypair) {
    let mut svm = LiteSVM::new();
    let bytes = include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../target/deploy/reach_pinocchio.so"
    ));
    svm.add_program(PROGRAM_ID, bytes).unwrap();
    let payer = Keypair::new();
    svm.airdrop(&payer.pubkey(), 100_000_000_000).unwrap();
    (svm, payer)
}

fn setup_mint(svm: &mut LiteSVM, payer: &Keypair, mint: &Keypair, authority: &Pubkey) {
    let rent = svm.minimum_balance_for_rent_exemption(82);
    let create_idx = system_instruction::create_account(
        &payer.pubkey(),
        &mint.pubkey(),
        rent,
        82,
        &anchor_spl::token::ID,
    );
    let blockhash1 = svm.latest_blockhash();
    let msg1 = Message::new_with_blockhash(&[create_idx], Some(&payer.pubkey()), &blockhash1);
    let tx1 = VersionedTransaction::try_new(VersionedMessage::Legacy(msg1), &[payer, mint]).unwrap();
    svm.send_transaction(tx1).unwrap();

    let init_mint_idx = anchor_spl::token::spl_token::instruction::initialize_mint(
        &anchor_spl::token::ID,
        &mint.pubkey(),
        authority,
        None,
        6,
    ).unwrap();
    let blockhash2 = svm.latest_blockhash();
    let msg2 = Message::new_with_blockhash(&[init_mint_idx], Some(&payer.pubkey()), &blockhash2);
    let tx2 = VersionedTransaction::try_new(VersionedMessage::Legacy(msg2), &[payer]).unwrap();
    svm.send_transaction(tx2).unwrap();
}

fn setup_token_account(svm: &mut LiteSVM, payer: &Keypair, owner: &Pubkey, mint: &Pubkey) -> Pubkey {
    let ata = anchor_spl::associated_token::get_associated_token_address(owner, mint);
    let create_ata_idx = anchor_spl::associated_token::spl_associated_token_account::instruction::create_associated_token_account(
        &payer.pubkey(),
        owner,
        mint,
        &anchor_spl::token::ID,
    );
    let blockhash = svm.latest_blockhash();
    let msg = Message::new_with_blockhash(&[create_ata_idx], Some(&payer.pubkey()), &blockhash);
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(msg), &[payer]).unwrap();
    svm.send_transaction(tx).unwrap();
    ata
}

fn mint_to(svm: &mut LiteSVM, payer: &Keypair, mint: &Pubkey, mint_authority: &Keypair, recipient: &Pubkey, amount: u64) {
    let mint_to_idx = anchor_spl::token::spl_token::instruction::mint_to(
        &anchor_spl::token::ID,
        mint,
        recipient,
        &mint_authority.pubkey(),
        &[],
        amount,
    ).unwrap();
    let blockhash = svm.latest_blockhash();
    let msg = Message::new_with_blockhash(&[mint_to_idx], Some(&payer.pubkey()), &blockhash);
    let tx = if payer.pubkey() == mint_authority.pubkey() {
        VersionedTransaction::try_new(VersionedMessage::Legacy(msg), &[payer]).unwrap()
    } else {
        VersionedTransaction::try_new(VersionedMessage::Legacy(msg), &[payer, mint_authority]).unwrap()
    };
    svm.send_transaction(tx).unwrap();
}

fn get_token_balance(svm: &LiteSVM, token_account: &Pubkey) -> u64 {
    let acc = svm.get_account(token_account).unwrap();
    u64::from_le_bytes(acc.data[64..72].try_into().unwrap())
}

#[test]
fn test_full_happy_path() {
    let (mut svm, owner) = setup_svm();
    let mint_auth = Keypair::new();
    let mint = Keypair::new();
    setup_mint(&mut svm, &owner, &mint, &mint_auth.pubkey());

    let creator = Keypair::new();
    let provider = Keypair::new();
    svm.airdrop(&creator.pubkey(), 10_000_000_000).unwrap();
    svm.airdrop(&provider.pubkey(), 10_000_000_000).unwrap();

    let creator_ata = setup_token_account(&mut svm, &owner, &creator.pubkey(), &mint.pubkey());
    let provider_ata = setup_token_account(&mut svm, &owner, &provider.pubkey(), &mint.pubkey());
    mint_to(&mut svm, &owner, &mint.pubkey(), &mint_auth, &creator_ata, 50_000_000);
    mint_to(&mut svm, &owner, &mint.pubkey(), &mint_auth, &provider_ata, 10_000_000);

    let (reach_state_pda, _) = Pubkey::find_program_address(&[b"reach_state"], &PROGRAM_ID);
    let (supported_stable_pda, _) = Pubkey::find_program_address(&[b"supported_stable", mint.pubkey().as_ref()], &PROGRAM_ID);
    let (fee_vault_pda, _) = Pubkey::find_program_address(&[b"fee_vault", mint.pubkey().as_ref()], &PROGRAM_ID);

    // 1. Initialize
    let mut init_data = vec![0u8];
    let mut name_bytes = [0u8; 10];
    name_bytes[..5].copy_from_slice(b"Admin");
    init_data.extend_from_slice(&name_bytes);
    let init_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: init_data,
    };
    let blockhash = svm.latest_blockhash();
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[init_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap();
    svm.send_transaction(tx).unwrap();

    // 2. Add Supported Stable
    let mut add_stable_data = vec![20u8];
    let mut sym_bytes = [0u8; 10];
    sym_bytes[..4].copy_from_slice(b"USDC");
    add_stable_data.extend_from_slice(&sym_bytes);
    let add_stable_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new(supported_stable_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: add_stable_data,
    };
    let blockhash = svm.latest_blockhash();
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[add_stable_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap();
    svm.send_transaction(tx).unwrap();

    // 3. Create Task (task_id: 1, labor: 600, material: 400, upfront: 50%, collateral: 200)
    let task_id = 1u64;
    let (task_pda, _) = Pubkey::find_program_address(&[b"task", &task_id.to_le_bytes()], &PROGRAM_ID);
    let (task_vault_pda, _) = Pubkey::find_program_address(&[b"task", task_pda.as_ref()], &PROGRAM_ID);

    let mut create_task_data = vec![6u8];
    create_task_data.extend_from_slice(&task_id.to_le_bytes());
    create_task_data.extend_from_slice(&600_000u64.to_le_bytes()); // labor
    create_task_data.extend_from_slice(&400_000u64.to_le_bytes()); // material
    create_task_data.extend_from_slice(&200_000u64.to_le_bytes()); // collateral
    create_task_data.push(50); // 50% upfront
    create_task_data.extend_from_slice(&[0u8; 7]); // pad
    create_task_data.extend_from_slice(&[0xaa; 32]); // metadata hash

    let create_task_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(supported_stable_pda, false),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(creator_ata, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: create_task_data,
    };
    let blockhash = svm.latest_blockhash();
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[create_task_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap();
    svm.send_transaction(tx).unwrap();

    assert_eq!(get_token_balance(&svm, &task_vault_pda), 1_000_000);

    // 4. Provider Applies
    let (app_pda, _) = Pubkey::find_program_address(&[b"application", provider.pubkey().as_ref(), task_pda.as_ref()], &PROGRAM_ID);
    let (debt_pda, _) = Pubkey::find_program_address(&[b"provider_debt", provider.pubkey().as_ref()], &PROGRAM_ID);

    let mut apply_data = vec![7u8];
    apply_data.extend_from_slice(&task_id.to_le_bytes());
    apply_data.extend_from_slice(&9999999999i64.to_le_bytes());

    let apply_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(provider.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(app_pda, false),
            AccountMeta::new_readonly(debt_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: apply_data,
    };
    let blockhash = svm.latest_blockhash();
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[apply_ix], Some(&provider.pubkey()), &blockhash)), &[&provider]).unwrap();
    svm.send_transaction(tx).unwrap();

    // 5. Creator Accepts Provider
    let mut accept_data = vec![8u8];
    accept_data.extend_from_slice(&task_id.to_le_bytes());
    accept_data.extend_from_slice(provider.pubkey().as_ref());

    let accept_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(app_pda, false),
        ],
        data: accept_data,
    };
    let blockhash = svm.latest_blockhash();
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[accept_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap();
    svm.send_transaction(tx).unwrap();

    // 6. Provider Deposits Collateral (200,000) & Gets Advance (200,000)
    let mut col_data = vec![9u8];
    col_data.extend_from_slice(&task_id.to_le_bytes());

    let col_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(provider.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(app_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(provider_ata, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(supported_stable_pda, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
        ],
        data: col_data,
    };
    let blockhash = svm.latest_blockhash();
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[col_ix], Some(&provider.pubkey()), &blockhash)), &[&provider]).unwrap();
    svm.send_transaction(tx).unwrap();

    // 7. Provider Completes Task
    let mut complete_data = vec![13u8];
    complete_data.extend_from_slice(&task_id.to_le_bytes());

    let complete_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(provider.pubkey(), true),
            AccountMeta::new(task_pda, false),
        ],
        data: complete_data,
    };
    let blockhash = svm.latest_blockhash();
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[complete_ix], Some(&provider.pubkey()), &blockhash)), &[&provider]).unwrap();
    svm.send_transaction(tx).unwrap();

    // 8. Creator Approves Work
    let mut approve_data = vec![14u8];
    approve_data.extend_from_slice(&task_id.to_le_bytes());

    let approve_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(provider_ata, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
        ],
        data: approve_data,
    };
    let blockhash = svm.latest_blockhash();
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[approve_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify final balances: task_vault is 0, provider received full payout + collateral
    assert_eq!(get_token_balance(&svm, &task_vault_pda), 0);
    assert_eq!(get_token_balance(&svm, &provider_ata), 11_000_000); // 10M initial + 1M labor+material
}

#[test]
fn test_task_cancellation_with_fee() {
    let (mut svm, owner) = setup_svm();
    let mint_auth = Keypair::new();
    let mint = Keypair::new();
    setup_mint(&mut svm, &owner, &mint, &mint_auth.pubkey());

    let creator = Keypair::new();
    svm.airdrop(&creator.pubkey(), 10_000_000_000).unwrap();
    let creator_ata = setup_token_account(&mut svm, &owner, &creator.pubkey(), &mint.pubkey());
    mint_to(&mut svm, &owner, &mint.pubkey(), &mint_auth, &creator_ata, 50_000_000);

    let (reach_state_pda, _) = Pubkey::find_program_address(&[b"reach_state"], &PROGRAM_ID);
    let (supported_stable_pda, _) = Pubkey::find_program_address(&[b"supported_stable", mint.pubkey().as_ref()], &PROGRAM_ID);
    let (fee_vault_pda, _) = Pubkey::find_program_address(&[b"fee_vault", mint.pubkey().as_ref()], &PROGRAM_ID);

    // Initialize & add stable
    let mut init_data = vec![0u8];
    let mut name_bytes = [0u8; 10];
    name_bytes[..5].copy_from_slice(b"Admin");
    init_data.extend_from_slice(&name_bytes);
    let init_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: init_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[init_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    let mut add_stable_data = vec![20u8];
    add_stable_data.extend_from_slice(&[0u8; 10]);
    let add_stable_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new(supported_stable_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: add_stable_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[add_stable_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    // Create Task (1_000_000 escrow)
    let task_id = 2u64;
    let (task_pda, _) = Pubkey::find_program_address(&[b"task", &task_id.to_le_bytes()], &PROGRAM_ID);
    let (task_vault_pda, _) = Pubkey::find_program_address(&[b"task", task_pda.as_ref()], &PROGRAM_ID);

    let mut create_task_data = vec![6u8];
    create_task_data.extend_from_slice(&task_id.to_le_bytes());
    create_task_data.extend_from_slice(&1_000_000u64.to_le_bytes()); // labor
    create_task_data.extend_from_slice(&0u64.to_le_bytes()); // material
    create_task_data.extend_from_slice(&0u64.to_le_bytes()); // collateral
    create_task_data.push(0);
    create_task_data.extend_from_slice(&[0u8; 7]);
    create_task_data.extend_from_slice(&[0xbb; 32]);

    let create_task_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(supported_stable_pda, false),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(creator_ata, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: create_task_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[create_task_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap()).unwrap();

    // Cancel task: 10% cancellation fee = 100_000, refund = 900_000
    let mut cancel_data = vec![11u8];
    cancel_data.extend_from_slice(&task_id.to_le_bytes());

    let cancel_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new(creator_ata, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: cancel_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[cancel_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap()).unwrap();

    assert_eq!(get_token_balance(&svm, &fee_vault_pda), 100_000);
    assert_eq!(get_token_balance(&svm, &creator_ata), 49_900_000);
    assert_eq!(get_token_balance(&svm, &task_vault_pda), 0);
}

#[test]
fn test_dispute_resolution() {
    let (mut svm, owner) = setup_svm();
    let mint_auth = Keypair::new();
    let mint = Keypair::new();
    setup_mint(&mut svm, &owner, &mint, &mint_auth.pubkey());

    let creator = Keypair::new();
    let provider = Keypair::new();
    svm.airdrop(&creator.pubkey(), 10_000_000_000).unwrap();
    svm.airdrop(&provider.pubkey(), 10_000_000_000).unwrap();

    let creator_ata = setup_token_account(&mut svm, &owner, &creator.pubkey(), &mint.pubkey());
    let provider_ata = setup_token_account(&mut svm, &owner, &provider.pubkey(), &mint.pubkey());
    mint_to(&mut svm, &owner, &mint.pubkey(), &mint_auth, &creator_ata, 50_000_000);

    let (reach_state_pda, _) = Pubkey::find_program_address(&[b"reach_state"], &PROGRAM_ID);
    let (supported_stable_pda, _) = Pubkey::find_program_address(&[b"supported_stable", mint.pubkey().as_ref()], &PROGRAM_ID);
    let (fee_vault_pda, _) = Pubkey::find_program_address(&[b"fee_vault", mint.pubkey().as_ref()], &PROGRAM_ID);

    // Initialize & add stable
    let mut init_data = vec![0u8];
    init_data.extend_from_slice(&[0u8; 10]);
    let init_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: init_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[init_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    let mut add_stable_data = vec![20u8];
    add_stable_data.extend_from_slice(&[0u8; 10]);
    let add_stable_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new(supported_stable_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: add_stable_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[add_stable_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    // Create Task (1_000_000 escrow)
    let task_id = 3u64;
    let (task_pda, _) = Pubkey::find_program_address(&[b"task", &task_id.to_le_bytes()], &PROGRAM_ID);
    let (task_vault_pda, _) = Pubkey::find_program_address(&[b"task", task_pda.as_ref()], &PROGRAM_ID);

    let mut create_task_data = vec![6u8];
    create_task_data.extend_from_slice(&task_id.to_le_bytes());
    create_task_data.extend_from_slice(&1_000_000u64.to_le_bytes());
    create_task_data.extend_from_slice(&0u64.to_le_bytes());
    create_task_data.extend_from_slice(&0u64.to_le_bytes());
    create_task_data.push(0);
    create_task_data.extend_from_slice(&[0u8; 7]);
    create_task_data.extend_from_slice(&[0xcc; 32]);

    let create_task_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(supported_stable_pda, false),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(creator_ata, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: create_task_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[create_task_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap()).unwrap();

    // Apply & Accept
    let (app_pda, _) = Pubkey::find_program_address(&[b"application", provider.pubkey().as_ref(), task_pda.as_ref()], &PROGRAM_ID);
    let (debt_pda, _) = Pubkey::find_program_address(&[b"provider_debt", provider.pubkey().as_ref()], &PROGRAM_ID);

    let mut apply_data = vec![7u8];
    apply_data.extend_from_slice(&task_id.to_le_bytes());
    apply_data.extend_from_slice(&9999999999i64.to_le_bytes());
    let apply_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(provider.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(app_pda, false),
            AccountMeta::new_readonly(debt_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: apply_data.clone(),
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[apply_ix], Some(&provider.pubkey()), &blockhash)), &[&provider]).unwrap()).unwrap();

    let mut accept_data = vec![8u8];
    accept_data.extend_from_slice(&task_id.to_le_bytes());
    accept_data.extend_from_slice(provider.pubkey().as_ref());
    let accept_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(app_pda, false),
        ],
        data: accept_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[accept_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap()).unwrap();

    // Raise Dispute
    let mut dispute_data = vec![15u8];
    dispute_data.extend_from_slice(&task_id.to_le_bytes());
    let dispute_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new(task_pda, false),
        ],
        data: dispute_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[dispute_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap()).unwrap();

    // Resolve Dispute: 60% creator refund (600,000), 40% provider payment (400,000)
    let mut resolve_data = vec![16u8];
    resolve_data.extend_from_slice(&task_id.to_le_bytes());
    resolve_data.push(60);
    resolve_data.push(40);

    let resolve_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(creator_ata, false),
            AccountMeta::new(provider_ata, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
        ],
        data: resolve_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[resolve_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    assert_eq!(get_token_balance(&svm, &creator_ata), 49_600_000); // 49M + 600k refund
    assert_eq!(get_token_balance(&svm, &provider_ata), 400_000);   // 400k payment
    assert_eq!(get_token_balance(&svm, &task_vault_pda), 0);
}

#[test]
fn test_approved_application_cancellation_and_debt_enforcement() {
    let (mut svm, owner) = setup_svm();
    let mint_auth = Keypair::new();
    let mint = Keypair::new();
    setup_mint(&mut svm, &owner, &mint, &mint_auth.pubkey());

    let creator = Keypair::new();
    let provider = Keypair::new();
    svm.airdrop(&creator.pubkey(), 10_000_000_000).unwrap();
    svm.airdrop(&provider.pubkey(), 10_000_000_000).unwrap();

    let creator_ata = setup_token_account(&mut svm, &owner, &creator.pubkey(), &mint.pubkey());
    let provider_ata = setup_token_account(&mut svm, &owner, &provider.pubkey(), &mint.pubkey());
    mint_to(&mut svm, &owner, &mint.pubkey(), &mint_auth, &creator_ata, 50_000_000);
    mint_to(&mut svm, &owner, &mint.pubkey(), &mint_auth, &provider_ata, 10_000_000);

    let (reach_state_pda, _) = Pubkey::find_program_address(&[b"reach_state"], &PROGRAM_ID);
    let (supported_stable_pda, _) = Pubkey::find_program_address(&[b"supported_stable", mint.pubkey().as_ref()], &PROGRAM_ID);
    let (fee_vault_pda, _) = Pubkey::find_program_address(&[b"fee_vault", mint.pubkey().as_ref()], &PROGRAM_ID);

    // Initialize & add stable
    let mut init_data = vec![0u8];
    init_data.extend_from_slice(&[0u8; 10]);
    let init_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: init_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[init_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    let mut add_stable_data = vec![20u8];
    add_stable_data.extend_from_slice(&[0u8; 10]);
    let add_stable_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new(supported_stable_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: add_stable_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[add_stable_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    // Create Task: material 500_000, 50% upfront = 250_000, 0 collateral
    let task_id = 4u64;
    let (task_pda, _) = Pubkey::find_program_address(&[b"task", &task_id.to_le_bytes()], &PROGRAM_ID);
    let (task_vault_pda, _) = Pubkey::find_program_address(&[b"task", task_pda.as_ref()], &PROGRAM_ID);

    let mut create_task_data = vec![6u8];
    create_task_data.extend_from_slice(&task_id.to_le_bytes());
    create_task_data.extend_from_slice(&500_000u64.to_le_bytes()); // labor
    create_task_data.extend_from_slice(&500_000u64.to_le_bytes()); // material
    create_task_data.extend_from_slice(&0u64.to_le_bytes());       // collateral = 0
    create_task_data.push(50); // 50% upfront
    create_task_data.extend_from_slice(&[0u8; 7]);
    create_task_data.extend_from_slice(&[0xdd; 32]);

    let create_task_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(supported_stable_pda, false),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(creator_ata, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: create_task_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[create_task_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap()).unwrap();

    // Apply & Accept (collateral = 0 -> status is Accepted, InProgress)
    let (app_pda, _) = Pubkey::find_program_address(&[b"application", provider.pubkey().as_ref(), task_pda.as_ref()], &PROGRAM_ID);
    let (debt_pda, _) = Pubkey::find_program_address(&[b"provider_debt", provider.pubkey().as_ref()], &PROGRAM_ID);

    let mut apply_data = vec![7u8];
    apply_data.extend_from_slice(&task_id.to_le_bytes());
    apply_data.extend_from_slice(&9999999999i64.to_le_bytes());
    let apply_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(provider.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(app_pda, false),
            AccountMeta::new_readonly(debt_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: apply_data.clone(),
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[apply_ix], Some(&provider.pubkey()), &blockhash)), &[&provider]).unwrap()).unwrap();

    let mut accept_data = vec![8u8];
    accept_data.extend_from_slice(&task_id.to_le_bytes());
    accept_data.extend_from_slice(provider.pubkey().as_ref());
    let accept_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(creator.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(app_pda, false),
        ],
        data: accept_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[accept_ix], Some(&creator.pubkey()), &blockhash)), &[&creator]).unwrap()).unwrap();

    // Provider claims advance (250_000)
    let mut claim_data = vec![10u8];
    claim_data.extend_from_slice(&task_id.to_le_bytes());
    let claim_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(provider.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(provider_ata, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
        ],
        data: claim_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[claim_ix], Some(&provider.pubkey()), &blockhash)), &[&provider]).unwrap()).unwrap();

    assert_eq!(get_token_balance(&svm, &provider_ata), 10_250_000);

    // Provider cancels approved application with advance > collateral
    // Provider repays difference (250_000) to task_vault and 10% fee (100_000) to fee_vault
    let mut cancel_app_data = vec![12u8];
    cancel_app_data.extend_from_slice(&task_id.to_le_bytes());
    let cancel_app_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(provider.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(task_vault_pda, false),
            AccountMeta::new(app_pda, false),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new(provider_ata, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new(debt_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: cancel_app_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[cancel_app_ix], Some(&provider.pubkey()), &blockhash)), &[&provider]).unwrap()).unwrap();

    // Task vault is restored to full 1_000_000 escrow
    assert_eq!(get_token_balance(&svm, &task_vault_pda), 1_000_000);
    assert_eq!(get_token_balance(&svm, &fee_vault_pda), 100_000);

    // Verify Provider Debt: has_debt is true in provider_debt account
    let debt_acc = svm.get_account(&debt_pda).unwrap();
    assert_eq!(debt_acc.data[40], 1); // has_debt = 1

    // Now provider attempts to apply for another task -> must FAIL with ProviderHasDebt
    let (app2_pda, _) = Pubkey::find_program_address(&[b"application", provider.pubkey().as_ref(), task_pda.as_ref()], &PROGRAM_ID);
    let apply_fail_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(provider.pubkey(), true),
            AccountMeta::new(task_pda, false),
            AccountMeta::new(app2_pda, false),
            AccountMeta::new_readonly(debt_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: apply_data,
    };
    let blockhash = svm.latest_blockhash();
    let res = svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[apply_fail_ix], Some(&provider.pubkey()), &blockhash)), &[&provider]).unwrap());
    assert!(res.is_err()); // Blocked because of debt!
}

#[test]
fn test_admin_and_protocol_fee_withdrawal() {
    let (mut svm, owner) = setup_svm();
    let mint_auth = Keypair::new();
    let mint = Keypair::new();
    setup_mint(&mut svm, &owner, &mint, &mint_auth.pubkey());

    let (reach_state_pda, _) = Pubkey::find_program_address(&[b"reach_state"], &PROGRAM_ID);
    let (supported_stable_pda, _) = Pubkey::find_program_address(&[b"supported_stable", mint.pubkey().as_ref()], &PROGRAM_ID);
    let (fee_vault_pda, _) = Pubkey::find_program_address(&[b"fee_vault", mint.pubkey().as_ref()], &PROGRAM_ID);

    // Initialize & add stable
    let mut init_data = vec![0u8];
    init_data.extend_from_slice(&[0u8; 10]);
    let init_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
        ],
        data: init_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[init_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    let mut add_stable_data = vec![20u8];
    add_stable_data.extend_from_slice(&[0u8; 10]);
    let add_stable_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new(supported_stable_pda, false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new_readonly(system_program::ID, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
            AccountMeta::new_readonly(anchor_lang::prelude::Rent::id(), false),
        ],
        data: add_stable_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[add_stable_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    // Mint fees directly to fee_vault
    mint_to(&mut svm, &owner, &mint.pubkey(), &mint_auth, &fee_vault_pda, 5_000_000);
    assert_eq!(get_token_balance(&svm, &fee_vault_pda), 5_000_000);

    // Owner withdraws protocol fees
    let receiver = setup_token_account(&mut svm, &owner, &owner.pubkey(), &mint.pubkey());
    let mut withdraw_data = vec![5u8];
    withdraw_data.extend_from_slice(&3_000_000u64.to_le_bytes()); // withdraw 3M

    let withdraw_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
            AccountMeta::new_readonly(mint.pubkey(), false),
            AccountMeta::new(fee_vault_pda, false),
            AccountMeta::new(receiver, false),
            AccountMeta::new_readonly(anchor_spl::token::ID, false),
        ],
        data: withdraw_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[withdraw_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    assert_eq!(get_token_balance(&svm, &receiver), 3_000_000);
    assert_eq!(get_token_balance(&svm, &fee_vault_pda), 2_000_000);

    // Add Admin
    let admin_user = Keypair::new();
    svm.airdrop(&admin_user.pubkey(), 10_000_000_000).unwrap();
    let mut add_admin_data = vec![18u8];
    let mut name = [0u8; 10];
    name[..5].copy_from_slice(b"Mod01");
    add_admin_data.extend_from_slice(&name);
    add_admin_data.extend_from_slice(admin_user.pubkey().as_ref());

    let add_admin_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(owner.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
        ],
        data: add_admin_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[add_admin_ix], Some(&owner.pubkey()), &blockhash)), &[&owner]).unwrap()).unwrap();

    // Verify admin can update creation fee pct
    let mut update_fee_data = vec![1u8];
    update_fee_data.extend_from_slice(&500u16.to_le_bytes()); // 5% fee
    let update_fee_ix = Instruction {
        program_id: PROGRAM_ID,
        accounts: vec![
            AccountMeta::new(admin_user.pubkey(), true),
            AccountMeta::new(reach_state_pda, false),
        ],
        data: update_fee_data,
    };
    let blockhash = svm.latest_blockhash();
    svm.send_transaction(VersionedTransaction::try_new(VersionedMessage::Legacy(Message::new_with_blockhash(&[update_fee_ix], Some(&admin_user.pubkey()), &blockhash)), &[&admin_user]).unwrap()).unwrap();
}
