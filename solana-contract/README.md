# Reach Solana Escrow Program (`solana-contract`)

Ultra-compact, high-performance zero-copy Solana settlement engine and escrow contract for **Reach**, written with [Pinocchio](https://github.com/febo/pinocchio).

- **Program ID (Devnet):** `UU9yePPAwpE9ZX67t6RKtac6GDK3bEXNweRPmZMaXb7`
- **Binary Size:** **19,424 bytes** (~19.0 KB)
- **Mainnet Deploy Rent:** **0.09955 SOL** (~**$9.95** at $100/SOL) — **96.0% smaller** than the legacy Anchor contract (486 KB).

---

## Architecture & Design

1. **Zero-Copy Serialization:** Account data layouts use `#[repr(C)]` flat memory structures directly inspected and mutated on the account data pointer without deserialization allocations or Borsh overhead.
2. **Deterministic PDA Derivations:** Uses canonical Solana system syscalls (`sol_create_program_address`) with in-place bump search, keeping instruction compute units (CU) under 1,000 for standard operations.
3. **Optimized CPI Invocations:** Packed C instruction representations (`#[repr(C, packed)]`) for SPL token transfers and system account creation bypass Anchor/Borsh macro bloat.
4. **Standalone & Self-Contained:** Fully independent from Anchor runtime dependencies.

---

## Directory Structure

```
solana-contract/
├── Cargo.toml            # Standalone package with size-tuned release profile
├── deploy/
│   └── reach_escrow-keypair.json  # Canonical program keypair (UU9yePPA...)
├── src/
│   ├── lib.rs            # Entrypoint & 22-instruction opcode dispatcher
│   ├── constants.rs      # PDA seeds, 1-byte discriminators, limits
│   ├── state.rs          # Zero-copy repr(C) account structs
│   ├── cpi.rs            # SPL Token & System CPI helpers (invoke_signed_unchecked)
│   ├── math.rs           # Checked arithmetic & proportional split helpers
│   ├── error.rs          # Program errors and conversion
│   └── instructions/
│       ├── admin.rs      # Global initialization, fees, admin & owner governance
│       ├── task.rs       # Task creation, escrow locking, work completion & disputes
│       ├── application.rs# Provider applications, collateral, advances & debt
│       └── stable_coin.rs# Supported stablecoin whitelist & fee vaults
├── tests/
│   └── test_reach_escrow.rs  # LiteSVM integration test suite
└── scripts/
    └── test_devnet.js    # Live Devnet verification test suite covering all 22 methods
```

---

## Instructions Reference (22 Opcodes)

| Opcode | Method Name | Description |
| :---: | :--- | :--- |
| `0` | `initialize` | Initialize global `ReachState` with owner name and defaults |
| `1` | `update_creation_fee_pct` | Set protocol task creation fee percentage (BPS) |
| `2` | `update_cancellation_fee_pct` | Set protocol task cancellation fee percentage (BPS) |
| `3` | `propose_owner_update` | Propose ownership transfer to a new address |
| `4` | `vote_owner_update` | Admin multi-sig vote to ratify ownership update |
| `5` | `withdraw_protocol_fees` | Owner withdraws accumulated protocol fees from fee vault |
| `6` | `create_task` | Creator locks task escrow + creation fee in task vault |
| `7` | `apply` | Provider submits application with expiration timestamp |
| `8` | `accept` | Creator accepts provider application |
| `9` | `provide_collateral` | Provider deposits collateral to activate task |
| `10` | `claim_advance` | Provider claims upfront material cost advance |
| `11` | `cancel_task` | Creator cancels open task and receives escrow refund |
| `12` | `cancel_approved_application`| Provider cancels with collateral settlement / debt recording |
| `13` | `complete_task` | Provider marks task work completed |
| `14` | `approve_work` | Creator approves work, releasing payment to provider |
| `15` | `raise_dispute` | Creator or provider initiates arbitration dispute |
| `16` | `resolve_dispute` | Admin resolves dispute with percentage refund/payout split |
| `17` | `withdraw_application` | Provider withdraws pending application |
| `18` | `add_admin` | Owner adds an authorized admin |
| `19` | `remove_admin` | Owner removes an admin |
| `20` | `add_supported_stable` | Whitelist stablecoin mint and initialize protocol fee vault |
| `21` | `remove_supported_stable`| De-whitelist stablecoin and close marker account |

---

## PDA Seeds

| Account | Seeds | Purpose |
| :--- | :--- | :--- |
| `reach_state` | `[b"reach_state"]` | Global configuration and admin set |
| `task` | `[b"task", task_id.to_le_bytes()]` | Task state and terms |
| `task_vault` | `[b"task", task_pubkey]` | SPL token vault holding task escrow |
| `application` | `[b"application", provider_pubkey, task_pubkey]` | Provider application record |
| `supported_stable` | `[b"supported_stable", mint_pubkey]` | Supported stablecoin marker |
| `fee_vault` | `[b"fee_vault", mint_pubkey]` | Protocol fee collection token account |
| `provider_debt` | `[b"provider_debt", provider_pubkey]` | Provider debt tracking record |

---

## Building & Testing

### 1. Build Optimized SBF Binary

```bash
cargo build-sbf
```

The resulting binary will be emitted to `target/deploy/reach_escrow.so` with a size of **19,424 bytes**.

### 2. Run Local Integration Tests (LiteSVM)

```bash
cargo test
```

Executes 5 integration tests covering task cancellation, admin withdrawals, dispute arbitration, debt enforcement, and the full happy path.

### 3. Deploy to Solana Devnet

```bash
solana program deploy \
  --url devnet \
  --program-id deploy/reach_escrow-keypair.json \
  target/deploy/reach_escrow.so
```

### 4. Run Live Devnet Verification Suite

```bash
node scripts/test_devnet.js
```
