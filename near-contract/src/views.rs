use crate::*;

#[near]
impl ReachContract {
    // --- Task Views ---

    pub fn get_task(&self, task_id: u64) -> Task {
        self.tasks.get(&task_id).expect("Task not found").clone()
    }

    pub fn get_tasks(&self, from_index: u64, limit: u64) -> Vec<(u64, Task)> {
        self.tasks
            .iter()
            .skip(from_index as usize)
            .take(limit as usize)
            .map(|(k, v)| (*k, v.clone()))
            .collect()
    }

    pub fn get_tasks_by_creator(
        &self,
        creator_id: AccountId,
        from_index: u64,
        limit: u64,
    ) -> Vec<(u64, Task)> {
        self.tasks
            .iter()
            .filter(|(_, t)| t.creator_id == creator_id)
            .skip(from_index as usize)
            .take(limit as usize)
            .map(|(k, v)| (*k, v.clone()))
            .collect()
    }

    pub fn get_tasks_by_provider(
        &self,
        provider_id: AccountId,
        from_index: u64,
        limit: u64,
    ) -> Vec<(u64, Task)> {
        self.tasks
            .iter()
            .filter(|(_, t)| t.provider_id.as_ref() == Some(&provider_id))
            .skip(from_index as usize)
            .take(limit as usize)
            .map(|(k, v)| (*k, v.clone()))
            .collect()
    }

    pub fn get_task_count(&self) -> u64 {
        self.task_count
    }

    // --- Application Views ---

    pub fn get_application(&self, application_id: u64) -> ProviderApplication {
        self.applications
            .get(&application_id)
            .expect("Application not found")
            .clone()
    }

    pub fn get_applications(
        &self,
        from_index: u64,
        limit: u64,
    ) -> Vec<(u64, ProviderApplication)> {
        self.applications
            .iter()
            .skip(from_index as usize)
            .take(limit as usize)
            .map(|(k, v)| (*k, v.clone()))
            .collect()
    }

    pub fn get_applications_by_task(&self, task_id: u64) -> Vec<(u64, ProviderApplication)> {
        self.applications
            .iter()
            .filter(|(_, a)| a.task_id == task_id)
            .map(|(k, v)| (*k, v.clone()))
            .collect()
    }

    pub fn get_applications_by_provider(
        &self,
        provider_id: AccountId,
        from_index: u64,
        limit: u64,
    ) -> Vec<(u64, ProviderApplication)> {
        self.applications
            .iter()
            .filter(|(_, a)| a.provider_id == provider_id)
            .skip(from_index as usize)
            .take(limit as usize)
            .map(|(k, v)| (*k, v.clone()))
            .collect()
    }

    pub fn get_application_count(&self) -> u64 {
        self.application_count
    }

    // --- Admin & Governance Views ---

    pub fn get_admins(&self) -> Vec<AccountId> {
        self.admins.iter().cloned().collect()
    }

    pub fn is_admin(&self, account_id: AccountId) -> bool {
        self.admins.contains(&account_id)
    }

    pub fn get_owner(&self) -> AccountId {
        self.owner_id.clone()
    }

    pub fn get_owner_proposal(&self) -> Option<AccountId> {
        self.owner_proposal.clone()
    }

    pub fn get_owner_votes(&self) -> Vec<AccountId> {
        self.owner_votes.iter().cloned().collect()
    }

    // --- Config Views ---

    pub fn get_supported_stables(&self) -> Vec<AccountId> {
        self.supported_stables.iter().cloned().collect()
    }

    pub fn get_stables_balance(&self, stablecoin: AccountId) -> U128 {
        U128(self.stables_balances.get(&stablecoin).copied().unwrap_or(0))
    }

    pub fn get_cancellation_fee_pct(&self) -> u16 {
        self.cancellation_fee_pct
    }

    pub fn get_creation_fee_pct(&self) -> u16 {
        self.creation_fee_pct
    }
}
