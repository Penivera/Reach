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
}
