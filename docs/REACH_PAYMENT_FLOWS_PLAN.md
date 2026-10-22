# Reach Payment Flows — Funding and Settlement Plan

Status: plan, 2026-10-22. Backend scope.
Companion to `reach_flows_and_architecture_documentation.md` (Model 1) and
`docs/REACH_MODEL1_PAYMENTS_PLAN.md` (the provider work already landed).

---

## 1. The one invariant

> **The escrow is always USDC held in the Anchor program's task vault, and it
> is locked at creation.**

Every rail — naira or crypto — funnels into the same place, and every provider
is settled out of the same place. The rails only decide two things:

1. **how the payer funds the escrow**, and
2. **how the provider cashes out**.

`create_task` debits the creator's USDC token account into the task vault (plus
the creation fee into the fee vault). `approve_work` moves the vault balance to
the provider's token account. Nothing else is escrow — a balance sitting in a
provider's wallet is custody, not escrow.

Because the doc's relayer is the creator (`payer_type = "custodial"`), the USDC
must be in the **relayer's token account** at the moment the relayer signs.

## 2. Where the money actually goes

```
naira rail                                    crypto rail
──────────                                    ──────────
payer ──naira──► Obiex collection              payer ──USDC──► treasury ATA
   (KYC: NIN+BVN)      │                             │
                       │ name match                 │ (or payer signs
                       ▼                             │  create_task
              Obiex USDC balance                    │  themselves)
                       │                             │
                       │ withdrawal on SOL           │
                       ▼                             │
                relayer's Solana ATA ◄──────────────┘
                       │
                       │ relayer signs create_task
                       ▼
              ██ escrow: task vault PDA ██   ← the canonical escrow
                       │
                       │ creator signs approve_work
                       ▼
              provider's Solana address
```

**Answer to "can the swapped naira go to the user's FossaPay address or to our
escrow?"** — It has to end up in **the escrow**, and the only way in is through
the relayer's token account, because that is the account `create_task` debits.
Sending it to the user's FossaPay address first would be a pass-through: their
wallet → (FossaPay signs a transfer) → relayer's account → vault. It adds a
vendor signature to the critical path, buys nothing, and hits FossaPay's
**10 signing requests per minute** cap on a production-only endpoint.

The FossaPay address still has a job, on the other side of the trade:

| Address | Owner | Used for | Signatures needed |
|---|---|---|---|
| Relayer's ATA | **Us** | The custodial creator's account — every escrow passes through it | Ours |
| Provider's address | Provider | The destination of `approve_work` | **None** — the relayer signs; the address only receives |
| Payer's address | Payer | Only if the payer wants a Reach-held on-chain balance or a USDC refund | Optional |

**Therefore: the payer does not need a FossaPay address to fund a task.** A
payer paying USDC sends it to the treasury ATA (or signs `create_task`
themselves, `payer_type = "wallet"`). A payer paying naira never sees a Solana
address at all. FossaPay is needed only for **providers who have no Solana
wallet**, where their custodial address is a receive-only destination.

## 3. Funding rails (payer side)

| | Naira | USDC (self-custody) | USDC (custodial) |
|---|---|---|---|
| What the payer does | KYC form (name, NIN, BVN), then transfers naira to the virtual account Obiex shows | Signs `create_task` in Phantom/Solflare | Sends USDC to the treasury ATA |
| What we do | Obiex collection → name match → USDC → withdrawal on SOL → relayer ATA | Relayer records the tx | Relayer signs `create_task` from its ATA |
| `payer_type` | `custodial` | `wallet` | `custodial` |
| Requires BVN/NIN | **Yes** | No | No |
| Needs FossaPay | No | No | No |

**On showing the payer a FossaPay address:** don't, for funding. It adds a
production-only signature to every funded task, and the payer gets nothing
for it — the escrow still has to be locked by the relayer. Show the treasury
ATA instead and attribute the payment from the transfer's sender address. If
we later want a Reach-held on-chain balance for a naira payer (so they can be
refunded in USDC), that is the moment to introduce their FossaPay address.

## 4. Cash-out (provider side)

The on-chain settlement is always USDC to an address. What changes is what the
provider does next.

**Decision for this milestone: case A.** The provider has their own Solana
wallet, `approve_work` releases USDC straight to it, and they convert to naira
themselves using any exchange they like. Nothing else runs on our side.

| Case | Provider has | Path | Status |
|---|---|---|---|
| **A** | **Their own Solana wallet** | `approve_work` → their address → they convert to naira themselves | **This milestone** |
| B | An exchange account (Obiex, Yellow Card, …) | `approve_work` → their exchange deposit address → they withdraw naira themselves | Deferred |
| C | Neither | `approve_work` → a custodial address we control → we pull the USDC back → Obiex fiat withdrawal → their bank | Deferred |

Case A needs two things from us:

1. The provider records their own Solana address (`PUT /users/me/onchain-address`,
   stored on `users.onchain_address`).
2. Their USDC token account has to exist before the release — a provider who
   has never held USDC on Solana has no associated token account, and
   `approve_work` would fail. The relayer creates it and pays the rent.

Case C, when it comes, is a separate endpoint (`POST /payments/payouts/withdraw`)
and must be **batched**: Obiex charges about 1 per withdrawal with a minimum
around 10, so a withdrawal per provider per job is uneconomic.

## 5. Cross-rail matrix

The payer and the provider never have to agree on a rail.

| Payer pays | Provider wants | Path |
|---|---|---|
| USDC (self-custody) | USDC | Payer signs `create_task` → escrow → `approve_work` → provider address |
| USDC (custodial) | USDC | USDC → treasury ATA → relayer signs → escrow → provider address |
| Naira | USDC | Obiex collection → USDC → relayer ATA → relayer signs → escrow → provider address (FossaPay if they have no wallet) |
| Naira | Naira | Same as above, then a separate off-ramp request to the provider's bank |
| USDC | Naira | Payer → treasury ATA → escrow → provider address, then a separate off-ramp request |

## 6. The services flow needs funding too

`ServiceRequest` is the services analogue of a funded job, and it has no
payment today: request → accept → complete, with the money moving nowhere.

Under Model 1 the **requester funds when they request**, not when the provider
accepts:

```
POST /services/requests  →  funding opens (naira or USDC)
   →  escrow locked on-chain  →  provider accepts  →  work  →  approve  →  release
```

### Task id namespacing (must be fixed before any service escrow exists)

The program's PDAs are seeded with `[b"task", task_id.to_le_bytes()]`, so the
task id is **global**. Today `Job.onchain_task_id` is the job's own id (the
doc's "1:1 ID parity"). A `ServiceRequest` with id 5 would collide with job 5
and reuse the same PDA.

- Jobs keep `task_id = job.id` (doc parity).
- Service requests use a namespaced id: `task_id = 1_000_000_000 + request_id`.
- `ServiceRequest` gains `onchain_task_id`, `onchain_tx_hash`,
  `funding_status`, `payer_type`, `onchain_status`.

## 7. Deltas against the architecture doc on `main`

| Doc says | Plan does | Why |
|---|---|---|
| "FossaPay collects fiat, auto-converts to stablecoins, triggers the relayer" | Obiex (or Yellow Card) collects and converts; FossaPay provides provider addresses | FossaPay has no fiat→stablecoin conversion |
| "Relayer Keypair Engine ... holds an automated Solana keypair" | Unchanged — our own keypair | — |
| "`payer_type = custodial`, the backend signs `approve_work`" | Unchanged | — |
| "Escrow locked when the task is created" | Unchanged, and extended to service requests | The services flow had no funding at all |
| Provider is paid USDC on-chain | Unchanged; naira cash-out is a later, separate step | Keeps the chain truth clean |
| `task_id = job.id` | Kept for jobs; service requests get a namespaced id | The PDA seed is global, so ids collide otherwise |

## 8. Work items

### A. Funding the services flow
1. `models/services.py` — add the on-chain columns to `ServiceRequest`.
2. `schemas/enums.py` — reuse `FundingStatus`, `PayerType`, `FundingRail`.
3. `services/funding.py` — `create_obiex_collection` and
   `create_crypto_deposit_address` currently take a `job`; make them take a
   `(target_type, target_id, amount, user, profile)` tuple so both flows share
   them.
4. `services/chain.py` — `fund_task_escrow` currently assumes a `Job`;
   generalise to any escrow target.
5. `routers/payments.py` — `POST /payments/service-requests/{id}/collection`,
   `GET /payments/service-requests/{id}`, `POST /payments/service-requests/{id}/release`.
6. `routers/services.py` — `POST /services/requests` creates the request in
   `pending_funding`; acceptance requires a funded escrow.
7. Migration — the new `ServiceRequest` columns.

### B. The payment surface the user sees
1. `POST /payments/{target}/collection` — one endpoint for both rails, with
   `rail` in the body, returning either bank-transfer details (naira) or a
   deposit address (USDC).
2. A KYC step for the naira rail: name, NIN, BVN, date of birth, address.
   The `payment_profiles` table already carries `bvn`/`nin`; validate them.
3. The treasury address for the crypto rail, with the amount and a reference
   so the payer can be attributed (`getSignaturesForAddress` on the treasury
   ATA → sender address → user).
4. `GET /payments/{target}` — funding state, escrow state, on-chain status.

### C. Provider payout destination
1. ~~`users.onchain_address`~~ — done: the provider's own Solana address,
   validated as a canonical 43/44-character base58 public key
   (`validate_solana_address`).
2. `PUT /users/me/onchain-address` — done.
3. `POST /payments/{target}/release` — done: resolves the provider's own
   address, creates their USDC token account if it does not exist, then signs
   `approve_work`.
4. Deferred: the FossaPay custodial address as a fallback destination, and the
   Obiex/Yellow Card naira off-ramp for providers who have no wallet of their
   own (cases B and C).

### D. Treasury reconciliation
1. Track the treasury ATA balance; alert below the float needed.
2. Attribute inbound transfers to payers and to funding intents.
3. Batch the Obiex withdrawal rather than one per task (Obiex charges ~1 per
   withdrawal, with a ~10 minimum).

### E. Provider naira cash-out (later milestone)
1. `POST /payments/payouts/withdraw` — the provider's bank details, an amount,
   and the Obiex/Yellow Card off-ramp call.
2. Reconciliation: the on-chain release and the off-ramp payout must be
   matched to each other.

## 9. Open questions

1. Should the naira rail be Obiex or Yellow Card? Yellow Card's direct
   settlement removes the withdrawal hop (naira → USDC straight to the
   treasury ATA) and it has a sandbox; Obiex's collections are simpler but
   gated and need a withdrawal step. Both need a business account.
2. Does Yellow Card accept a direct settlement to an arbitrary (non-whitelisted)
   Solana address? Their balance pay-outs are whitelisted; the receive request
   takes a free-form `walletAddress`. This decides the treasury design.
3. Do we want a Reach-held on-chain balance for naira payers (their FossaPay
   address), or is naira-in/naira-out the customer promise?
4. Which USDC mint do the providers' addresses hold? It must be
   `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`, the SPL USDC the program's
   `stable_coin_mint` check accepts.
