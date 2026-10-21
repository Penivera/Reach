> **Superseded.** This document describes the pay-after-acceptance fiat
> flow (FossaPay checkout after an applicant is accepted, a naira payout with a
> 5% commission, and an escrow ledger in Postgres). Model 1 replaced it: the
> escrow is locked on Solana when the task is created, the Anchor program is
> the settlement layer, and settlement is the program's `approve_work`.
>
> See `docs/REACH_MODEL1_PAYMENTS_PLAN.md` for the current design and
> `reach_flows_and_architecture_documentation.md` for the architecture.

# Payments Handoff

Companion to `PAYMENTS_IMPLEMENTATION_PLAN.md`. This file is the working document: what is already built, what the frontend has to do, what is still missing on the backend, and the full reference for the new endpoints.

- Plan (design + rationale): `docs/PAYMENTS_IMPLEMENTATION_PLAN.md`
- Branch: `feat/fossapay-payments`

---

## 1. Where the backend is today

### Working flow (jobs only)

```
signup ─► email verification ─► login
                              └─► payment profile (required)
                                    └─► FossaPay customer + NGN wallet created
                              └─► poster accepts an applicant  → job = awaiting_payment
                              └─► poster creates a checkout     → bank transfer details
                              └─► customer pays the exact amount
                              └─► webhook: provider lookup      → job = in_progress
                              └─► both parties confirm done
                              └─► release                       → provider wallet paid (5% fee)
```

### What is built

| Area | Status |
|---|---|
| Payment profile + FossaPay customer/wallet provisioning | Done |
| Job checkout via FossaPay `POST /checkouts` | Done |
| Webhook handling with provider verification | Done |
| Payout release to the provider's FossaPay wallet | Done |
| 5% commission, ₦1,000 minimum | Done |
| Webhook hardening (exact raw signature, provider lookup, dedupe) | Done |
| Tests (29, no database required) | Done |

### What is not built

Escrow ledger, refunds, disputes, KYC/limits, auto-release cron, reconciliation, services flow, product orders, provider withdrawal path, admin tooling.

---

## 2. Frontend work

Nothing in the frontend has been changed. All of this is still to do.

### 2.1 The one rule

**The browser never decides that money moved.** Only the backend state does:

- `profile_completed` / `can_pay` from `GET /payments/profile`
- `status` from `GET /payments/jobs/{job_id}`
- `status` from `GET /payments/jobs/{job_id}/payout`

Never infer payment from a bank receipt, a redirect, or a timer.

### 2.2 Money formatting

The backend returns **integer kobo** (`amount_kobo`, `amount_payable_kobo`, `commission_kobo`, `provider_payout_kobo`). Format in one place:

```ts
export const formatNaira = (kobo: number) =>
  `₦${(kobo / 100).toLocaleString("en-NG", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
```

Never do arithmetic on floats. If a price must be entered in naira, send `Math.round(naira * 100)` — and remember FossaPay checkouts only accept **whole naira** (backend rejects the rest with a 400).

### 2.3 New screens and states

#### A. Payment profile (new screen, required)

Trigger: after email verification / first login, call `GET /payments/profile`. If `profile_completed === false`, redirect to the payment-profile screen before the app shell. If `can_pay === false` but `profile_completed === true`, show a "finishing payment setup" state with a retry button.

Fields:

| Field | Source | Notes |
|---|---|---|
| First name | `first_name` (optional override) | One name, no spaces/digits |
| Last name | `last_name` (optional override) | One name, no spaces/digits |
| Phone number | `phone_number` (optional override) | Normalized to `+234…` by the backend |
| Middle name | `middle_name` | Optional |
| Date of birth | required | `YYYY-MM-DD`, must be 18+ |
| Address | required | Street address, not lat/lon |
| City | required | |
| Country | required | Defaults to `Nigeria` |

Submit → `PUT /payments/profile`. Response is the same state object; provisioning happens in the background, so poll `GET /payments/profile` until `provisioning.status === "provisioned"`.

#### B. Checkout / payment instructions (new screen)

Called from the job detail page when `job.status === "awaiting_payment"`.

1. `POST /payments/jobs/{job_id}/checkout` (job owner only).
2. Render the returned transfer details:
   - `amount_payable_kobo` (may include FossaPay's checkout fee, since the customer bears it)
   - `bank_name`, `account_name`, `account_number`
   - `expires_at` → countdown
3. Poll `GET /payments/jobs/{job_id}` every ~10s while `status === "pending"`. Stop on `paid`, `failed`, `expired`, `reversed`.
4. On `paid`, refresh the job — it moves to `in_progress`.

Copy to use: "Transfer the exact amount to the account below before the timer ends. The job starts once we confirm the payment."

#### C. Release (existing screen, new behaviour)

`CompleteJobSheet` currently only closes. Change it to:

- Worker marks complete → `PATCH /jobs/{job_id}/completion` (existing endpoint).
- Poster signs off → `PATCH /jobs/{job_id}/completion` → then `POST /payments/jobs/{job_id}/release`.
- Show the result from `GET /payments/jobs/{job_id}/payout`:
  - `processing` → "Payout on the way"
  - `completed` → "Paid ₦X"
  - `failed` / `reversed` → "Payout issue — support has been notified"

The release endpoint is idempotent, so a double tap is safe.

#### D. Provider earnings

Not built yet. When it lands, the source of truth is `GET /payments/jobs/{job_id}/payout` per job for now. A list endpoint (`GET /payouts/me`) is on the remaining list.

### 2.4 Status values the UI must handle

| Endpoint | Values |
|---|---|
| `GET /payments/profile` | `provisioning.status`: `pending`, `provisioned`, `failed` (no record = not started) |
| `GET /payments/jobs/{id}` | `status`: `pending`, `paid`, `failed`, `expired`, `reversed` |
| `GET /payments/jobs/{id}/payout` | `status`: `processing`, `completed`, `failed`, `reversed` |
| Job | `status`: `open`, `awaiting_payment`, `in_progress`, `completed`, `cancelled` |

`awaiting_payment` is new. The current job UI only knows `in_progress`, so it will need a branch.

### 2.5 Suggested frontend files

```
lib/payments.ts          typed wrappers for the endpoints below
utils/money.ts           kobo <-> naira formatting
hooks/usePaymentStatus.ts polling for a job payment
app/onboarding/payment-profile/page.tsx
app/payments/[jobId]/page.tsx   (or a sheet on the job page)
```

### 2.6 Do not touch

The NEAR integration (`lib/near/*`, `WalletContext`, wallet UI) belongs to another owner. It is not part of the fiat flow and should not be used to decide whether a payment succeeded. Leave it alone.

---

## 3. Backend work remaining

### P0 — before any live money

| # | Task | Why |
|---|---|---|
| 1 | Provide a PostGIS `DATABASE_URL`, run `alembic upgrade head` | Nothing is verifiable without a DB. Migrations `b7c1f2a9d4e6` → `e3f4a5b6c7d8` are written but unapplied |
| 2 | Live FossaPay key + public webhook URL, then capture a real event and confirm the raw-`data` signature extraction matches their signing | The signature format is the highest-risk unknown |
| 3 | Enforce whole-naira, minimum, and per-tier maximum **at job creation**, not at checkout | Right now a job can be accepted and then fail to pay |
| 4 | KYC: provider NIN/BVN before payout **and** a buyer path for amounts above the unverified cap | Limits are useless without verification |
| 5 | Decide release-time limit behaviour (queue to next day vs hold) and enforce the daily payout cap | Undefined today |
| 6 | Reconciliation job: master wallet balance ≥ escrow + provider payable + refund payable, with alerts | No way to detect drift or loss |
| 7 | Payout failure alerts + a manual review queue | `payout.failed` currently just sits in the DB |
| 8 | Fix the dead ₦1m dual-approval threshold (lower it, aggregate it, or drop it) | Cannot trigger under a ₦200k cap |
| 9 | Checkout-fee refund policy, in code and in the terms | Currently undefined |
| 10 | Provider withdrawal path (wallet credit → bank) and wallet refunds for payers | Wallet money is not spendable today |
| 11 | Legacy job policy — paying at sign-off after the work is done is not escrow, and there is no "poster never pays" path | |
| 12 | Privacy: redact PII from provider calls/raw payloads, encrypt bank account numbers with a keyed hash, NDPA consent/retention | `payment_profiles` already holds DOB and address |
| 13 | Infra: a worker/scheduler with `SKIP LOCKED` and a single scheduler; no sleeping instance for webhooks | Needed for cron, batch, retries |

### P1 — next milestone

- **Services flow**: fund at acceptance, pay before start, requester confirms, release.
- **Orders flow**: `Product`/`Order` models, checkout, seller fulfilment, buyer confirmation, longer auto-release window with delivery proof.
- **Disputes**: evidence + 48h response, admin resolution, split release/refund, and a dispute that pauses the auto-release timer.
- **Refunds**: admin case-by-case, wallet first then bank, fee deducted on bank refunds.
- **Auto-release**: 3-day cron after worker completion, plus the order-specific longer window.
- **Escrow + ledger**: only when refunds/splits exist. If built, follow the plan's corrected rules — many payment intents per escrow, partial unique index on active statuses, `released` means the obligation moved to `provider_payable`, per-user ledger dimensions, append-only rows, a DB-level balance trigger, and a suspense account for duplicates/overpayments.
- **Expiry policy**: grace period after the 30-minute checkout window, and a cooldown for repeated accept-and-expire.

### P2 — later

- `admin_approvals`, `audit_logs`, payment `notifications`, create-request idempotency tables.
- Payout fraud controls: KYC name match, OTP/re-auth on bank changes, cooling-off period.
- Buyer KYC economics, tax/VAT on the commission, receipts and invoices.

---

## 4. Endpoint reference

Base URL: `/api` behind `NEXT_PUBLIC_API_URL`. All payment endpoints require the session cookie (`access_token`, httpOnly) and the `credentials: "include"` fetch option.

### `GET /payments/profile`

Returns the payment profile state. Works before a profile exists.

```json
{
  "profile_completed": true,
  "can_pay": true,
  "missing_fields": [],
  "profile": {
    "id": 1,
    "user_id": 42,
    "middle_name": "Ngozi",
    "date_of_birth": "1990-08-15",
    "address": "12 Example Street",
    "city": "Lagos",
    "country": "Nigeria"
  },
  "provisioning": {
    "status": "provisioned",
    "provider_customer_id": "11111111-1111-4111-8111-111111111111",
    "wallet_id": "33333333-3333-4333-8333-333333333333",
    "account_number": "9710000000",
    "account_name": "ADA OKORO",
    "bank_name": "Example Bank",
    "bank_code": "000000",
    "last_error": null
  }
}
```

`missing_fields` lists what the UI should prompt for: `date_of_birth`, `address`, `city`, `country`, plus `first_name` / `last_name` / `phone_number` when the stored values cannot be sent to FossaPay.

### `PUT /payments/profile`

Create or update the profile and start provisioning in the background.

```json
{
  "first_name": "Ada",
  "last_name": "Okoro",
  "phone_number": "08031234567",
  "middle_name": "Ngozi",
  "date_of_birth": "1990-08-15",
  "address": "12 Example Street",
  "city": "Lagos",
  "country": "Nigeria"
}
```

`first_name`, `last_name` and `phone_number` are optional corrections of the signup values. Response is the state object above, with `provisioning.status = "pending"`.

Errors: `422` invalid name/phone/DOB, `400` identity change after provisioning.

### `POST /payments/profile/provision`

Retries provisioning after a failure. Same response shape. `400` if no profile exists yet.

### `POST /payments/jobs/{job_id}/checkout`

Job owner only. Creates a FossaPay checkout for the accepted application.

- Job must be `awaiting_payment`.
- The poster's payment profile must be provisioned.
- Amount = accepted application's `proposed_price`, whole naira, at least ₦1,000.
- Idempotent while a pending checkout is still alive.

```json
{
  "id": 12,
  "job_id": 5,
  "reference": "job-5-a1b2c3d4e5f6",
  "amount_kobo": 1000000,
  "amount_payable_kobo": 1008000,
  "status": "pending",
  "provider_checkout_id": "35f5f6fb-0c8d-4e96-ba4a-c04750724ff6",
  "bank_name": "Sterling Bank",
  "account_name": "FOSSAPAY CHECKOUT",
  "account_number": "9541382701",
  "expires_at": "2026-09-11T10:30:00Z",
  "paid_at": null
}
```

Errors: `400` wrong job state / no accepted applicant / profile not ready / amount not whole naira / below minimum, `403` not the owner, `502` FossaPay error, `503` FossaPay not configured.

### `GET /payments/jobs/{job_id}`

Latest payment intent for a job. Visible to the job owner and the accepted applicant. `404` if there is none.

### `POST /payments/jobs/{job_id}/release`

Job owner only. Releases the funded job to the provider.

- Both parties must have confirmed completion (`client_completed` and `worker_completed`).
- The payment intent must be `paid`.
- The provider must have a provisioned FossaPay wallet.
- 5% commission, rounded down to a whole naira.
- Idempotent: an existing payout is returned unchanged.

```json
{
  "id": 3,
  "payment_intent_id": 12,
  "reference": "payout-job-5-12",
  "amount_kobo": 1000000,
  "commission_kobo": 50000,
  "provider_payout_kobo": 950000,
  "status": "completed",
  "provider_payout_id": "a9af907d-965f-4ad8-9472-f437fc11df21",
  "failure_reason": null,
  "completed_at": "2026-09-11T12:05:10Z"
}
```

Errors: `400` not both parties confirmed / job not funded / provider wallet not ready, `403` not the owner, `502`/`503` FossaPay error.

### `GET /payments/jobs/{job_id}/payout`

The payout record for a job. `404` if there is none.

### `POST /webhooks/fossapay`

Called by FossaPay. No auth; verified by HMAC signature over the **exact raw `data` bytes** of the request body.

- Invalid signature → `401`, event stored as `rejected`.
- Unknown checkout/payout → `503` so FossaPay retries.
- Provider object is looked up (`GET /checkouts/{id}` / `GET /payouts/{id}`) before any state change.
- Duplicate events are ignored.

Configure the public URL and secret in the FossaPay dashboard, then set `FOSSAPAY_WEBHOOK_SECRET`.

---

## 5. Data model and migrations

| Migration | Adds |
|---|---|
| `b7c1f2a9d4e6` | `payment_profiles`, `fossapay_customers`, `provisioningstatus` enum |
| `c1d2e3f4a5b6` | `payment_intents`, `paymentstatus` enum, `jobstatus` gains `AWAITING_PAYMENT` |
| `d2e3f4a5b6c7` | `payouts`, `payoutstatus` enum, `fossapay_customers.bank_code` |
| `e3f4a5b6c7d8` | `webhook_events`, `webhookstatus` enum |

```bash
cd backend
alembic upgrade head
```

---

## 6. Environment

```bash
cd backend
cp .env.example .env
```

| Variable | Local | Production |
|---|---|---|
| `FOSSAPAY_ENABLED` | `false` | `true` |
| `PAYMENT_PROVIDER` | `fake` | `fossapay` |
| `FOSSAPAY_API_KEY` | empty | `fk_production_…` |
| `FOSSAPAY_WEBHOOK_SECRET` | any value | the dashboard value |
| `PLATFORM_FEE_BPS` | `500` (5%) | `500` |
| `MIN_ESCROW_KOBO` | `100000` (₦1,000) | `100000` |

FossaPay has **no sandbox**. `PAYMENT_PROVIDER=fake` keeps local runs free of live money.

---

## 7. Running the tests

```bash
cd backend
venv/bin/python -m unittest discover -s tests -v
```

29 tests, no database required:

- `test_payment_amounts.py` — kobo/naira conversion, commission rounding
- `test_payment_signatures.py` — exact raw `data` extraction, signature verification
- `test_payment_validation.py` — names, phone, date of birth
- `test_webhook_handler.py` — valid event, replay with a new `eventId`, changed `eventType`, invalid signature
- `test_webhook_flow.py` — provider checkout/payout sync, amount mismatch, replay, provider failure
- `test_release_flow.py` — commission split, both parties required, idempotent release, owner only
