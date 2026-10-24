# Frontend Integration TODO — FossaPay / Solana Wallet Architecture

> Derived from:
> [`FRONTEND_WALLET_ESCROW_HANDOFF.md`](file:///c:/Users/user/Reach/docs/FRONTEND_WALLET_ESCROW_HANDOFF.md),
> [`PAYMENTS_IMPLEMENTATION_PLAN.md`](file:///c:/Users/user/Reach/docs/PAYMENTS_IMPLEMENTATION_PLAN.md) *(historical, superseded)*,
> [`FRONTEND_BACKEND_GAPS_HANDOFF.md`](file:///c:/Users/user/Reach/docs/FRONTEND_BACKEND_GAPS_HANDOFF.md),
> [`CHANGELOG_feat_fossapay_payments.md`](file:///c:/Users/user/Reach/CHANGELOG_feat_fossapay_payments.md)

---

## Phase 0 — Wallet infrastructure & context

- [ ] **0.1** Create a new `SolanaWalletContext` (or repurpose [`WalletContext.tsx`](file:///c:/Users/user/Reach/frontend/reach/context/WalletContext.tsx)) to support Phantom, Solflare and Backpack via `@solana/wallet-adapter-react`.
  - Expose: `publicKey`, `connected`, `signTransaction`, `disconnect`.
  - Configurable cluster (devnet / mainnet-beta) matching the backend's `REACH_SOLANA_RPC_URL`.
- [ ] **0.2** Implement the `signPreparedTransaction` helper (§5 of the handoff):
  - Deserialise base64 → legacy `Transaction`, call `signTransaction`, re-serialise to base64.
  - Do **not** alter the fee payer, blockhash, or accounts.
  - Handle user rejection (stay on current step, never call submit).
  - Handle expired blockhash (re-call prepare, sign the new tx).
- [ ] **0.3** Call `PUT /users/me/onchain-address` when the wallet is first connected and the user has no `onchain_address` on their profile.
- [ ] **0.4** Add a `formatUsdc(units: number)` display helper: `(units / 1_000_000).toFixed(6) + " USDC"`.
- [ ] **0.5** Surface the `payer_type` field from `JobResponse` (`"wallet"` | `"custodial"`) and branch all payment UI on it.

---

## Phase 1 — Client-side escrow funding (wallet path)

- [ ] **1.1** In the job creation flow, after `POST /jobs` returns `pending_funding`:
  - If `payer_type === "wallet"`: show **"Fund escrow"** CTA.
  - Call `POST /jobs/{id}/onchain/fund` with the USDC amount.
  - If `already_done === true`: refresh job state and stop.
  - Otherwise: prompt wallet to sign the `create_task` transaction.
  - Submit via `POST /jobs/{id}/onchain/fund/submit`.
  - On success: job becomes `open` / `funded` / `Open`.
- [ ] **1.2** If `payer_type === "custodial"`: keep using the existing fiat collection flow (`POST /payments/jobs/{id}/collection`).
- [ ] **1.3** Never show wallet prepare endpoints for custodial jobs, and never show relayer accept/release buttons for wallet jobs.

---

## Phase 2 — Provider apply (on-chain, wallet path)

- [ ] **2.1** When a provider applies to a wallet-funded job:
  - Call `POST /jobs/{id}/onchain/apply` with `{ proposal_text, proposed_price }`.
  - Prompt the provider's wallet to sign the returned `apply` transaction.
  - Submit via `POST /jobs/{id}/onchain/apply/submit`.
- [ ] **2.2** Ensure the provider has called `PUT /users/me/onchain-address` before applying.
- [ ] **2.3** For custodial jobs, keep using the existing DB-only application endpoint.

---

## Phase 3 — Client accepts applicant (on-chain, wallet path)

> [!IMPORTANT]
> **This phase includes the specific TODO for [`page.tsx`](file:///c:/Users/user/Reach/frontend/reach/app/(secondary)/requests/[id]/page.tsx).**

- [ ] **3.1** ⭐ **Reinstate `accountId` and wallet selector context in [`app/(secondary)/requests/[id]/page.tsx`](file:///c:/Users/user/Reach/frontend/reach/app/(secondary)/requests/[id]/page.tsx#L152-L203).**
  - The current `confirmAccept` function (lines 177–203) uses `getWalletSelector()` and reads `state.accounts.find(a => a.active)?.accountId` as a NEAR-era workaround. The `useWallet()` import and `accountId` destructure are commented out on lines 17 and 47.
  - **Replace with:**
    1. Import and use the new `SolanaWalletContext` to get `publicKey` and `signTransaction`.
    2. Branch on `job.payer_type`:
       - **`"wallet"`**: call `POST /jobs/applications/{application_id}/onchain/accept` (no body), sign the returned transaction with the client's Solana wallet, then submit via `POST /jobs/applications/{application_id}/onchain/accept/submit`.
       - **`"custodial"`**: keep calling `updateApplicationStatus(id, { status: "accepted" })` (the relayer handles the on-chain accept).
    3. Remove the dead NEAR `getWalletSelector()` / `getNearApplicationId` / `acceptApplicationOnChain` imports and calls.
    4. Remove the `near_task_id` / `near_application_id` guard — replace it with the `payer_type` branch.
    5. On wallet rejection or chain failure: stay on the current step, show a toast, do **not** call submit.
    6. On success: refresh job + applications state.

- [ ] **3.2** Update `AcceptApplicationModal` to show the USDC escrow amount (from `GET /payments/jobs/{id}` → `intent.usdc_amount` or the prepare response) instead of `job.budget` for wallet jobs.
- [ ] **3.3** Update the `CompleteJobSheet` similarly — show USDC amounts for wallet jobs, naira for custodial.

---

## Phase 4 — Provider completes task (on-chain, wallet path)

- [ ] **4.1** When the accepted provider marks the job complete:
  - Call `POST /jobs/{id}/onchain/complete` (no body).
  - Sign the `complete_task` transaction with the provider's wallet.
  - Submit via `POST /jobs/{id}/onchain/complete/submit`.
  - On success: `onchain_status` → `AwaitingApproval`, `worker_completed` → `true`.
- [ ] **4.2** For custodial jobs, keep the existing completion flow.

---

## Phase 5 — Client confirms completion & releases escrow

- [ ] **5.1** After the provider completes (`worker_completed = true`, `onchain_status = "AwaitingApproval"`):
  - Show **"Confirm completion"** to the client.
  - Call `PATCH /jobs/{id}/completion` (no body) to set `client_completed = true`.
- [ ] **5.2** After both flags are set, show **"Release payment"**:
  - Call `POST /jobs/{id}/onchain/release` (no body).
  - Sign the `approve_work` transaction with the client's wallet.
  - Submit via `POST /jobs/{id}/onchain/release/submit`.
  - On success: `status` → `completed`, `onchain_status` → `Completed`.
- [ ] **5.3** For custodial jobs: call `POST /payments/jobs/{id}/release` (relayer signs).

---

## Phase 6 — UI state map & display

- [ ] **6.1** Map all backend states to UI according to §6 of the handoff:

  | Backend state | UI |
  |---|---|
  | `pending_funding` + `funding_status = pending` | Show "Fund escrow" |
  | `open` + `payer_type = wallet` | "Escrow funded" — providers can apply |
  | Application `pending` | "Application submitted" |
  | `in_progress` | "Work in progress" |
  | `onchain_status = AwaitingApproval` + `worker_completed` | "Provider completed; confirm and release" |
  | `client_completed = true`, not released | "Release payment" |
  | `status = completed` | "Paid" |

- [ ] **6.2** **Stop using `job.budget` as the USDC amount.** Use:
  - Fund prepare response: `amount_units`, `escrow_units`, `creation_fee_units`.
  - `GET /payments/jobs/{id}`: `intent.usdc_amount`.
  - `GET /jobs/{id}/onchain`: `labor_fee` / `creator_locked_balance`.
- [ ] **6.3** Show the on-chain state badge (optional): `GET /jobs/{id}/onchain`.

---

## Phase 7 — Error handling & edge cases

- [ ] **7.1** Handle all error codes per §8 of the handoff:
  - `400` invalid signed transaction → re-prepare and sign again.
  - `400` wallet missing → redirect to wallet setup / `PUT /users/me/onchain-address`.
  - `409` not enough USDC → show required amount.
  - `409` wrong state → refresh job.
  - `409` payment on another rail → surface the conflict.
  - `503` relayer/RPC unavailable → retry later.
  - `502` chain submission failed → check `ChainTransactionResponse.error`, re-prepare.
- [ ] **7.2** Respect `already_done = true` — refresh and stop; do not sign a second transaction.
- [ ] **7.3** Never silently swallow a wallet rejection or chain failure.
- [ ] **7.4** Guard against wrong Solana cluster (wallet + backend + relayer must agree).

---

## Phase 8 — Backend gap items (non-wallet)

- [ ] **8.1** **Categories**: fetch from `GET /categories`; do not send fallback category IDs to the API.
- [ ] **8.2** **Signup email**: show "check your email" after signup; offer resend; handle `503` from resend.
- [ ] **8.3** **Jobs feed**: `GET /jobs` now only returns `open` + `funded` jobs. Use `GET /jobs/me` for the poster's drafts/history.
- [ ] **8.4** **Service search**: add `q`, `limit`, `offset` to service search; use server-side `GET /services` / `GET /services/nearby`.
- [ ] **8.5** **Service create/response contract**: align `createService` to send `business_id`, `starting_price`, `category_id`, `latitude`, `longitude`, `location_name` (not `min_price`/`max_price`).
- [ ] **8.6** **Provider payouts UI**: wire up `GET /payouts/me`, `GET /payouts/banks`, `POST /payouts/banks/resolve`, `POST /payments/offramp`. Show the resolved account name before confirming.

---

## Phase 9 — Security & "must not do" checklist

- [ ] **9.1** Never send private keys or seed phrases to the backend.
- [ ] **9.2** Never use custodial accept/release endpoints for a `wallet` job (returns `409`).
- [ ] **9.3** Never use `PATCH /jobs/{id}/link-chain` for new funding — use `/onchain/fund/submit`.
- [ ] **9.4** Never treat `job.budget` as USDC.
- [ ] **9.5** Never assume the UI can mark the job completed before `approve_work` confirms.

---

## Phase 10 — Testing

- [ ] **10.1** Wallet not connected → prompt connection; no backend call.
- [ ] **10.2** Wallet connected, no `onchain_address` → save it first.
- [ ] **10.3** Client wallet has no USDC → prepare returns `409` with the required amount.
- [ ] **10.4** Client wallet has no SOL → `create_task` submit fails → show chain error.
- [ ] **10.5** User rejects wallet prompt → stay on step, no submit.
- [ ] **10.6** Double-click submit → backend is idempotent; refresh and stop.
- [ ] **10.7** Provider uses wallet A to apply, then wallet B to complete → backend rejects.
- [ ] **10.8** Release before `PATCH /completion` → `409` → show "confirm completion first".
- [ ] **10.9** Release on custodial job → use `POST /payments/jobs/{id}/release`, not wallet endpoint.
- [ ] **10.10** Full devnet E2E: fund → apply → accept → complete → confirm → release → provider balance increases.

