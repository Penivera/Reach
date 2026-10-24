# Reach crypto-only runbook (USDC on Solana)

Status: **staging run pending**. This runbook covers the crypto-only milestone:
USDC escrow on Solana, provider-signed `apply` / `complete_task`, and two
funding models: a wallet-funded escrow where the client signs `create_task` /
`accept` / `approve_work`, and a custodial escrow where the relayer signs those
instructions from a manually pre-funded treasury. Naira collection, naira
cash-out, and the full legal/on-ramp work are out of scope.

The backend is the only component in scope here. The frontend wallet UX is
owned by the frontend workstream; the API contract it needs is in
`docs/REACH_MODEL1_PAYMENTS_PLAN.md` §3a.

## 1. What must be true before you start

- The Anchor program is deployed at `REACH_PROGRAM_ID` and its IDL is at
  `sol-contract/idl.json`.
- You have a Solana RPC endpoint for the target cluster (devnet or mainnet).
- The relayer has a keypair with:
  - enough SOL to pay transaction fees and create token accounts;
  - enough USDC in its associated token account to lock escrows.
- Postgres with PostGIS is reachable.
- The API is running with the same `REACH_*` settings as the relayer.

> **Crypto rail caveat:** `POST /payments/jobs/{id}/collection?rail=crypto`
> currently asks Obiex for a per-task USDC deposit address via
> `POST /addresses/broker`. This is Obiex's **Collections** business API; it
> does **not** use the fiat `POST /collections` endpoint, but Obiex's public
> docs place deposit addresses under Collections and describe them as
> “associated with your business.” It is not yet confirmed whether a standard
> business API key can call `/addresses/broker` without the Business
> Collections enablement. If Obiex is not configured, fund the relayer's ATA
> manually (§5) and use the internal `fund_task_escrow` path (or wait for the
> crypto rail to be decoupled from Obiex). The on-chain lifecycle itself does
> not depend on Obiex.

## 2. Environment

Copy `backend/.env.example` to `backend/.env` and set at least:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/work_near

# Solana (mainnet example; for devnet change the RPC and the mint together)
REACH_SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
REACH_PROGRAM_ID=5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY
REACH_STABLE_MINT=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
REACH_RELAYER_SECRET_KEY=<base58 secret key>
REACH_RELAYER_CONFIRM_TIMEOUT=60
REACH_MIN_ESCROW_UNITS=1000000
REACH_CREATION_FEE_BPS=250
REACH_APPLICATION_TTL_SECONDS=604800

# Treasury float, in USDC base units (6 decimals).
REACH_TREASURY_TARGET_UNITS=500000000
REACH_TREASURY_MIN_WITHDRAWAL_UNITS=10000000

# Crypto-only milestone: keep fiat rails and naira cash-out off.
FOSSAPAY_ENABLED=false
PAYMENT_PROVIDER=fake
OBiex_ENABLED=false
REACH_OFFRAMP_ENABLED=false
```

Notes:

- `REACH_STABLE_MINT` is mainnet USDC by default. On devnet, set the devnet
  USDC mint instead.
- `REACH_RELAYER_SECRET_KEY` is a base58 Solana secret key. Never commit it.
- `REACH_MIN_ESCROW_UNITS` and the treasury amounts are **base units**, not
  whole USDC.

## 3. Database migration

From `backend/`:

```bash
source venv/bin/activate
alembic upgrade head
alembic current
```

`alembic current` should print `f1a2b3c4d5e6 (head)`. If the connection is
refused, start Postgres first (`docker compose up -d postgres` in the repo
root) or point `DATABASE_URL` at a reachable database, then rerun.

The Model 1 migrations end at `f1a2b3c4d5e6` (off-ramp). The provider-signed
lifecycle itself does **not** add a migration: it derives the application PDA
from the provider's saved `users.onchain_address` and stores signatures in
`chain_transactions`.

Verify the expected columns exist:

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'jobs'
  AND column_name IN ('funding_status', 'payer_type', 'onchain_status');
```

## 4. Relayer identity and ATA

Print the relayer address, its USDC associated token account (ATA), and the
current balance:

```bash
cd backend
source venv/bin/activate
python - <<'PY'
import asyncio

from dotenv import load_dotenv

load_dotenv()

from core.relayer import relayer_from_env

async def main():
    relayer = relayer_from_env()
    ata = await relayer.token_account_address(relayer.address)
    print("relayer:", relayer.address)
    print("usdc ata:", ata)
    print("usdc units:", await relayer.token_balance())

asyncio.run(main())
PY
```

Fund the relayer with SOL first. Then send USDC to the printed ATA. The ATA may
not exist yet; `spl-token create-account <MINT>` (with the relayer as payer) or
a wallet transfer to the owner address will create it. The backend also creates
a provider's ATA at release time if it does not exist.

## 5. Manual treasury pre-fund (acceptable for this milestone)

There is no production on-ramp in scope yet. For staging:

1. Send USDC to the relayer ATA from a wallet or exchange.
2. Confirm the balance with the script in §4.
3. Keep enough float for the largest test escrow **plus** the creation fee.
   The backend scales the escrow down to leave room for
   `REACH_CREATION_FEE_BPS`.
4. Do not call `POST /payments/treasury/top-up` unless Obiex is configured; it
   is the automated Obiex → Solana path.

Recommended staging float: 50–100 USDC, which covers many small escrows and
leaves room for failed-test cleanup.

To lock an escrow for an existing job without a payment webhook (the manual
path while the crypto rail is still coupled to Obiex):

```bash
cd backend
source venv/bin/activate
python - <<'PY'
import asyncio

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import select

from DB.database import AsyncSessionLocal
from core import settings
from models import Job
from services.chain import fund_task_escrow

JOB_ID = 123
FUNDED_UNITS = 5_000_000  # 5 USDC in base units

async def main():
    async with AsyncSessionLocal() as db:
        job = (
            await db.execute(select(Job).where(Job.id == JOB_ID))
        ).scalar_one()
        tx = await fund_task_escrow(
            db,
            job,
            funded_units=FUNDED_UNITS,
            creation_fee_bps=settings.REACH_CREATION_FEE_BPS,
            tag=(job.title or "")[:30],
            desc=(job.description or "")[:200],
        )
        await db.refresh(job)
        print(tx.signature, job.status, job.funding_status, job.onchain_task_id)

asyncio.run(main())
PY
```

This is idempotent on `create-task-<job_id>`; do not run it twice for the same
job.

## 5a. Direct wallet-funded escrow (client signs)

This is the non-custodial path. The client's wallet becomes the on-chain
creator, so the client signs `create_task`, `accept` and `approve_work`. The
relayer does **not** need USDC for the escrow; it only needs SOL to create the
client and provider token accounts and to read/submit transactions.

Client wallet requirements:

- USDC in its associated token account, at least `escrow + creation fee`;
- SOL for the `create_task` transaction fee and the task/vault rent.

Steps:

1. `PUT /users/me/onchain-address` with the client's wallet address.
2. `POST /jobs/{id}/onchain/fund` with `{ "usdc_amount": "5.000000" }`.
   The response contains an unsigned legacy transaction, `amount_units`,
   `escrow_units` and `creation_fee_units`.
3. Sign the transaction in Phantom/Solflare/Backpack and send the base64 bytes
   to `POST /jobs/{id}/onchain/fund/submit`.
4. The backend verifies the signed bytes, submits `create_task`, reads the task
   back, and marks the job `FUNDED` / `OPEN`.
5. The provider applies with the existing `POST /jobs/{id}/onchain/apply` and
   `/apply/submit`.
6. The client accepts with `POST /jobs/applications/{id}/onchain/accept`, signs,
   and submits to `/accept/submit`.
7. The provider completes with the existing `POST /jobs/{id}/onchain/complete`
   and `/complete/submit`.
8. The client records completion with `PATCH /jobs/{id}/completion`.
9. The client releases with `POST /jobs/{id}/onchain/release`, signs, and
   submits to `/release/submit`. The provider receives the USDC in its token
   account.
10. `GET /jobs/{id}/onchain` returns the decoded task state at any point.

The older `PATCH /jobs/{id}/link-chain` endpoint is a verified reconciliation
fallback; new clients should use the fund/submit endpoints.

## 6. Staging smoke test

Use two users: a **poster** and a **provider**. Authenticate each with the
normal session cookie flow and keep separate cookie jars.

1. **Provider saves a payout wallet.**
   ```bash
   curl -X PUT "$API/users/me/onchain-address" \
     -H 'Content-Type: application/json' \
     -b provider.cookies \
     -d '{"onchain_address":"<provider Solana pubkey>"}'
   ```
   This must be the same wallet the provider will sign with. Release rejects a
   different address.

2. **Poster creates and funds a job.**
   ```bash
   curl -X POST "$API/jobs" -H 'Content-Type: application/json' -b poster.cookies \
     -d '{"title":"Staging sink","description":"Fix it","budget":5000,
          "category_id":1,"latitude":6.5,"longitude":3.3,
          "location_name":"Lagos"}'
   ```
   The job starts in `pending_funding`. Fund it through the crypto rail (or
   the manual path in §1), then confirm:
   ```bash
   curl "$API/payments/jobs/<job_id>" -b poster.cookies
   ```
   Wait for `funding_status == "funded"` and `status == "open"`.

3. **Provider applies on-chain.**
   ```bash
   curl -X POST "$API/jobs/<job_id>/onchain/apply" \
     -H 'Content-Type: application/json' -b provider.cookies \
     -d '{"proposal_text":"I can do it","proposed_price":5000}'
   ```
   The response contains `transaction` (base64 legacy transaction) or
   `already_done: true`. Sign `transaction` with the provider wallet without
   modifying it, then:
   ```bash
   curl -X POST "$API/jobs/<job_id>/onchain/apply/submit" \
     -H 'Content-Type: application/json' -b provider.cookies \
     -d '{"signed_transaction":"<base64>"}'
   ```
   Check `chain_transactions` and that the application PDA exists on-chain.

4. **Poster accepts.**
   ```bash
   curl -X PATCH "$API/jobs/applications/<application_id>/status" \
     -H 'Content-Type: application/json' -b poster.cookies \
     -d '{"status":"accepted"}'
   ```
   The backend signs `accept` with the relayer because the custodial escrow's
   creator is the relayer. The job moves to `in_progress`.

5. **Provider completes on-chain.**
   ```bash
   curl -X POST "$API/jobs/<job_id>/onchain/complete" -b provider.cookies
   # sign the returned transaction with the provider wallet
   curl -X POST "$API/jobs/<job_id>/onchain/complete/submit" \
     -H 'Content-Type: application/json' -b provider.cookies \
     -d '{"signed_transaction":"<base64>"}'
   ```
   Verify the task is `AwaitingApproval` and `jobs.worker_completed = true`.

6. **Poster signs off and releases.**
   ```bash
   curl -X PATCH "$API/jobs/<job_id>/completion" -b poster.cookies
   curl -X POST "$API/payments/jobs/<job_id>/release" -b poster.cookies
   ```
   Release requires both `client_completed` and `worker_completed`. The relayer
   creates the provider ATA if needed, signs `approve_work`, and the provider's
   USDC balance increases. The job becomes `completed`.

7. **Confirm the ledger.**
   ```bash
   curl "$API/payments/jobs/<job_id>/transactions" -b poster.cookies
   ```
   Expected kinds: `apply`, `accept_application`, `complete`, `approve_work`.

## 7. Failure handling

| Symptom | Meaning | Action |
|---|---|---|
| `400` "Add a Solana payout address" | `users.onchain_address` is empty | Save the provider wallet first. |
| `409` "not open for applications on-chain yet" | Job is not `funded`/`open` | Wait for the escrow to be locked. |
| `400` "signed transaction does not match" | Wallet modified the transaction, wrong wallet, or wrong cluster | Re-prepare and sign the exact bytes. |
| `400` "fee payer must be the provider's wallet" | Wallet substituted its own fee payer | Use the wallet saved as `onchain_address`. |
| `409` "connected wallet is not the provider" | `complete_task` signed by a different wallet than the one accepted | Use the application wallet. |
| `400` "Both the creator and the provider must confirm" | Release before both sides finished | Complete both steps. |
| `400` "provider has not added a Solana address" | Payout wallet missing at release | Provider must save it. |
| `502`/`503` relayer errors | RPC/keypair/configuration | Check `REACH_SOLANA_RPC_URL`, secret key, SOL balance, program id. |

A failed transaction is written to `chain_transactions` with status `failed`.
Nothing in the job row is marked complete on failure.

## 8. Operational checks

- **RPC health:** the API and relayer use the same `REACH_SOLANA_RPC_URL`.
- **SOL balance:** a drained relayer cannot create accounts or submit.
- **USDC float:** watch the relayer ATA; a short float leaves jobs in
  `pending_funding`.
- **Idempotency:** `apply`, `complete_task`, `accept` and `approve_work` all
  use `chain_transactions.idempotency_key`. Do not delete those rows to "retry"
  a transaction; fix the chain state or add a new key deliberately.
- **Escrow creator:** the signer of `accept` and `approve_work` must match the
  on-chain creator. For a custodial escrow that is the relayer; for a
  wallet-funded escrow it is the client. Calling the relayer endpoints on a
  wallet-funded escrow returns `409` and points at the client prepare
  endpoints.
- **Application expiry:** `REACH_APPLICATION_TTL_SECONDS` (default 7 days) is
  written into the application account as `expires_at`. The program records it
  but does not enforce it yet, so expiry is informational for this milestone.

## 9. Known limitations for this milestone

- The direct wallet flow is backend-complete; the frontend wallet UI is owned
  by the frontend workstream and is still outstanding.
- The custodial crypto deposit address is still issued through Obiex; a
  standalone USDC deposit path for the custodial rail is future work. The
  direct wallet flow does not use Obiex.
- Naira collection and naira cash-out are disabled.
- `provide_collateral`, `cancel_task` and `raise_dispute` are not exposed by
  the API yet. A wallet-funded refund/cancellation therefore needs a future
  client-signed `cancel_task`.
- The job still carries the existing naira `budget` as a reference; a proper
  USDC job price field is a later schema cleanup. The actual USDC amount is
  stored on the wallet payment intent and on the on-chain task.
- There is no background reconciler; the ops team must check
  `chain_transactions` and the relayer balance during staging.
- Manual treasury pre-funding is expected for the custodial path until the
  Obiex/USDC flow and the legal/on-ramp work are complete.
