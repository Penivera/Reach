pub const TASK_SEED: &[u8] = b"task";
pub const APPLICATION_SEED: &[u8] = b"application";
pub const STABLE_COIN_SEED: &[u8] = b"supported_stable";
pub const REACH_STATE_SEED: &[u8] = b"reach_state";
pub const FEE_VAULT_SEED: &[u8] = b"fee_vault";
pub const PROVIDER_DEBT_SEED: &[u8] = b"provider_debt";

// 1-byte account discriminators
pub const REACH_STATE_DISCM: u8 = 1;
pub const TASK_DISCM: u8 = 2;
pub const APPLICATION_DISCM: u8 = 3;
pub const SUPPORTED_STABLE_DISCM: u8 = 4;
pub const PROVIDER_DEBT_DISCM: u8 = 5;

pub const MAX_ADMINS: usize = 5;
