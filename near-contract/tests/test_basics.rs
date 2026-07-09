use near_api::{AccountId, NearToken};
use near_sdk::serde_json::json;

async fn test_basics_on(contract_wasm: Vec<u8>) -> testresult::TestResult<()> {
    let sandbox = near_sandbox::Sandbox::start_sandbox().await?;
    let sandbox_network =
        near_api::NetworkConfig::from_rpc_url("sandbox", sandbox.rpc_addr.parse()?);

    // Create accounts
    let creator = create_subaccount(&sandbox, "creator.sandbox").await?;
    let provider = create_subaccount(&sandbox, "provider.sandbox").await?;
    
    let contract = create_subaccount(&sandbox, "contract.sandbox")
        .await?
        .as_contract();

    // Deploy and initialize contract
    let signer = near_api::Signer::from_secret_key(
        near_sandbox::config::DEFAULT_GENESIS_ACCOUNT_PRIVATE_KEY
            .parse()
            .unwrap(),
    )?;

    // We initialize the contract with creator as a supported stablecoin
    // This allows creator to call ft_on_transfer directly acting as the FT contract itself
    // Deploy to creator to mock the FT contract
    near_api::Contract::deploy(creator.account_id().clone())
        .use_code(contract_wasm.clone())
        .with_init_call(
            "init",
            json!({
                "supported_stables": [
                    creator.account_id().to_string(),
                    provider.account_id().to_string()
                ]
            }),
        )?
        .with_signer(signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    near_api::Contract::deploy(contract.account_id().clone())
        .use_code(contract_wasm)
        .with_init_call(
            "init",
            json!({
                "supported_stables": [
                    creator.account_id().to_string(),
                    provider.account_id().to_string()
                ]
            }),
        )?
        .with_signer(signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // 1. Create task via ft_on_transfer
    let terms = json!({
        "labor_fee": "1000",
        "material_cost": "500",
        "upfront_release_pct": 0,
        "required_provider_collateral": null
    });
    
    let msg = json!({
        "CreateTask": {
            "desc": "Build a DApp",
            "tag": "Development",
            "stablecoin": creator.account_id().to_string(),
            "terms": terms
        }
    }).to_string();

    let amount = 1000 + 500 + 37; // 2.5% fee on 1500 is 37.5 -> 37

    contract
        .call_function("ft_on_transfer", json!({
            "_sender_id": creator.account_id().to_string(),
            "amount": amount.to_string(),
            "msg": msg
        }))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();
    
    // 2. Provider creates application
    contract
        .call_function("create_application", json!({"task_id": 0}))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // 3. Creator accepts application
    contract
        .call_function("accept_application", json!({"application_id": 0}))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // 4. Provider completes task
    contract
        .call_function("complete_task", json!({"task_id": 0}))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // 5. Creator approves work
    contract
        .call_function("approve_work", json!({"task_id": 0}))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone()) 
        .send_to(&sandbox_network)
        .await?
        .assert_success();
    // 6. Test add_admin and remove_admin (Owner functionality)
    let admin_account = create_subaccount(&sandbox, "admin-account.sandbox").await?;
    
    // Add admin should succeed when called by the owner (which is the contract account in this test)
    contract
        .call_function("add_admin", json!({"admin_id": admin_account.account_id().to_string()}))
        .transaction()
        .with_signer(contract.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Verify admin was successfully added
    let admins: Vec<AccountId> = contract
        .call_function("get_admins", json!({}))
        .read_only()
        .fetch_from(&sandbox_network)
        .await?
        .data;
    assert!(admins.contains(admin_account.account_id()));

    // Remove admin should succeed when called by the owner
    contract
        .call_function("remove_admin", json!({"admin_id": admin_account.account_id().to_string()}))
        .transaction()
        .with_signer(contract.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Verify admin was successfully removed
    let admins_after: Vec<AccountId> = contract
        .call_function("get_admins", json!({}))
        .read_only()
        .fetch_from(&sandbox_network)
        .await?
        .data;
    assert!(!admins_after.contains(admin_account.account_id()));

    // 7. Test withdraw_application
    // First, let's create a new task that provider will apply to
    let terms_2 = json!({
        "labor_fee": "100",
        "material_cost": "50",
        "upfront_release_pct": 0,
        "required_provider_collateral": null
    });
    
    let msg_2 = json!({
        "CreateTask": {
            "desc": "Task to withdraw from",
            "tag": "Testing",
            "stablecoin": creator.account_id().to_string(),
            "terms": terms_2
        }
    }).to_string();

    let amount_2 = 100 + 50 + 3; // 2.5% fee on 150 is 3.75 -> 3
    contract
        .call_function("ft_on_transfer", json!({
            "_sender_id": creator.account_id().to_string(),
            "amount": amount_2.to_string(),
            "msg": msg_2
        }))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Create a provider application for the new task (task_id 1)
    contract
        .call_function("create_application", json!({"task_id": 1}))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // The application should have application_id 1
    // Let's verify it is there
    let app: near_sdk::serde_json::Value = contract
        .call_function("get_application", json!({"application_id": 1}))
        .read_only()
        .fetch_from(&sandbox_network)
        .await?
        .data;
    assert_eq!(app["provider_id"].as_str().unwrap(), provider.account_id().to_string());

    // Withdraw the application (should succeed and delete it)
    contract
        .call_function("withdraw_application", json!({"application_id": 1}))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Verify it is deleted (get_application should now return an error)
    let app_res: Result<near_api::Data<near_sdk::serde_json::Value>, _> = contract
        .call_function("get_application", json!({"application_id": 1}))
        .read_only()
        .fetch_from(&sandbox_network)
        .await;
    assert!(app_res.is_err());

    // 8. Test cancel_approved_application Case A (Advance <= Collateral)
    // First, let's create task 2: labor 100, material 50, collateral 50
    let terms_3 = json!({
        "labor_fee": "100",
        "material_cost": "50",
        "upfront_release_pct": 0,
        "required_provider_collateral": "50"
    });
    
    let msg_3 = json!({
        "CreateTask": {
            "desc": "Case A task",
            "tag": "Testing",
            "stablecoin": creator.account_id().to_string(),
            "terms": terms_3
        }
    }).to_string();

    let amount_3 = 100 + 50 + 3; // 2.5% fee on 150 = 3.75 -> 3
    contract
        .call_function("ft_on_transfer", json!({
            "_sender_id": creator.account_id().to_string(),
            "amount": amount_3.to_string(),
            "msg": msg_3
        }))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Provider creates application 2
    contract
        .call_function("create_application", json!({"task_id": 2}))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Creator accepts application 2
    contract
        .call_function("accept_application", json!({"application_id": 2}))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Provider provides collateral
    let coll_msg = json!({
        "ProvideCollateral": {
            "task_id": 2,
            "application_id": 2
        }
    }).to_string();
    contract
        .call_function("ft_on_transfer", json!({
            "_sender_id": provider.account_id().to_string(),
            "amount": "50",
            "msg": coll_msg
        }))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Provider cancels application (Case A: advance = 0, collateral = 50 -> no debt)
    contract
        .call_function("cancel_approved_application", json!({"task_id": 2}))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Verify task is reset to Pending
    let task2: near_sdk::serde_json::Value = contract
        .call_function("get_task", json!({"task_id": 2}))
        .read_only()
        .fetch_from(&sandbox_network)
        .await?
        .data;
    assert_eq!(task2["status"].as_str().unwrap(), "Pending");

    // 9. Test cancel_approved_application Case B (Advance > Collateral)
    // Create task 3: labor 100, material 100, upfront 100% (advance 100), collateral 50
    let terms_4 = json!({
        "labor_fee": "100",
        "material_cost": "100",
        "upfront_release_pct": 100,
        "required_provider_collateral": "50"
    });
    
    let msg_4 = json!({
        "CreateTask": {
            "desc": "Case B task",
            "tag": "Testing",
            "stablecoin": creator.account_id().to_string(),
            "terms": terms_4
        }
    }).to_string();

    let amount_4 = 100 + 100 + 5; // 2.5% fee on 200 = 5
    contract
        .call_function("ft_on_transfer", json!({
            "_sender_id": creator.account_id().to_string(),
            "amount": amount_4.to_string(),
            "msg": msg_4
        }))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Provider creates application 3
    contract
        .call_function("create_application", json!({"task_id": 3}))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Creator accepts application 3
    contract
        .call_function("accept_application", json!({"application_id": 3}))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Provider locks collateral and receives upfront advance (100 tokens)
    let coll_msg_2 = json!({
        "ProvideCollateral": {
            "task_id": 3,
            "application_id": 3
        }
    }).to_string();
    contract
        .call_function("ft_on_transfer", json!({
            "_sender_id": provider.account_id().to_string(),
            "amount": "50",
            "msg": coll_msg_2
        }))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Provider abandons task: advance = 100, collateral = 50 -> debt = 50.
    // Fee = 10% on 200 = 20.
    // Total payback required = 70 tokens.
    let payback_msg = json!({
        "CancelApprovedApplication": {
            "task_id": 3
        }
    }).to_string();
    contract
        .call_function("ft_on_transfer", json!({
            "_sender_id": provider.account_id().to_string(),
            "amount": "70",
            "msg": payback_msg
        }))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Verify task is reset to Pending
    let task3: near_sdk::serde_json::Value = contract
        .call_function("get_task", json!({"task_id": 3}))
        .read_only()
        .fetch_from(&sandbox_network)
        .await?
        .data;
    assert_eq!(task3["status"].as_str().unwrap(), "Pending");

    // Provider is now blacklisted. Let's create task 4 and show provider cannot apply.
    let terms_5 = json!({
        "labor_fee": "100",
        "material_cost": "50",
        "upfront_release_pct": 0,
        "required_provider_collateral": null
    });
    let msg_5 = json!({
        "CreateTask": {
            "desc": "Task 4",
            "tag": "Testing",
            "stablecoin": creator.account_id().to_string(),
            "terms": terms_5
        }
    }).to_string();
    let amount_5 = 100 + 50 + 3;
    contract
        .call_function("ft_on_transfer", json!({
            "_sender_id": creator.account_id().to_string(),
            "amount": amount_5.to_string(),
            "msg": msg_5
        }))
        .transaction()
        .with_signer(creator.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await?
        .assert_success();

    // Provider attempts to apply to task 4 (should fail due to blacklist)
    let app_res_blacklisted = contract
        .call_function("create_application", json!({"task_id": 4}))
        .transaction()
        .with_signer(provider.account_id().clone(), signer.clone())
        .send_to(&sandbox_network)
        .await;
    assert!(app_res_blacklisted.is_err() || !app_res_blacklisted.unwrap().is_success());

    Ok(())
}

async fn create_subaccount(
    sandbox: &near_sandbox::Sandbox,
    name: &str,
) -> testresult::TestResult<near_api::Account> {
    let account_id: AccountId = name.parse().unwrap();
    sandbox
        .create_account(account_id.clone())
        .initial_balance(NearToken::from_near(10))
        .send()
        .await?;
    Ok(near_api::Account(account_id))
}

#[tokio::test]
async fn test_contract_is_operational() -> testresult::TestResult<()> {
    let contract_wasm_path = cargo_near_build::build_with_cli(Default::default())?;
    let contract_wasm = std::fs::read(contract_wasm_path)?;

    test_basics_on(contract_wasm).await
}
