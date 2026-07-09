use crate::*;

impl ReachContract {
    pub(crate) fn calculate_fee(&self, amount: u128, fee_basis_points: u16) -> u128 {
        (amount * fee_basis_points as u128) / 10000
    }

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
        let internal_fee = self.calculate_fee(required_escrow, self.creation_fee_pct);
        let total_required_escrow = required_escrow + internal_fee;
        
        require!(
            amount.0 == total_required_escrow,
            format!("Provided Funds Below Required Amount ${:?} fee applied", total_required_escrow)
        );

        require!(terms.upfront_release_pct <= 100, "Percentage can only be from 0-100");
        let escrow_state = EscrowState {
            creator_locked_balance: U128(required_escrow),
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
            stablecoin: stablecoin.clone(),
            status: TaskStatus::Pending,
            terms,
            escrow: escrow_state,
            created_at: env::block_timestamp(),
            updated_at: env::block_timestamp(),
        };

        // Add fee to protocol balance
        let mut fee_balance = self.stables_balances.get(&stablecoin).copied().unwrap_or(0);
        fee_balance += internal_fee;
        self.stables_balances.insert(stablecoin, fee_balance);

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

    pub(crate) fn internal_cancel_approved_application_with_debt(
        &mut self,
        provider_id: AccountId,
        amount: U128,
        task_id: u64,
    ) -> near_sdk::PromiseOrValue<U128> {
        let (debt, fee) = {
            let task = self.tasks.get(&task_id).expect("Task not found");
            require!(task.provider_id.as_ref() == Some(&provider_id), "Only the assigned provider can cancel application");
            require!(
                matches!(task.status, TaskStatus::InProgress) || matches!(task.status, TaskStatus::AwaitingEscrow),
                "Task not in progress or awaiting escrow"
            );

            let advance = if task.escrow.advance_disbursed {
                (task.terms.upfront_release_pct as u128 * task.terms.material_cost.0) / 100
            } else {
                0
            };

            let collateral = task.escrow.provider_locked_balance.unwrap_or(U128(0)).0;
            require!(advance > collateral, "No debt is owed: cancel application directly without transfer");

            let debt = advance - collateral;
            let task_value = task.terms.labor_fee.0 + task.terms.material_cost.0;
            let fee = self.calculate_fee(task_value, self.cancellation_fee_pct);
            (debt, fee)
        };

        let task = self.tasks.get_mut(&task_id).unwrap();

        let total_required = debt + fee;
        require!(amount.0 == total_required, format!("Must transfer exactly debt + fee = {}", total_required));

        // Add fee to protocol balance
        let mut fee_balance = self.stables_balances.get(&task.stablecoin).copied().unwrap_or(0);
        fee_balance += fee;
        self.stables_balances.insert(task.stablecoin.clone(), fee_balance);

        // Reset task status
        task.provider_id = None;
        task.status = TaskStatus::Pending;
        task.escrow.provider_locked_balance = None;
        task.escrow.advance_disbursed = false;

        // Reset application status to CancelledWithDebt
        for (_, app) in self.applications.iter_mut() {
            if app.task_id == task_id && app.status == ProviderApplicationStatus::Accepted {
                app.status = ProviderApplicationStatus::CancelledWithDebt;
                break;
            }
        }

        // Blacklist the provider
        self.blacklist.insert(provider_id);

        near_sdk::PromiseOrValue::Value(U128(0))
    }
}