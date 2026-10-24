# CHANGELOG — `feat/fossapay-payments` (Model 1 payments, backend)

Rebased onto `origin/main` (Model 1 architecture: Solana Anchor program is the canonical escrow, fiat collections settle into USDC via Obiex, relayer signs on-chain).

> **Branch state (2026-10-23):** synced with `origin/feat/fossapay-payments`; the working tree is clean. The branch was force-pushed after the rebase. Future history rewrites need `git push --force-with-lease origin feat/fossapay-payments`.

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

`alembic/env.py` was a stub that only printed the database URL and exited
successfully without running anything. It now has the standard offline/online
runner and calls `context.run_migrations()`, so `alembic upgrade head` either
applies the revisions or fails loudly when Postgres is unreachable.

---

## 10. Tests

| File | Count | Notes |
|---|---|---|
| `test_webhook_handler.py` | 15 | FossaPay + Obiex webhooks, both signature schemes, replay/held/invalid, off-ramp dispatch. |
| `test_webhook_flow.py` | 9 | `_sync_checkout`, `_sync_payout` unit tests. |
| `test_release_flow.py` | 4 | Release requires funded escrow, owner, provider address. |
| `test_solana_layer.py` | 18 | PDA/ATA derivation, instruction encoding against independent decoder, task/application decoding, base58 round-trips, legacy transaction submission. |
| `test_geo_serialization.py` | 2 | Job/Service latitude/longitude serialization from PostGIS (requires Shapely). |
| `test_provider_flow.py` | 12 | Provider prepare/submit verification, tampering, replay reconciliation, relayer-signed accept. |
| `test_creator_flow.py` | 12 | Client-signed `create_task` / `accept` / `approve_work`, tampering, idempotency, completion checks. |
| `test_obiex_client.py` | 11 | Request signing, webhook verification, missing credentials. |
| `test_funding.py` | 15 | Escrow arithmetic (creation fee room), status mapping, amount conversions, per-job crypto deposit identifiers. |
| `test_provider_payout.py` | 8 | Canonical address validation, endpoint 422s. |
| `test_treasury.py` | 8 | `plan_top_up` logic, minimum withdrawal, wallet balance parsing. |
| `test_offramp.py` | 24 | Off-ramp quote, name match, create, partial/overpayment, swap/payout, retry, refund, bank resolution. |
| `test_auth_email.py` | 2 | Signup sends the verification email and survives a mail outage. |
| `test_fossapay_client.py` | 2 | FossaPay client envelope/signature helpers. |
| `test_relayer.py` | 4 | Relayer address and policy checks. |
| `test_payment_amounts.py` | 4 | Kobo/naira conversion and commission rounding. |
| `test_payment_signatures.py` | 4 | Raw `data` extraction and signature verification. |
| `test_payment_validation.py` | 4 | Name, phone, and date-of-birth validation. |

**Total: 158 tests, no database required.**

---

## 11. Docs updated

| File | What |
|---|---|
| `reach_flows_and_architecture_documentation.md` | Appendix: "Provider Mapping" — what each provider actually does vs. what the doc assumed. |
| `docs/REACH_MODEL1_PAYMENTS_PLAN.md` | Progress tracker, still-open items, treasury design. |
| `docs/REACH_PAYMENT_FLOWS_PLAN.md` | Cross-rail matrix, funding per rail, provider payout cases, treasury loop, services flow funding, task-id namespacing. |
| `docs/REACH_CRYPTO_RUNBOOK.md` | Direct wallet-funded escrow steps, wallet/SOL requirements, and the updated known limitations. |
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
| Crypto deposit matching | Each job gets its own Obiex `uniqueUserIdentifier`, and the `DEPOSIT` webhook only matches a pending intent, so two jobs for one user cannot collide. |
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

1. **On-chain provider lifecycle** — the backend now prepares, verifies and submits provider-signed `apply` / `complete_task` and relayer-signed `accept` (see §15). The remaining work is the frontend wallet UX (connect Phantom/Solflare, save `onchain_address`, sign the returned transaction), which is owned by the frontend workstream. `approve_work` is reachable once the provider completes through that flow.
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

## 15. Provider-signed on-chain lifecycle (2026-10-23)

The program requires the provider's own key for `apply` and `complete_task`, so
the backend cannot mirror those instructions from a DB write. This pass adds a
prepare → wallet-signs → submit flow.

| File | Purpose |
|---|---|
| `core/solana.py` | `decode_application_account`; discriminator-aware task decoding; `build_legacy_transaction`; `send_transaction` accepts legacy or versioned transactions; `get_token_account_balance` now takes the token account address. |
| `core/relayer.py` | `accept_application` (relayer signs `accept` as the custodial creator); `token_balance` derives the owner's ATA first. |
| `services/provider_flow.py` | `prepare_provider_transaction`, `submit_provider_transaction`, `accept_application_onchain`, and typed errors. |
| `routers/jobs.py` | `POST /jobs/{id}/onchain/apply`, `.../apply/submit`, `.../complete`, `.../complete/submit`; `PATCH /jobs/applications/{id}/status` now performs the on-chain accept; provider completion requires `onchain_status == "AwaitingApproval"`. |
| `services/chain.py` | Release verifies the on-chain provider matches the accepted applicant's wallet. |
| `routers/payments.py` | Release requires both `client_completed` and `worker_completed`. |
| `schemas/jobs.py` | `JobOnchainPrepareResponse`, `JobOnchainSubmitRequest`; `JobResponse` now exposes `funding_status`, `payer_type`, `onchain_status`, `client_completed`, `worker_completed`. |
| `schemas/enums.py` | `ProviderAction` (`apply`, `complete`). |
| `core/configs.py` | `REACH_APPLICATION_TTL_SECONDS` (default 604800). |
| `tests/test_provider_flow.py` | Prepare/submit/accept tests, including tampered-signature rejection. |
| `tests/test_solana_layer.py` | Discriminator-aware fixtures and legacy-transaction serialization. |

Controls:

- Submit decodes a **legacy** `Transaction`, requires the provider's saved
  address as fee payer and the only signer, and requires exactly one
  instruction with the expected program/discriminator/args/accounts.
- `apply` task id and `expires_at` are re-read from the signed instruction;
  a transaction for another task is rejected.
- DB state is only written after the task/application is read back from
  Solana. A failed confirmation is recorded as `FAILED` and never marks the
  job complete. The same guard now covers `create_task` and `approve_work`.
- `apply` and `complete_task` are idempotent; a replay returns the confirmed
  `chain_transactions` row and reconciles the job from chain state. The
  application key includes the provider wallet, so several providers can apply
  to the same task without colliding.
- The relayer refuses `accept` when the escrow creator is not the relayer, so a
  wallet-funded escrow cannot be silently accepted by the backend.

**Test count:** 140 at the time of that pass; see the current total below.

---

## 16. Client-signed wallet-funded escrow (2026-10-24)

The client can now fund the task directly from their own Solana wallet. The
client's wallet is the on-chain creator, so it signs `create_task`, `accept`
and `approve_work`. The provider still signs `apply` and `complete_task`.

| File | Purpose |
|---|---|
| `services/creator_flow.py` | `prepare_create_task` / `submit_create_task`, `prepare_accept` / `submit_accept`, `prepare_release` / `submit_release`; wallet/transaction/state errors. |
| `services/onchain_verify.py` | Shared legacy-transaction verification extracted from `provider_flow.py`: fee payer, sole signer, signature, exact instruction/accounts/args. |
| `routers/jobs.py` | `POST /jobs/{id}/onchain/fund`, `/fund/submit`; `POST /jobs/applications/{id}/onchain/accept`, `/accept/submit`; `POST /jobs/{id}/onchain/release`, `/release/submit`; `GET /jobs/{id}/onchain`. |
| `routers/jobs.py` | `PATCH /jobs/{id}/link-chain` now reads the task from Solana and requires the caller's wallet to be the creator before marking the job funded. |
| `routers/jobs.py` | `PATCH /jobs/applications/{id}/status` rejects wallet-funded escrows with a `409` pointing at the client prepare/submit endpoints. |
| `routers/payments.py` | Relayer-signed release rejects wallet-funded escrows with a `409` pointing at `/jobs/{id}/onchain/release`. |
| `schemas/jobs.py` | `JobOnchainFundRequest`, `JobOnchainStateResponse`, and `signer_address` / `amount_units` / `escrow_units` / `creation_fee_units` on the prepare response. |
| `schemas/enums.py` | `CreatorAction` (`create_task`, `accept`, `approve_work`). |
| `tests/test_creator_flow.py` | Prepare/submit tests for all three client actions, tampered-signature rejection, completion-flag checks and idempotent reconciliation. |

Controls:

- `create_task` uses the client's wallet as fee payer and only signer; the
  backend verifies the exact term sheet and reads the task back before marking
  the job `FUNDED`.
- `accept` verifies that the provider applied on-chain and that the client's
  wallet is the task creator.
- `approve_work` ensures the provider's USDC token account exists, then
  verifies the client-signed instruction before submitting.
- A confirmed submit that lost its DB write is reconciled from the on-chain
  task state instead of submitting the same PDA twice.
- Phase 1 stores the USDC amount on `payment_intents.usdc_amount` (rail
  `wallet`); no schema migration is required. `jobs.budget` remains the naira
  reference until a USDC price field is added.

**Test count:** 152 at the time of that pass; see the current total below.

---

## 17. Backend gap fixes (2026-10-24)

| Area | Change |
|---|---|
| Categories | Alembic data migration `b3c4d5e6f7a8` seeds Food, Fix, Move, Beauty, Tutor, Clean and Trade idempotently. `scripts/seed_categories.py` does the same for databases created with `build_tables.py`. |
| Signup email | `POST /auth/create-user` now calls `send_verification_email`; a mail outage is logged and does not roll back the account. `resend-verification` returns `503` when the mailer is unavailable. |
| Email provider | `SMTP_START_TLS` setting; credentials are only passed when configured. SMTP is configured for ZeptoMail (`smtp.zeptomail.com:587`, username `emailapikey`, Send Mail token as the password). The unused `resend` dependency was removed. |
| Jobs feed | `GET /jobs` and `GET /jobs/nearby` only return `OPEN` + `FUNDED` jobs. `/jobs/nearby` was moved above `/{job_id}` so it is no longer shadowed by the route parameter. |
| Services search | `GET /services` and `GET /services/nearby` accept `q`, `category_id`, `limit` and `offset`. Search covers service title, description and business name. Nearby now returns only `ACTIVE` services. |
| Services response | Added `Service.latitude` / `Service.longitude` properties so `ServiceResponse` no longer fails on a real service. Added `shapely` to requirements (GeoAlchemy2's optional dependency, also required by `Job.latitude` / `Job.longitude`). `POST /jobs` now validates that `category_id` exists. |
| Payouts | Added `GET /payouts/me`, `GET /payouts/banks`, `POST /payouts/banks/resolve`; `POST /payments/offramp/resolve-account` exposes the existing bank-name resolution. Bank listing/resolution works while live payouts are disabled. |
| Orders | Not implemented; remains a Phase 4 feature. |

**Test count:** 158, no database required.

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