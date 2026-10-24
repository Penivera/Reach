# Frontend handoff — wallet-funded escrow (USDC on Solana)

Status: **backend ready, frontend not implemented.** This document is the
frontend contract for a client who pays USDC from their own Solana wallet
directly into the task vault, and for the provider who receives the USDC when
the work is approved.

The frontend workstream owns the wallet UI. This document only describes the
API, the signing rules and the states the UI must show.

---

## 1. The two funding models

| | Wallet-funded (this document) | Custodial / naira (existing) |
|---|---|---|
| Who is the on-chain creator | The client's wallet | The Reach relayer |
| Who signs `create_task` | Client | Relayer |
| Who signs `accept` | Client | Relayer |
| Who signs `approve_work` | Client | Relayer |
| Who signs `apply` / `complete_task` | Provider | Provider |
| Source of USDC | Client's wallet | Reach treasury (naira on-ramp) |
| `job.payer_type` | `wallet` | `custodial` |

The frontend must branch on `job.payer_type`:

- `wallet` → use the prepare/sign/submit endpoints in this document.
- `custodial` → keep using the existing relayer endpoints
  (`PATCH /jobs/applications/{id}/status` and
  `POST /payments/jobs/{id}/release`).

A custodial client must never be shown the wallet prepare endpoints, and a
wallet client must never be shown the relayer accept/release buttons.

---

## 2. Roles and signatures

| Step | Handler | Signer | Instruction |
|---|---|---|---|
| Fund escrow | Client | Client wallet | `create_task` |
| Apply | Provider | Provider wallet | `apply` |
| Accept | Client | Client wallet | `accept` |
| Complete | Provider | Provider wallet | `complete_task` |
| Approve/release | Client | Client wallet | `approve_work` |

The backend never holds the client's or provider's private key. It prepares an
unsigned legacy transaction, verifies the signed bytes, then submits them.

---

## 3. Prerequisites

Client:

- Phantom, Solflare or Backpack connected.
- `PUT /users/me/onchain-address` called once with the client's wallet.
- USDC in the wallet's associated token account. The backend can create the
  ATA, but the client must fund it.
- SOL for the `create_task` transaction fee and the task/vault rent.

Provider:

- `PUT /users/me/onchain-address` called once with the provider's payout
  wallet.
- SOL for the `apply` and `complete_task` transaction fees.
- The provider's USDC token account can be absent; the backend creates it at
  release time.

Relayer/backend (not frontend work):

- `REACH_SOLANA_RPC_URL`
- `REACH_RELAYER_SECRET_KEY`
- SOL in the relayer wallet for ATA creation
- The Anchor program ID and USDC mint must match the cluster.

---

## 4. Happy path

### Step 0 — create the job (existing)

`POST /jobs` returns the job in `pending_funding`.

### Step 1 — save the client wallet

```http
PUT /users/me/onchain-address
Content-Type: application/json

{ "onchain_address": "<client wallet public key>" }
```

Response: `UserResponse` with `onchain_address` set.

### Step 2 — prepare the escrow transaction

```http
POST /jobs/{job_id}/onchain/fund
Content-Type: application/json

{ "usdc_amount": "5.000000" }
```

`usdc_amount` is the **total the client spends**: escrow + creation fee. It
supports at most 6 decimals.

Response:

```json
{
  "action": "create_task",
  "job_id": 123,
  "task_id": 123,
  "signer_address": "<client wallet>",
  "provider_address": null,
  "transaction": "<base64 legacy transaction>",
  "recent_blockhash": "<blockhash>",
  "expires_at": null,
  "amount_units": 5000000,
  "escrow_units": 4878048,
  "creation_fee_units": 121952,
  "already_done": false
}
```

If `already_done` is `true`, the escrow already exists. Refresh the job and
stop; do not sign.

### Step 3 — sign and submit the escrow

The client signs the base64 transaction with their wallet (see §5), then:

```http
POST /jobs/{job_id}/onchain/fund/submit
Content-Type: application/json

{ "signed_transaction": "<base64 signed transaction>" }
```

Success: a `ChainTransactionResponse` with `kind = "create_task"` and
`status = "confirmed"` or `"finalized"`. The job is now:

```json
{
  "status": "open",
  "funding_status": "funded",
  "payer_type": "wallet",
  "onchain_status": "Open"
}
```

### Step 4 — provider applies (existing provider flow)

The provider calls:

```http
POST /jobs/{job_id}/onchain/apply
Content-Type: application/json

{ "proposal_text": "...", "proposed_price": 5.0 }
```

The response contains the unsigned `apply` transaction and an `application`
object. The provider signs and calls:

```http
POST /jobs/{job_id}/onchain/apply/submit
Content-Type: application/json

{ "signed_transaction": "<base64>" }
```

The `application.id` in the prepare response is the id the client needs for
acceptance.

### Step 5 — client accepts the provider

```http
POST /jobs/applications/{application_id}/onchain/accept
```

No body. Response is the same prepare shape with `action = "accept"`,
`signer_address`, `provider_address` and the unsigned transaction.

Client signs, then:

```http
POST /jobs/applications/{application_id}/onchain/accept/submit
Content-Type: application/json

{ "signed_transaction": "<base64>" }
```

Success: the job moves to:

```json
{
  "status": "in_progress",
  "onchain_status": "InProgress"
}
```

The application becomes `accepted`; other pending applications are rejected.

### Step 6 — provider completes (existing provider flow)

```http
POST /jobs/{job_id}/onchain/complete
```

Provider signs, then:

```http
POST /jobs/{job_id}/onchain/complete/submit
Content-Type: application/json

{ "signed_transaction": "<base64>" }
```

Success: `onchain_status = "AwaitingApproval"` and
`worker_completed = true`.

### Step 7 — client confirms completion

```http
PATCH /jobs/{job_id}/completion
```

No body. The job owner sets `client_completed = true`. The provider branch of
this endpoint is only a DB mirror; providers should use the on-chain
`complete_task` flow.

The client must complete this step before release. The release endpoint
requires **both** `client_completed` and `worker_completed`.

### Step 8 — client releases the escrow

```http
POST /jobs/{job_id}/onchain/release
```

No body. The response contains the unsigned `approve_work` transaction.

Client signs, then:

```http
POST /jobs/{job_id}/onchain/release/submit
Content-Type: application/json

{ "signed_transaction": "<base64>" }
```

Success: the provider's USDC token account receives the escrow, and the job
becomes:

```json
{
  "status": "completed",
  "onchain_status": "Completed"
}
```

### Step 9 — read the on-chain state (optional)

```http
GET /jobs/{job_id}/onchain
```

Returns the decoded task:

```json
{
  "task_id": 123,
  "creator": "<client wallet>",
  "provider": "<provider wallet>",
  "status": "Open",
  "labor_fee": 4878048,
  "material_cost": 0,
  "creator_locked_balance": 4878048,
  "provider_locked_balance": null,
  "advanced_disbursed": false,
  "created_at": 1700000000,
  "updated_at": 1700000100
}
```

The job owner and the accepted provider can read it.

---

## 5. Signing helper

Use the legacy `Transaction` format. The backend prepares it; the wallet only
signs it.

```ts
import { Transaction } from "@solana/web3.js";

export async function signPreparedTransaction(
  wallet: { signTransaction: (tx: Transaction) => Promise<Transaction> },
  base64Transaction: string,
): Promise<string> {
  const transaction = Transaction.from(
    Buffer.from(base64Transaction, "base64"),
  );

  const signed = await wallet.signTransaction(transaction);
  return signed.serialize().toString("base64");
}
```

Rules:

- Use `signTransaction`, not `signAllTransactions`.
- Do **not** add instructions.
- Do **not** change the fee payer, blockhash or account list.
- Do **not** re-serialize with a different format.
- Handle the user rejecting the wallet prompt: stay on the current step and do
  not call submit.
- If the transaction fails with an expired blockhash, call the prepare
  endpoint again and sign the new transaction.

---

## 6. UI state map

Use `GET /jobs/{id}` and `GET /payments/jobs/{id}`.

| Backend state | UI |
|---|---|
| `status = pending_funding`, `funding_status = pending` | Show “Fund escrow” |
| `status = pending_funding`, wallet intent `pending` | Show “Continue wallet funding” or allow switching to a fiat rail |
| `status = open`, `payer_type = wallet` | Show “Escrow funded”; providers can apply |
| Application `pending` for the provider | Show “Application submitted” |
| `status = in_progress` | Show “Work in progress” |
| `onchain_status = AwaitingApproval`, `worker_completed = true` | Show “Provider completed; confirm and release” |
| `client_completed = true` but not released | Show “Release payment” |
| `status = completed` | Show “Paid”; provider has the USDC |

Do not use `job.budget` as the USDC amount. `job.budget` is the existing naira
reference. The USDC amount is in:

- the fund prepare response: `amount_units`, `escrow_units`,
  `creation_fee_units`;
- `GET /payments/jobs/{id}`: `intent.usdc_amount` (total spend);
- `GET /jobs/{id}/onchain`: `labor_fee` / `creator_locked_balance` (escrow).

---

## 7. Amounts

All USDC amounts are integer **base units** with 6 decimals.

```text
1 USDC = 1_000_000 units
```

Display helper:

```ts
export const formatUsdc = (units: number) =>
  `${(units / 1_000_000).toFixed(6)} USDC`;
```

The client pays `escrow_units + creation_fee_units`. The provider receives
`escrow_units`.

---

## 8. Errors, retries and idempotency

| Response | Meaning | UI action |
|---|---|---|
| `400` invalid signed transaction | Wrong signer, fee payer, instruction or tampered bytes | Re-prepare and sign again |
| `400` wallet missing/invalid | `PUT /users/me/onchain-address` not done | Send to wallet setup |
| `409` not enough USDC | Client wallet has less than escrow + fee | Show the required amount and how to fund |
| `409` wrong state | Task already funded/accepted/completed, or release before completion | Refresh `GET /jobs/{id}` |
| `409` “payment already open on another rail” | A pending fiat or wallet intent exists | Finish, cancel or switch only when allowed |
| `503` relayer/RPC unavailable | Backend cannot read/submit/create ATAs | Retry later |
| `502` chain submission failed | The transaction did not confirm | Check `ChainTransactionResponse.error`, then re-prepare if the state allows |

`already_done = true` means the previous action is already on-chain. Refresh
and stop; do not sign a second transaction.

A successful wallet prompt is **not** evidence that money moved. Only refresh
the backend after submit succeeds.

---

## 9. Endpoint reference

| Method | Path | Body | Auth/role | Response |
|---|---|---|---|---|
| `PUT` | `/users/me/onchain-address` | `{onchain_address}` | any user | `UserResponse` |
| `POST` | `/jobs/{id}/onchain/fund` | `{usdc_amount}` | job owner | `JobOnchainPrepareResponse` |
| `POST` | `/jobs/{id}/onchain/fund/submit` | `{signed_transaction}` | job owner | `ChainTransactionResponse` |
| `POST` | `/jobs/{id}/onchain/apply` | `{proposal_text, proposed_price}` | provider | `JobOnchainPrepareResponse` with `application` |
| `POST` | `/jobs/{id}/onchain/apply/submit` | `{signed_transaction}` | provider | `ChainTransactionResponse` |
| `POST` | `/jobs/applications/{application_id}/onchain/accept` | none | job owner | `JobOnchainPrepareResponse` |
| `POST` | `/jobs/applications/{application_id}/onchain/accept/submit` | `{signed_transaction}` | job owner | `ChainTransactionResponse` |
| `POST` | `/jobs/{id}/onchain/complete` | none | accepted provider | `JobOnchainPrepareResponse` |
| `POST` | `/jobs/{id}/onchain/complete/submit` | `{signed_transaction}` | accepted provider | `ChainTransactionResponse` |
| `PATCH` | `/jobs/{id}/completion` | none | job owner or accepted provider | `JobResponse` |
| `POST` | `/jobs/{id}/onchain/release` | none | job owner | `JobOnchainPrepareResponse` |
| `POST` | `/jobs/{id}/onchain/release/submit` | `{signed_transaction}` | job owner | `ChainTransactionResponse` |
| `GET` | `/jobs/{id}/onchain` | — | owner or accepted provider | `JobOnchainStateResponse` |
| `GET` | `/jobs/{id}` | — | participant | `JobResponse` |
| `GET` | `/payments/jobs/{id}` | — | participant | `FundingStateResponse` |

---

## 10. What the frontend must not do

- Do not send private keys or seed phrases to the backend.
- Do not use the custodial accept/release endpoints for a `wallet` job. They
  return `409` and point at the client-signed endpoints.
- Do not use `PATCH /jobs/{id}/link-chain` for new funding. It is a verified
  reconciliation fallback; new clients use `/onchain/fund/submit`.
- Do not treat `job.budget` as USDC.
- Do not assume the UI can mark the job completed before `approve_work`
  confirms.
- Do not silently swallow a wallet rejection or a chain failure.
- Do not let the user sign on the wrong cluster. The backend, relayer and
  wallet must all use the same Solana cluster and USDC mint.

---

## 11. Naira / custodial path (for context only)

The existing custodial flow remains:

```text
POST /payments/jobs/{id}/collection?rail=obiex_fiat|fossapay_checkout|crypto
  -> payment webhook
  -> relayer signs create_task from the treasury
  -> provider applies / completes
  -> client PATCH /jobs/{id}/completion
  -> POST /payments/jobs/{id}/release  (relayer signs approve_work)
  -> provider receives USDC
```

`payer_type` is `custodial`. The frontend should not show the wallet prepare
buttons for these jobs.

---

## 12. Frontend test checklist

- Wallet not connected → ask for connection; no backend call.
- Wallet connected but no `onchain_address` → save it first.
- Client wallet has no USDC → prepare returns `409` with the required amount.
- Client wallet has no SOL → `create_task` submit fails; show the chain error
  and ask for SOL.
- User rejects the wallet prompt → stay on the step, no submit.
- Double-click submit → the backend is idempotent; refresh and stop.
- Provider applies with wallet A, then tries to complete with wallet B → the
  backend rejects; keep the provider on wallet A.
- Release before `PATCH /completion` → `409`; show “confirm completion first”.
- Release on a `custodial` job → the frontend should call
  `POST /payments/jobs/{id}/release`, not the wallet endpoint.
- Full devnet run: fund → apply → accept → complete → client completion →
  release → provider balance increases.
```
