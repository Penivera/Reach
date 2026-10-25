pub const TASK_SEED: &[u8] = b"task";
pub const APPLICATION_SEED: &[u8] = b"application";
pub const STABLE_COIN_SEED: &[u8] = b"supported_stable";
pub const REACH_STATE_SEED: &[u8] = b"reach_state";
pub const FEE_VAULT_SEED: &[u8] = b"fee_vault";
pub const PROVIDER_DEBT_SEED: &[u8] = b"provider_debt";

// Anchor-compatible 8-byte account discriminators
pub const REACH_STATE_DISCM: [u8; 8] = [242, 61, 237, 219, 137, 188, 187, 85];
pub const TASK_DISCM: [u8; 8] = [79, 34, 151, 64, 49, 12, 69, 180];
pub const APPLICATION_DISCM: [u8; 8] = [142, 140, 246, 117, 107, 7, 122, 128];
pub const SUPPORTED_STABLE_DISCM: [u8; 8] = [229, 219, 169, 69, 126, 194, 178, 121];
pub const PROVIDER_DEBT_DISCM: [u8; 8] = [122, 59, 103, 115, 175, 41, 101, 119];

pub const MAX_ADMINS: usize = 5;
