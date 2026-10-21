# Reach Model 1 — Backend Payments Plan (FossaPay + Obiex + Solana)

Status: **phase 0–2 and 4–6 implemented** on `feat/fossapay-payments`, 2026-10-21.
Scope: **backend only** (the FossaPay integration). Spec:
`reach_flows_and_architecture_documentation.md` (Model 1, canonical).

## Progress

| Phase | State | Notes |
|---|---|---|
| 0 — reset to the doc | Done | Branch rebased onto `origin/main`; `AWAITING_PAYMENT` replaced by `PENDING_FUNDING`; the DB ledger work parked on `wip/db-ledger`. |
| 1 — provider clients | Done | `core/fossapay.py` extended (crypto wallets, KYC, transfers, webhook settings/simulate); `core/obiex.py` added with HMAC request signing. |
| 2 — Solana layer | Done | `core/solana.py` (IDL-driven instruction building, PDA/ATA derivation, task decoding, async JSON-RPC); `core/relayer.py` (keypair, policy gate, sign/submit/confirm). |
| 3 — chain state mirror | Done | `services/chain.py` maps the program's task status onto the job row. |
| 4 — payment API | Done | `routers/payments.py` and `routers/webhooks.py` rewritten for the rails; the Obiex webhook is new. |
| 5 — schema | Done | Migration `a1b2c3d4e5f6`. |
| 6 — tests | Done | 69 tests, no database required. |
| 7 — ops | Pending | Needs live credentials, a staging run and a treasury float policy. |

### Still open

- The treasury float: an escrow is locked from the relayer's USDC balance, so
  the platform holds USDC and replenishes it with Obiex withdrawals. The
  replenishment job is not written yet.
- The provider cash-out endpoint (Obiex `wallets/ext/debit/fiat`) is not
  exposed yet; providers currently receive USDC on-chain only.
- The FossaPay webhook signature scheme has to be confirmed against a real
  event. Both the v1 (over `data`) and v2 (over the body) schemes are
  accepted for now, and the matched scheme is reported.
- The on-chain task lifecycle beyond `create_task` and `approve_work`
  (`accept`, `provide_collateral`, `complete_task`, `cancel_task`,
  `raise_dispute`) is not yet driven by the backend.

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
| USDC collection per customer (crypto-native users) | Obiex | `POST /addresses/broker` → `DEPOSIT` webhook |
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
POST /jobs -> user signs create_task in Phantom -> PATCH /jobs/{id}/link-chain
   -> backend mirrors on-chain state
```

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
  (IDL present and complete), PDA + ATA derivation, v0 `VersionedTransaction` with ALTs.
- `backend/core/relayer.py`: keypair loading, fee/SOL top-up checks, policy gate
  (allowlisted program id + mint + amounts), sign + submit to RPC, confirm/finalize tracking.
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

### Phase 5 — schema
- `jobs`: `payer_type`, `funding_status`, `onchain_status`; drop `AWAITING_PAYMENT`.
- `payment_profiles`: add BVN/NIN, bank code + account number (provider cash-out).
- new `funding_intents` (rail: obiex_fiat | crypto | wallet, status, amounts, refs).
- new `chain_transactions` (business ref, kind, tx hash, status, error, raw).

### Phase 6 — tests
- Extend the fake provider in `backend/tests/support.py`; keep the 29 existing tests.
- New: instruction-encoding golden tests (PDA/ATA vs anchor), HMAC verification,
  webhook dedupe/replay, relayer idempotency, collection -> escrow flow, release flow.
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
| Provider cash-out | providers stuck in USDC | Obiex fiat withdrawal behind a request endpoint (phase 2) |
