# Frontend handoff — backend gap fixes

Status: **backend changes ready; frontend wiring still needed.** This covers the
items reported after the initial backend audit: categories, signup email,
provider payouts/bank verification, service search, and the jobs feed.

It does **not** cover product orders, which remain a Phase 4 feature.

---

## 1. Categories

`GET /categories` now returns the seeded core categories after
`alembic upgrade head`:

- Food
- Fix
- Move
- Beauty
- Tutor
- Clean
- Trade

The data migration is idempotent (`INSERT ... ON CONFLICT (name) DO NOTHING`).
For databases created with `build_tables.py`, run:

```bash
cd backend
venv/bin/python -m scripts.seed_categories
```

Frontend action:

- The hardcoded fallback can stay as a visual fallback, but **do not send a
  fallback category id to the API**. `category_id` must be a real row from
  `GET /categories`.
- Remove the fallback once the migration is applied in the environment.

---

## 2. Signup email

`POST /auth/create-user` now calls the mailer after the account and token are
committed. A mail outage does not roll the signup back.

`POST /auth/resend-verification` still exists and returns `503` if the mailer
is unavailable.

The mailer supports **Brevo's HTTP API** and a **SMTP fallback**:

```dotenv
# Brevo (preferred)
BREVO_ENABLED=true
BREVO_API_KEY=<Brevo API v3 key>
SMTP_FROM_NAME=Reach
SMTP_FROM_EMAIL=<address verified in Brevo>

# SMTP fallback, used when BREVO_ENABLED=false
SMTP_HOST=smtp.zeptomail.com
SMTP_PORT=587
SMTP_START_TLS=true
SMTP_USERNAME=emailapikey
SMTP_PASSWORD=<ZeptoMail Send Mail token>
```

Frontend action:

- Show “check your email” after signup.
- If the user does not receive it, offer the resend action.
- A `503` from resend is a mail-provider/configuration problem, not a bad
  email address.

---

## 3. Provider payouts

New aliases/endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/payouts/me` | The provider's naira payout history (`OffRampWithdrawalResponse[]`) |
| `GET` | `/payouts/banks` | Nigerian banks available for a payout |
| `POST` | `/payouts/banks/resolve` | Resolve an account name before confirming |
| `POST` | `/payments/offramp` | Create the actual payout (existing endpoint) |
| `GET` | `/payments/offramp` | Same history as `/payouts/me` (existing) |

### Resolve an account

```http
POST /payouts/banks/resolve
Content-Type: application/json

{
  "bank_code": "058",
  "account_number": "9012345678"
}
```

Response:

```json
{
  "account_name": "Ada Okafor",
  "account_number": "9012345678",
  "bank_name": "GTBank",
  "bank_code": "058",
  "bank_id": "..."
}
```

Use this before enabling the “Withdraw” button. It works even while
`REACH_OFFRAMP_ENABLED=false`.

### Create a payout

```http
POST /payments/offramp
Content-Type: application/json
Idempotency-Key: <client-generated key>

{
  "amount_usdc": "10.000000",
  "bank_code": "058",
  "bank_account_number": "9012345678",
  "bank_account_name": "Ada Okafor"
}
```

The response contains the Obiex deposit address and the quoted NGN amount.
The provider sends USDC to that address; the webhook continues the payout.

Known gaps:

- `/payouts/me` is the payout history, not a wallet summary.
- “Available balance” and “pending releases” still need either:
  - a Solana RPC read of the provider’s USDC ATA, or
  - a backend summary endpoint.
- The legacy `Payout` model/table is not the source of truth; the off-ramp
  table is.

---

## 4. Service search

`GET /services` now accepts:

```text
q, category_id, limit, offset
```

`GET /services/nearby` now accepts:

```text
latitude, longitude, radius, category_id, q, limit, offset
```

`q` searches service title, description and business name. Nearby results are
limited to `ACTIVE` services.

Examples:

```http
GET /services?q=plumber&category_id=2&limit=20&offset=0
GET /services/nearby?latitude=6.5&longitude=3.3&radius=20&q=rice&limit=20
```

Frontend action:

- Add `q`, `limit` and `offset` to the service search query type.
- The existing provider-listings search is client-side only; it can stay for
  the provider's own listings, but global search should call the API.

---

## 5. Jobs feed

`GET /jobs` and `GET /jobs/nearby` now return only:

```text
status = open
funding_status = funded
```

This prevents drafts and unfunded escrows from appearing in the provider feed.

`GET /jobs/nearby` was also moved above `/jobs/{job_id}` so the route is no
longer shadowed by the path parameter. It now behaves like
`/services/nearby`.

Frontend action:

- The requests feed can keep using `GET /jobs`; it will no longer show
  `pending_funding` jobs.
- Use `GET /jobs/me` for the owner's drafts and history.

---

## 6. Orders

No order endpoints exist yet. `GET /orders/me` and the rest of the product
order flow are still missing. The frontend orders page remains mock data until
the `Product` / `Order` / `OrderItem` models, checkout, escrow and release
flow are implemented.

---

## 7. Service create/response contract — still needs alignment

This is **not fixed** by the gap pass. The frontend and backend currently
disagree:

Backend `ServiceCreate` expects:

```json
{
  "business_id": 1,
  "title": "...",
  "description": "...",
  "starting_price": 4500,
  "category_id": 1,
  "latitude": 6.5,
  "longitude": 3.3,
  "location_name": "..."
}
```

Frontend `createService` currently sends `min_price` / `max_price` and does
not send `business_id` or location. The frontend `Service` type also expects
`business_name`, `owner_id`, `min_price` and `max_price`, while the backend
returns `business_id` and `starting_price`.

This will 422 or render undefined values until one side is aligned. Decide
whether:

1. the frontend sends the backend's `business_id` and location fields, or
2. the backend accepts `min_price` / `max_price` and derives the business
   (e.g. the caller's business) and location.

The first is the smaller change if the frontend already has the user's
business/location; the second is a product decision about multiple businesses
per user.

---

## 8. What was not done

- Product orders.
- A provider balance/pending-release summary endpoint.
- The service create/response contract alignment above.
- A staging run with ZeptoMail credentials and a real verified sender domain.
