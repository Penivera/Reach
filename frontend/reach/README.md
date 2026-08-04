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

- a landing page
- sign-in and sign-up flows
- authentication UI connected to the backend API
- reusable UI components for forms and buttons
- API helpers for auth-related endpoints

Planned or expected product areas include:

- comparing prices for services and goods
- posting services for hire
- posting tasks that need to be completed
- user dashboards and profile flows
- richer listings and booking experiences

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

The app uses the following environment variable:

- NEXT_PUBLIC_API_URL

If it is not provided, the app defaults to:

```bash
http://localhost:8000
```

## Project structure

A quick overview of the frontend structure:

- app/ - routes and page components
- components/ - shared UI and layout components
- lib/ - API and auth helper modules
- public/ - static assets

## Backend note

The backend is expected to be run from the full repository. If you are working in the monorepo, follow the backend README for setup and start instructions.

## Development notes

This frontend is already wired for authentication flows and uses the backend API through a small shared API layer. The product experience is still expanding, so expect additional routes and features as the marketplace evolves.


Reach is currently in an early but active stage, with authentication and core frontend structure in place and the broader marketplace experience still being built out.
