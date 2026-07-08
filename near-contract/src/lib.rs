pub mod models;
pub mod internal;
pub mod ext;
pub mod admin;
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
    pub owner_id: AccountId,
    pub owner_proposal: Option<AccountId>,
    pub owner_votes: IterableSet<AccountId>,
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
            owner_id: env::predecessor_account_id(),
            owner_proposal: None,
            owner_votes: IterableSet::new(b"v"),
            tasks: IterableMap::new(b"t"),
            applications: IterableMap::new(b"a"),
            supported_stables: IterableSet::new(b"s"),
            admins: IterableSet::new(b"d"),
            task_count: 0,
            stables_balances: IterableMap::new(b"b"),
            application_count: 0,
            
        };
        contract.admins.insert(env::predecessor_account_id());
        for stable_coin in supported_stables {
            contract.supported_stables.insert(stable_coin);
        }
        contract
    }

    // --- Provider Applications ---
    pub fn create_application(&mut self, task_id: u64) {
        let provider_id = env::predecessor_account_id();
        let task = self.tasks.get(&task_id).expect("Task not found");
        require!(matches!(task.status, TaskStatus::Pending), "Task is not pending");

        let app = ProviderApplication {
            provider_id,
            task_id,
            status: ProviderApplicationStatus::Pending,
            created_at: env::block_timestamp(),
            expires_at: env::block_timestamp() + 86_400_000_000_000, // +1 day approx
        };

        self.applications.insert(self.application_count, app);
        self.application_count += 1;
    }

    pub fn accept_application(&mut self, application_id: u64) -> near_sdk::PromiseOrValue<()> {
        let caller = env::predecessor_account_id();
        let app = self.applications.get_mut(&application_id).expect("App not found");
        
        let task_id = app.task_id;
        let provider_id = app.provider_id.clone();
        
        let task = self.tasks.get_mut(&task_id).expect("Task not found");
        require!(task.creator_id == caller, "Only creator can accept applications");
        require!(matches!(task.status, TaskStatus::Pending), "Task not pending");

        app.status = ProviderApplicationStatus::Accepted;
        task.provider_id = Some(provider_id.clone());

        // Discard other applications
        for (_, other_app) in self.applications.iter_mut() {
            if other_app.task_id == task_id && other_app.status == ProviderApplicationStatus::Pending {
                other_app.status = ProviderApplicationStatus::Rejected;
            }
        }

        if task.terms.required_provider_collateral.is_some() {
            task.status = TaskStatus::AwaitingEscrow;
            near_sdk::PromiseOrValue::Value(())
        } else {
            task.status = TaskStatus::InProgress;
            
            if !task.escrow.advance_disbursed && task.terms.upfront_release_pct > 0 {
                let upfront_amount = (task.terms.upfront_release_pct as u128 / 100) * task.terms.material_cost.0;
                let promise = ft_contract::ext(task.stablecoin.clone())
                    .with_attached_deposit(near_sdk::NearToken::from_yoctonear(1))
                    .with_static_gas(near_sdk::Gas::from_tgas(20))
                    .ft_transfer(provider_id, U128(upfront_amount));
                    
                let callback = Self::ext(env::current_account_id())
                    .with_static_gas(near_sdk::Gas::from_tgas(20))
                    .accept_application_callback(task_id, application_id);
                    
                near_sdk::PromiseOrValue::Promise(promise.then(callback))
            } else {
                near_sdk::PromiseOrValue::Value(())
            }
        }
    }

    #[private]
    pub fn accept_application_callback(&mut self, task_id: u64, application_id: u64) {
        if near_sdk::is_promise_success() {
            let task = self.tasks.get_mut(&task_id).unwrap();
            task.escrow.advance_disbursed = true;
        } else {
            let task = self.tasks.get_mut(&task_id).unwrap();
            task.provider_id = None;
            task.status = TaskStatus::Pending;
            
            for (_, other_app) in self.applications.iter_mut() {
                if other_app.task_id == task_id && other_app.status == ProviderApplicationStatus::Rejected {
                    other_app.status = ProviderApplicationStatus::Pending;
                }
            }
            let app = self.applications.get_mut(&application_id).unwrap();
            app.status = ProviderApplicationStatus::Pending;

            panic!("Advance payment failed");
        }
    }

    // --- Task Lifecycle & Resolution ---
    pub fn complete_task(&mut self, task_id: u64) {
        let caller = env::predecessor_account_id();
        let task = self.tasks.get_mut(&task_id).expect("Task not found");
        require!(task.provider_id.as_ref() == Some(&caller), "Only provider can complete task");
        require!(matches!(task.status, TaskStatus::InProgress), "Task not in progress");
        
        task.status = TaskStatus::Completed;
    }

    pub fn approve_work(&mut self, task_id: u64) -> near_sdk::PromiseOrValue<()> {
        let caller = env::predecessor_account_id();
        let task = self.tasks.get_mut(&task_id).expect("Task not found");
        require!(task.creator_id == caller, "Only creator can approve work");
        require!(matches!(task.status, TaskStatus::Completed) || matches!(task.status, TaskStatus::InProgress), "Task not ready for approval");

        let remaining_material = if task.escrow.advance_disbursed {
            let upfront = (task.terms.upfront_release_pct as u128 / 100) * task.terms.material_cost.0;
            task.terms.material_cost.0 - upfront
        } else {
            task.terms.material_cost.0
        };
        let total_payout = task.terms.labor_fee.0 + remaining_material;
        
        let provider_id = task.provider_id.clone().unwrap();

        // Release funds to provider
        let mut total_to_send = total_payout;
        if let Some(col) = task.escrow.provider_locked_balance {
            total_to_send += col.0;
        }

        task.status = TaskStatus::Completed;

        if total_to_send > 0 {
            let promise = ft_contract::ext(task.stablecoin.clone())
                .with_attached_deposit(near_sdk::NearToken::from_yoctonear(1))
                .with_static_gas(near_sdk::Gas::from_tgas(20))
                .ft_transfer(provider_id, U128(total_to_send));
                
            let callback = Self::ext(env::current_account_id())
                .with_static_gas(near_sdk::Gas::from_tgas(20))
                .approve_work_callback(task_id);
                
            near_sdk::PromiseOrValue::Promise(promise.then(callback))
        } else {
            near_sdk::PromiseOrValue::Value(())
        }
    }

    #[private]
    pub fn approve_work_callback(&mut self, task_id: u64) {
        if !near_sdk::is_promise_success() {
            let task = self.tasks.get_mut(&task_id).unwrap();
            task.status = TaskStatus::InProgress;
            panic!("Payment failed");
        }
    }

    pub fn raise_dispute(&mut self, task_id: u64) {
        let caller = env::predecessor_account_id();
        let task = self.tasks.get_mut(&task_id).expect("Task not found");
        require!(task.creator_id == caller || task.provider_id.as_ref() == Some(&caller), "Only participants can raise dispute");
        task.status = TaskStatus::Disputed;
    }

    pub fn resolve_dispute(&mut self, task_id: u64, creator_refund_pct: u8, provider_payment_pct: u8) -> near_sdk::PromiseOrValue<()> {
        require!(creator_refund_pct + provider_payment_pct == 100, "Percentages must sum to 100");
        let caller = env::predecessor_account_id();
        require!(self.admins.contains(&caller), "Only admins can resolve disputes");
        
        let task = self.tasks.get_mut(&task_id).expect("Task not found");
        require!(matches!(task.status, TaskStatus::Disputed), "Task not disputed");

        // Simple logic for payout split...
        let total_creator_funds = task.escrow.creator_locked_balance.0;
        let creator_refund = (total_creator_funds * creator_refund_pct as u128) / 100;
        let provider_payment = (total_creator_funds * provider_payment_pct as u128) / 100;

        let mut promise: Option<near_sdk::Promise> = None;

        if creator_refund > 0 {
            let p = ft_contract::ext(task.stablecoin.clone())
                .with_attached_deposit(near_sdk::NearToken::from_yoctonear(1))
                .with_static_gas(near_sdk::Gas::from_tgas(20))
                .ft_transfer(task.creator_id.clone(), U128(creator_refund));
            promise = Some(p);
        }

        if provider_payment > 0 {
            let provider_id = task.provider_id.clone().unwrap();
            let p = ft_contract::ext(task.stablecoin.clone())
                .with_attached_deposit(near_sdk::NearToken::from_yoctonear(1))
                .with_static_gas(near_sdk::Gas::from_tgas(20))
                .ft_transfer(provider_id, U128(provider_payment));
            promise = match promise {
                Some(prev) => Some(prev.and(p)),
                None => Some(p),
            };
        }
        
        if let Some(col) = task.escrow.provider_locked_balance {
            let provider_id = task.provider_id.clone().unwrap();
            let collateral_refund = (col.0 * provider_payment_pct as u128) / 100;
            if collateral_refund > 0 {
                let p = ft_contract::ext(task.stablecoin.clone())
                    .with_attached_deposit(near_sdk::NearToken::from_yoctonear(1))
                    .with_static_gas(near_sdk::Gas::from_tgas(20))
                    .ft_transfer(provider_id, U128(collateral_refund));
                promise = match promise {
                    Some(prev) => Some(prev.and(p)),
                    None => Some(p),
                };
            }
        }

        let new_status = if creator_refund_pct > 50 { TaskStatus::Refunded } else { TaskStatus::Completed };
        task.status = new_status;

        if let Some(p) = promise {
            let callback = Self::ext(env::current_account_id())
                .with_static_gas(near_sdk::Gas::from_tgas(20))
                .resolve_dispute_callback(task_id);
            near_sdk::PromiseOrValue::Promise(p.then(callback))
        } else {
            near_sdk::PromiseOrValue::Value(())
        }
    }

    #[private]
    pub fn resolve_dispute_callback(&mut self, task_id: u64) {
        if !near_sdk::is_promise_success() {
            let task = self.tasks.get_mut(&task_id).unwrap();
            task.status = TaskStatus::Disputed;
            panic!("Payment failed");
        }
    }

    // --- FT Receive Methods ---
    //NOTE Payment to either create a task or provide collateral
    pub fn ft_on_transfer(&mut self, _sender_id: AccountId, amount: U128, msg: String) -> near_sdk::PromiseOrValue<U128> {
        let transfer_action = serde_json::from_str::<TransferAction>(&msg).expect("Invalid Transfer Action");
        let caller_id = env::signer_account_id();

        require!(self.supported_stables.contains(&env::predecessor_account_id()), "Unsupported Stablecoin");

        match transfer_action {
            TransferAction::CreateTask { desc, tag, stablecoin: _, terms } => {
                self.internal_create_task(caller_id, env::predecessor_account_id(), amount, desc, tag, terms)
            },
            TransferAction::ProvideCollateral { task_id, application_id } => {
                self.internal_provide_collateral(caller_id, amount, task_id, application_id)
            }
        }
    }

    #[private]
    pub fn ft_transfer_callback(&mut self, task_id: u64, amount: U128) -> U128 {
        if near_sdk::is_promise_success() {
            let task = self.tasks.get_mut(&task_id).unwrap();
            if amount.0 > 0 {
                task.escrow.provider_locked_balance = Some(amount);
            }
            task.status = TaskStatus::InProgress;
            task.escrow.advance_disbursed = true;
            U128(0)
        } else {
            // Panicking will reject the cross-contract call from the token contract,
            // effectively refunding the collateral to the user.
            panic!("Advance payment failed, refunding collateral");
        }
    }

    // Dummy method for testing mock FT callbacks in tests
    #[payable]
    #[allow(unused_variables)]
    pub fn ft_transfer(&mut self, receiver_id: AccountId, amount: U128, memo: Option<String>) {
        // Do nothing
    }
}
