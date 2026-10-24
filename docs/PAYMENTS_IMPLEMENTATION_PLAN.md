> **Superseded.** This document describes the pay-after-acceptance fiat
> flow (FossaPay checkout after an applicant is accepted, a naira payout with a
> 5% commission, and an escrow ledger in Postgres). Model 1 replaced it: the
> escrow is locked on Solana when the task is created, the Anchor program is
> the settlement layer, and settlement is the program's `approve_work`.
>
> See `docs/REACH_MODEL1_PAYMENTS_PLAN.md` for the current design,
> `reach_flows_and_architecture_documentation.md` for the architecture, and
> `docs/REACH_NAIRA_OFFRAMP.md` for the provider naira cash-out.
>
> **Historical only:** the design, endpoints, and data model below describe
> the pre-Model-1 plan and are not the current implementation.

# Reach Payments — Fiat Escrow Implementation Plan

**Status:** historical — superseded by Model 1; the content below records the earlier FossaPay/Postgres-ledger plan only
**Owner:** Backend
**Scope:** Jobs/requests, service requests, product orders
**Provider:** FossaPay (NGN, production-only)
**Goal:** Add a production-grade fiat escrow system alongside the existing code: customers pay into escrow, funds are released to providers only after verified completion, and every movement is auditable and reconcilable. The existing NEAR/Solana code is **out of scope and will not be modified**.

**Also see:** `docs/PAYMENTS_HANDOFF.md` — what is built, what the frontend must do, what is still missing, and the endpoint reference.

---

## 1. Executive summary

Reach currently has a real NEAR escrow contract, but the app never funds it, never creates on-chain applications, and never releases funds. The job marketplace is a DB-only state machine; product checkout, orders, payouts, and disputes are mock UI.

**Scope boundary:** the NEAR/Solana contracts and the existing NEAR frontend integration belong to another owner. This plan treats them as read-only. Nothing under `near-contract/`, `sol-contract/`, `frontend/reach/lib/near/`, `frontend/reach/context/WalletContext.tsx`, or the NEAR wallet UI will be edited. The fiat layer is additive and lives beside the existing code.

### Confirmed decisions

| Decision | Choice |
|---|---|
| Custody | **Master wallet escrow** (FossaPay docs: customer funds → customer wallets; business funds → master wallet; no escrow/hold API). Legal review still required. |
| Checkout fee | Customer pays (`feeBearer=customer`) |
| Platform commission | **5% of the released amount**, deducted from the provider. Full refund = no commission; partial split = 5% of the provider's release share. Rounded down to the kobo. |
| Minimum escrow | **₦1,000**; platform absorbs any fee shortfall; provider net never below zero |
| FossaPay customers | **Created in an immediate payment-profile step after signup**, together with their NGN wallet. Signup itself stays lightweight. |
| Job funding | When the poster accepts an applicant |
| Service funding | After provider accepts, **before work starts** (pay-before-start) |
| Order funding | At checkout |
| Completion | Both parties; **3-day auto-release** after worker marks complete if poster is silent |
| Payouts | Wallet credit default, bank optional; wallet instant; bank instant only when both signed off, otherwise daily at **17:00 Africa/Lagos** |
| Payout fee | Provider pays (deducted from net) |
| Refunds | Admin case-by-case; wallet first (free), bank fallback (fee deducted) |
| Provider no-show | Admin review (one admin, 48h) |
| Duplicates/overpayments | Manual review for all |
| Partial/returns | Buyer and seller agree a split; admin fallback |
| KYC/limits | Providers KYC; **₦10,000/day unverified, ₦200,000/day verified**, applied to payouts and transaction size |
| Existing jobs | Escrow at poster sign-off; amount = accepted `proposed_price`, fallback `budget` |
| Stale escrow | **30 days** → admin review |
| Expiry | Jobs revert immediately to `OPEN`; services stay accepted with payment retry |
| Disputes | Evidence + 48h response; admin decides within 48h |
| Notifications | In-app + email + push |
| Admin actions | Single admin + audit; **dual approval above ₦1,000,000** |
| Rollout | Jobs first, then services, then orders |
| Chain code | Untouched |

### Implemented so far

- Payment profile + FossaPay customer/NGN wallet provisioning.
- Job acceptance now sets `AWAITING_PAYMENT` instead of `IN_PROGRESS`.
- `POST /payments/jobs/{job_id}/checkout` creates a FossaPay checkout.
- `GET /payments/jobs/{job_id}` returns the latest payment intent.
- `POST /webhooks/fossapay` verifies the exact raw `data` bytes, looks up the provider object before changing state, deduplicates on the business object, and stores rejected/failed events.
- `POST /payments/jobs/{job_id}/release` pays the provider's FossaPay wallet after both parties confirm completion, retaining 5% commission.
- `GET /payments/jobs/{job_id}/payout` returns the payout record.
- Payout webhooks update the payout status.
- **Not built yet:** full double-entry ledger, refunds, disputes, services/orders payments.

This plan makes **FossaPay the payment rail** and puts the escrow logic in the Reach backend:

```
Customer bank transfer
        │
        ▼
FossaPay Checkout  ──webhook──►  Reach backend
(30-minute virtual account)        │
                                   ├─ PaymentIntent (PAID)
                                   ├─ Escrow (FUNDED)
                                   └─ Double-entry ledger
                                            │
                          completion / dispute resolution
                                            │
                                            ▼
                                   FossaPay Master Wallet Payout
                                   (to provider bank or FossaPay wallet)
                                            │
                                      payout.completed
                                            │
                                   Escrow (RELEASED)
```

**Important:** FossaPay does not provide a native escrow/hold product. Reach will hold escrowed funds in the FossaPay **merchant master wallet** and record the obligation to each provider in an internal double-entry ledger. This is custodial escrow and must be reviewed for legal/compliance implications before launch.

### Custody decision (verified against FossaPay docs)

FossaPay documents two wallet types:

- **Customer NGN wallet** — belongs to an individual customer created through the Customers API. Only one NGN wallet per customer.
- **Master NGN wallet** — belongs to the merchant; the source for Master Wallet Payouts.

Their guidance is explicit: *“Choose the source wallet according to economic ownership. Customer funds must use customer-wallet operations; business funds must use the merchant master wallet and Payouts API.”* They also say *“Keep customer funds separate from merchant master-wallet funds.”*

There is **no escrow, hold, freeze, or split-payment endpoint**. Wallet-to-wallet transfers are free, but they are immediate transfers between wallets owned by the same merchant — not a hold. A “Reach-owned escrow customer” is not a supported construct: a customer represents an individual served by the business, and using a customer wallet for platform-held third-party funds would conflict with the ownership rule.

Therefore:

- **Chosen model:** checkout settles to the **merchant master wallet**; Reach records `escrow_liability` per transaction; payouts go from the master wallet.
- **Not used:** customer-wallet escrow, per-transaction escrow wallets, and a platform-owned “escrow customer”.
- **Compliance:** holding customer funds in the master wallet is custodial. Legal/compliance sign-off remains a launch gate.
- **Refunds:** wallet refunds require a FossaPay customer wallet for the payer (free same-business payout); bank refunds use an external payout with the fee deducted.

### Why the fiat rail is separate

For context only — none of this is a task in this plan:

- No task is ever created on-chain from the UI.
- `createTaskOnChain` is unused and does not match the contract's fee math.
- The chain-ID columns the frontend depends on were dropped by a later migration.
- Wallet identity is not linked to users.
- The product wants NGN, not a testnet stablecoin.

Because the chain code is owned elsewhere, **do not fix, remove, or refactor it here.** Build the fiat payment layer behind a small `PaymentProvider` interface so a future chain rail can plug in without touching this code. If the existing chain fields cause response validation failures in `backend/schemas/jobs.py`, report it to the owner; do not "clean it up" as part of payments work.

---

## 2. Current state (what this replaces)

| Area | Current state | Target |
|---|---|---|
| Job posting | `POST /jobs`, DB only | DB job, no payment until a provider is accepted |
| Applying | DB only | DB only |
| Accepting | Sets job `IN_PROGRESS` unconditionally; optional NEAR call that never fires | Job `AWAITING_PAYMENT`; escrow must be funded before `IN_PROGRESS` |
| Completion | UI sheet callbacks are empty | Dual completion + verified escrow release |
| Dispute | Mock page, TODO | Backend dispute + admin resolution + split payout/refund |
| Service requests | DB lifecycle only, no money | Escrow-funded service requests |
| Product orders | Mock product/payment/orders UI, `/checkout` route missing | Real products, orders, checkout, escrow, release |
| Payouts | Hardcoded mock data | Real payout records + FossaPay payouts |
| Wallet | NEAR testnet wallet selector | Left untouched. The fiat flow does not use, require, or modify it; FossaPay customer/wallet provisioning is backend-only |
| Money types | `Float` for budgets/prices | Integer kobo / `Numeric`, never floats |

### Repo-specific blockers to fix first

1. **Pre-existing chain-ID schema drift (leave alone):** `near_task_id` / `near_application_id` are required in `backend/schemas/jobs.py` but are missing from `backend/models/jobs.py` and were dropped by `backend/alembic/versions/7ec44a13ae47_add_business_media_relationship.py`. This can break job responses. It belongs to the NEAR owner, not this work. The fiat flow must not read, write, or depend on those fields; report the issue instead of changing it.
2. **Float money:** `Job.budget`, `JobApplication.proposed_price`, `Service.starting_price`, `ServiceRequest.proposed_price` are `Float`. Convert to integer kobo (or `Numeric(18,2)`) before building the ledger.
3. **No order/product models** exist. They are greenfield.
4. **No test suite** exists under `backend/`. Add pytest + an async test client and a fake payment provider before touching money flows.
5. **Service completion is provider-driven** (`PATCH /services/requests/{id}/complete`). Money should be released by the requester (or by an auto-release policy), not the party being paid.
6. **Alembic autogenerate is drifting** from models; add a CI check that autogenerate produces an empty diff.

---

## 3. Architecture

### 3.1 Components

| Component | Responsibility |
|---|---|
| `FossaPayClient` | Thin HTTP client: customers, NGN wallets, checkouts, payouts, banks, name enquiry, fees. Handles auth, timeouts, idempotency, response envelope, redacted logging. |
| `CustomerProvisioningService` | Creates the FossaPay customer + NGN wallet after the payment profile is completed; retries failures; backfills existing users before their next money action. |
| `PaymentIntentService` | Creates and tracks one collection attempt for a business object. Owns checkout creation, expiry, status refresh, and reconciliation. |
| `EscrowService` | Business-level hold: fund, release, refund, dispute, resolve. Enforces allowed transitions. |
| `LedgerService` | Double-entry postings. The only code allowed to write ledger entries. |
| `PayoutService` | Provider payouts, bank verification, payout webhooks, retries/manual review. |
| `ReconciliationService` | Polls pending checkouts/payouts, compares ledger cash to FossaPay master wallet, alerts on drift. |
| `WebhookInbox` | Durable, deduplicated webhook storage. HTTP handler returns 200 quickly; a worker processes events. |
| `PaymentProvider` interface | `FossaPayProvider` in production, `FakeProvider` in tests/local. Prevents FossaPay-specific logic from leaking into domain services. |

### 3.2 Suggested file layout

```
backend/
  core/
    configs.py                 # add FossaPay + escrow settings
    fossapay.py                # HTTP client
  models/
    payments.py                # PaymentIntent, Escrow, Payout, Refund
    ledger.py                  # LedgerTransaction, LedgerEntry
    fossapay.py                # FossaPayCustomer, BankAccount
    webhooks.py                # WebhookEvent inbox
    orders.py                  # Product, Order, OrderItem (Phase 4)
  schemas/
    payments.py
    orders.py
  services/
    payments.py
    escrow.py
    ledger.py
    payouts.py
    provisioning.py            # payment-profile customer/wallet provisioning + backfill
    reconciliation.py
    fossapay_service.py
    payment_provider.py        # protocol + FakeProvider
  routers/
    payments.py
    webhooks.py
    payouts.py
    admin_payments.py
    orders.py
  workers/
    webhook_worker.py
    reconcile.py
  utils/
    money.py                   # kobo <-> Decimal/NGN strings
    signatures.py              # HMAC verification
  tests/
    conftest.py
    test_ledger.py
    test_payments.py
    test_webhooks.py
    test_payouts.py
    test_escrow_flows.py
```

### 3.3 Configuration

Add to `backend/core/configs.py` / `.env`:

```env
FOSSAPAY_API_URL=https://api-production.fossapay.com/api/v1
FOSSAPAY_API_KEY=fk_production_...
FOSSAPAY_WEBHOOK_SECRET=...
FOSSAPAY_ENABLED=true
PAYMENT_PROVIDER=fossapay            # or "fake" for tests

PLATFORM_FEE_BPS=500                 # 5% of released amount, deducted from provider
MIN_ESCROW_KOBO=100000               # ₦1,000 minimum
PROVISION_FOSSAPAY_AFTER_PROFILE=true  # create customer + NGN wallet after the profile step
CHECKOUT_FEE_BEARER=customer         # customer pays the FossaPay checkout fee
PAYOUT_FEE_BEARER=provider           # deducted from provider net
REFUND_BANK_FEE_BEARER=customer      # wallet refunds free; bank refunds deduct fee

ESCROW_AUTO_RELEASE_DAYS=3           # after worker completion, if poster is silent
STALE_ESCROW_DAYS=30                 # then admin review
PAYMENT_INTENT_TTL_MINUTES=30        # FossaPay checkout expiry

DAILY_PAYOUT_TIME=17:00
PAYOUT_TIMEZONE=Africa/Lagos
KYC_UNVERIFIED_DAILY_LIMIT_KOBO=1000000    # ₦10,000
KYC_VERIFIED_DAILY_LIMIT_KOBO=20000000     # ₦200,000
ADMIN_DUAL_APPROVAL_KOBO=100000000         # ₦1,000,000

RECONCILE_PENDING_AFTER_MINUTES=10
RECONCILE_INTERVAL_SECONDS=300
```

Never expose `FOSSAPAY_API_KEY` or `FOSSAPAY_WEBHOOK_SECRET` to the frontend. The frontend only receives checkout instructions (`accountNumber`, `bankName`, `accountName`, `amountPayable`, `expiresAt`) from the Reach backend.

---

## 4. Money representation

**Rule: never use `float` for money.**

- Store amounts as **integer kobo** (`BIGINT`) in the database.
- Convert at the boundary:
  - `kobo -> "1234.56"` decimal string for FossaPay.
  - `kobo -> ₦` formatting for the frontend.
- FossaPay checkout `amount` must be a whole NGN amount ≥ 1. Validate and round only with an explicit business rule.
- FossaPay returns decimal strings (e.g. `"5000.00"`); parse with `Decimal`, never `float`.
- For every provider call, store the request amount, returned `amount`, `fee`, `amountPayable`, and `settlementAmount` as integers.

Migration work:

- `jobs.budget_kobo BIGINT` (backfill `round(budget * 100)`), keep `budget` temporarily for compatibility, then drop.
- `job_applications.proposed_price_kobo`
- `services.starting_price_kobo`
- `service_requests.proposed_price_kobo`
- Product/order money fields in kobo.

---

## 5. Data model

All tables use the existing `TimeStampMixin` where appropriate. All monetary columns are `BIGINT` kobo.

### 5.1 FossaPay customer and bank accounts

```text
payment_profiles
  id                    PK
  user_id               FK users.id, UNIQUE
  middle_name           TEXT NULL
  date_of_birth         DATE
  address               TEXT
  city                  TEXT
  country               TEXT DEFAULT 'Nigeria'
  completed_at          TIMESTAMPTZ
  created_at, updated_at

fossapay_customers
  id                    PK
  user_id               FK users.id, UNIQUE
  provider_customer_id  TEXT UNIQUE          # FossaPay customer UUID
  wallet_id             TEXT                  # FossaPay NGN wallet ID
  account_number        TEXT                  # virtual account
  account_name          TEXT
  bank_name             TEXT
  status                ENUM(active, disabled)
  raw                   JSONB
  created_at, updated_at

bank_accounts
  id                    PK
  user_id               FK users.id
  bank_code             TEXT
  bank_name             TEXT
  account_number        TEXT                  # encrypted/masked at rest
  account_name          TEXT                  # verified name
  verified_at           TIMESTAMPTZ
  is_default            BOOLEAN
  created_at, updated_at
  UNIQUE(user_id, bank_code, account_number)

user_kyc
  id                    PK
  user_id               FK users.id, UNIQUE
  status                ENUM(unverified, pending, verified, rejected)
  method                ENUM(NIN, BVN) NULL
  provider_reference    TEXT
  identity_last4        TEXT                  # never store the full NIN/BVN
  verified_at           TIMESTAMPTZ
  rejection_reason      TEXT
  raw                   JSONB
  created_at, updated_at
```

KYC is required for providers before payout. The limits (`KYC_UNVERIFIED_DAILY_LIMIT_KOBO`, `KYC_VERIFIED_DAILY_LIMIT_KOBO`) are enforced from this table plus the ledger's daily payout totals.

**Flow: signup → email verification → immediate payment profile → provisioning.** Signup stays lightweight. Because login is blocked until email verification (`auth.py`), the payment profile is the **first authenticated screen after verification/login**. The frontend redirects there before the normal app, and the profile is required before any money action. (If you want it before email verification, that needs a short-lived signup token — not included here.)

**Payment-profile flow:**

1. Signup creates the Reach user with the existing basic fields.
2. After verification/login, the frontend calls `GET /payments/profile`. If `profile_completed=false` or `can_pay=false`, it shows the payment-profile step.
3. `PUT /payments/profile` saves `middle_name` (optional), `date_of_birth`, `address`, `city`, and `country`. It can also correct `first_name`, `last_name`, and `phone_number` captured at signup.
4. The backend validates names/phone, saves the profile, creates a `fossapay_customers` row in `pending`, and schedules provisioning.
5. Provisioning calls `POST /customers` and `POST /wallets/fiat/create` with a stable `walletReference` (`reach-user-{user_id}`).
6. `GET /payments/profile` returns `can_pay=true` only when the profile is complete **and** provisioning is `provisioned`.
7. If FossaPay fails, the profile stays saved. Keep `provisioning_status=pending/failed`, expose the error, and let the user retry via `POST /payments/profile/provision`.
8. If the customer-create response is lost, search existing customers by email before retrying. If the wallet-create response is lost, retrieve the customer wallet before retrying; wallet creation has no idempotency semantics.

**Fields required by FossaPay:** `firstName`, `lastName`, `emailAddress`, `mobileNumber`, `dateOfBirth`, `address`, `city`, `country`, `type=individual`. Name fields accept exactly one name each (no spaces/numbers); phone must be international format.

| FossaPay field | Required | Reach source | Notes |
|---|---|---|---|
| `firstName` | Yes | Signup `first_name`, correctable in profile | Must be one name, no spaces/numbers |
| `lastName` | Yes | Signup `last_name`, correctable in profile | Must be one name, no spaces/numbers |
| `middleName` | No | Payment profile | Optional |
| `emailAddress` | Yes | Signup `email` | Already validated with `EmailStr` |
| `mobileNumber` | Yes | Signup `phone_number`, correctable in profile | Normalize to E.164 (`+234...`) |
| `dateOfBirth` | Yes | Payment profile | `date_of_birth DATE`, serialize `YYYY-MM-DD` |
| `address` | Yes | Payment profile | Street address, not lat/lon |
| `city` | Yes | Payment profile | City |
| `country` | Yes | Payment profile | Default `Nigeria` |
| `type` | Yes | Server-side constant | Hardcode `individual`; never accept from client |

`location_name`, `latitude`, and `longitude` are **not** substitutes for `address`, `city`, or `country`; they are free-form/geographic and cannot reliably populate FossaPay’s required fields.

**Validation rules:** one name per field (no spaces/numbers), normalize Nigerian phone numbers to `+234…`, require ISO date format, require age ≥ 18, and keep `country` as a controlled value. If a user has a compound first or last name, the profile step can correct it or collect a middle name rather than passing multiple names in one field.

**Existing users:** backfill lazily on next login/payment. Their FossaPay customer is created before their next money action; existing jobs are grandfathered per the legacy-job rule.

**KYC is separate:** creating a FossaPay customer is not KYC. Providers still verify NIN/BVN before payouts.

### 5.2 Payment intents

One row per collection attempt.

```text
payment_intents
  id                    PK
  reference             TEXT UNIQUE           # e.g. PI-JOB-42-<uuid>
  user_id               FK users.id           # payer
  purpose               ENUM(job_escrow, service_escrow, order)
  target_type           ENUM(job, service_request, order)
  target_id             BIGINT
  amount_kobo           BIGINT                # amount owed to Reach
  fee_bearer            ENUM(customer, merchant)
  amount_payable_kobo   BIGINT                # from FossaPay response
  provider_fee_kobo     BIGINT
  settlement_kobo       BIGINT
  currency              TEXT DEFAULT 'NGN'
  provider              ENUM(fossapay, fake)
  provider_checkout_id  TEXT UNIQUE
  provider_reference    TEXT                  # usually == reference
  idempotency_key       TEXT UNIQUE
  status                ENUM(created, pending, paid, failed, expired, reversed)
  account_snapshot      JSONB                 # bank name/number/name/type/expiry
  expires_at            TIMESTAMPTZ
  paid_at               TIMESTAMPTZ
  failure_reason        TEXT
  raw                   JSONB
  created_at, updated_at

  INDEX(target_type, target_id)
  INDEX(status, expires_at)
```

### 5.3 Escrows

One row per funded business object.

```text
escrows
  id                    PK
  payment_intent_id     FK payment_intents.id, UNIQUE
  target_type           ENUM(job, service_request, order)
  target_id             BIGINT
  payer_id              FK users.id
  payee_id              FK users.id NULL       # provider/seller once assigned
  amount_kobo           BIGINT                  # funded amount
  platform_fee_kobo     BIGINT                  # agreed at release time
  provider_net_kobo     BIGINT
  status                ENUM(awaiting_funds, funded, disputed, released, refunded, partially_released)
  funded_at             TIMESTAMPTZ
  released_at           TIMESTAMPTZ
  refunded_at           TIMESTAMPTZ
  dispute_reason        TEXT
  created_at, updated_at

  UNIQUE(target_type, target_id)              # one active escrow per object
  INDEX(status)
```

> `amount_kobo` is the amount the customer paid into escrow. The platform fee is computed at release, not at funding, so policy changes do not corrupt historical funding amounts. Store the fee used on the escrow at release time for auditability.

### 5.4 Payouts and refunds

```text
payouts
  id                    PK
  reference             TEXT UNIQUE
  escrow_id             FK escrows.id NULL
  user_id               FK users.id             # recipient
  kind                  ENUM(provider_release, refund, dispute_split)
  amount_kobo           BIGINT                  # what recipient receives
  fee_kobo              BIGINT                  # provider fee (from FossaPay)
  total_debited_kobo    BIGINT
  currency              TEXT DEFAULT 'NGN'
  destination_type      ENUM(bank_account, fossapay_wallet)
  destination_snapshot  JSONB                   # bank code/name/account; masked in logs
  provider_payout_id    TEXT UNIQUE
  provider_reference    TEXT
  idempotency_key       TEXT UNIQUE
  status                ENUM(scheduled, created, processing, completed, failed, reversed, needs_review)
  scheduled_for         TIMESTAMPTZ              # next 17:00 Africa/Lagos for bank payouts
  failure_reason        TEXT
  completed_at          TIMESTAMPTZ
  raw                   JSONB
  created_at, updated_at

  INDEX(status)
  INDEX(scheduled_for)
  INDEX(user_id, created_at)
```

`refunds` can be a view over `payouts(kind='refund')`; a separate table is optional. Prefer one `payouts` table with `kind` to reuse idempotency and webhook handling.

### 5.5 Ledger

```text
ledger_transactions
  id                    PK
  reference             TEXT UNIQUE           # business idempotency key
  kind                  ENUM(checkout_paid, escrow_release, payout_completed,
                             payout_fee, refund, dispute_resolution, adjustment)
  target_type           TEXT
  target_id             BIGINT
  description           TEXT
  created_at

ledger_entries
  id                    PK
  transaction_id        FK ledger_transactions.id
  account               ENUM(cash_fossapay, escrow_liability, provider_payable,
                             platform_revenue, refund_payable, payout_fee_expense,
                             customer_credit, adjustment)
  direction             ENUM(debit, credit)
  amount_kobo           BIGINT
  entry_metadata        JSONB
  created_at

  INDEX(account)
  INDEX(transaction_id)
```

**Invariant:** for every `ledger_transactions` row, `sum(debit amounts) == sum(credit amounts)`. Enforce in `LedgerService.post()` and add a test that walks the whole table.

Account meanings:

| Account | Type | Meaning |
|---|---|---|
| `cash_fossapay` | Asset | Funds held in the FossaPay master wallet |
| `escrow_liability` | Liability | Money owed to customers/providers while held |
| `provider_payable` | Liability | Released but not yet paid out |
| `platform_revenue` | Income | Reach commission |
| `refund_payable` | Liability | Approved refunds awaiting payout |
| `payout_fee_expense` | Expense | FossaPay payout fees borne by Reach |
| `customer_credit` | Liability | Optional wallet credit (if introduced) |
| `adjustment` | Equity/clearing | Reconciliation differences, manual review |

**Example:** ₦10,000 order, 5% commission (₦500), customer pays the FossaPay checkout fee.

1. Checkout completed:
   - Dr `cash_fossapay` 1,000,000 kobo
   - Cr `escrow_liability` 1,000,000 kobo
2. Release:
   - Dr `escrow_liability` 1,000,000
   - Cr `provider_payable` 950,000
   - Cr `platform_revenue` 50,000
3. Payout, provider pays a ₦50 FossaPay fee:
   - Provider net is ₦9,450. FossaPay call: `amount=9450`, `totalDebited=9500`.
   - Dr `provider_payable` 950,000
   - Cr `cash_fossapay` 950,000
   - The ₦50 fee is inside the `totalDebited`; the provider effectively bears it because their payable was reduced from ₦9,500 to ₦9,450 at payout time.
   - If Reach chooses to absorb the fee, debit `payout_fee_expense` instead and pay out the full ₦9,500.

**Commission rule:** `commission_kobo = floor(released_kobo * 500 / 10000)` (5% in basis points, rounded down). For a partial split, apply 5% to the amount released to the provider, not to the full escrow. For a full refund, commission is zero.

**Shortfall rule:** `provider_net = max(0, released - commission - payout_fee)`. With the ₦1,000 minimum escrow, the commission is ₦50, so a provider nets at least ₦950 before any payout fee. If the payout fee would push the net below zero, Reach absorbs the excess and records it as an expense; never deduct more than the provider is owed.

Pick one fee policy and encode it once in `PayoutService`. Never let the provider's net amount be implicit.

### 5.6 Webhook inbox

```text
webhook_events
  id                    PK
  event_id              TEXT UNIQUE           # envelope eventId (or raw-body hash)
  event_type            TEXT                  # unsigned
  reference             TEXT
  provider_object_id    TEXT                  # checkoutId / payoutId
  signature_valid       BOOLEAN
  status                ENUM(received, processing, processed, failed, rejected, ignored)
  attempts              INT DEFAULT 0
  last_error            TEXT
  received_at           TIMESTAMPTZ
  processed_at          TIMESTAMPTZ

  INDEX(status, received_at)
```

### 5.7 Provider call audit (recommended)

```text
provider_calls
  id, provider, operation, reference, idempotency_key,
  request_body JSONB, response_status INT, response_body JSONB,
  status ENUM(started, succeeded, failed, ambiguous),
  created_at, updated_at
```

This is how you recover from timeouts: persist the reference and idempotency key **before** the HTTP call, then look up by reference instead of retrying blindly.

---

## 6. State machines

### 6.1 PaymentIntent

```text
created ──► pending ──► paid
                ├────► failed
                ├────► expired
                └────► reversed
```

- `created` exists only inside the create transaction before the provider responds.
- `given up` is not a state: use `expired`.
- `reversed` is terminal for the collection; a new intent is required for another attempt.

### 6.2 Escrow

```text
awaiting_funds ──► funded ──► released
        │              ├────► refunded
        │              ├────► partially_released
        │              └────► disputed ──► released | refunded | partially_released
        └────► cancelled (no money moved)
```

### 6.3 Job

Keep business status and escrow status separate, but enforce guards:

```text
OPEN
  └─ accept applicant ──► AWAITING_PAYMENT
        ├─ checkout.completed ──► IN_PROGRESS
        ├─ payment expired/failed ──► OPEN immediately
        │                           (application reverts to PENDING; both notified)
        └─ poster cancels ──► CANCELLED (no money)
IN_PROGRESS
  ├─ worker_completed + client_completed ──► COMPLETED (release)
  ├─ worker_completed + poster silent 3 days ──► COMPLETED (auto-release)
  ├─ either party raises dispute ──► DISPUTED
  └─ cancel before work (admin case-by-case) ──► REFUNDED
DISPUTED
  └─ admin resolution (48h) ──► COMPLETED | REFUNDED | SPLIT
```

Required enum additions: `AWAITING_PAYMENT`, `DISPUTED`, `REFUNDED` (and optionally `SPLIT`). Add `worker_completed_at` / `client_completed_at` for auto-release.

**Guard:** `IN_PROGRESS` is only reachable from a verified `checkout.completed` webhook (or a verified reconciliation lookup) that created a `funded` escrow. Never from the accept endpoint directly.

### 6.4 ServiceRequest

```text
PENDING ──► ACCEPTED ──► AWAITING_PAYMENT ──► START ──► AWAITING_CONFIRMATION ──► COMPLETED
   │            │                 │
   │            │                 └─ expired/failed ──► ACCEPTED (retry payment)
   │            └─ declined ──► DECLINED
   └─ cancelled ──► CANCELLED
```

- Provider accepts; **requester must fund escrow before the provider starts** (`START` is only reachable from a funded escrow).
- Provider completes → `AWAITING_CONFIRMATION`; **requester confirms** (not the provider). Release then follows; 3-day auto-release if the requester is silent.
- If the checkout expires, the request stays `ACCEPTED` and the requester can retry with a new checkout. The provider is not released from the assignment.
- Dispute state mirrors jobs.

### 6.5 Order

```text
PENDING_PAYMENT ──► FUNDED ──► FULFILLING ──► DELIVERED ──► COMPLETED (released)
        │               │             │             │
        │               │             │             ├─ buyer confirms ──► COMPLETED
        │               │             │             ├─ buyer silent 3 days ──► COMPLETED (auto-release)
        │               │             │             └─ dispute ──► DISPUTED ──► split/release/refund
        │               │             └─ cancelled (admin case-by-case)
        │               └─ expired ──► CANCELLED (buyer re-orders)
        └─ failed/reversed ──► CANCELLED
```

---

## 7. FossaPay integration

Base URL: `https://api-production.fossapay.com/api/v1`
Auth: `x-api-key: <production key>`
Envelope: `{ "status": "success", "statusCode": 201, "message": "...", "data": { ... } }`

> FossaPay currently has **no sandbox**. Every request uses production money. Build a `FakeProvider` and only run live smoke tests with controlled small amounts.

### 7.1 Endpoints used

| Operation | Endpoint | Notes |
|---|---|---|
| Create customer | `POST /customers` | Called **after the payment profile is completed**. Required fields include `firstName`, `lastName`, `emailAddress`, `mobileNumber`, `dateOfBirth`, `address`, `city`, `country`, `type=individual` |
| Create NGN wallet | `POST /wallets/fiat/create` | Body: `customerId`, `walletName`, `walletReference` |
| Get customer wallet | `GET /wallets/fiat/{walletId}` | Balance/reconciliation |
| Create checkout | `POST /checkouts` | Requires `X-Idempotency-Key`; body: `amount`, `currency: "NGN"`, `reference`, `feeBearer`, optional `customer`, `metadata`, `description` |
| Get checkout by ID | `GET /checkouts/{id}` | Reconciliation |
| Get checkout by reference | `GET /checkouts/reference/{reference}` | Recovery when create response is ambiguous |
| Expire checkout | `POST /checkouts/{id}/expire` | Only while `pending` |
| Get master wallet | `GET /wallets/fiat/master` | Cash reconciliation |
| Create payout | `POST /payouts` | Requires `X-Idempotency-Key`; `amount`, `reference`, beneficiary details |
| Get payout by ID / reference | `GET /payouts/{id}`, `GET /payouts/reference/{reference}` | Reconciliation |
| Supported banks | `GET /transfers/fiat/banks` | Never hard-code bank list |
| Name enquiry | `POST /transfers/fiat/bank-name-enquiry` | Verify beneficiary before payout |
| Calculate fee | `GET /transfers/fiat/calculate-fee?amount=...` | Use server-calculated fee |
| Wallet-to-wallet | `POST /wallets/fiat/transfers/wallet-to-wallet` | Free within same business |
| Inter-bank transfer | `POST /transfers/fiat/inter-bank` | Customer-funded withdrawal |
| Identity verification | `POST /kyc/verifications` | NIN/BVN; ₦120/₦70 per completed lookup; gate provider onboarding; requires `X-Idempotency-Key` |

### 7.2 Checkout flow

1. Backend computes the amount from the DB (never from the client) and creates a `PaymentIntent` + `Escrow(awaiting_funds)` inside one transaction.
2. Persist the reference and idempotency key **before** the HTTP call.
3. Call `POST /checkouts` with `feeBearer` from config and `metadata: { reach_payment_intent_id, target_type, target_id }`.
4. Store `provider_checkout_id`, `amountPayable`, `settlementAmount`, account snapshot, `expiresAt`.
5. Return only the payment instructions to the frontend:
   ```json
   {
     "paymentIntentId": 42,
     "status": "pending",
     "amountPayable": "10080.00",
     "currency": "NGN",
     "account": { "bankName": "...", "accountName": "...", "accountNumber": "..." },
     "expiresAt": "...",
     "reference": "PI-JOB-42-..."
   }
   ```
6. The frontend shows a countdown and polls `GET /payments/intents/{id}` (or uses websocket/push later). It must not claim success from a bank receipt or a redirect.
7. On `checkout.completed`, the webhook handler transitions the intent to `paid`, the escrow to `funded`, posts the ledger entry, and advances the business object exactly once.

**Amount rules:**
- `amount` is the merchant's order amount.
- `amountPayable` is what the customer must send exactly, in one transfer.
- `feeBearer=customer` is the configured policy: the customer pays `amount + fee`, and settlement equals the order amount.
- Never calculate the checkout fee yourself; use the returned values.
- Enforce `amount_kobo >= MIN_ESCROW_KOBO` (₦1,000) **before** creating the checkout. Reject smaller jobs/orders with a clear message.
- Checkouts expire after ~30 minutes. Show the expiry and stop displaying the account after terminal state.
- Use a unique `reference` and idempotency key per attempt. Do not reuse a reference after a terminal state.

### 7.3 Payout flow

**Confirmed payout policy:**

- **Wallet credit is the default.** Every provider gets a FossaPay customer + NGN wallet. A Master Wallet Payout to their virtual account is `same_business`, free, and instant.
- **Bank payout is optional.** The provider saves a verified bank account (name enquiry required).
- **Timing:**
  - Wallet credit: **always instant** on release.
  - Bank payout: **instant when both parties have signed off**.
  - Bank payout when the release came from the **3-day auto-release** (poster did not sign off): joins the **daily batch at 17:00 Africa/Lagos**.
- **Fees:** the provider pays the FossaPay payout fee, deducted from their net. Wallet credits have no FossaPay payout fee.
- `202` / `processing` is not success. Wait for `payout.completed` or reconcile by reference.
- `payout.failed` / `payout.reversed`: mark `needs_review`; reverse/restore the ledger; do **not** automatically create a replacement with a new key.

**Instant vs daily implementation:** `PayoutService` decides at release time. `instant = both_signed_off || destination_type == wallet`. Otherwise set `scheduled_for` to the next 17:00 Africa/Lagos run. The batch worker processes all `scheduled` payouts once and uses one idempotency key per payout.

Payout idempotency rules:
- One idempotency key per logical payout; persist it before calling.
- Same key + same body returns the original payout; same key + different body returns `409`.
- If the HTTP call times out, look up by `reference` first. Do not retry with a new key.
- Never pay out more than the escrow's provider net and never exceed the ledger `provider_payable` balance.

### 7.4 Refunds

FossaPay documents checkout reversal for failed/incorrect incoming payments (`checkout.reversed`), but **does not document a generic "refund a completed checkout" endpoint**. Plan for refunds as outbound payouts:

- **Default: refund to the payer's FossaPay wallet** (Master Wallet Payout to their virtual account, same-business/free). Free and instant.
- **Fallback: refund to a verified payer bank account** (Master Wallet Payout, external-bank fee). The FossaPay fee is **deducted from the refund**; show the net amount before confirming.
- **Approval:** refunds and provider no-show cases are **admin case-by-case**. One admin can approve within 48h; dual approval above ₦1,000,000. Audit every decision.
- **Partial refunds:** use a split ledger transaction; refund the agreed amount to the payer and release the rest to the provider.

**Action item:** confirm refund mechanics and limits with FossaPay support (`product@fossapay.com`) before building the dispute/refund UI. Treat this as a launch blocker if the product promises instant refunds.

### 7.5 Webhooks

Handler: `POST /webhooks/fossapay` (public, no auth, signature required).

Envelope:

```json
{
  "eventId": "evt_...",
  "eventType": "checkout.completed",
  "data": { "...": "..." },
  "timestamp": "2026-09-11T10:08:14.186Z"
}
```

Headers: `x-fossapay-signature`, `X-Event-Id`, `X-Event-Type`, `X-Retry-Count`.

Signature: HMAC-SHA256 over **`JSON.stringify(body.data)`**, lowercase hex, compared with `timingSafeEqual`.

**Critical implementation detail:** FossaPay signs `JSON.stringify(body.data)`, not the full envelope. Do **not** re-serialize with `json.dumps`; Python and JavaScript format numbers differently (`5000.00` → `5000.0`). Extract the exact raw `data` value from the received body and HMAC those bytes.

1. Read the raw request body.
2. Locate the top-level `data` value and slice its exact bytes.
3. HMAC-SHA256 those bytes with the webhook secret.
4. Add fixtures captured from real FossaPay events and test them.
5. If verification fails, store a `rejected` event and return `401`; never process it.

Processing rules:

- Treat `eventId`, `eventType`, and `timestamp` as **unsigned**.
- Deduplicate on the business object (`checkoutId` / `payoutId`) plus terminal status, not only `event_id`.
- Before funding an escrow or completing a payout, call `GET /checkouts/{id}` or `GET /payouts/{id}` and trust that response. The webhook only tells you to look.
- Make every state transition idempotent on `reference` / `checkoutId` / `payoutId`.
- Events may arrive out of order or be retried up to 5 times. Look up by reference, not just local IDs.
- If signature is invalid: `401`, store `rejected`, alert. If the secret is missing: fail closed.
- Map:
  - `checkout.completed` → fund escrow
  - `checkout.failed` / `expired` / `reversed` → fail/expire intent, revert business object
  - `payout.completed` → mark payout complete
  - `payout.failed` / `reversed` → manual review + ledger reversal
  - `deposit.completed`, `withdrawal.completed`, `transfer.completed` → wallet reconciliation if using customer wallets
  - `wallet.balance.updated` → refresh cached balance; never treat as proof of payment

---

## 8. Business flows

### 8.1 Job / request escrow

**Funding point: when the poster accepts an applicant.**

Why not at posting:
- Most posted jobs never get accepted; funding at posting creates refund noise.
- The agreed price can differ from the original budget (`JobApplication.proposed_price`).
- FossaPay checkout is an immediate payment, not a card authorization hold.

Flow:

1. Poster posts a job → `OPEN`, no money.
2. Providers apply → `PENDING`.
3. Poster accepts applicant:
   - In one DB transaction: accept the application, reject others, set job `AWAITING_PAYMENT`. Do not call FossaPay yet.
   - The poster then calls `POST /payments/jobs/{job_id}/checkout`.
   - The backend creates the `PaymentIntent` and calls FossaPay `POST /checkouts`. If the call fails, keep the job `AWAITING_PAYMENT`; the poster can retry.
4. Poster transfers the exact `amountPayable` before expiry.
5. `checkout.completed`:
   - Validate `checkoutId`, `reference`, `amountPayable`, and `settlementAmount` against the stored intent.
   - `PaymentIntent → paid`; `Escrow → funded`; `Job → IN_PROGRESS`; post ledger; notify both parties; invalidate other payment attempts for the same target.
6. Provider marks work complete → `worker_completed=true`, `worker_completed_at=now`. No money moves.
7. Poster signs off → require both flags:
   - Commission is **5%** (`PLATFORM_FEE_BPS=500`), deducted from the provider's release.
   - `Escrow → released`; `Job → COMPLETED`; `Ledger`: escrow liability → provider payable + platform revenue.
   - Create `Payout` with a deterministic reference, e.g. `PO-JOB-42-<escrow_id>-v1`.
   - Wallet credit is instant and free. Bank payout is instant because both parties signed off; otherwise it joins the 17:00 Africa/Lagos batch.
   - `Payout → processing`; webhook `payout.completed` → `Payout → completed`; post cash/payable entries.
8. If the poster does nothing after `worker_completed_at + ESCROW_AUTO_RELEASE_DAYS` (**3 days**), a cron releases automatically. Notify the poster before release. Because the poster did not sign off, a bank payout goes into the daily batch; a wallet credit is still instant.
9. Dispute:
   - Either party can open a dispute while escrow is `funded` (and before release).
   - `Escrow → disputed`; `Job → DISPUTED`; block release.
   - Require evidence; give the other party 48h to respond; admin decides within 48h.
   - Admin resolves with a split in kobo or percentages: create a refund payout for the payer and a release payout for the provider. Post a single balanced ledger transaction.
   - Store the admin user, reason, evidence, response, and split on the dispute record.
10. Cancellation:
    - Before funding: `Job → CANCELLED`, no money.
    - After funding: **admin case-by-case** (no unilateral provider/poster refund). Full refund, partial refund, or release by decision.
    - Provider no-show: admin review; default remedy is refund to the poster after evidence.
11. Stale escrow:
    - If nobody completes, signs off, disputes, or cancels for **30 days**, flag for admin review. Admin then refunds, releases, or splits. Funds stay in escrow until then.

**Legacy jobs (created before this launch):**
- They keep the old flow until the poster signs off.
- At poster sign-off, require escrow for the accepted `proposed_price` (fallback `job.budget`).
- Worker completion alone does not require payment.
- Jobs already `COMPLETED` before launch are historical and untouched.

**Duplicates/overpayments:** manual review for all. If two checkouts fund the same target, the later payment is held and flagged; do not auto-start work twice.

**Important backend changes:**
- Remove the unconditional `job.status = IN_PROGRESS` from `PATCH /jobs/applications/{id}/status`. Accepting should only move to `AWAITING_PAYMENT`.
- `PATCH /jobs/{id}/completion` should not set `COMPLETED` directly. It should record the side's confirmation and call `EscrowService.release()` only when policy conditions are met and the escrow is funded.
- Add `POST /jobs/{id}/payment-intent` or fold intent creation into the accept endpoint and return the payment instructions.
- Add `GET /jobs/{id}/payment` for the current payment/escrow state.

### 8.2 Service requests

1. Requester requests a service → `PENDING`, no money.
2. Provider accepts → `ACCEPTED`, then create a payment intent and set `AWAITING_PAYMENT` (requester pays). The provider **cannot start work** until the escrow is funded.
3. `checkout.completed` → `START`; work begins.
4. Provider marks work complete → `AWAITING_CONFIRMATION` (new state).
5. Requester confirms → release escrow and complete; 3-day auto-release if the requester is silent.
6. If the checkout expires or fails, the request stays `ACCEPTED`; the requester can retry with a new checkout. The provider remains assigned but cannot start.
7. Dispute/cancel mirror jobs; refunds are admin case-by-case.
8. If the provider never starts after funding, admin review; default remedy is a refund to the requester.

Change `PATCH /services/requests/{id}/complete` so only the **requester** can confirm completion, or split it into provider `mark-complete` and requester `confirm-complete`. The provider must not release their own funds.

### 8.3 Product orders

This is greenfield. Minimum model:

```text
products
  id, business_id FK businesses.id, name, description, price_kobo,
  status ENUM(active, paused, archived), media, created_at, updated_at

orders
  id, buyer_id FK users.id, business_id FK businesses.id,
  status ENUM(pending_payment, funded, fulfilling, delivered, completed,
              cancelled, disputed, refunded),
  subtotal_kobo, delivery_fee_kobo, platform_fee_kobo, total_kobo,
  delivery_address, escrow_id, created_at, updated_at

order_items
  id, order_id FK orders.id, product_id FK products.id,
  quantity, unit_price_kobo, line_total_kobo
```

Flow:

1. Buyer creates an order → `PENDING_PAYMENT`; server computes totals from product prices (never trust the client).
2. Enforce the **₦1,000 minimum escrow** and the buyer's KYC transaction limit. Create checkout + escrow; return instructions.
3. `checkout.completed` → `FUNDED`; notify seller.
4. Seller fulfills/marks delivered → `DELIVERED`.
5. Buyer confirms receipt → release; `COMPLETED`.
6. Auto-release after **3 days** if the buyer does not confirm and there is no dispute.
7. Dispute → `DISPUTED`; evidence + 48h response; admin decides within 48h.
8. Partial fulfillment, returns, or damaged goods: buyer and seller can agree a split; admin fallback if they disagree. The split creates a refund to the buyer and a release to the seller in one ledger transaction.
9. Cancellation before fulfillment: admin case-by-case.
10. Expired/failed checkout → `CANCELLED`; the buyer can re-order.
11. Duplicate/overpayment → manual review; do not auto-fulfill twice.

**Fee allocation:** the 5% commission is deducted from the seller's payout. Delivery fees belong to whoever fulfills delivery: seller-delivered → seller payout; Reach-delivered → platform revenue. Make this explicit in `OrderService`; never infer it from the client.

---

## 9. API surface

### Customer-facing — implemented

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/payments/profile` | Profile + FossaPay customer/wallet state; `can_pay` flag |
| `PUT` | `/payments/profile` | Complete/update the payment profile and start provisioning |
| `POST` | `/payments/profile/provision` | Retry FossaPay customer/wallet provisioning |
| `POST` | `/payments/jobs/{job_id}/checkout` | Create a FossaPay checkout for an accepted job |
| `GET` | `/payments/jobs/{job_id}` | Get the latest payment intent for a job |
| `POST` | `/payments/jobs/{job_id}/release` | Release a funded, completed job to the provider |
| `GET` | `/payments/jobs/{job_id}/payout` | Get the payout record for a job |

All amounts are **integer kobo** (`amount_kobo`, `amount_payable_kobo`, `commission_kobo`, `provider_payout_kobo`). Payment endpoints require the session cookie. Full request/response payloads, error codes and the frontend flow live in `docs/PAYMENTS_HANDOFF.md`.

**Job status change:** accepting an applicant now sets the job to `awaiting_payment` (new status). `in_progress` is only reached once FossaPay confirms the payment.

### Planned

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/payments/intents` | Generalized payment intent for services/orders |
| `GET` | `/payments/intents/{id}` | Get payment status/instructions |
| `GET` | `/payments/me` | Payment history |
| `GET` | `/escrows/{id}` | Escrow status for participants |
| `POST` | `/escrows/{id}/dispute` | Open a dispute with reason/evidence |
| `POST` | `/escrows/{id}/release` | Poster/buyer sign-off |
| `GET` | `/payouts/me` | Provider payout history |
| `GET` | `/banks` | Supported banks |
| `POST` | `/bank-accounts/verify` | Name enquiry |
| `POST` | `/bank-accounts` | Save verified bank account |

### Webhooks

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/webhooks/fossapay` | Signature-verified FossaPay events |

### Admin

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/payments` | Payment intent list/filters |
| `GET` | `/admin/escrows` | Escrow list/filters |
| `GET` | `/admin/escrows/{id}` | Full ledger + provider calls |
| `POST` | `/admin/escrows/{id}/resolve` | Resolve dispute with split |
| `POST` | `/admin/escrows/{id}/refund` | Admin-approved refund (case-by-case) |
| `POST` | `/admin/escrows/{id}/release` | Admin-approved release |
| `GET` | `/admin/escrows/stale` | Escrows with no activity for 30 days |
| `POST` | `/admin/payouts/{id}/retry` | Retry a failed payout **with review** |
| `POST` | `/admin/payouts/batch/run` | Trigger the 17:00 bank payout batch manually |
| `GET` | `/admin/reconciliation` | Drift report |
| `POST` | `/admin/reconciliation/run` | Trigger reconciliation |

All admin routes must check `UserRole.ADMIN` (currently `UserRole.ADMIN` exists) and write an audit log. Single-admin approval is allowed; require a second admin for movements above ₦1,000,000.

---

## 10. Reconciliation and failure handling

### 10.1 Pending operations

- A `PaymentIntent` in `pending` older than `RECONCILE_PENDING_AFTER_MINUTES` → `GET /checkouts/reference/{reference}`.
- A `Payout` in `processing` older than the threshold → `GET /payouts/reference/{reference}`.
- If the lookup returns a terminal state, process it through the same idempotent transition used by webhooks.
- If the lookup itself fails, retry with backoff; never create a new intent/payout.
- An escrow in `funded` or `disputed` with no activity for `STALE_ESCROW_DAYS` (30) → alert and surface in `/admin/escrows/stale`. Do not auto-move money; admin decides refund/release/split.
- A bank payout scheduled for the daily batch but not yet created by 17:05 → alert; do not silently skip it.

### 10.2 Daily cash reconciliation

- `sum(cash_fossapay debits - credits)` must equal the FossaPay master wallet `availableBalance` (minus any in-flight payouts and including pending credits).
- `sum(escrow_liability credits - debits)` must equal the sum of `funded`/`disputed` escrows.
- `sum(provider_payable credits - debits)` must equal the sum of provider balances not yet paid.
- Any difference → alert + `adjustment` entry only after manual review.

### 10.3 Ambiguous outcomes

The most dangerous cases:

| Case | Handling |
|---|---|
| Checkout create times out | Look up by `reference`. If found, continue; if not, retry with the **same** idempotency key. |
| Payout create times out | Look up by `reference`. Never submit a second payout with a new key. |
| Webhook arrives twice | `event_id` unique + conditional status updates. |
| Webhook arrives before DB commit | Retry/worker; look up by reference. |
| `payout.failed` without reversal | Keep liability, mark `needs_review`, contact FossaPay. Do not silently retry. |
| `payout.reversed` | Reverse the payout ledger; restore `provider_payable` or `refund_payable`. |
| `checkout.reversed` after `paid` | Treat as a refund/reversal: reverse escrow if not released; if already released, create a negative adjustment and manual review. |

### 10.4 Manual review queue

Create `needs_review` statuses and an admin list for:

- payout failed/reversed
- webhook signature failures
- amount mismatch (`amountPayable` vs stored)
- escrow funded but business object missing
- duplicate references
- ledger imbalance

### 10.5 Edge-case decision table

| Case | Policy |
|---|---|
| Two applicants accepted concurrently | Row-lock the job; only one transition to `AWAITING_PAYMENT` succeeds; reject the other request. |
| Both parties click complete/release simultaneously | Idempotent release keyed by `escrow_id`; second call is a no-op; one payout only. |
| Duplicate payment for the same target | Manual review; hold the extra funds; do not start work twice or create a second escrow. |
| Underpayment / overpayment | Checkout goes `failed`; never start work; admin/reconciliation refunds or collects the difference. |
| `checkout.reversed` before release | Revert escrow to `awaiting_funds`/`refunded`; job/service/order returns to the appropriate pre-work state; notify both. |
| `checkout.reversed` after release | Do not auto-debit the provider; create a negative adjustment and route to manual review. |
| Payout `failed` | Keep `provider_payable`; mark `needs_review`; do not auto-retry with a new key. |
| Payout `reversed` | Restore the payable; re-enter the payout queue only after review. |
| Provider changes bank account after payout scheduled | Cancel/supersede the scheduled payout only if it has not been submitted; otherwise wait for terminal state and review. |
| Provider deleted/deactivated with funds due | Keep `provider_payable`; block payout; manual review (account owner/estate/KYC). |
| Poster/buyer deleted/deactivated with escrow funded | Keep escrow; admin decides refund/release; do not auto-release to a missing provider. |
| Provider no-show after funding | Admin review; default remedy refund to payer; provider reputation/limit impact. |
| Poster silent after worker completion | Auto-release after 3 days; bank payout joins the 17:00 batch; wallet instant. |
| Both parties silent | Stale escrow at 30 days → admin review; no automatic money movement. |
| Dispute unresolved past 48h | Escalate to senior admin/ops; funds stay locked; notify both parties. |
| Partial fulfillment / return | Buyer and seller agree split; admin fallback; one balanced ledger transaction. Full refund → no commission; partial release → 5% of the provider's release share, shortfall absorbed. |
| Refund bank account closed/invalid | Payout fails → manual review; offer wallet credit or collect new bank details. |
| KYC limit exceeded | Reject the transaction/payout with a clear message; offer KYC upgrade; no partial bypass. |
| Legacy job below ₦1,000 | Admin review; either waive the minimum for that legacy job or cancel/repost. New jobs always enforce the minimum. |
| User has no FossaPay wallet/bank details | Wallet refund/credit requires provisioning; bank payout requires verified bank account; block release until resolved. |
| Payment profile while FossaPay is down | Save the profile anyway; mark provisioning `pending`; retry with backoff; block money actions until provisioned. |
| Customer-create timeout/retry | Search FossaPay customers by email before retrying; do not create duplicate customers. Wallet creation has no idempotency semantics. |
| Existing user missing DOB/address/city/country | Prompt before their next money action; backfill the FossaPay customer then; existing jobs continue under the legacy rule. |
| User edits legal name/DOB after provisioning | Treat identity fields as immutable for payment purposes; require support/admin review before changing the FossaPay customer identity. |
| Account deleted before provisioning | Cancel the pending provisioning job; never create a FossaPay customer for a deleted user. |
| Master wallet balance insufficient | Block payout creation, alert ops, keep `provider_payable`; never partially pay silently. |
| FossaPay timeout/5xx | Persist the operation as `ambiguous`, reconcile by reference, never retry blindly. |
| Webhook signature mismatch | `401`, store the event as `rejected`, alert; do not process. |
| Out-of-order webhooks | Process by reference/terminal status; ignore events that would move a terminal state backward. |
| Job budget/price edited after funding | Reject edits that change financial terms; require cancel/refund and a new agreement. |
| Job cancelled after funding before start | Admin case-by-case; refund/partial per decision. |
| Service cancelled after funding | Admin case-by-case; refund/partial per decision. |
| Order cancelled after funding | Admin case-by-case; refund/partial; if already delivered, dispute path. |
| Provider starts before payment (service) | Blocked by the state machine; `START` requires a funded escrow. |
| Two jobs/orders created by double-click | Idempotency key per create request; return the existing record. |
| Admin manual adjustment | Requires reason + audit; dual approval above ₦1,000,000. |
| Bank transfer fee on refund | Wallet refund free; bank refund deducts the FossaPay fee from the refund. |

---

## 11. Security and compliance

### 11.1 Secrets and transport

- FossaPay API key and webhook secret only in backend env/secret manager.
- HTTPS only for webhooks; configure the public URL in the FossaPay dashboard.
- Rotate keys with a documented procedure; support a grace period if FossaPay allows multiple active keys.
- Redact API keys, authorization headers, full bank account numbers, and webhook secrets from logs.

### 11.2 Webhook security

- Verify HMAC before parsing business logic.
- Deduplicate `event_id`.
- Reject requests with a missing/invalid signature (`401`).
- Rate-limit the endpoint; do not trust `X-Retry-Count` for security.
- Ensure the reverse proxy does not alter the JSON body if relying on raw-body verification.

### 11.3 Authorization

- Payment intent/escrow endpoints must verify the current user is the payer, payee, or an admin.
- Completion/release endpoints must verify the caller is the correct party.
- Admin dispute resolution must be role-gated and audited.
- Cookie auth is used (`access_token` httpOnly cookie). Add CSRF protection (double-submit token or strict SameSite + origin check) for state-changing endpoints, especially if the frontend and backend are on different origins.
- Do not accept amounts, fees, or provider IDs from the client. Recompute from DB.

### 11.4 KYC/AML and custody

- **Providers must complete KYC before receiving payouts.** Use FossaPay identity verification (`POST /kyc/verifications`, NIN ₦120 / BVN ₦70 per completed lookup); store the reference, method, result, and verification timestamp.
- **Limits:** unverified users **₦10,000/day**; verified users **₦200,000/day**. Apply these to both **payouts** and **single transaction size** (job budget, service price, order total). Count a rolling 24h window per user. Reject or require KYC when the cap is exceeded.
- Verify bank account names via name enquiry before saving/paying.
- Apply velocity checks and flag unusual patterns; route over-limit attempts to manual review.
- Separate `platform_revenue` from `escrow_liability` in the ledger. Never spend escrow funds on operations.
- Confirm the legal characterization of holding customer funds in the merchant master wallet with FossaPay and counsel. If Reach is deemed to be holding customer funds, licensing/partner requirements may apply. This is a launch gate, not a later optimization.
- **Admin controls:** one admin can approve refunds/payouts with an audit log; require **two admins above ₦1,000,000**. Record actor, reason, target, amount, and before/after state.
- Keep an audit trail for all admin actions and manual adjustments.

### 11.5 Data

- Encrypt bank account numbers at rest if possible (app-level encryption or `pgcrypto`).
- Store only masked account numbers in logs/analytics.
- Back up the ledger; it is the source of truth for money owed.

---

## 12. Implementation phases

Estimates assume one backend developer, with frontend work in parallel. Adjust for review/QA.

### Phase 0 — Foundation (≈1 week)

**Deliverables**
- `FossaPayClient` skeleton + `PaymentProvider` interface + `FakeProvider`.
- Config additions and startup validation (fail fast if production provider enabled without keys).
- Money utilities (`kobo`, `Decimal`, NGN formatting).
- Migrations: `payment_profiles`, `fossapay_customers`, `payment_intents`, `escrows`, `payouts`, `ledger_transactions`, `ledger_entries`, `webhook_events`, `bank_accounts`, `user_kyc`, `provider_calls`.
- Money column migration for jobs/services (`*_kobo`).
- Payment-profile model/endpoints (`date_of_birth`, `address`, `city`, `country`, optional name/phone corrections) + validation rules.
- Payment-profile endpoints + provisioning hook: create FossaPay customer + NGN wallet; `provisioning_status` with retry/backfill.
- `LedgerService` with balance invariant + tests.
- Webhook inbox model + `POST /webhooks/fossapay` that stores events and returns 200.
- Test harness: pytest, async DB fixtures, fake provider, factory helpers.

**Done when**
- Ledger unit tests prove every transaction balances.
- Fake checkout can be created and completed end-to-end in tests.
- The payment profile saves even when provisioning fails, and the retry endpoint provisions the customer/wallet.
- Migrations upgrade/downgrade cleanly; autogenerate diff is empty.

### Phase 1 — FossaPay client and webhooks (≈1 week)

**Deliverables**
- FossaPay customer + NGN wallet provisioning **after the immediate payment profile**, with retry/backfill for failures and existing users.
- Checkout create/get/expire; payout create/get; banks/name-enquiry/fee.
- Idempotency key persistence and ambiguous-outcome recovery.
- Webhook signature verification + fixtures; worker processing with dedupe/locking.
- Reconciliation job skeleton for pending intents/payouts.
- Structured logging/metrics (request id, provider reference, event id).

**Done when**
- A controlled live ₦1 checkout can be created and its `checkout.completed` webhook is verified and processed exactly once.
- A replayed webhook does not double-credit.
- A simulated timeout recovers via reference lookup.
- A controlled live payout is completed and reconciled (small amount).

### Phase 2 — Jobs escrow (≈1.5 weeks)

**Deliverables**
- Payment intent + escrow creation on application acceptance.
- Job states `AWAITING_PAYMENT`, `DISPUTED`, `REFUNDED`; guards.
- `checkout.completed` → fund escrow → `IN_PROGRESS`.
- Expiry/failure/reversal → **immediately** revert to `OPEN`, application back to `PENDING`, notify both.
- Dual completion + **3-day auto-release** + release service + payout creation.
- 5% commission (`PLATFORM_FEE_BPS=500`), ₦1,000 minimum escrow, provider-net floor zero.
- Cancel after funding is **admin case-by-case**; provider no-show is admin review.
- Dispute open (evidence + 48h response) + admin resolve (split).
- Notifications in-app + email + push for funded, completed, released, disputed, expiring.
- Endpoints from §9 for jobs.
- Do not modify the NEAR accept/complete path or chain fields. Add the fiat payment layer beside it and gate the UI on the new escrow status, not on wallet/chain IDs.

**Done when**
- No job can reach `IN_PROGRESS` without a `funded` escrow.
- A completed job releases exactly once; duplicate sign-off/release is a no-op.
- Expired/failed checkout leaves the job in a consistent state and notifies both parties.
- E2E test covers happy path, expiry, double webhook, dispute split, refund.

### Phase 3 — Payouts, refunds, and provider onboarding (≈1 week)

**Deliverables**
- FossaPay customer/wallet provisioning after the payment profile for every user; retry/backfill for failures and existing users.
- Bank account CRUD + name enquiry + default account.
- Payout modes: wallet credit instant/free (default); bank optional.
- Bank payout timing: instant when both parties sign off; daily batch at **17:00 Africa/Lagos** for auto-release cases.
- Payout webhooks (`completed`, `failed`, `reversed`) + ledger updates + manual review.
- Refund service: wallet first (free), bank fallback (fee deducted), admin case-by-case.
- Provider earnings/payout history endpoints.
- Admin reconciliation + manual review endpoints.
- Provider KYC via FossaPay `POST /kyc/verifications`; limits ₦10k/day unverified, ₦200k/day verified.

**Done when**
- Provider release creates one payout and cannot double-pay.
- `payout.failed`/`reversed` restore the liability correctly.
- Provider sees available/pending/paid balances from the ledger, not mock data.
- Refund path confirmed with FossaPay and tested.

### Phase 4 — Services and orders (≈1.5–2 weeks)

**Deliverables**
- Service request funding at provider acceptance; **pay before start**; requester confirmation; release.
- Service expiry keeps the provider assigned (`ACCEPTED`) with payment retry.
- `Product`, `Order`, `OrderItem` models + migrations.
- Order checkout, funding, fulfillment, delivery confirmation, 3-day auto-release.
- Partial fulfillment/returns: agreed split, admin fallback.
- Product/order UI API integration; fix `/checkout` vs `/payment` route mismatch.
- Shared escrow/ledger code reused across all three flows (no duplicated money logic).

**Done when**
- All three flows use `PaymentIntentService` + `EscrowService` + `LedgerService`.
- E2E tests for each flow, including cancel/refund/dispute.
- Dashboard/earnings derive from the ledger.

### Phase 5 — Production hardening (≈1 week)

**Deliverables**
- Daily reconciliation + alerts (cash vs ledger, escrow liabilities, payout backlog).
- Rate limits, request size limits, idempotency cleanup, webhook replay protection.
- Provider KYC gating and the **₦10k/day unverified — ₦200k/day verified** limits on payouts and transaction size; velocity checks and manual review.
- Audit log for admin actions and manual adjustments.
- Runbooks: webhook outage, provider outage, payout failure, reconciliation drift, disputed charge.
- Load test checkout creation/webhook processing.
- Secrets rotation and least-privilege API key plan.
- Legal/compliance sign-off on custody, refunds, and KYC.

**Done when**
- Reconciliation is green for 7 consecutive days.
- Alerts fire on synthetic drift/failed payouts.
- Runbooks are exercised in a game day.
- No payment-critical TODO/mock remains in backend or frontend.

---

## 13. Testing strategy

### Unit
- Money parsing/formatting, kobo/Decimal boundaries.
- Ledger balance invariant for every transaction kind.
- State machine guards (illegal transitions rejected).
- Webhook signature verification with captured fixtures.
- Idempotency: same key/body vs same key/different body.
- Fee computation: 5% of released amount, rounding down to the kobo; ₦1,000 minimum; provider-net floor; payout fee deduction; full refund → zero commission.
- KYC limit enforcement: ₦10k/day unverified, ₦200k/day verified, on payouts and transaction size.
- Payout scheduling: instant when both signed, next 17:00 batch otherwise; wallet always instant.
- Stale escrow detection at 30 days.

### Integration (fake provider)
- Create intent → fake checkout → complete webhook → escrow funded.
- Duplicate webhook → one credit.
- Expired/failed/reversed → correct business revert.
- Release → payout created → payout webhook → balances correct.
- Payout failed/reversed → liability restored.
- Dispute split → refund + payout ledger balanced.
- Timeout recovery via reference lookup.
- 3-day auto-release when the poster is silent; payout goes to the daily batch if bank.
- Immediate job revert on checkout expiry; service stays accepted with retry.
- Duplicate/overpayment → manual review, no double start/payout.
- Partial order split → buyer refund + seller release balanced.
- KYC limit rejection on payout and transaction size.
- Legacy job: escrow at poster sign-off using accepted proposed price.

### Live smoke (production key, controlled amounts)
- ₦1 checkout → webhook → webhook replay.
- ₦1 wallet payout → webhook.
- Bank name enquiry.
- Master wallet balance vs ledger.
- Run only with a dedicated small-amount test merchant/user and a feature flag.

### Regression
- Existing auth/users/jobs/services tests (to be created).
- Permission tests for every payment endpoint (payer/payee/admin/other user).
- CSRF/origin tests for cookie-authenticated writes.

---

## 14. Observability

Metrics:
- checkout created / completed / failed / expired (count, amount)
- webhook received / processed / failed / duplicate
- payout created / completed / failed / reversed (count, amount)
- pending intents older than 15/30/60 minutes
- escrow funded / released / disputed amounts
- ledger cash vs FossaPay master wallet drift
- payout backlog and manual-review count

Logs:
- `payment_intent_id`, `escrow_id`, `payout_id`, `reference`, `event_id`, `provider_checkout_id`, `provider_payout_id`
- Never log full account numbers, API keys, or webhook secrets.

Alerts:
- webhook signature failures > threshold
- pending checkout/payout older than SLA
- payout failed/reversed
- reconciliation drift
- ledger imbalance (should never happen)
- FossaPay 5xx rate

---

## 15. Rollout

1. **Dark launch:** build and test against `FakeProvider`; no live money.
2. **Internal live smoke:** production key, ₦1 transactions, manual reconciliation.
3. **Beta:** a small set of users; cap amounts; daily manual reconciliation; feature flag per flow (jobs first).
4. **Jobs GA:** enable job escrow; keep services/orders in beta.
5. **Services/orders GA:** enable as each passes e2e and reconciliation.
6. **Deprecate mocks:** remove mock payment/orders/payouts screens from the fiat flow. Leave NEAR wallet prompts untouched — they are not part of the fiat path.
7. **Post-launch:** review incident log, tune auto-release window/fees, add provider instant payouts.

---

## 16. Resolved decisions and remaining blockers

The commercial and lifecycle decisions are locked in §1 (“Confirmed decisions”). The remaining items are operational/legal, not product design:

1. **FossaPay master-wallet custody sign-off** — confirm with FossaPay and counsel that Reach may hold escrow liabilities in the merchant master wallet. Launch gate.
2. **Refund mechanics** — confirm that an outbound Master Wallet Payout is the correct way to refund a completed checkout. There is no documented refund endpoint.
3. **Payment-profile provisioning failure handling** — the profile saves even if FossaPay is down; `scripts/provision_pending.py` retries pending/failed records. Wire it to a scheduler and build the user-facing “payment setup pending” state for new and existing users.
4. **Webhook signature fixture** — capture a real FossaPay event and prove exact raw-`data` extraction matches their `JSON.stringify(body.data)` signing. Launch gate.
5. **Production-only testing** — approve the small live-amount smoke test plan and the `FakeProvider` test strategy.
6. **Provider bank details** — default: collect at first payout, but allow adding earlier. Confirm if onboarding should require it.
7. **KYC provider flow** — wire `POST /kyc/verifications` and define what happens when a provider fails or refuses KYC.
8. **`checkout.reversed` after release** — default: manual review + ledger adjustment; no automatic provider debit. Confirm.
9. **Admin tooling** — single admin approval with audit; dual approval above ₦1,000,000. Build the review/audit screens.
10. **Existing jobs** — validate the “escrow at poster sign-off, accepted proposed price” rule against real data before rollout.
11. **Tax and receipts** — confirm VAT treatment of the 5% commission, who issues receipts/invoices, and what customers/providers see. Not covered by FossaPay’s API.
12. **Legal terms** — update marketplace terms to explain escrow, auto-release, cancellation, disputes, and the fact that Reach holds funds in its merchant wallet.

---

## 17. Definition of done

- A customer can pay for a job, service request, or order and see the exact bank-transfer instructions and expiry.
- A business object cannot enter an in-progress state without a verified, funded escrow.
- Completion releases funds exactly once, only to the correct payee, with a ledger entry and a FossaPay payout reference.
- Expiry, failure, reversal, duplicate webhooks, and timeouts all leave the system in a consistent state.
- Every money movement is traceable from business object → payment intent → escrow → ledger transaction → FossaPay checkout/payout.
- Pending checkouts/payouts are reconciled automatically; cash matches the FossaPay master wallet.
- Providers see real available/pending/paid balances and payout history derived from the ledger.
- Admins can resolve disputes with an auditable split.
- No mock payment UI, no float money in the critical path, and the fiat flow does not require a NEAR wallet (the existing NEAR UI is left untouched).
- Runbooks and alerts exist for the failure modes in §10.

---

## Appendix A — FossaPay field notes

- Checkout `amount` is the merchant order amount; `amountPayable` is what the customer sends; `settlementAmount` is what Reach receives.
- **Checkout fee:** `feeBearer=customer`, so the customer pays `amount + fee` and Reach settles the full order amount.
- **Commission:** 5% of the released amount, deducted from the provider payout. Minimum escrow ₦1,000; provider net floors at zero. Full refund → zero commission.
- Checkout statuses: `pending`, `processing`, `completed`, `failed`, `expired`, `reversed`.
- Payout statuses: `completed`, `processing`, `failed`, `reversed`; HTTP `202` means accepted, not paid.
- Payout `totalDebited = amount + fee` for charged routes; `same_business` payouts are free.
- **Payout timing:** wallet credit instant/free; bank payout instant only after both parties sign off, otherwise the 17:00 Africa/Lagos batch. Provider pays the payout fee.
- **Refunds:** wallet first (free); bank fallback (fee deducted from refund). Admin case-by-case within 48h; dual approval above ₦1,000,000.
- **No escrow/hold API:** FossaPay customer wallets are for customer funds; master wallet is for business funds. Use master wallet escrow with a ledger liability.
- **KYC:** `POST /kyc/verifications` costs ₦120 (NIN) / ₦70 (BVN) per completed lookup; limits ₦10k/day unverified, ₦200k/day verified.
- Checkout/payout create require `X-Idempotency-Key` (or `Idempotency-Key`); same key + same body returns the original, same key + different body returns `409`.
- References are unique per merchant; do not reuse after a terminal state.
- Webhook deliveries retry up to 5 times; deduplicate on `eventId`.
- FossaPay has no sandbox; use `FakeProvider` for tests and small live amounts for smoke tests.

## Appendix B — Existing files that must change

### Backend (this work)

- `backend/core/configs.py` — FossaPay + escrow config.
- `backend/models/payments.py`, `backend/schemas/payments.py`, `backend/routers/payments.py` — payment profile fields, validation, status endpoints, and provisioning trigger.
- `backend/models/users.py` — add the `payment_profile` and `fossapay_customer` relationships. Keep signup itself unchanged.
- `backend/models/jobs.py`, `backend/models/services.py`, `backend/models/__init__.py` — money columns and new lifecycle states. **Do not remove or rename the existing chain fields; leave them exactly as they are.**
- `backend/schemas/jobs.py`, `backend/schemas/service.py` — kobo fields and new states. Leave chain fields untouched.
- `backend/routers/jobs.py` — add payment-intent/escrow endpoints and payment guards. Do not edit the existing `link-chain` routes.
- `backend/routers/services.py` — provider accept → payment request; requester pays before `START`; requester confirms → release.
- `backend/routers/__init__.py` — register payment/webhook/admin/order routers.
- `backend/app.py` — include routers, webhook route, startup config validation.
- `backend/DB/database.py` / Alembic — new models/migrations (additive only; no NEAR migrations).
- New files listed in §3.2.

### Frontend (coordinate with the frontend owner; not part of backend scope)

- `frontend/reach/app/payment/[id]/page.tsx` — real payment instructions, status polling.
- `frontend/reach/app/(main)/orders/page.tsx` — real orders; release confirmation.
- `frontend/reach/app/(secondary)/provider/payouts/page.tsx` — real payouts/earnings.
- `frontend/reach/components/layout/CompleteJobSheet.tsx` — call backend release/confirm.
- `frontend/reach/app/(secondary)/requests/dispute/page.tsx` — real dispute submission.
- `frontend/reach/lib/jobs.ts`, `lib/services.ts` — payment/escrow endpoints, kobo types.
- Add `frontend/reach/lib/payments.ts`, `lib/orders.ts`.

### Explicitly untouched

- `near-contract/**`
- `sol-contract/**`
- `frontend/reach/lib/near/**`
- `frontend/reach/context/WalletContext.tsx`
- NEAR wallet selector setup and wallet UI
- Existing `link-chain` backend endpoints and chain-ID columns
