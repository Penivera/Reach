# Reach Solana Program

This folder contains the Anchor-based Solana program for Reach task escrow.

## Program ID

- `5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY` (from `programs/sol-contract/src/lib.rs`)

## Instruction Groups

- **Setup/Admin**
  - `initialize`
  - `add_supported_stable`, `remove_supported_stable`
  - `add_admin`, `remove_admin`
  - `update_creation_fee_pct`, `update_cancellation_fee_pct`
  - `propose_owner_update`, `vote_owner_update`
  - `withdraw_protocol_fees`
- **Task lifecycle**
  - `create_task`
  - `apply`
  - `accept`
  - `provide_collateral`
  - `claim_advance`
  - `complete_task`
  - `approve_work`
  - `cancel_task`
  - `cancel_approved_application`
  - `withdraw_application`
  - `raise_dispute`
  - `resolve_dispute`

## PDA Seeds (Required for Reads and Writes)

All account reads should derive the PDA exactly as listed below.

| Account | PDA seeds (in order) | Notes |
| --- | --- | --- |
| `reach_state` | `["reach_state"]` | Global config/state |
| `task` | `["task", task_id.to_le_bytes()]` | One account per task id |
| `task_vault` | `["task", task_pubkey]` | Token vault owned by `task` PDA |
| `application` | `["application", provider_pubkey, task_pubkey]` | Provider application for one task |
| `supported_token` / `supported_token_check` | `["supported_stable", stable_mint_pubkey]` | Supported stablecoin marker |
| `fee_vault` | `["fee_vault", stable_mint_pubkey]` | Protocol fee vault token account |
| `provider_debt` | `["provider_debt", provider_pubkey]` | Debt status for provider |

## Read Calls (What to Fetch)

Common read patterns:

1. **Global state**
   - Derive `reach_state` PDA and fetch `ReachState`.
2. **Task details**
   - Derive `task` PDA from task id and fetch `Task`.
   - Derive `task_vault` PDA from task PDA and fetch token account balance for escrow.
3. **Provider application status**
   - Derive `application` PDA using provider pubkey + task PDA and fetch `ProviderApplication`.
4. **Supported stablecoin check**
   - Derive `supported_stable` PDA from mint and fetch `SupportedStable`.
5. **Protocol fee balance**
   - Derive `fee_vault` PDA from mint and fetch token account balance.
6. **Provider debt check**
   - Derive `provider_debt` PDA from provider pubkey and fetch `ProviderDebt` if initialized.

## Seed Dependency Order

Some reads require earlier derived PDAs:

- `task_id` -> derive `task` -> derive `task_vault` and `application`
- `stable_mint` -> derive `supported_stable` and `fee_vault`

## Source of Truth

For integration, treat these files as canonical:

- PDA constants: `programs/sol-contract/src/constants.rs`
- Account constraints and seeds: `programs/sol-contract/src/instructions/*.rs`
- Account data structures: `programs/sol-contract/src/state.rs`
- Program entrypoints: `programs/sol-contract/src/lib.rs`
