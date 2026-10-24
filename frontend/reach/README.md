# Reach

Reach is the frontend for a local marketplace app built around everyday help and everyday needs. The idea is simple: people can compare prices, find nearby help for common tasks, and post requests for services they need done.

Think of it as a place where users can quickly answer questions like:

- How much does this cost?
- How much would it take to hire someone for this?
- Who nearby can help with this task right now?

## What Reach does

Reach is designed for everyday tasks and services such as:

- plumbing
- hairdressing
- picking something up for someone
- simple home help
- local service requests
- small jobs that people want completed nearby

The platform is meant to support two core experiences:

1. People looking for help
2. People offering services or completing tasks

## Current frontend scope

The current frontend includes:

- a landing page and authentication flows (sign-in, sign-up, location)
- home, chat, request, order, product, and payment routes
- profile and account flows, including becoming a provider
- provider dashboard, listings, job detail, and payout screens
- API helpers for auth, jobs, services, users, and provider profiles
- reusable UI components for forms and buttons

Still not integrated:

- the Model 1 payment profile and funding/checkout screens
- the provider naira off-ramp UI
- the Solana provider wallet flow for `apply` / `complete_task`
- a one-click USDC withdrawal to the off-ramp deposit address

The existing `lib/near/*` wallet integration is legacy and is not the current
settlement path. The backend payment APIs are implemented, but the frontend
still needs to be wired to them.

## Tech stack

Reach is built with:

- Next.js
- React
- TypeScript
- Tailwind CSS
- ESLint

## Getting started

### Prerequisites

- Node.js (latest stable version recommended)
- pnpm

### Install dependencies

```bash
pnpm install
```

### Run the development server

```bash
pnpm dev
```

Then open http://localhost:3000 in your browser.

## Environment variables

The app uses the following environment variables:

- `NEXT_PUBLIC_API_URL` — backend base URL; defaults to `http://localhost:8000`
- `NEXT_PUBLIC_NOMINATIM_EMAIL` — contact email for the Nominatim geocoder;
  defaults to `contact@example.com`

## Project structure

A quick overview of the frontend structure:

- app/ - routes and page components
- components/ - shared UI and layout components
- lib/ - API and auth helper modules
- public/ - static assets

## Backend note

The backend lives in `../../backend/`. There is no backend README; use the
FastAPI app entry point (`backend/app.py`), `backend/.env.example`, and the
payment docs in `../../docs/`.

## Development notes

This frontend is wired for authentication and marketplace flows and uses the
backend API through a shared API layer. Payment and off-ramp integration is
still in progress; do not infer payment success from a client-side action.
Only the backend state is authoritative.


Reach is currently in an early but active stage, with authentication and core frontend structure in place and the broader marketplace experience still being built out.
