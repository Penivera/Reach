# Reach

> Reach more from your device.

Reach is a local marketplace for posting tasks and services, finding nearby
providers, and settling completed work with on-chain escrow.

## Current status (2026-10-24)

- **Canonical settlement:** the Solana Anchor program is the escrow and the
  source of truth. A job is funded into escrow at creation and opened once the
  escrow is on-chain.
- **Funding:** a client can fund from their own Solana wallet
  (`create_task` / `accept` / `approve_work` signed by the client) or through a
  naira on-ramp (Obiex/FossaPay, relayer-signed custodial escrow).
- **Provider payout:** the provider signs `apply` / `complete_task`; the
  creator releases with `approve_work`, which pays the provider's own USDC
  token account.
- **Naira off-ramp:** the deposit-address flow is implemented behind
  `REACH_OFFRAMP_ENABLED=false`. It stays disabled until Obiex confirms
  Business Collections access and the prerequisites in
  `docs/REACH_NAIRA_OFFRAMP.md` §6. `/payouts/me` and bank-account resolution
  are available for the provider dashboard.
- **Still outstanding:** frontend wallet/payment integration, applying the
  migrations to a real database, and a staging end-to-end payout. Product
  orders are still a Phase 4 feature.
- **Seed data:** the core categories (Food, Fix, Move, Beauty, Tutor, Clean,
  Trade) are inserted by the Alembic data migration `b3c4d5e6f7a8`. A local
  operator can also run `python -m scripts.seed_categories`.

## Documentation

| Document | Purpose |
|---|---|
| [`reach_flows_and_architecture_documentation.md`](reach_flows_and_architecture_documentation.md) | Canonical Model 1 architecture and flows |
| [`docs/REACH_MODEL1_PAYMENTS_PLAN.md`](docs/REACH_MODEL1_PAYMENTS_PLAN.md) | Backend payments plan, progress, and open work |
| [`docs/REACH_PAYMENT_FLOWS_PLAN.md`](docs/REACH_PAYMENT_FLOWS_PLAN.md) | Funding rails, provider payout cases, treasury |
| [`docs/REACH_NAIRA_OFFRAMP.md`](docs/REACH_NAIRA_OFFRAMP.md) | Provider naira cash-out design, API, Obiex prerequisites, runbook |
| [`CHANGELOG_feat_fossapay_payments.md`](CHANGELOG_feat_fossapay_payments.md) | Branch-level implementation changelog |
| [`docs/PAYMENTS_HANDOFF.md`](docs/PAYMENTS_HANDOFF.md) | Historical pre-Model-1 handoff (superseded) |
| [`docs/PAYMENTS_IMPLEMENTATION_PLAN.md`](docs/PAYMENTS_IMPLEMENTATION_PLAN.md) | Historical pre-Model-1 plan (superseded) |

## Repository layout

- `backend/` — FastAPI app, payment providers, Solana relayer, migrations, tests
- `frontend/reach/` — Next.js marketplace app
- `sol-contract/` — Anchor escrow program (canonical)
- `near-contract/` — deprecated standalone NEAR escrow contract

## Docker

The app stack runs with Docker Compose:

| Service | URL | Notes |
|---|---|---|
| `frontend` | http://localhost:3000 | Next.js production build |
| `backend` | http://localhost:8000 | FastAPI; runs migrations on start |

PostGIS is **not** part of this Compose file. The backend expects a reachable
`DATABASE_URL` for an existing PostGIS database.

```bash
# Optional: put provider keys and real SMTP/Cloudinary values in backend/.env.
cp backend/.env.example backend/.env

# Required: the PostGIS connection string (Compose reads this file).
cat > .env <<'EOF'
DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/work_near
EOF

docker compose up --build
```

Use `host.docker.internal` when PostGIS runs on your host; the backend service
is configured to resolve it on Linux too. For a database in another container
or host, use an address reachable from inside the backend container (not
`localhost`). `DATABASE_URL` may also be exported in your shell instead of
being written to the root `.env`.

`backend/.env` is optional and supplies provider/SMTP/Cloudinary settings;
`DATABASE_URL` must be in the root `.env` or the shell because Compose
interpolates it. `NEXT_PUBLIC_API_URL` is baked into the frontend at build
time, so rebuild the frontend after changing it:

```bash
NEXT_PUBLIC_API_URL=https://api.example.com docker compose up -d --build frontend
```

Useful commands:

```bash
docker compose logs -f backend   # follow API logs
docker compose exec backend alembic upgrade head
docker compose down              # stop the stack
```

For backend-only local development, run your PostGIS instance separately and
point `DATABASE_URL` at it:

```bash
cd backend
venv/bin/alembic upgrade head
```

Verification and password-reset email use **ZeptoMail SMTP**. Set these in
`backend/.env`:

```dotenv
SMTP_HOST=smtp.zeptomail.com
SMTP_PORT=587
SMTP_START_TLS=true
SMTP_USERNAME=emailapikey
SMTP_PASSWORD=<your ZeptoMail Send Mail token>
SMTP_FROM_NAME=Reach
SMTP_FROM_EMAIL=<an address on your verified ZeptoMail domain>
```

The core category seed is applied by `alembic upgrade head`. If the database
was created with `build_tables.py` instead, run:

```bash
cd backend
venv/bin/python -m scripts.seed_categories
```

## Tests

```bash
cd backend
venv/bin/python -m unittest discover -s tests
```

The backend currently has 158 tests and does not require a database.
