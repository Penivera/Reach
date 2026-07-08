use crate::*;

#[near]
impl ReachContract {
    // --- Admin & Owner Methods ---
    #[private]
    pub fn add_admin(&mut self, admin_id: AccountId) {
        self.admins.insert(admin_id);
    }

    #[private]
    pub fn remove_admin(&mut self, admin_id: AccountId) {
        self.admins.remove(&admin_id);
    }

    pub fn propose_owner_update(&mut self, new_owner: AccountId) {
        let caller = env::predecessor_account_id();
        require!(self.admins.contains(&caller), "Only admins can propose owner updates");
        self.owner_proposal = Some(new_owner);
        self.owner_votes.clear();
        self.owner_votes.insert(caller);
    }

    pub fn vote_owner_update(&mut self) {
        let caller = env::predecessor_account_id();
        require!(self.admins.contains(&caller), "Only admins can vote");
        require!(self.owner_proposal.is_some(), "No active owner update proposal");

        self.owner_votes.insert(caller);

        let required_votes = (self.admins.len() / 2) + 1;
        if self.owner_votes.len() as u32 >= required_votes {
            self.owner_id = self.owner_proposal.take().unwrap();
            self.owner_votes.clear();
        }
    }

    pub fn update_cancellation_fee_pct(&mut self, fee_pct: u16) {
        let caller = env::predecessor_account_id();
        require!(self.admins.contains(&caller), "Only admins can update fee");
        require!(fee_pct <= 1000, "Fee percentage cannot exceed 100%");
        self.cancellation_fee_pct = fee_pct;
    }

    pub fn update_creation_fee_pct(&mut self, fee_pct: u16) {
        let caller = env::predecessor_account_id();
        require!(self.admins.contains(&caller), "Only admins can update fee");
        require!(fee_pct <= 1000, "Fee percentage cannot exceed 100%");
        self.creation_fee_pct = fee_pct;
    }

    // --- Supported Stables Management ---

    pub fn add_supported_stable(&mut self, stable_id: AccountId) {
        let caller = env::predecessor_account_id();
        require!(self.admins.contains(&caller), "Only admins can manage supported stables");
        self.supported_stables.insert(stable_id);
    }

    pub fn remove_supported_stable(&mut self, stable_id: AccountId) {
        let caller = env::predecessor_account_id();
        require!(self.admins.contains(&caller), "Only admins can manage supported stables");
        self.supported_stables.remove(&stable_id);
    }

    // --- Protocol Fee Withdrawal ---

    pub fn withdraw_protocol_fees(
        &mut self,
        stablecoin: AccountId,
        amount: U128,
        receiver: AccountId,
    ) -> near_sdk::Promise {
        let caller = env::predecessor_account_id();
        require!(self.admins.contains(&caller), "Only admins can withdraw protocol fees");

        let balance = self.stables_balances.get(&stablecoin).copied().unwrap_or(0);
        require!(balance >= amount.0, "Insufficient protocol fee balance");

        // Deduct optimistically, rollback in callback on failure
        self.stables_balances.insert(stablecoin.clone(), balance - amount.0);

        let promise = ft_contract::ext(stablecoin.clone())
            .with_attached_deposit(near_sdk::NearToken::from_yoctonear(1))
            .with_static_gas(near_sdk::Gas::from_tgas(20))
            .ft_transfer(receiver, amount);

        let callback = Self::ext(env::current_account_id())
            .with_static_gas(near_sdk::Gas::from_tgas(20))
            .withdraw_protocol_fees_callback(stablecoin, amount);

        promise.then(callback)
    }

    #[private]
    pub fn withdraw_protocol_fees_callback(&mut self, stablecoin: AccountId, amount: U128) {
        if !near_sdk::is_promise_success() {
            let balance = self.stables_balances.get(&stablecoin).copied().unwrap_or(0);
            self.stables_balances.insert(stablecoin, balance + amount.0);
            panic!("Fee withdrawal failed");
        }
    }
}
