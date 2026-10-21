# [DEPRECATED] Reach Protocol - NEAR Standalone Escrow Contract

> [!WARNING]
> **DEPRECATION NOTICE (ARCHITECTURE MODEL 1):**
> This standalone NEAR escrow smart contract (`reach.testnet`) has been **DEPRECATED** in favor of **Model 1 (Canonical Solana Settlement + NEAR Chain Abstraction)**:
> 
> * **Canonical Settlement Layer:** All task escrow locking, collateral management, advance disbursement, and final settlement are executed on the **Solana Anchor Program** located at [`sol-contract/programs/sol-contract`](../sol-contract/programs/sol-contract).
> * **Role of NEAR Protocol:** NEAR is leveraged exclusively for **Chain Abstraction**:
>   1. **NEAR Intents (Defuse Solver Network):** Enables users on multichain ecosystems (Ethereum, Base, Arbitrum, NEAR, Polygon) to convert any asset into Solana SPL USDC in a single click.
>   2. **NEAR Chain Signatures (MPC):** Enables non-Solana wallets to derive deterministic Solana addresses and sign Anchor transactions on Solana directly without requiring a separate Solana wallet or manual bridging.
> 
> *Do not deploy or wire new application features to this standalone contract.*

---

## Historical Context & Reference

This contract was originally developed as an NEP-141 escrow contract for NEAR Protocol using `near-sdk` v5.

### Methods Overview (Archival Reference):
* `init(supported_stables)`: Initializes the contract state with fee basis points (creation: 2.5%, cancellation: 10%).
* `ft_on_transfer`: Handles incoming NEP-141 stablecoins via `TransferAction`:
  * `CreateTask { desc, tag, stablecoin, terms }`: Escrows labor and material funds.
  * `ProvideCollateral { task_id, application_id }`: Escrows provider collateral.
  * `CancelApprovedApplication { task_id }`: Handles provider abandonment and debt enforcement.
* `complete_task`: Provider marks task completed.
* `approve_work`: Creator releases escrow to provider.
* `cancel_task`: Creator cancels before work begins (cancellation fee deducted).
* `raise_dispute` & `resolve_dispute`: Dispute handling and admin-controlled payout splits.

---

## Build & Test Instructions (Archived)

```bash
cargo test
cargo near build
```
