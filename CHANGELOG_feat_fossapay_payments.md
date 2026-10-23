# CHANGELOG — `feat/fossapay-payments` (Model 1 payments, backend)

Rebased onto `origin/main` (Model 1 architecture: Solana Anchor program is the canonical escrow, fiat collections settle into USDC via Obiex, relayer signs on-chain).

> **Branch state (2026-10-23):** synced with `origin/feat/fossapay-payments` at `8b57ffc`. The branch was force-pushed after the rebase; the working tree is clean. Future history rewrites need `git push --force-with-lease origin feat/fossapay-payments`.

---

## 0. Structural reset

- **Rebased onto `origin/main`** — the branch now sits on top of the Model 1 architecture doc, the `onchain_*` renames, and the §4 contract patches. The pre-rebase head is preserved at `backup/feat-fossapay-payments-pre-rebase`.
- **Removed the DB double-entry ledger** — `Escrow`, `LedgerEntry`, `LedgerTransaction`, `services/ledger.py|escrow.py` moved to `wip/db-ledger`. The Solana program is the escrow; a second ledger would compete with chain state as the source of truth.
- **Dropped `AWAITING_PAYMENT`** — Model 1 funds the escrow at task creation, not after acceptance. Jobs now start in `PENDING_FUNDING` and open when the escrow is on-chain.

---

## 1. Solana settlement layer

| Commit | File | Purpose |
|---|---|---|
| `53bac6e` | `core/solana.py` | IDL-driven instruction builder, PDA/ATA derivation, task account decoding, async JSON-RPC client. |
| `53bac6e` | `core/relayer.py` | The "FastAPI Keypair Engine" — loads the relayer keypair, enforces policy (allowlisted program + mint + amounts), signs and submits `create_task`, `approve_work`, `cancel_task`, confirms/finalizes. |

**What changed vs. the doc's assumption:** The relayer is a self-hosted keypair (not FossaPay's managed wallet), because the doc says the backend holds an automated Solana keypair.

---

## 2. Provider clients

| Commit | File | Purpose |
|---|---|---|
| `e89ccc1` | `core/fossapay.py` | Extended the FossaPay client: crypto wallets, KYC, transfers + fee quotes, wallet transactions, webhook settings + simulation, both v1 (`data`) and v2 (body) signature verification. |
| `e89ccc1` | `core/obiex.py` | New Obiex client: HMAC-SHA256 request signing, HMAC-SHA512 webhook verification, Business Collections, broker deposit addresses, swaps, crypto/fiat withdrawals, naira banks + account resolve. |

**Key correction:** FossaPay has **no fiat→stablecoin conversion** — its checkout is NGN-only. Obiex supplies the missing leg (collections settle naira → USDC). The "FossaPay auto-converts fiat" line in the architecture doc is wrong; the updated doc appendix records the real provider mapping.

---

## 3. Model 1 funding lifecycle (jobs)

| Commit | File | Purpose |
|---|---|---|
| `a60e925` | `models/jobs.py`, `schemas/enums.py` | New columns: `funding_status`, `payer_type`, `onchain_status`; `JobStatus.PENDING_FUNDING` replaces `AWAITING_PAYMENT`. |
| `a60e925` | `models/payments.py` | `PaymentIntent.rail` (Obiex / FossaPay / crypto / wallet), `usdc_amount`, `provider_reference`, `deposit_address`; new `ChainTransaction` table (idempotency-keyed on-chain tx records); `FossaPayCustomer` gains crypto wallet fields for providers. |
| `a60e925` | `services/funding.py`, `routers/payments.py` | Three rails: Obiex collection (NGN→USDC, NIN+BVN), FossaPay checkout (NGN), crypto deposit address (USDC). All funnel into the same treasury → relayer → escrow path. |
| `a60e925` | `services/chain.py` | `fund_task_escrow` locks the escrow via the relayer; `retry_pending_fundings` locks escrows waiting on the float; `notify_nearby_providers` fires when the escrow is on-chain (per the doc: providers notified after escrow, not when drafted). |

**Behavioural changes:**

- A task is created in `PENDING_FUNDING`. It opens when the escrow is on-chain.
- Accepting an applicant **requires the escrow to be `FUNDED`**; the DB then mirrors the program's `InProgress` state.
- The rai is chosen per payment: `POST /payments/jobs/{id}/collection?rail=obiex_fiat|crypto|fossapay_checkout`.
- `GET /payments/requirements` tells the frontend exactly what the customer still needs for a given rail — the profile is collected **at payment time**, not at signup.

---

## 4. Provider payout: Case A (provider's own Solana address)

| Commit | File | Purpose |
|---|---|---|
| `3cf9aa1` | `models/users.py`, `schemas/users.py` | `users.onchain_address` — provider's own Solana address, canonical base58 validated. |
| `3cf9aa1` | `routers/users.py` | `PUT /users/me/onchain-address` — provider sets their payout address. |
| `3cf9aa1` | `services/chain.py` | `release_task_escrow` resolves the provider's own address, **creates their ATA and pays the rent** if they've never held USDC on Solana, then signs `approve_work`. |

**Case B (exchange deposit address) and Case C (custodial + Obiex off-ramp) are deferred.** The batching requirement is noted for Case C.

**Case D (provider deposit-address naira off-ramp) is implemented behind a disabled flag.** See §13 and `docs/REACH_NAIRA_OFFRAMP.md`.

---

## 5. The treasury — the piece that was blocking fiat escrows

| Commit | File | Purpose |
|---|---|---|
| `476d952` | `services/treasury.py` | Reads two balances: **on-chain** (USDC in relayer's token account) and **provider** (USDC in our Obiex wallet). Withdraws the difference. Batched: sweeps provider balance down to `REACH_TREASURY_TARGET_UNITS` instead of per-job. |
| `476d952` | `services/chain.py` | `retry_pending_fundings` — locks escrows waiting on the float. |
| `476d952` | `routers/webhooks.py` | `_sync_withdrawal` — confirms the Obiex withdrawal, marks `treasury_transfers` confirmed, fires the retry. |
| `476d952` | `routers/payments.py` | `POST /payments/treasury/top-up` — manual lever for ops. |

**The loop:**

```
COLLECTION (COMPLETED) → intent PAID, usdc_amount recorded
  → float short → treasury.request_withdrawal (batched, min 10 USDC)
  → job stays pending, money safe with provider
WITHDRAWAL (SUCCESSFUL) → treasury_transfers confirmed
  → retry_pending_fundings() locks waiting escrows
  → job opens, providers notified
```

---

## 6. Webhooks — both providers, both verified

| Commit | File | Purpose |
|---|---|---|
| `a60e925` + `476d952` | `routers/webhooks.py` | FossaPay: accepts **both v1 (over `data`)** and **v2 (over body)**; Obiex: HMAC-SHA512 over raw body. Both deduplicated (`eventId` / `reference`). FossaPay webhook now uses `estimate_usdc_units` (live Obiex rate) to get the settled USDC amount. |

---

## 7. Payment profile — collected when they pay, not at signup

| Commit | File | Purpose |
|---|---|---|
| *(latest)* | `services/funding.py` | `missing_fields_for_rail(rail, user, profile)` — per-rail requirements (crypto: none; naira: NIN+BVN + identity). |
| *(latest)* | `routers/payments.py` | `GET /payments/requirements?rail=...` — frontend calls this when the user taps pay; `POST /payments/jobs/{id}/collection` gates the rail on those missing fields. |

---

## 8. Services flow funding (blocked on task-id namespacing)

The current `ServiceRequest` flow has **no payment** (request → accept → complete, money never moves). The plan adds the same rails to service requests, with:

- `task_id = 1_000_000_000 + request_id` (jobs keep `task_id = job.id` for the doc's "1:1 parity").
- `ServiceRequest` gains `onchain_task_id`, `onchain_tx_hash`, `funding_status`, `payer_type`, `onchain_status`.
- Same `POST /payments/service-requests/{id}/collection`, `GET`, `POST .../release`.

---

## 9. Migrations

| Migration | Purpose |
|---|---|
| `a1b2c3d4e5f6` | Model 1 funding lifecycle: `funding_status`, `payer_type`, `onchain_status`, `PaymentIntent.rail`, `usdc_amount`, `provider_reference`, `deposit_address`, `ChainTransaction`, crypto wallet fields on `FossaPayCustomer`, `bvn`/`nin`/bank fields on `PaymentProfile`. |
| `b2c3d4e5f6a7` | `users.onchain_address` for provider payouts. |
| `c3d4e5f6a7b8` | `treasury_transfers` table (batched withdrawals). |
| `f1a2b3c4d5e6` | `offramp_withdrawals` table and `offrampstatus` enum for the provider naira off-ramp. |

---

## 10. Tests

| File | Count | Notes |
|---|---|---|
| `test_webhook_handler.py` | 15 | FossaPay + Obiex webhooks, both signature schemes, replay/held/invalid, off-ramp dispatch. |
| `test_webhook_flow.py` | 9 | `_sync_checkout`, `_sync_payout` unit tests. |
| `test_release_flow.py` | 4 | Release requires funded escrow, owner, provider address. |
| `test_solana_layer.py` | 17 | PDA/ATA derivation, instruction encoding against independent decoder, task decoding, base58 round-trips. |
| `test_obiex_client.py` | 11 | Request signing, webhook verification, missing credentials. |
| `test_funding.py` | 14 | Escrow arithmetic (creation fee room), status mapping, amount conversions. |
| `test_provider_payout.py` | 8 | Canonical address validation, endpoint 422s. |
| `test_treasury.py` | 8 | `plan_top_up` logic, minimum withdrawal, wallet balance parsing. |
| `test_offramp.py` | 22 | Off-ramp quote, name match, create, partial/overpayment, swap/payout, retry, refund. |
| `test_fossapay_client.py` | 2 | FossaPay client envelope/signature helpers. |
| `test_relayer.py` | 4 | Relayer address and policy checks. |
| `test_payment_amounts.py` | 4 | Kobo/naira conversion and commission rounding. |
| `test_payment_signatures.py` | 4 | Raw `data` extraction and signature verification. |
| `test_payment_validation.py` | 4 | Name, phone, and date-of-birth validation. |

**Total: 126 tests, no database required.**

---

## 11. Docs updated

| File | What |
|---|---|
| `reach_flows_and_architecture_documentation.md` | Appendix: "Provider Mapping" — what each provider actually does vs. what the doc assumed. |
| `docs/REACH_MODEL1_PAYMENTS_PLAN.md` | Progress tracker, still-open items, treasury design. |
| `docs/REACH_PAYMENT_FLOWS_PLAN.md` | Cross-rail matrix, funding per rail, provider payout cases, treasury loop, services flow funding, task-id namespacing. |
| `docs/PAYMENTS_HANDOFF.md`, `docs/PAYMENTS_IMPLEMENTATION_PLAN.md` | Marked **Superseded** with a banner pointing to the current plan. |

---

## 12. Blocker fixes (this pass)

| Area | Fix |
|---|---|
| Relayer identity | `Relayer.address` no longer calls `keypair.pubkey()` twice. |
| Provider ATA | `ensure_token_account` uses one `CreateIdempotent` instruction with the correct `[payer, ata, owner, mint, system, token]` order; it no longer creates the account twice. |
| FossaPay client | `_request` accepts `params`, so transaction listing and fee quotes work. |
| Job endpoints | `PUT /jobs/{id}` no longer calls `.model_dump()` on a dict; lat/lon must be updated together. |
| Accept gate | An applicant can only be accepted on a `FUNDED` task in `OPEN`; the old inverted status write is gone. |
| Wallet funding | `link-chain` now sets `FUNDED`, `WALLET`, `Open` and enforces `onchain_task_id == job.id`. |
| Amounts | Budgets must be whole naira and at least `MIN_ESCROW_KOBO`; Obiex collections must match the intent's naira amount or are `HELD`. |
| Single rail | A job cannot open a second rail while another intent is pending (409). |
| Duplicate payments | A second payment for an already-funded task is recorded as `REVERSED` with a refund reason instead of being silently escrowed. |
| Webhooks | Duplicate `(provider_object_id, event_type)` deliveries return the existing event instead of crashing; Obiex status is part of the dedupe key. |
| Release | `approve_work` is only attempted after reading `AwaitingApproval`, with a clear error otherwise. |
| Completion | Mutual completion no longer marks the job `COMPLETED`; only `approve_work` settles and completes it. |
| Retries | `fund_task_escrow` checks its idempotency record before topping up the float; retries skip closed jobs. |

## 13. Provider deposit-address naira off-ramp

| File | Purpose |
|---|---|
| `models/payments.py`, `schemas/enums.py` | New `OffRampWithdrawal` row and `OffRampStatus` state machine. |
| `services/offramp.py` | Quote, create deposit address, deposit matching, USDC→NGNX swap, NGNX bank payout, retry, refund, reconcile. |
| `routers/payments.py` | `/payments/offramp` endpoints, including admin retry/refund/reconcile. |
| `routers/webhooks.py` | DEPOSIT dispatch by `deposit_address`; WITHDRAWAL dispatch by provider reference. |
| `core/obiex.py` | GET bank-account resolve, trade-pair discovery, fiat withdrawal semantics. |
| `alembic/versions/f1a2b3c4d5e6_*` | `offramp_withdrawals` table. |
| `docs/REACH_NAIRA_OFFRAMP.md` | Design, API, confirmed Obiex facts, and the must-ask list. |

Key controls:

- The provider keeps custody; Reach only holds the brief deposit-to-payout
  window.
- Exact base-unit amounts; no rounding of USDC or kobo.
- `sellRate` for off-ramp, `buyRate` only for naira-in.
- Name matching against Obiex's resolved account name.
- Slippage floor, minimum payout, deposit expiry, partial/overpayment holds.
- Failed payouts have an admin retry path; deposits that have not been swapped
  can be refunded to `users.onchain_address`. Held payouts require manual review.
- `REACH_OFFRAMP_ENABLED=false` by default.

## Still open (blocking real money)

1. **On-chain provider lifecycle** — `apply`, `accept`, `complete_task` require a provider Solana wallet signature. The backend can sign `accept` as creator, but there is no provider wallet flow in the frontend yet, so `approve_work` still cannot be reached without an out-of-band `apply`/`complete_task`. This is the next blocker.
2. **Obiex Business Collections access** — gated; needs the confirmation email to `sales@obiex.finance` and the API/support contact.
3. **USDC-on-SOL withdrawability in Obiex** — docs only show USDT on `SOL`. The treasury needs USDC on SOL; asked Obiex in the email.
4. **Services flow funding** — needs the `task_id` namespacing fix and the same rails.
5. **FossaPay signature scheme** — accepts both v1 and v2; needs one real event to pin down.
6. **Provider naira cash-out** — backend endpoints and reconciliation now exist behind `REACH_OFFRAMP_ENABLED=false`. Live enablement is blocked on the Obiex confirmations in `docs/REACH_NAIRA_OFFRAMP.md` §6 (third-party bank payouts, USDC/SOL deposits, `USDC/NGNX` pair, withdrawal idempotency, fee/min/max, and `sortCode` vs `bankId`).
7. **Duplicate-payment refund** — a second payment is flagged `REVERSED`, but there is no automated refund/return path yet.

---

## 14. Documentation audit (2026-10-23)

- Updated `docs/REACH_MODEL1_PAYMENTS_PLAN.md` to the current test count,
  phase status, treasury behaviour, and off-ramp state.
- Added Case D (deposit-address naira off-ramp) to
  `docs/REACH_PAYMENT_FLOWS_PLAN.md`.
- Corrected the canonical architecture doc's fiat-to-USDC description and
  replaced stale absolute file links with repo-relative links.
- Added the Obiex Business Collections access blocker to
  `docs/REACH_NAIRA_OFFRAMP.md`.
- Marked the legacy `PAYMENTS_HANDOFF.md` and
  `PAYMENTS_IMPLEMENTATION_PLAN.md` explicitly as historical.

---

## Commits in this branch (oldest → newest)

```
21a98c7 chore(backend): add env example and align requirements
f5d5bb6 feat(payments): add FossaPay client, settings and money helpers
0085820 feat(payments): add payment profile, customer and provisioning
bd929bf feat(payments): add job checkout, payout release and hardened webhooks
f00d9fc test(payments): add unit and fake-provider integration tests
fe736a1 docs(payments): add payments implementation plan
dec601e docs(payments): add handoff with remaining work, frontend guide and endpoint reference
509b1e5 docs(payments): document implemented endpoints and link the handoff
7dfd9b5 feat(payments): add the Solana settlement layer
9b9dd4b feat(payments): add the Obiex client and extend the FossaPay client
48d469b feat(payments): fund tasks on-chain under Model 1
ca6bb85 test(payments): cover the Model 1 funding flow
7547316 docs(payments): record the Model 1 provider mapping
c8b9161 feat(payments): release the escrow to the provider's own Solana address
6cee01f docs(payments): record the case A provider payout decision
a417fbf feat(payments): add the treasury that funds the escrow float
6412c7b docs(payments): record the treasury design with Obiex as the provider
8b57ffc feat(payments): add provider naira off-ramp and harden payment flows
```

---

## To update the remote after a history rewrite

```bash
git push --force-with-lease origin feat/fossapay-payments
```

(The branch is currently synced; only use this after another rebase.)