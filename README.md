# Reach

> Reach more from your device.

Reach is a local marketplace for posting tasks and services, finding nearby
providers, and settling completed work with on-chain escrow.

## Current status (2026-10-23)

- **Canonical settlement:** the Solana Anchor program is the escrow and the
  source of truth. A job is funded into escrow at creation and opened once the
  escrow is on-chain.
- **On-ramp:** Obiex Business Collections (naira → USDC; access gated) and
  FossaPay checkout (naira) feed the treasury. A crypto payer can also fund
  with USDC directly.
- **Provider payout:** `approve_work` releases USDC to the provider's own
  Solana address.
- **Naira off-ramp:** the deposit-address flow is implemented behind
  `REACH_OFFRAMP_ENABLED=false`. It stays disabled until Obiex confirms
  Business Collections access and the prerequisites in
  `docs/REACH_NAIRA_OFFRAMP.md` §6.
- **Still outstanding:** provider-signed on-chain `apply` / `complete_task`,
  frontend payment/off-ramp integration, applying the migration to a real
  database, and a staging end-to-end payout.

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

## Tests

```bash
cd backend
venv/bin/python -m unittest discover -s tests
```

The payments branch currently has 126 tests and does not require a database.
