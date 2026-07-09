use {
    anchor_lang::{
        prelude::{Pubkey, Rent, sysvar::SysvarId},
        solana_program::{instruction::Instruction, system_instruction, system_program},
        AccountDeserialize, InstructionData, ToAccountMetas,
    },
    litesvm::LiteSVM,
    solana_keypair::Keypair,
    solana_message::{Message, VersionedMessage},
    solana_signer::Signer,
    solana_transaction::versioned::VersionedTransaction,
    sol_contract::state::*,
};

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

fn setup_svm() -> (LiteSVM, Pubkey, Keypair) {
    let program_id = sol_contract::id();
    let mut svm = LiteSVM::new();
    let bytes = include_bytes!(concat!(
        env!("CARGO_TARGET_TMPDIR"),
        "/../deploy/sol_contract.so"
    ));
    svm.add_program(program_id, bytes).unwrap();
    let payer = Keypair::new();
    svm.airdrop(&payer.pubkey(), 10_000_000_000).unwrap();
    (svm, program_id, payer)
}

#[test]
fn test_happy_path() {
    let (mut svm, program_id, owner) = setup_svm();

    // 1. Initialize ReachState
    let reach_state_pda = Pubkey::find_program_address(&[sol_contract::constants::REACH_STATE_SEED], &program_id).0;
    let init_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::Initialize { owner_name: "OwnerAdmin".to_string() }.data(),
        sol_contract::accounts::Initialize {
            owner: owner.pubkey(),
            reach_state: reach_state_pda,
            system_program: system_program::ID,
        }.to_account_metas(None),
    );

    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[init_ix], Some(&owner.pubkey()), &svm.latest_blockhash())),
        &[&owner],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify ReachState
    let state_acc = svm.get_account(&reach_state_pda).unwrap();
    let reach_state = ReachState::try_deserialize(&mut &state_acc.data[..]).unwrap();
    assert_eq!(reach_state.owner, owner.pubkey());
    assert_eq!(reach_state.admins[0].name, "OwnerAdmin");
    assert_eq!(reach_state.admins[0].address, owner.pubkey());

    // 2. Setup stablecoin Mint
    let usdc_mint = Keypair::new();
    setup_mint(&mut svm, &owner, &usdc_mint, &owner.pubkey());

    // 3. Add Supported Stable
    let supported_stable_pda = Pubkey::find_program_address(
        &[sol_contract::constants::STABLE_COIN_SEED, usdc_mint.pubkey().as_ref()],
        &program_id,
    ).0;
    
    let add_stable_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::AddSupportedStable { stable_name: "USDC".to_string() }.data(),
        sol_contract::accounts::AddSupportedStable {
            caller: owner.pubkey(),
            reach_state: reach_state_pda,
            stable_coin_mint: usdc_mint.pubkey(),
            supported_token: supported_stable_pda,
            system_program: system_program::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[add_stable_ix], Some(&owner.pubkey()), &svm.latest_blockhash())),
        &[&owner],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify SupportedStable
    let stable_acc = svm.get_account(&supported_stable_pda).unwrap();
    let supported_stable = SupportedStable::try_deserialize(&mut &stable_acc.data[..]).unwrap();
    assert_eq!(supported_stable.mint, usdc_mint.pubkey());
    assert_eq!(supported_stable.name, "USDC");

    // 4. Update creation fee pct to 5% (500 basis points)
    let update_fee_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::UpdateCreationFeePct { fee_pct: 500 }.data(),
        sol_contract::accounts::AdminAction {
            caller: owner.pubkey(),
            reach_state: reach_state_pda,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[update_fee_ix], Some(&owner.pubkey()), &svm.latest_blockhash())),
        &[&owner],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // 5. Create Task
    let creator = Keypair::new();
    svm.airdrop(&creator.pubkey(), 1_000_000_000).unwrap();
    let creator_token_acc = setup_token_account(&mut svm, &owner, &creator.pubkey(), &usdc_mint.pubkey());
    mint_to(&mut svm, &owner, &usdc_mint.pubkey(), &owner, &creator_token_acc, 1000);

    let task_id: u64 = 101;
    let task_pda = Pubkey::find_program_address(
        &[sol_contract::constants::TASK_SEED, &task_id.to_le_bytes()],
        &program_id,
    ).0;
    let task_vault_pda = Pubkey::find_program_address(
        &[sol_contract::constants::TASK_SEED, task_pda.as_ref()],
        &program_id,
    ).0;
    let fee_vault_pda = Pubkey::find_program_address(
        &[b"fee_vault", usdc_mint.pubkey().as_ref()],
        &program_id,
    ).0;

    let terms = FinancialTerms {
        labor_fee: 100,
        material_cost: 100,
        upfront_release_pct: 50, // 50% upfront
        required_provider_collateral: 50,
    };

    let create_task_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::CreateTask {
            task_id,
            terms: terms.clone(),
            tag: Some("Rust".to_string()),
            desc: Some("Write Anchor Contract".to_string()),
        }.data(),
        sol_contract::accounts::CreateTask {
            creator: creator.pubkey(),
            stable_coin_mint: usdc_mint.pubkey(),
            supported_token_check: supported_stable_pda,
            reach_state: reach_state_pda,
            fee_vault: fee_vault_pda,
            task: task_pda,
            task_vault: task_vault_pda,
            creator_token_account: creator_token_acc,
            system_program: system_program::ID,
            token_program: anchor_spl::token::ID,
            rent: Rent::id(),
        }.to_account_metas(None),
    );

    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[create_task_ix], Some(&creator.pubkey()), &svm.latest_blockhash())),
        &[&creator],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify task creation balances
    // Total Escrow = 100 + 100 = 200 tokens. Creation Fee (5%) = 10 tokens.
    // Creator paid 210 tokens. task_vault should have 200. fee_vault should have 10.
    let creator_balance = svm.get_account(&creator_token_acc).unwrap();
    let creator_ata = anchor_spl::token::TokenAccount::try_deserialize(&mut &creator_balance.data[..]).unwrap();
    assert_eq!(creator_ata.amount, 1000 - 210);

    let vault_balance = svm.get_account(&task_vault_pda).unwrap();
    let task_vault = anchor_spl::token::TokenAccount::try_deserialize(&mut &vault_balance.data[..]).unwrap();
    assert_eq!(task_vault.amount, 200);

    let fee_balance = svm.get_account(&fee_vault_pda).unwrap();
    let fee_vault = anchor_spl::token::TokenAccount::try_deserialize(&mut &fee_balance.data[..]).unwrap();
    assert_eq!(fee_vault.amount, 10);

    let task_acc = svm.get_account(&task_pda).unwrap();
    let task = Task::try_deserialize(&mut &task_acc.data[..]).unwrap();
    assert_eq!(task.status, TaskStatus::Open);

    // 6. Provider Applies to Task
    let provider = Keypair::new();
    svm.airdrop(&provider.pubkey(), 1_000_000_000).unwrap();
    let provider_token_acc = setup_token_account(&mut svm, &owner, &provider.pubkey(), &usdc_mint.pubkey());
    mint_to(&mut svm, &owner, &usdc_mint.pubkey(), &owner, &provider_token_acc, 50); // 50 tokens for collateral

    let application_pda = Pubkey::find_program_address(
        &[sol_contract::constants::APPLICATION_SEED, provider.pubkey().as_ref(), task_pda.as_ref()],
        &program_id,
    ).0;
    let provider_debt_pda = Pubkey::find_program_address(
        &[b"provider_debt", provider.pubkey().as_ref()],
        &program_id,
    ).0;

    let apply_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::Apply { task_id, expires_at: 9999999999 }.data(),
        sol_contract::accounts::CreateApplication {
            provider: provider.pubkey(),
            task: task_pda,
            application: application_pda,
            provider_debt: provider_debt_pda,
            system_program: system_program::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[apply_ix], Some(&provider.pubkey()), &svm.latest_blockhash())),
        &[&provider],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    let app_acc = svm.get_account(&application_pda).unwrap();
    let application = ProviderApplication::try_deserialize(&mut &app_acc.data[..]).unwrap();
    assert_eq!(application.status, ProviderApplicationStatus::Pending);

    // 7. Accept Application (signed by state owner)
    let accept_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::Accept { task_id, provider: provider.pubkey() }.data(),
        sol_contract::accounts::AcceptApplication {
            owner: owner.pubkey(),
            task: task_pda,
            application: application_pda,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[accept_ix], Some(&owner.pubkey()), &svm.latest_blockhash())),
        &[&owner],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    let task_acc = svm.get_account(&task_pda).unwrap();
    let task = Task::try_deserialize(&mut &task_acc.data[..]).unwrap();
    assert_eq!(task.provider, Some(provider.pubkey()));

    // Status is AcceptedPendingCollateral because required_provider_collateral is > 0
    let app_acc = svm.get_account(&application_pda).unwrap();
    let application = ProviderApplication::try_deserialize(&mut &app_acc.data[..]).unwrap();
    assert_eq!(application.status, ProviderApplicationStatus::AcceptedPendingCollateral);

    // 8. Provide Collateral
    let collateral_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::ProvideCollateral { task_id }.data(),
        sol_contract::accounts::ProvideCollateral {
            provider: provider.pubkey(),
            task: task_pda,
            application: application_pda,
            task_vault: task_vault_pda,
            provider_token_account: provider_token_acc,
            stable_coin_mint: usdc_mint.pubkey(),
            supported_token_check: supported_stable_pda,
            token_program: anchor_spl::token::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[collateral_ix], Some(&provider.pubkey()), &svm.latest_blockhash())),
        &[&provider],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify collateral and advance
    // Provider deposited 50 (collateral), and received 50 (upfront material cost)
    // Net provider balance should remain 50.
    let provider_balance = svm.get_account(&provider_token_acc).unwrap();
    let provider_ata = anchor_spl::token::TokenAccount::try_deserialize(&mut &provider_balance.data[..]).unwrap();
    assert_eq!(provider_ata.amount, 50);

    // task_vault should hold: 200 (creator) + 50 (provider collateral) - 50 (advance) = 200 tokens
    let vault_balance = svm.get_account(&task_vault_pda).unwrap();
    let task_vault = anchor_spl::token::TokenAccount::try_deserialize(&mut &vault_balance.data[..]).unwrap();
    assert_eq!(task_vault.amount, 200);

    let app_acc = svm.get_account(&application_pda).unwrap();
    let application = ProviderApplication::try_deserialize(&mut &app_acc.data[..]).unwrap();
    assert_eq!(application.status, ProviderApplicationStatus::AcceptedAndCollateralProvided);

    // 9. Complete Task (Provider flags as complete)
    let complete_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::CompleteTask { task_id }.data(),
        sol_contract::accounts::CompleteTask {
            provider: provider.pubkey(),
            task: task_pda,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[complete_ix], Some(&provider.pubkey()), &svm.latest_blockhash())),
        &[&provider],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    let task_acc = svm.get_account(&task_pda).unwrap();
    let task = Task::try_deserialize(&mut &task_acc.data[..]).unwrap();
    assert_eq!(task.status, TaskStatus::AwaitingApproval);

    // 10. Approve Work (Creator approves task)
    let approve_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::ApproveWork { task_id }.data(),
        sol_contract::accounts::ApproveWork {
            creator: creator.pubkey(),
            task: task_pda,
            task_vault: task_vault_pda,
            provider_token_account: provider_token_acc,
            stable_coin_mint: usdc_mint.pubkey(),
            token_program: anchor_spl::token::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[approve_ix], Some(&creator.pubkey()), &svm.latest_blockhash())),
        &[&creator],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify final payouts:
    // task_vault is now empty
    // Provider is paid remaining creator escrow (200 - 50 = 150) + gets collateral back (50) = 200 tokens
    // Provider's final ATA balance should be: 50 + 200 = 250 tokens.
    let provider_balance = svm.get_account(&provider_token_acc).unwrap();
    let provider_ata = anchor_spl::token::TokenAccount::try_deserialize(&mut &provider_balance.data[..]).unwrap();
    assert_eq!(provider_ata.amount, 250);

    let vault_balance = svm.get_account(&task_vault_pda).unwrap();
    let task_vault = anchor_spl::token::TokenAccount::try_deserialize(&mut &vault_balance.data[..]).unwrap();
    assert_eq!(task_vault.amount, 0);

    let task_acc = svm.get_account(&task_pda).unwrap();
    let task = Task::try_deserialize(&mut &task_acc.data[..]).unwrap();
    assert_eq!(task.status, TaskStatus::Completed);
}

#[test]
fn test_cancellation_and_debt() {
    let (mut svm, program_id, owner) = setup_svm();

    // 1. Initialize ReachState
    let reach_state_pda = Pubkey::find_program_address(&[sol_contract::constants::REACH_STATE_SEED], &program_id).0;
    let init_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::Initialize { owner_name: "OwnerAdmin".to_string() }.data(),
        sol_contract::accounts::Initialize {
            owner: owner.pubkey(),
            reach_state: reach_state_pda,
            system_program: system_program::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[init_ix], Some(&owner.pubkey()), &svm.latest_blockhash())),
        &[&owner],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Update cancellation fee to 10% (1000 basis points)
    let update_cancel_fee_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::UpdateCancellationFeePct { fee_pct: 1000 }.data(),
        sol_contract::accounts::AdminAction {
            caller: owner.pubkey(),
            reach_state: reach_state_pda,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[update_cancel_fee_ix], Some(&owner.pubkey()), &svm.latest_blockhash())),
        &[&owner],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Setup stable Mint & stable PDA check
    let usdc_mint = Keypair::new();
    setup_mint(&mut svm, &owner, &usdc_mint, &owner.pubkey());
    let supported_stable_pda = Pubkey::find_program_address(
        &[sol_contract::constants::STABLE_COIN_SEED, usdc_mint.pubkey().as_ref()],
        &program_id,
    ).0;
    let add_stable_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::AddSupportedStable { stable_name: "USDC".to_string() }.data(),
        sol_contract::accounts::AddSupportedStable {
            caller: owner.pubkey(),
            reach_state: reach_state_pda,
            stable_coin_mint: usdc_mint.pubkey(),
            supported_token: supported_stable_pda,
            system_program: system_program::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[add_stable_ix], Some(&owner.pubkey()), &svm.latest_blockhash())),
        &[&owner],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // 2. Creator Cancels Task (Happy cancellation with fee routing)
    let creator = Keypair::new();
    svm.airdrop(&creator.pubkey(), 1_000_000_000).unwrap();
    let creator_token_acc = setup_token_account(&mut svm, &owner, &creator.pubkey(), &usdc_mint.pubkey());
    mint_to(&mut svm, &owner, &usdc_mint.pubkey(), &owner, &creator_token_acc, 500);

    let task_id_1: u64 = 201;
    let task_pda_1 = Pubkey::find_program_address(
        &[sol_contract::constants::TASK_SEED, &task_id_1.to_le_bytes()],
        &program_id,
    ).0;
    let task_vault_pda_1 = Pubkey::find_program_address(
        &[sol_contract::constants::TASK_SEED, task_pda_1.as_ref()],
        &program_id,
    ).0;
    let fee_vault_pda = Pubkey::find_program_address(
        &[b"fee_vault", usdc_mint.pubkey().as_ref()],
        &program_id,
    ).0;

    let terms = FinancialTerms {
        labor_fee: 100,
        material_cost: 100,
        upfront_release_pct: 0,
        required_provider_collateral: 0,
    };

    // Create task
    let create_task_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::CreateTask {
            task_id: task_id_1,
            terms: terms.clone(),
            tag: None,
            desc: None,
        }.data(),
        sol_contract::accounts::CreateTask {
            creator: creator.pubkey(),
            stable_coin_mint: usdc_mint.pubkey(),
            supported_token_check: supported_stable_pda,
            reach_state: reach_state_pda,
            fee_vault: fee_vault_pda,
            task: task_pda_1,
            task_vault: task_vault_pda_1,
            creator_token_account: creator_token_acc,
            system_program: system_program::ID,
            token_program: anchor_spl::token::ID,
            rent: Rent::id(),
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[create_task_ix], Some(&creator.pubkey()), &svm.latest_blockhash())),
        &[&creator],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Cancel task
    let cancel_task_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::CancelTask { task_id: task_id_1 }.data(),
        sol_contract::accounts::CancelTask {
            creator: creator.pubkey(),
            task: task_pda_1,
            task_vault: task_vault_pda_1,
            reach_state: reach_state_pda,
            fee_vault: fee_vault_pda,
            creator_token_account: creator_token_acc,
            stable_coin_mint: usdc_mint.pubkey(),
            system_program: system_program::ID,
            token_program: anchor_spl::token::ID,
            rent: Rent::id(),
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[cancel_task_ix], Some(&creator.pubkey()), &svm.latest_blockhash())),
        &[&creator],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify task refund
    // Total Escrow = 200. Cancellation Fee (10%) = 20 tokens. Creator refunded = 180 tokens.
    // Creator balance should be: 500 - 200 (created) + 180 (refunded) = 480 tokens.
    let creator_balance = svm.get_account(&creator_token_acc).unwrap();
    let creator_ata = anchor_spl::token::TokenAccount::try_deserialize(&mut &creator_balance.data[..]).unwrap();
    assert_eq!(creator_ata.amount, 480);

    let fee_balance = svm.get_account(&fee_vault_pda).unwrap();
    let fee_vault = anchor_spl::token::TokenAccount::try_deserialize(&mut &fee_balance.data[..]).unwrap();
    assert_eq!(fee_vault.amount, 20);

    let task_acc = svm.get_account(&task_pda_1).unwrap();
    let task = Task::try_deserialize(&mut &task_acc.data[..]).unwrap();
    assert_eq!(task.status, TaskStatus::Refunded);

    // 3. Setup Task 2 for Case B (Provider debt on cancellation)
    let task_id_2: u64 = 202;
    let task_pda_2 = Pubkey::find_program_address(
        &[sol_contract::constants::TASK_SEED, &task_id_2.to_le_bytes()],
        &program_id,
    ).0;
    let task_vault_pda_2 = Pubkey::find_program_address(
        &[sol_contract::constants::TASK_SEED, task_pda_2.as_ref()],
        &program_id,
    ).0;

    let debt_terms = FinancialTerms {
        labor_fee: 100,
        material_cost: 100,
        upfront_release_pct: 50, // 50% advance = 50 tokens
        required_provider_collateral: 20, // collateral of 20 tokens (exceeded by advance)
    };

    let create_task_ix_2 = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::CreateTask {
            task_id: task_id_2,
            terms: debt_terms.clone(),
            tag: None,
            desc: None,
        }.data(),
        sol_contract::accounts::CreateTask {
            creator: creator.pubkey(),
            stable_coin_mint: usdc_mint.pubkey(),
            supported_token_check: supported_stable_pda,
            reach_state: reach_state_pda,
            fee_vault: fee_vault_pda,
            task: task_pda_2,
            task_vault: task_vault_pda_2,
            creator_token_account: creator_token_acc,
            system_program: system_program::ID,
            token_program: anchor_spl::token::ID,
            rent: Rent::id(),
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[create_task_ix_2], Some(&creator.pubkey()), &svm.latest_blockhash())),
        &[&creator],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Setup provider
    let provider = Keypair::new();
    svm.airdrop(&provider.pubkey(), 1_000_000_000).unwrap();
    let provider_token_acc = setup_token_account(&mut svm, &owner, &provider.pubkey(), &usdc_mint.pubkey());
    mint_to(&mut svm, &owner, &usdc_mint.pubkey(), &owner, &provider_token_acc, 100); // has enough to pay collateral & subsequent debt

    let application_pda = Pubkey::find_program_address(
        &[sol_contract::constants::APPLICATION_SEED, provider.pubkey().as_ref(), task_pda_2.as_ref()],
        &program_id,
    ).0;
    let provider_debt_pda = Pubkey::find_program_address(
        &[b"provider_debt", provider.pubkey().as_ref()],
        &program_id,
    ).0;

    // Apply
    let apply_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::Apply { task_id: task_id_2, expires_at: 9999999999 }.data(),
        sol_contract::accounts::CreateApplication {
            provider: provider.pubkey(),
            task: task_pda_2,
            application: application_pda,
            provider_debt: provider_debt_pda,
            system_program: system_program::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[apply_ix], Some(&provider.pubkey()), &svm.latest_blockhash())),
        &[&provider],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Accept
    let accept_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::Accept { task_id: task_id_2, provider: provider.pubkey() }.data(),
        sol_contract::accounts::AcceptApplication {
            owner: creator.pubkey(),
            task: task_pda_2,
            application: application_pda,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[accept_ix], Some(&creator.pubkey()), &svm.latest_blockhash())),
        &[&creator],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Provider locks collateral (20 tokens) & receives upfront advance (50 tokens)
    // Provider net balance: 100 - 20 (locked) + 50 (received) = 130 tokens
    let collateral_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::ProvideCollateral { task_id: task_id_2 }.data(),
        sol_contract::accounts::ProvideCollateral {
            provider: provider.pubkey(),
            task: task_pda_2,
            application: application_pda,
            task_vault: task_vault_pda_2,
            provider_token_account: provider_token_acc,
            stable_coin_mint: usdc_mint.pubkey(),
            supported_token_check: supported_stable_pda,
            token_program: anchor_spl::token::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[collateral_ix], Some(&provider.pubkey()), &svm.latest_blockhash())),
        &[&provider],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    let provider_balance = svm.get_account(&provider_token_acc).unwrap();
    let provider_ata = anchor_spl::token::TokenAccount::try_deserialize(&mut &provider_balance.data[..]).unwrap();
    assert_eq!(provider_ata.amount, 130);

    // 4. Provider cancels their approved application (Case B)
    // Advance = 50. Collateral = 20. (Advance > Collateral).
    // Provider gets 0 refund.
    // Provider pays difference: 30 back to task_vault.
    // Provider pays additional 10% cancellation fee: 20 tokens to fee_vault.
    // Provider total debited: 30 + 20 = 50 tokens. Provider final balance: 130 - 50 = 80 tokens.
    let cancel_app_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::CancelApprovedApplication { task_id: task_id_2 }.data(),
        sol_contract::accounts::CancelApprovedApplication {
            provider: provider.pubkey(),
            task: task_pda_2,
            task_vault: task_vault_pda_2,
            application: application_pda,
            reach_state: reach_state_pda,
            fee_vault: fee_vault_pda,
            provider_token_account: provider_token_acc,
            stable_coin_mint: usdc_mint.pubkey(),
            provider_debt: provider_debt_pda,
            system_program: system_program::ID,
            token_program: anchor_spl::token::ID,
            rent: Rent::id(),
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[cancel_app_ix], Some(&provider.pubkey()), &svm.latest_blockhash())),
        &[&provider],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify balances
    let provider_balance = svm.get_account(&provider_token_acc).unwrap();
    let provider_ata = anchor_spl::token::TokenAccount::try_deserialize(&mut &provider_balance.data[..]).unwrap();
    assert_eq!(provider_ata.amount, 80); // net loss is 20 tokens (10% fee) from their original 100.

    // Creator's (and vault's) full 200 escrow is restored in task_vault_pda_2
    let vault_balance = svm.get_account(&task_vault_pda_2).unwrap();
    let task_vault = anchor_spl::token::TokenAccount::try_deserialize(&mut &vault_balance.data[..]).unwrap();
    assert_eq!(task_vault.amount, 200);

    // Fee vault should have: 20 (cancellation fee task 1) + 20 (cancellation fee task 2) = 40 tokens.
    let fee_balance = svm.get_account(&fee_vault_pda).unwrap();
    let fee_vault = anchor_spl::token::TokenAccount::try_deserialize(&mut &fee_balance.data[..]).unwrap();
    assert_eq!(fee_vault.amount, 40);

    // Verify application status is now CancelledWithDebt
    let app_acc = svm.get_account(&application_pda).unwrap();
    let application = ProviderApplication::try_deserialize(&mut &app_acc.data[..]).unwrap();
    assert_eq!(application.status, ProviderApplicationStatus::CancelledWithDebt);

    // Verify ProviderDebt PDA status
    let debt_acc = svm.get_account(&provider_debt_pda).unwrap();
    let provider_debt = ProviderDebt::try_deserialize(&mut &debt_acc.data[..]).unwrap();
    assert_eq!(provider_debt.has_debt, true);
    assert_eq!(provider_debt.provider, provider.pubkey());

    // 5. Try to apply again - should fail with ProviderHasDebt (exit code / transaction fails)
    let task_id_3: u64 = 203;
    let task_pda_3 = Pubkey::find_program_address(
        &[sol_contract::constants::TASK_SEED, &task_id_3.to_le_bytes()],
        &program_id,
    ).0;
    let application_pda_3 = Pubkey::find_program_address(
        &[sol_contract::constants::APPLICATION_SEED, provider.pubkey().as_ref(), task_pda_3.as_ref()],
        &program_id,
    ).0;

    let try_apply_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::Apply { task_id: task_id_3, expires_at: 9999999999 }.data(),
        sol_contract::accounts::CreateApplication {
            provider: provider.pubkey(),
            task: task_pda_3,
            application: application_pda_3,
            provider_debt: provider_debt_pda,
            system_program: system_program::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[try_apply_ix], Some(&provider.pubkey()), &svm.latest_blockhash())),
        &[&provider],
    ).unwrap();
    
    // Transaction must fail
    assert!(svm.send_transaction(tx).is_err());

    // 6. Withdraw application check (for clean provider withdrawing pending application)
    let provider2 = Keypair::new();
    svm.airdrop(&provider2.pubkey(), 1_000_000_000).unwrap();
    let provider_debt_pda2 = Pubkey::find_program_address(
        &[b"provider_debt", provider2.pubkey().as_ref()],
        &program_id,
    ).0;
    let application_pda2 = Pubkey::find_program_address(
        &[sol_contract::constants::APPLICATION_SEED, provider2.pubkey().as_ref(), task_pda_2.as_ref()],
        &program_id,
    ).0;

    // Apply
    let apply_ix2 = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::Apply { task_id: task_id_2, expires_at: 9999999999 }.data(),
        sol_contract::accounts::CreateApplication {
            provider: provider2.pubkey(),
            task: task_pda_2,
            application: application_pda2,
            provider_debt: provider_debt_pda2,
            system_program: system_program::ID,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[apply_ix2], Some(&provider2.pubkey()), &svm.latest_blockhash())),
        &[&provider2],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Withdraw application
    let withdraw_ix = Instruction::new_with_bytes(
        program_id,
        &sol_contract::instruction::WithdrawApplication { task_id: task_id_2 }.data(),
        sol_contract::accounts::WithdrawApplication {
            provider: provider2.pubkey(),
            task: task_pda_2,
            application: application_pda2,
        }.to_account_metas(None),
    );
    let tx = VersionedTransaction::try_new(
        VersionedMessage::Legacy(Message::new_with_blockhash(&[withdraw_ix], Some(&provider2.pubkey()), &svm.latest_blockhash())),
        &[&provider2],
    ).unwrap();
    svm.send_transaction(tx).unwrap();

    // Verify application account is closed (returns None)
    assert!(svm.get_account(&application_pda2).is_none());
}
