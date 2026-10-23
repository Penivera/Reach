# Provider naira off-ramp (deposit-address model)

Status: **implemented, live payouts disabled**.

The provider keeps custody of their USDC. Reach never asks for a private key.
Instead, Reach creates a one-time Obiex USDC-on-Solana deposit address, the
provider sends USDC to it, Obiex credits Reach's wallet, Reach swaps the USDC
to NGNX, and Obiex pays naira to the provider's bank account.

This is the recommended model because it needs no custodial provider wallets
and no provider signing beyond the existing on-chain escrow lifecycle.

---

## 1. Why this model

| Model | Custody | Provider signing | Verdict |
|---|---|---|---|
| A. On-chain payout to provider wallet | None | Needs `apply` / `complete_task` | Already built; blocked on the provider wallet flow |
| B. Exchange deposit address | None | Same as A | Deferred; an exchange address is not a payout API |
| C. Reach-controlled provider wallet + Obiex off-ramp | Reach holds keys | Reach signs | Deferred; largest custody and compliance burden |
| **D. Provider sends USDC to a Reach-owned Obiex deposit address** | Brief, capped at one payout | None | **Implemented here** |

Model D does not weaken the escrow rule: a job's money is still released only
by `approve_work`, and the off-ramp is a separate request for USDC the provider
already owns. The backend never marks a job settled or paid before
`approve_work`.

---

## 2. Flow

```
provider                         Reach                         Obiex
   |                               |                              |
   | POST /payments/offramp        |                              |
   |------------------------------>| create deposit address       |
   |                               |----------------------------->|
   |                               |<-----------------------------|
   |<------------------------------| address + quote              |
   |                               |                              |
   | send exact USDC to address    |                              |
   |------------------------------------------------------------->|
   |                               | DEPOSIT webhook (CONFIRMED)  |
   |                               |<-----------------------------|
   |                               | swap USDC -> NGNX            |
   |                               |----------------------------->|
   |                               |<-----------------------------|
   |                               | debit NGNX to provider bank  |
   |                               |----------------------------->|
   |                               | WITHDRAWAL webhook           |
   |                               |<-----------------------------|
   |<------------------------------| status = paid                |
```

Each row is one `offramp_withdrawals` record. It stores the quoted rate, the
executed swap, the Obiex withdrawal reference, the exact fee, and the bank
payout amount. That makes reconciliation possible without relying on webhook
delivery.

Creating a payout requires a payment profile with bank details, a first and
last name that match Obiex's resolved account name, and a Solana
`users.onchain_address` for any refund.

---

## 3. API

All endpoints require the normal Reach login cookie. The feature flag
`REACH_OFFRAMP_ENABLED` gates the whole surface; the default is `false`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/payments/offramp/banks` | Nigerian banks Obiex can pay |
| `POST` | `/payments/offramp/quote` | Indicative naira quote from `sellRate` |
| `POST` | `/payments/offramp` | Create a deposit address and payout row |
| `GET` | `/payments/offramp` | The provider's payouts |
| `GET` | `/payments/offramp/{id}` | One payout |
| `POST` | `/payments/offramp/{id}/cancel` | Cancel before USDC arrives |
| `POST` | `/payments/offramp/{id}/retry` | Admin: retry a failed settlement |
| `POST` | `/payments/offramp/{id}/refund` | Admin: refund USDC to the provider |
| `POST` | `/payments/offramp/reconcile` | Admin: expire stale rows, poll payouts |

`POST /payments/offramp` accepts an `Idempotency-Key` header. Repeating the
request with the same key returns the existing payout.

Request:

```json
{
  "amount_usdc": "25.00",
  "bank_code": "058",
  "bank_account_number": "0123456789",
  "bank_account_name": "Ada Okafor"
}
```

The bank fields are optional when the provider's `PaymentProfile` already has
them. The account name is always the one Obiex resolves; a client cannot
substitute a different beneficiary name.

Response highlights:

```json
{
  "id": 12,
  "reference": "offramp-...",
  "status": "awaiting_deposit",
  "amount_usdc_units": 25000000,
  "deposit_address": "...",
  "deposit_currency": "USDC",
  "deposit_network": "SOL",
  "bank_account_name": "Ada Okafor",
  "expires_at": "..."
}
```

### State machine

```
awaiting_deposit
  ├─ partial deposit ─────────────> partially_funded ── full ──> deposit_confirmed
  ├─ cancelled ───────────────────> cancelled
  └─ no deposit before expiry ────> expired

deposit_confirmed
  ├─ swap + withdrawal accepted ──> withdrawing
  ├─ rate/amount outside limits ──> held
  └─ provider error ──────────────> failed

withdrawing
  ├─ SUCCESSFUL ──────────────────> paid
  └─ FAILED / REJECTED ───────────> failed

held / failed
  ├─ admin retry (failed only) ──> deposit_confirmed
  └─ admin refund ────────────────> refunding
                                        ├─ SUCCESSFUL ──> refunded
                                        └─ FAILED ──────> held
```

A late deposit to a cancelled or expired address is **held**, never silently
accepted. A new deposit after a payout has already started is also held; it
is never folded into an automatic second payout. An overpayment or a non-USDC
deposit is held for manual review.

---

## 4. Money handling

- USDC is stored in base units (`10^6`). A request with more than six decimal
  places is rejected; nothing is rounded.
- Naira is stored in kobo. A swap or payout with sub-kobo precision is
  rejected.
- The quote uses Obiex's `sellRate` (the amount of naira received for 1 USDT),
  never `buyRate`. Obiex publishes the rate against USDT; the quote treats
  USDC as approximately 1 USDT, and the executed USDC→NGNX swap is what
  actually sets the payout.
- The quote is indicative. The executed swap's `amountReceived` is the
  authoritative naira amount.
- A slippage floor (`REACH_OFFRAMP_SLIPPAGE_BPS`, default 200 = 2%) stops the
  payout if the executed rate is materially worse than the quote.
- `REACH_OFFRAMP_MIN_USDC_UNITS`, `REACH_OFFRAMP_MAX_USDC_UNITS`, and
  `REACH_OFFRAMP_MIN_NGN_KOBO` cap the request.
- The actual bank payout amount and fee come from the
  `/wallets/ext/debit/fiat` response (`payout.payoutAmount`, `payout.fee`).
  The quote-time fee is only an estimate.
- A failed bank payout is left in `failed` (Obiex returns the NGNX to the
  wallet). An admin can retry it; the retry reuses the recorded NGNX and
  **does not swap the USDC twice**. If a provider reference already exists,
  the retry first polls that transaction. A still-live payout is returned
  unchanged; only a terminal `FAILED`/`REJECTED` state clears the reference
  and creates a fresh bank payout. A held deposit that has not been swapped
  can be refunded to `users.onchain_address`; a payout that has already been
  swapped must be retried or have its swap reversed by support.

---

## 5. Obiex prerequisites — confirmed from the public docs

These are verified facts from Obiex's developer docs and official Node SDK on
2026-10-23.

### Authentication

- Headers: `X-API-KEY`, `X-API-TIMESTAMP` (milliseconds), `X-API-SIGNATURE`.
- Signature: HMAC-SHA256 of `{METHOD}{full path including /v1}{timestamp}`.
- Staging base URL: `https://staging.api.obiex.finance/v1`.
- Webhook header: `x-obiex-signature`, HMAC-SHA512 hex of the **raw** body,
  using the dashboard's Signature Secret.

### Deposit address

- `POST /addresses/broker`
- Body uses **currency codes** and **network codes**, not names:
  `currency: "USDC"`, `network: "SOL"`.
- Before calling it, check `GET /currencies/networks/active` and require
  `isReceivable: true` for the pair.
- The endpoint generates **or returns the existing** address for a
  `uniqueUserIdentifier` on that pair. Reach generates a fresh identifier per
  payout (`reach-offramp-<random>`), so each payout gets its own address.
- `GET /addresses/me/broker` lists the addresses.
- DEPOSIT webhooks include `address`, `currency`, `amount`, `status`,
  `reference`, `transactionId`, and `hash`. `status` must be `CONFIRMED`.
- Deposit addresses are permanent unless Obiex changes them; Reach's
  `expires_at` is an application-level window, not an Obiex expiry.

### Bank data

- `GET /ngn-payments/banks` returns bank `name`, `uuid`, and `sortCode`.
- `GET /ngn-payments/accounts/resolve` is a **GET** with `accountNumber` and
  either `sortCode` or `bankId`.
  - The OpenAPI page says `sortCode`.
  - The current Node SDK calls it with `bankId`.
  - Reach sends `sortCode` by default and can send `bankId` when one is
    supplied. This discrepancy must be settled with Obiex before go-live.
- The resolved `accountName` is snapshotted on the payout row.

### Swap

- `GET /currencies/fiat-rates` returns USDT/fiat rates. `sellRate` is the
  naira received when selling 1 USDT. It supports `NGNX` and `GHS`.
- `GET /trades/pairs` lists supported pairs.
- `POST /trades/swap` with `sourceId`, `targetId`, `amount`, and
  `side: "SELL"` swaps immediately.
- A direct `USDC/NGNX` pair must be confirmed. Reach checks the pair list and
  falls back through `USDT` (`USDC -> USDT -> NGNX`) when necessary.

### Bank payout

- `POST /wallets/ext/debit/fiat`
- Body: `amount`, `currency` (a currency **code**), `destination` with
  `accountNumber`, `accountName`, `bankName`, `bankCode`, and optional
  `narration`.
- The official example is an NGNX debit with `amount: 15000`,
  `payout.payoutAmount: 15000`, `payout.fee: 50`, and
  `payout.payoutCurrency: "NGNX"`. This supports Reach's model: swap to NGNX
  first, then request a naira amount.
- The README shows `withdrawNaira(10000, {..., merchantCode})`, but the
  current source and OpenAPI only expose
  `withdrawFiat(amount, currency, destination)`. Confirm whether
  `merchantCode` is still required.
- Withdrawal statuses: `PENDING`, `APPROVED`, `PROCESSING`, `SUCCESSFUL`,
  `FAILED`, `REJECTED`. `FAILED`/`REJECTED` return the funds to the wallet.
- The response includes a top-level `reference`, a top-level `id` (the
  transaction id), and a `payout.transactionId` equal to that id. The webhook
  `reference` matches the top-level `reference`; `GET /transactions/{id}`
  uses the top-level `id`. Reach stores both fields.
- The response includes the bank account snapshot and the exact `payout.fee`
  and `payout.payoutAmount`.

### Transactions

- `GET /transactions/{transactionId}` returns the current state.
- `GET /transactions/withdrawals/me` lists withdrawals.
- Webhooks are the primary path; reach's reconcile endpoint is the safety net.

---

## 6. Obiex prerequisites — must be confirmed before enabling live payouts

These are **not** answered by the public docs. Send them to Obiex
(`sales@obiex.finance`, and the API/support contact) and record the answers
here before flipping `REACH_OFFRAMP_ENABLED=true`.

### Account and compliance

1. Is Reach's business account enabled for **third-party bank payouts**? The
   API terms require KYB and KYCC/Travel Rule data for end users. Confirm that
   paying a provider's own bank account (name matches the Reach user) is
   allowed, and what beneficiary data must be retained.
2. What KYB documents and end-user KYC/KYCC data does Obiex require for this
   use case, and what are the volume limits?
3. Does Reach need a Nigerian SEC VASP licence or another licence for this
   flow? Obtain legal advice; Obiex's API terms do not make Reach compliant by
   themselves.
4. Are there sanctions, PEP, or restricted-bank checks that can reject a
   payout after the USDC has been deposited?

### Deposits and swaps

5. Is `USDC` on `SOL` receivable for Reach's business account? Confirm
   `isReceivable` and the minimum/maximum deposit.
6. Does `POST /addresses/broker` return a **unique** address for every new
   `uniqueUserIdentifier`, and can multiple identifiers share one currency /
   network pair? What is the address lifetime?
7. Is there a direct `USDC/NGNX` trade pair? If not, confirm the
   `USDC -> USDT -> NGNX` route, the spread, and whether the second swap can
   fail after the first succeeds.
8. What are the swap minimums, maximums, and rate-lock behaviour? The fiat
   rates endpoint is cached for up to 60 seconds; the swap is the executable
   rate.

### Bank payout semantics

9. For `/wallets/ext/debit/fiat`, does `currency` identify the **source
   wallet** (NGNX) and `amount` the naira amount? Confirm whether the fee is
   deducted from `amount`, added on top, or charged separately. The docs
   example shows `amount == payoutAmount == 15000` with `fee == 50`.
10. What are the bank payout minimum, maximum, daily limit, cutoff time, and
    expected settlement time? Are there per-bank restrictions?
11. Which identifier should be sent to `/ngn-payments/accounts/resolve`:
    `sortCode` or the bank `uuid` as `bankId`? The OpenAPI and SDK disagree.
12. Does the fiat withdrawal endpoint accept an idempotency key or a
    client-supplied reference? The request schema has no reference field. If a
    request times out, Reach cannot tell whether the payout was created. Until
    this is answered, a timed-out payout must be reconciled with
    `GET /transactions/withdrawals/me` before any retry.
13. What are the exact fee components (deposit, swap/spread, fiat withdrawal,
    bank)? Is the `payout.fee` in naira? Are there bank charges deducted from
    the beneficiary?
14. What is the webhook retry policy, event ID, and ordering guarantee? Can a
    `FAILED` webhook arrive after a `SUCCESSFUL` one? Does Obiex send a
    withdrawal webhook for `APPROVED` and `PROCESSING`, or only terminal
    states?
15. Does the `WITHDRAWAL` webhook `reference` always equal the top-level
    response `reference`? Reach prefers that field, then falls back to the
    provider transaction id (`provider_withdrawal_id` / refund transaction
    id). Confirm both are stable. (The docs example shows top-level
    `reference` and `id` as different values.)
16. What is the staging behaviour for bank payouts? Are test banks/accounts
    available, or does staging only exercise the API shape without a real
    transfer?

### Operations

17. Is there a supported way to reverse a successful payout? What is the
    process if the bank account is closed after the USDC deposit?
18. What status/health endpoint and rate limits apply to the endpoints Reach
    uses? The quote endpoint is limited to 100 requests/hour; Reach avoids it
    and uses `/currencies/fiat-rates`.
19. Can Obiex provide a dedicated webhook secret per environment (staging vs
    production) and rotate it without downtime?
20. Does `/wallets/ext/debit/crypto` accept an idempotency key or client
    reference? A timed-out USDC refund has the same duplicate-submission risk
    as a fiat payout.

---

## 7. Configuration

```env
REACH_OFFRAMP_ENABLED=false

REACH_OFFRAMP_SOURCE_CURRENCY=USDC
REACH_OFFRAMP_TARGET_CURRENCY=NGNX
REACH_OFFRAMP_NETWORK=SOL
REACH_OFFRAMP_FALLBACK_CURRENCY=USDT

REACH_OFFRAMP_MIN_USDC_UNITS=5000000       # 5 USDC
REACH_OFFRAMP_MAX_USDC_UNITS=1000000000    # 1,000 USDC
REACH_OFFRAMP_MIN_NGN_KOBO=500000          # ₦5,000
REACH_OFFRAMP_DEPOSIT_TTL_SECONDS=1800     # 30 minutes
REACH_OFFRAMP_QUOTE_TTL_SECONDS=300        # 5 minutes
REACH_OFFRAMP_SLIPPAGE_BPS=200             # 2%
REACH_OFFRAMP_FIAT_FEE_KOBO=5000           # quote-time estimate; live fee wins
REACH_OFFRAMP_REQUIRE_NAME_MATCH=true
```

`REACH_OFFRAMP_ENABLED=false` is deliberate. The endpoints return `503` until
the prerequisites above are answered and a staging run has passed.

---

## 8. Go-live checklist

1. Run the migration (`f1a2b3c4d5e6_add_offramp_withdrawals`).
2. Set Obiex staging credentials and `REACH_OFFRAMP_ENABLED=true` in staging.
3. Verify `GET /payments/offramp/banks` returns the expected banks.
4. Resolve a test account and confirm whether `sortCode` or `bankId` works.
5. Create one payout; verify the deposit address is USDC/SOL and
   `isReceivable`.
6. Send a small USDC deposit from a test wallet.
7. Confirm the DEPOSIT webhook matches the address and the swap executes.
8. Confirm the bank payout response includes `payoutAmount` and `fee` in
   NGNX.
9. Confirm the WITHDRAWAL webhook arrives and the row reaches `paid`.
10. Force a failed payout and verify the `failed` path and admin retry.
11. Force a held deposit and verify the refund to the provider's
    `onchain_address`.
12. Run reconcile with a stale row and a pending withdrawal.
13. Only then enable production, starting with a low maximum and manual
    review of every payout.

---

## 9. Remaining blockers outside this feature

- The on-chain provider lifecycle still needs a provider wallet that can sign
  `apply` and `complete_task`; `approve_work` cannot be reached without it.
  The off-ramp does not bypass that rule.
- The frontend still needs a Solana wallet transfer (or clear manual exchange
  send instructions) for the USDC deposit. The backend returns the address and
  network; the UI must not pretend the deposit happened.
- A scheduler is not part of the app. Run `POST /payments/offramp/reconcile`
  from an external cron until a background worker exists.
