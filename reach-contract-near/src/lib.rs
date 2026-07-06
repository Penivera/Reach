pub mod models;
pub mod internal;
pub mod ext;
// Find NEAR documentation at https://docs.near.org
use near_sdk::json_types::U128;
use near_sdk::{
    AccountId,
    PanicOnDefault,
    env,
    near,
    require,
    store::{IterableMap,IterableSet},
    serde_json
};

pub use crate::models::*;
pub use crate::ext::*;



// Define the contract structure
#[near(contract_state)]
#[derive(PanicOnDefault)] // The contract is required to be initialized with `#[init]` functions
pub struct ReachContract {
    pub tasks: IterableMap<u64, Task>,
    pub applications: IterableMap<u64,ProviderApplication>,
    pub supported_stables: IterableSet<AccountId>,
    pub admins: IterableSet<AccountId>,
    pub task_count: u64,
    pub stables_balances: IterableMap<AccountId,u128>,
    pub application_count:u64,
}

// Implement the contract functions
#[near]
impl ReachContract {
    #[private]
    #[init]
    pub fn init(supported_stables:Vec<AccountId>)-> Self{
        let mut contract = ReachContract{
            tasks: IterableMap::new(b"t"),
            applications: IterableMap::new(b"a"),
            supported_stables: IterableSet::new(b"s"),
            admins: IterableSet::new(b"d"),
            task_count: 0,
            stables_balances: IterableMap::new(b"b"),
            application_count: 0,
            
        };
        contract.admins.insert(env::predecessor_account_id());
        let _ = supported_stables.into_iter().map(
            | stable_coin | contract.supported_stables.insert(stable_coin)
        );
        contract
    }

    //NOTE Payment to either create a task or provide collateral
    pub fn ft_on_transfer(&mut self, _sender_id: AccountId, amount: U128, msg: String) -> near_sdk::PromiseOrValue<U128> {
        let transfer_action = serde_json::from_str::<TransferAction>(&msg).expect("Invalid Transfer Action");

        let caller_id = env::signer_account_id();

        require!(
            self.supported_stables.contains(
                &env::predecessor_account_id()),
            "Unsupported Stablecoin"
        );

        match transfer_action {
            TransferAction::CreateTask { desc, tag, stablecoin: _, terms } => {
                let required_escrow:u128 = terms.labor_fee.0 + terms.material_cost.0;
                // 2.5% = 25 / 1000
                let internal_fee = (required_escrow * 25) / 1000;
                let total_required_escrow = required_escrow + internal_fee;
                
                require!( amount.0 == total_required_escrow,format!("Provided Funds Below Required Amount ${:?} 1% fee applied",total_required_escrow));

                require!( terms.upfront_release_pct <=100, "Percentage can only be from 0-100");
                let escrow_state = EscrowState{
                    creator_locked_balance : U128(total_required_escrow),
                    provider_locked_balance:match terms.required_provider_collateral {
                            None => None,
                            Some(amount) => Some(amount), 
                        },
                    advance_disbursed: false,
                };
                let new_task = Task{
                    creator_id: caller_id,
                    provider_id: None,
                    tag: tag,
                    desc:desc,
                    stablecoin: env::predecessor_account_id(),
                    status: TaskStatus::Pending,
                    terms: terms,
                    escrow:escrow_state,
                    created_at: env::block_timestamp(),
                    updated_at: env::block_timestamp()   
                };
                self.tasks.insert(self.task_count, new_task);
                self.task_count += 1;
                near_sdk::PromiseOrValue::Value(U128(0))
            },
            TransferAction::ProvideCollateral { task_id, application_id } => {
                let application = self.applications.get(&application_id).expect("Can only provide collateral to active accepted tasks");
                let task = self.tasks.get_mut(&task_id).expect("No task for this Id");
                let required_collateral = task.terms.required_provider_collateral.expect("Task Does Not Require Collateral To Complete");
        
                require!(amount == required_collateral, format!("Collateral Provided Does Not Match Required {:?}",required_collateral));

                require!( application.status == ProviderApplicationStatus::Accepted,
                    "Can Only Provide Liq. For Accepted Applications");

                require!(caller_id == application.provider_id, "You can Only Provide Colateral For You own application");

                if !task.escrow.advance_disbursed && task.terms.upfront_release_pct > 0 {
                    let upfront_amount = (task.terms.upfront_release_pct as u128/100) * task.terms.material_cost.0;
                    
                    let promise = ft_contract::ext(task.stablecoin.clone())
                        .with_attached_deposit(near_sdk::NearToken::from_yoctonear(1))
                        .with_static_gas(near_sdk::Gas::from_tgas(20))
                        .ft_transfer(caller_id, U128(upfront_amount));
                        
                    let callback = Self::ext(env::current_account_id())
                        .with_static_gas(near_sdk::Gas::from_tgas(20))
                        .ft_transfer_callback(task_id, amount);
                        
                    near_sdk::PromiseOrValue::Promise(promise.then(callback))
                } else {
                    task.escrow.provider_locked_balance = Some(amount);
                    task.status = TaskStatus::InProgress;
                    near_sdk::PromiseOrValue::Value(U128(0))
                }
            }
        }
    }

    #[private]
    pub fn ft_transfer_callback(&mut self, task_id: u64, amount: U128) -> U128 {
        if near_sdk::is_promise_success() {
            let task = self.tasks.get_mut(&task_id).unwrap();
            task.escrow.provider_locked_balance = Some(amount);
            task.status = TaskStatus::InProgress;
            task.escrow.advance_disbursed = true;
            U128(0)
        } else {
            // Panicking will reject the cross-contract call from the token contract,
            // effectively refunding the collateral to the user.
            panic!("Advance payment failed, refunding collateral");
        }
    }
}

