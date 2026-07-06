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
                "supported_stables": [creator.account_id().to_string()]
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
                "supported_stables": [creator.account_id().to_string()]
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
