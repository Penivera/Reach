use crate::*;

impl ReachContract {
    pub(crate) fn internal_create_task(
        &mut self,
        caller_id: AccountId,
        stablecoin: AccountId,
        amount: U128,
        desc: Option<String>,
        tag: Option<String>,
        terms: FinancialTerms,
    ) -> near_sdk::PromiseOrValue<U128> {
        let required_escrow: u128 = terms.labor_fee.0 + terms.material_cost.0;
        let internal_fee = (required_escrow * self.creation_fee_pct as u128) / 1000;
        let total_required_escrow = required_escrow + internal_fee;
        
        require!(
            amount.0 == total_required_escrow,
            format!("Provided Funds Below Required Amount ${:?} 1% fee applied", total_required_escrow)
        );

        require!(terms.upfront_release_pct <= 100, "Percentage can only be from 0-100");
        let escrow_state = EscrowState {
            creator_locked_balance: U128(total_required_escrow),
            provider_locked_balance: match terms.required_provider_collateral {
                None => None,
                Some(amount) => Some(amount),
            },
            advance_disbursed: false,
        };
        let new_task = Task {
            creator_id: caller_id,
            provider_id: None,
            tag,
            desc,
            stablecoin,
            status: TaskStatus::Pending,
            terms,
            escrow: escrow_state,
            created_at: env::block_timestamp(),
            updated_at: env::block_timestamp(),
        };
        self.tasks.insert(self.task_count, new_task);
        self.task_count += 1;
        near_sdk::PromiseOrValue::Value(U128(0))
    }

    pub(crate) fn internal_provide_collateral(
        &mut self,
        caller_id: AccountId,
        amount: U128,
        task_id: u64,
        application_id: u64,
    ) -> near_sdk::PromiseOrValue<U128> {
        let application = self.applications.get(&application_id).expect("Can only provide collateral to active accepted tasks");
        let task = self.tasks.get_mut(&task_id).expect("No task for this Id");
        let required_collateral = task.terms.required_provider_collateral.expect("Task Does Not Require Collateral To Complete");

        require!(amount == required_collateral, format!("Collateral Provided Does Not Match Required {:?}", required_collateral));

        require!(
            application.status == ProviderApplicationStatus::Accepted,
            "Can Only Provide Liq. For Accepted Applications"
        );

        require!(caller_id == application.provider_id, "You can Only Provide Colateral For You own application");

        if !task.escrow.advance_disbursed && task.terms.upfront_release_pct > 0 {
            let upfront_amount = (task.terms.upfront_release_pct as u128 / 100) * task.terms.material_cost.0;
            
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