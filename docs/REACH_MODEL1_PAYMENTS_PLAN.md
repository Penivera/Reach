# Reach Model 1 — Backend Payments Plan (FossaPay + Obiex + Solana)

Status: **phases 0–6, the provider-signed lifecycle, and the client-signed
wallet escrow flow implemented; phase 7 (ops) pending** on
`feat/fossapay-payments`, reviewed 2026-10-24. The crypto-only staging
checklist is in `docs/REACH_CRYPTO_RUNBOOK.md`.
Scope: **backend only**. Spec: `reach_flows_and_architecture_documentation.md`
(Model 1, canonical).

## Progress

| Phase | State | Notes |
|---|---|---|
| 0 — reset to the doc | Done | Branch rebased onto `origin/main`; `AWAITING_PAYMENT` replaced by `PENDING_FUNDING`; the DB ledger work parked on `wip/db-ledger`. |
| 1 — provider clients | Done | `core/fossapay.py` extended (crypto wallets, KYC, transfers, webhook settings/simulate); `core/obiex.py` added with HMAC request signing. |
| 2 — Solana layer | Done | `core/solana.py` (IDL-driven instruction building, PDA/ATA derivation, task decoding, async JSON-RPC); `core/relayer.py` (keypair, policy gate, sign/submit/confirm). |
| 3 — chain state mirror | Done | `services/chain.py` maps the program's task status onto the job row. |
| 4 — payment API | Done | `routers/payments.py` and `routers/webhooks.py` rewritten for the rails; the Obiex webhook is new. |
| 5 — schema | Done | Migration `a1b2c3d4e5f6`. |
| 6 — tests | Done | 158 tests, no database required. |
| 6a — provider-signed lifecycle | Done | `apply` / `complete_task` are prepared for the provider's wallet and verified after signing; `accept` and `approve_work` are signed by the relayer. |
| 6b — client-signed wallet escrow | Done | `create_task` / `accept` / `approve_work` are prepared for the client's wallet and verified after signing. The client becomes the on-chain creator and no treasury is used. |
| 7 — ops | Pending | Needs live credentials, a staging run, a treasury float policy and an external scheduler for reconciliation. |

### Still open

- The treasury float: an escrow is locked from the relayer's USDC balance, so
  the platform holds USDC and replenishes it with Obiex withdrawals. A
  collection that arrives while the float is short is retried automatically
  by `retry_pending_fundings` after the withdrawal webhook; there is no
  background scheduler yet, so reconciliation still needs external cron.
- Provider naira cash-out is implemented as the deposit-address off-ramp
  (`/payments/offramp`), but live payouts remain disabled behind
  `REACH_OFFRAMP_ENABLED=false` until Obiex Business Collections access and
  the prerequisites in `docs/REACH_NAIRA_OFFRAMP.md` §6 are confirmed.
  Providers otherwise receive USDC on-chain only.
- The FossaPay webhook signature scheme has to be confirmed against a real
  event. Both the v1 (over `data`) and v2 (over the body) schemes are
  accepted for now, and the matched scheme is reported.
- `apply`, `accept`, `complete_task` and `approve_work` are now driven by the
  backend (see §3a). For a wallet-funded escrow the client signs
  `create_task`, `accept` and `approve_work`; for a custodial escrow the
  relayer signs the creator-side instructions. The remaining lifecycle
  instructions (`provide_collateral`, `cancel_task`, `raise_dispute`) are
  still not exposed by the API. Release requires the task to be
  `AwaitingApproval` **and** the on-chain provider to match the accepted
  applicant's saved wallet, so a provider cannot be paid into a different
  address than the one that applied.
- The client wallet UI is owned by the frontend workstream. The backend
  prepare/submit contract is in §3a; the frontend must call the three client
  prepare endpoints, sign in Phantom/Solflare/Backpack, and submit the signed
  bytes.
- Phase 1 stores the client's USDC amount on `payment_intents.usdc_amount`
  (rail `wallet`) rather than adding a USDC job-price column. The existing
  `jobs.budget` remains the naira reference. A proper USDC price field is a
  later schema cleanup.
- Wallet-funded refunds/cancellations require a client-signed `cancel_task`;
  that endpoint is not exposed yet. The custodial path can still be cancelled
  by the relayer.
- The crypto-only path still needs a real staging run: relayer/RPC
  credentials, the pending migration, and a manually pre-funded USDC treasury
  are operational prerequisites. See `docs/REACH_CRYPTO_RUNBOOK.md`.

---

## 1. What the architecture doc mandates

- Solana Anchor program `5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY` is the **canonical settlement layer**.
- Escrow is locked **at task creation**, not after an application is accepted.
- Fees are on-chain: creation 2.5%, cancellation 10%. There is no platform commission at payout time.
- A **backend relayer** holds an automated Solana keypair and signs `create_task` / `approve_work` on the user's behalf (`payer_type = "custodial"`).
- `near-contract/` is deprecated; `onchain_task_id` / `onchain_tx_hash` are the DB-side anchors.

## 2. Provider capability map (verified against live API specs)

| Role | Provider | Endpoint |
|---|---|---|
| Collect NGN per customer, auto-settle to USDC | **Obiex** | `POST /collections` (Business account, gated) → `COLLECTION` webhook |
| USDC collection per task (crypto-native users) | Obiex | `POST /addresses/broker` → `DEPOSIT` webhook |
| Platform NGN→USDC conversion | Obiex | `POST /trades/swap` |
| Move USDC into the escrow | Obiex | `POST /wallets/ext/debit/crypto` (`network: SOL`) → relayer ATA |
| Provider cash-out USDC→NGN | Obiex | `POST /wallets/ext/debit/fiat` |
| Identity (NIN/BVN) | FossaPay | `POST /api/v1/kyc/verifications` |
| Solana custodial wallet per user | FossaPay | `POST /api/v1/wallets/crypto/create` |
| Customer USDC transfer | FossaPay | `POST /api/v1/transfers/crypto` |
| Relayer signing | **ours** (own Solana keypair) | local sign + Solana RPC |
| Test environment | Obiex staging | `staging.api.obiex.finance` (FossaPay has **no** sandbox) |

### Deviations from the doc (to be reflected in an updated doc section)

1. The doc assigns the fiat-gateway role to FossaPay ("collects fiat, auto-converts to stablecoins").
   Implemented by **Obiex Business Collections** — it does per-customer NGN collection with BVN/NIN
   identity and settles into USDC. FossaPay retains KYC, Solana wallet provisioning, crypto
   transfers and NGN payouts.
2. The relayer is a **self-hosted keypair** (per the doc), not FossaPay's managed wallet.

### Resolved risk: NGN→USDC

`POST /checkouts` is NGN-only and no FossaPay endpoint converts fiat to stablecoins.
Obiex supplies the missing leg (`/collections` settlement, `/trades/swap` for treasury float).

## 3. End-to-end flows

### Flow 2a — fiat payer (custodial, on-chain escrow)

```
POST /jobs (draft)  ->  POST /payments/jobs/{id}/collection
   -> Obiex POST /collections (NGNX -> USDC, BVN/NIN)  -> virtual NGN account shown to payer
   -> payer transfers NGN  -> Obiex name-matches  -> COLLECTION webhook (COMPLETED | HELD)
   -> backend: Obiex POST /wallets/ext/debit/crypto (USDC, SOL) -> relayer ATA
   -> relayer signs sol_contract::create_task (escrow locked in USDC)  -> job.status = OPEN
   -> provider accepts / applies / collateral  -> complete_task
   -> creator approves  -> relayer signs approve_work  -> provider USDC released on-chain
```

### Flow 2b — crypto payer

```
POST /jobs (draft)  ->  user pays USDC to a Solana address  -> DEPOSIT webhook
   -> relayer signs create_task funded from the same treasury ATA  -> job.status = OPEN
```

### Flow 1 — native Solana user (frontend-owned)

```
POST /jobs -> POST /jobs/{id}/onchain/fund -> user signs create_task
   -> POST /jobs/{id}/onchain/fund/submit -> backend verifies + mirrors state
```

The client is the on-chain creator, so the same prepare → sign → submit flow
covers `accept` and `approve_work` (see §3b). `PATCH /jobs/{id}/link-chain`
remains a verified reconciliation fallback.

### 3a — provider-signed lifecycle (`apply`, `complete_task`)

The Anchor program requires the **provider's own key** for `apply` and
`complete_task`. The backend never signs for them. Each instruction uses a
prepare → wallet-signs → submit flow:

```
PUT  /users/me/onchain-address                 # once; the provider's payout wallet
POST /jobs/{id}/onchain/apply                  # create/refresh the DB application,
                                               # return an unsigned legacy transaction
     provider wallet signs the returned base64 transaction
POST /jobs/{id}/onchain/apply/submit           # backend verifies + submits + mirrors state
PATCH /jobs/applications/{id}/status {accepted}# relayer signs `accept` (custodial creator)
POST /jobs/{id}/onchain/complete               # return the unsigned `complete_task`
     provider wallet signs
POST /jobs/{id}/onchain/complete/submit        # verify + submit; job -> AwaitingApproval
PATCH /jobs/{id}/completion                    # creator records client_completed
POST /payments/jobs/{id}/release               # relayer signs `approve_work` (custodial only)
```

Verification on submit is deliberately strict:

- the transaction must decode as a legacy `Transaction`;
- the provider's saved address must be the fee payer and the only signer;
- there must be exactly one instruction, with the expected program id,
  discriminator, arguments and account list;
- for `apply`, the task id and `expires_at` are read back out of the signed
  instruction and re-checked against the job;
- the backend reads the task (and application) back from Solana before it
  writes `onchain_status`, `worker_completed` or a confirmed
  `chain_transactions` row.

`apply` is idempotent: if the application PDA already exists the prepare call
returns `already_done` with no transaction. `complete_task` is likewise
idempotent once the task is `AwaitingApproval`. Application expiry is
`REACH_APPLICATION_TTL_SECONDS` (default 7 days).

The creator-side `accept` is different: for a custodial escrow the relayer is
the on-chain creator, so `PATCH /jobs/applications/{id}/status` signs it
server-side.

### 3b — client-signed wallet escrow (`create_task`, `accept`, `approve_work`)

When the client funds from their own wallet, the client is the on-chain
creator. The backend prepares the same kind of unsigned legacy transaction and
the client signs it:

```
PUT  /users/me/onchain-address                  # the client's wallet
POST /jobs/{id}/onchain/fund { usdc_amount }    # unsigned create_task
     client wallet signs the base64 transaction
POST /jobs/{id}/onchain/fund/submit             # verify + submit + mirror; job -> FUNDED / OPEN
POST /jobs/applications/{id}/onchain/accept     # unsigned accept
     client wallet signs
POST /jobs/applications/{id}/onchain/accept/submit
POST /jobs/{id}/completion                      # client records client_completed
POST /jobs/{id}/onchain/release                 # unsigned approve_work
     client wallet signs
POST /jobs/{id}/onchain/release/submit          # provider receives USDC
GET  /jobs/{id}/onchain                          # decoded task state
```

The client wallet needs USDC for the escrow plus the creation fee, and SOL for
the transaction fee and task/vault rent. The relayer only creates the client's
USDC ATA and the provider's payout ATA; it does not fund the escrow.

Phase 1 stores the selected USDC amount on `payment_intents.usdc_amount` (rail
`wallet`). `jobs.budget` remains the naira reference until a USDC job-price
column is added.

Frontend contract (owned by the frontend workstream):

1. Connect an injected Solana wallet (Phantom / Solflare / Backpack).
2. `PUT /users/me/onchain-address` with `wallet.publicKey.toBase58()`.
3. Call the prepare endpoint. If `already_done` is true, refresh and stop.
4. `Transaction.from(Buffer.from(transaction, "base64"))`, then
   `wallet.signTransaction(tx)`, then `tx.serialize().toString("base64")`.
5. Call the submit endpoint with `{ "signed_transaction": "<base64>" }`.

The wallet must not add instructions or change the fee payer; the backend
rejects anything that is not exactly the prepared instruction.

## 4. Work plan

### Phase 0 — reset to the doc
- `git rebase origin/main` onto `feat/fossapay-payments` (backup branch first).
  Brings the architecture doc, the `onchain_*` renames and the §4 contract patches.
- Drop the branch's `AWAITING_PAYMENT` job status and its use on application accept
  (Model 1 funds escrow at creation).
- Move the uncommitted `Escrow` / `LedgerEntry` / `LedgerTransaction` work and
  `services/ledger.py|escrow.py` to a `wip/db-ledger` branch — a second DB ledger would
  compete with on-chain state as the source of truth.
- Rename `services/payments_sync.py` -> `services/fossapay_sync.py` (provider state only).

### Phase 1 — provider clients
- `backend/core/fossapay.py`: real `/api/v1/...` paths, `X-Idempotency-Key` on writes,
  envelope unwrap, decimal strings (never floats), pagination.
  Add: crypto wallet create, customer balance, crypto transfer + fee quote, KYC verify,
  wallet transactions, webhook settings, webhook simulate.
  Webhook signing: support **v1** (`x-fossapay-signature`) and **v2** (`x-fossapay-signature-v2`).
  The current branch signs raw body bytes; FossaPay's own example signs `JSON.stringify(body.data)`.
  Must be confirmed against a real event before go-live.
- `backend/core/obiex.py` (new): HMAC-SHA512 request signing (`x-api-key`, `x-api-timestamp`,
  `x-api-signature`), collections, broker deposit addresses, balances, swap, crypto/fiat withdrawals,
  naira banks + account resolve, transaction lookups.

### Phase 2 — Solana layer
- `backend/core/solana.py`: Anchor instruction encoding from `sol-contract/idl.json`
  (IDL present and complete), PDA + ATA derivation, v0 `VersionedTransaction` with ALTs,
  and a legacy `Transaction` builder for browser-wallet signing.
- `backend/core/relayer.py`: keypair loading, fee/SOL top-up checks, policy gate
  (allowlisted program id + mint + amounts), sign + submit to RPC, confirm/finalize tracking,
  and `accept_application` for the custodial creator.
- Dependency: `solders` (Solana SDK) — add to `backend/requirements.txt`.

### Phase 3 — chain state mirror
- `backend/services/chain_sync.py`: read Task PDA -> map `TaskStatus` -> `JobStatus`;
  persist `onchain_task_id`, `onchain_tx_hash`, `onchain_status`, `payer_type`.
- Background reconciler for pending/failed transactions.

### Phase 4 — payment API
- `POST /jobs` -> draft; funding unlocks the job.
- `POST /payments/jobs/{id}/collection` -> Obiex collection (virtual NGN account).
- `POST /payments/jobs/{id}/deposit-address` -> Obiex broker address (USDC/SOL).
- `POST /webhooks/obiex` -> verify HMAC-SHA512, dedupe on `reference`/`transactionId`.
- `POST /webhooks/fossapay` -> verify v1/v2, dedupe on `eventId`.
- `POST /payments/jobs/{id}/release` -> relayer signs `approve_work`.
- `GET /payments/jobs/{id}` -> unified funding + chain status.
- `POST /jobs/{id}/onchain/apply` / `.../apply/submit` -> provider-signed application.
- `POST /jobs/{id}/onchain/complete` / `.../complete/submit` -> provider-signed completion.
- `PATCH /jobs/applications/{id}/status` -> relayer-signed `accept` for custodial escrows.
- `POST /jobs/{id}/onchain/fund` / `.../fund/submit` -> client-signed `create_task` for wallet-funded escrows.
- `POST /jobs/applications/{id}/onchain/accept` / `.../accept/submit` -> client-signed `accept`.
- `POST /jobs/{id}/onchain/release` / `.../release/submit` -> client-signed `approve_work`.
- `GET /jobs/{id}/onchain` -> decoded on-chain task state (creator, provider, status, fees).
- `PATCH /jobs/{id}/link-chain` -> legacy verified reconciliation fallback; new clients use `/onchain/fund/submit`.

### Phase 5 — schema
- `jobs`: `payer_type`, `funding_status`, `onchain_status`; drop `AWAITING_PAYMENT`.
- `payment_profiles`: add BVN/NIN, bank code + account number (provider cash-out).
- new `funding_intents` (rail: obiex_fiat | crypto | wallet, status, amounts, refs).
- new `chain_transactions` (business ref, kind, tx hash, status, error, raw).

### Phase 6 — tests
- Extend the fake provider in `backend/tests/support.py`; the branch currently has 158 tests.
- New: instruction-encoding golden tests (PDA/ATA vs anchor), HMAC verification,
  webhook dedupe/replay, relayer idempotency, collection -> escrow flow, release flow,
  provider prepare/submit verification (tampering, wrong signer, wrong task).
- Obiex **staging** is the only place an end-to-end run can happen safely.

### Phase 7 — ops
- Env vars, webhook URLs, treasury float policy, reconciliation job, runbook.

## 5. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| FossaPay has no sandbox | cannot test webhooks safely | Obiex staging for the crypto/USDC path; FossaPay limited to KYC + wallet provisioning until a real event is captured |
| Obiex Business Collections is access-gated | collection rail blocked | sales@obiex.finance; keep the FossaPay checkout rail as fallback |
| FossaPay webhook signature format unconfirmed | webhooks rejected or forged | support v1+v2, log both, confirm with a real event |
| Obiex `USDC` on `SOL` availability | escrow funding leg blocked | check `GET /currencies/networks/active` at startup; fall back to a supported network + the FossaPay master wallet |
| Conversion/float lag | escrow funding delayed | keep a USDC float in the relayer ATA; alert below threshold |
| Provider cash-out | providers stuck in USDC | Deposit-address off-ramp is implemented (`/payments/offramp`) behind `REACH_OFFRAMP_ENABLED=false`; see `docs/REACH_NAIRA_OFFRAMP.md`. Live enablement needs Obiex confirmation of third-party bank payouts, USDC/SOL deposits, `USDC/NGNX` pair, and withdrawal idempotency. |
