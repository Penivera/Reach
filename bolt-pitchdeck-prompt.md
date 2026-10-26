# Bolt.new Prompt — Reach Pitch Deck

## Prompt

```
Build a pitch deck as a full-screen single-page web app using React + Tailwind CSS. The deck should have keyboard arrow navigation, smooth cross-fade slide transitions, and a minimal progress bar at the bottom edge.

## DESIGN SYSTEM — Cloudflare-inspired, matching this exact spec:

BACKGROUNDS:
- Alternate between pure white (#FFFFFF) slides and near-black (#0F172A / slate-900) slides
- White slides for problem framing, features, and data
- Dark slides for title, architecture, closing, and dramatic reveals
- Each slide has a thin bottom bar (full-width, ~6px height, subtle rounded-lg container card background color like slate-100 on white slides, slate-800 on dark slides) sitting at the very bottom

TYPOGRAPHY:
- Primary font: Inter (bold for headlines, regular for body)
- Monospace accent font: JetBrains Mono (for labels, tags, technical terms, numbered markers)
- Headline hierarchy on EVERY content slide follows this exact pattern:
  - Line 1: Small caps label in JetBrains Mono, bold, 11px, tracking-widest, in the accent color (orange). Example: " THE TRUST GAP " or " HOW REACH WORKS "
  - Line 2: Large bold Inter headline, 30-38px, in the primary text color. This states the TAKEAWAY, not a topic. Example: "Healthy Infrastructure Can Still Be Unreachable." not "Problem Statement"
  - Bottom of slide: One-line summary sentence in Inter, 14px, muted gray (slate-500 on white, slate-400 on dark)
- Body text: Inter, 14-16px, slate-500 (#64748B) on white slides, slate-400 on dark slides
- Near-black text (#0F172A) for titles and card headings on white slides
- White (#FFFFFF) for titles on dark slides

COLOR PALETTE:
- Accent: Orange (#EA580C / orange-600 for tags and markers, #F97316 / orange-500 for highlights)
- Use orange ONLY for: the small-caps label, numbered markers (01, 02, 03), status badges, and the final slide's closing keyword
- Success green: #166534 / #15803D for positive states
- Danger red: #991B1B / #B91C1C for negative states / problems
- NEVER use orange as a background fill. It is always text or small badge only.

LAYOUT:
- Content cards: Rounded-lg containers with subtle slate-100 backgrounds on white slides, slate-800 on dark slides
- Cards arranged in 2-column or 3-column grids, never bullet-point lists
- Generous whitespace — content sits in roughly the center 85% of the slide, with comfortable margins
- Small icons inside subtle circular icon containers (slate-200 circle, icon inside) at top of each card
- Numbered markers (01, 02, 03) in JetBrains Mono bold orange, placed left of card titles
- Flow connectors: Use a centered arrow icon (→) between card groups when showing a transformation or comparison

CARDS:
- Each card has: icon container at top → bold Inter title (16-18px, #0F172A) → description in Inter regular (14px, #64748B)
- Cards have equal width, aligned in clean grids
- Status badges (small rounded pills) in JetBrains Mono 10-11px, bold, placed top-right of cards or sections: "DOWN" in red, "HEALTHY" in green, "ACTIVE" in orange, etc.

---

## SLIDES — 10 slides total:

SLIDE 1 — TITLE (dark slide, #0F172A background)
- Small logo icon placeholder (circle, 20px) top-left
- Next to it in JetBrains Mono bold orange 11px: "LOCAL SERVICES & ESCROW"
- Large bold Inter headline: "REACH" (60px, white, slight letter-spacing)
- Below: "Find anything, close to home." in Inter regular 18px, slate-400 (#94A3B8)
- Bottom bar with three JetBrains Mono labels in small pills: "SOLANA ESCROW" | "FIAT RAILS" | "GEOSPATIAL MATCHING"
- Bottom-right: "Penivera" in Inter bold white 14px, below it "Pitch Deck 2026" in JetBrains Mono bold orange 11px

SLIDE 2 — PROBLEM (white slide)
- Label: " THE TRUST GAP "
- Headline: "Money Moves on Hope. Not Guarantees."
- Two-column layout:
  LEFT column — "STATUS QUO" badge (red, JetBrains Mono). Title "Local Services Today" in red (#991B1B). Three cards stacked:
    • 01 — "No Payment Guarantee" / "Providers complete work with no assurance of getting paid"
    • 02 — "Upfront Risk" / "Clients pay before seeing results, with no recourse"
    • 03 — "Word-of-Mouth Pricing" / "No reliable way to discover or compare local service costs"
  RIGHT column — center arrow (→) icon pointing to empty/greyed state with text "?" to create tension
- Bottom summary: "A ₦4T+ informal services market running entirely on social trust."

SLIDE 3 — SOLUTION (white slide)
- Label: " ESCROW-POWERED SERVICES "
- Headline: "Make Every Transaction Trustless."
- Three equal cards in a row:
    Card 1: icon (lock) — "Funds Locked" / "Client's payment is locked in a Solana escrow PDA before work begins."
    Card 2: icon (check) — "Work Verified" / "Provider completes the task. Client reviews and approves."
    Card 3: icon (wallet) — "Payment Released" / "Funds release to provider automatically. Disputes get fair on-chain splits."
- Bottom summary: "Blockchain settles the transaction. The user never sees it."

SLIDE 4 — HOW IT WORKS (white slide)
- Label: " HOW REACH WORKS "
- Headline: "Simple for Users. Powerful Underneath."
- Three-zone architecture visual (similar to Bridge's architecture slide):
  LEFT zone — "01 : CLIENT SIDE" label (slate muted). Title: "Post & Pay". Description: "Post a task with budget and location. Pay in naira via card or bank transfer."
  CENTER zone — "02 : REACH PLATFORM" label (orange, JetBrains Mono). Title: "Escrow & Match" (bold, orange-tinted). Description: "Server-side relayer locks funds in Solana escrow. PostGIS matches nearby providers." Badge: "CUSTODIAL RELAYER"
  RIGHT zone — "03 : PROVIDER SIDE" label (slate muted). Title: "Work & Earn". Description: "Accept jobs, complete work, receive USDC or cash out to naira bank account."
- Bottom summary: "Three funding rails: Naira cards, bank transfer, or native Solana wallet."

SLIDE 5 — PRODUCT FEATURES (white slide)
- Label: " THE PLATFORM "
- Headline: "What We've Built."
- 2×3 grid of feature cards, each with numbered marker (01-06) in orange JetBrains Mono:
    01 — "Geospatial Discovery" / "PostGIS-powered search finds providers within your radius"
    02 — "On-Chain Escrow" / "Solana Anchor program with collateral, advances, and dispute resolution"
    03 — "Fiat Payment Rails" / "Obiex and FossaPay integration for naira card and bank payments"
    04 — "In-App Messaging" / "Real-time chat between clients and providers"
    05 — "Reviews & Ratings" / "Bidirectional reputation system builds trust over time"
    06 — "KYC Verification" / "NIN and BVN identity checks via FossaPay"
- Bottom summary: "PWA-ready. Push notifications. Cloudinary media. Production-grade."

SLIDE 6 — MARKET (white slide)
- Label: " MARKET OPPORTUNITY "
- Headline: "Nigeria's Service Economy Is Massive and Underserved."
- Four stat cards in a row, each with a large bold number and label below:
    "200M+" / "Population"
    "70%" / "Under 30"
    "#1" / "African Crypto Adoption"
    "₦4T+" / "Informal Services"
- Below: Two-column comparison cards:
  LEFT — "Starting Point" / "Akwa Ibom & Uyo — Emerging tech hub with high artisan density, strong smartphone adoption, and a tight-knit service economy"
  RIGHT — "Expansion Path" / "South-South (Port Harcourt, Calabar) → Lagos → Abuja → Accra → Nairobi"
- Bottom summary: "Mobile-first, young, crypto-fluent. The market is ready."

SLIDE 7 — BUSINESS MODEL (white slide)
- Label: " REVENUE MODEL "
- Headline: "Transparent, On-Chain Revenue."
- Three revenue cards side by side:
    Card 1: "2.5%" large bold number, "Task Creation Fee" title, "Charged when escrow is funded. Flows to protocol fee vault." description
    Card 2: "5%" large bold number, "Platform Commission" title, "Deducted from provider payout on task completion." description
    Card 3: "10%" large bold number, "Cancellation Fee" title, "Charged when a client cancels an active task." description
- Bottom callout card (full-width, darker background): "All revenue sits in an on-chain Solana fee vault — public, auditable, verifiable."
- Bottom summary: "Revenue is protocol infrastructure, not an opaque ledger."

SLIDE 8 — TECH STACK (dark slide, #0F172A background)
- Label: " TECHNICAL ARCHITECTURE " (orange on dark)
- Headline: "Built for Scale and Trust." (white)
- Five horizontal rows (like Bridge's slide 8), each a full-width bar with:
    01 — "FRONTEND" / "Next.js 16 + React 19 + TypeScript + Tailwind v4"
    02 — "BACKEND" / "FastAPI (async) + SQLAlchemy 2.0 + asyncpg + Pydantic v2"
    03 — "DATABASE" / "PostgreSQL + PostGIS + Redis"
    04 — "SMART CONTRACT" / "Solana Anchor (Rust) — escrow, disputes, fee vault"
    05 — "INFRASTRUCTURE" / "Docker Compose + Cloudinary CDN + Firebase Push"
- Side stat: "31,000+ lines of code" in a subtle badge
- Bottom summary: "158 tests. End-to-end type safety. Server-side Solana relayer." (slate-400)

SLIDE 9 — ROADMAP (white slide)
- Label: " EXECUTION TIMELINE "
- Headline: "From Code to Market."
- Five milestone cards in a horizontal row, each with status indicator:
    ✅ "Q3 2026" / "Backend + Smart Contract" / "Core complete. 158 tests passing."
    🔄 "Q4 2026" / "Frontend + Staging" / "Payment screens, wallet integration, end-to-end testing."
    🎯 "Q1 2027" / "Uyo Beta" / "Invite-only launch in Akwa Ibom. First real escrow settlements."
    🚀 "Q2 2027" / "Multi-City" / "Product orders. Abuja + Port Harcourt."
    🌍 "Q3 2027" / "West Africa" / "Multichain intents. Accra + Nairobi."
- Bottom summary: "The backend is built. The contract is audited. We're closing the last mile to market."

SLIDE 10 — CLOSING (dark slide, #0F172A background)
- Small logo icon centered near top
- "REACH" in JetBrains Mono bold orange 11px, next to icon
- Large bold Inter text, centered, multi-line:
  "YOUR MONEY." (white, 48px)
  "YOUR WORK." (white, 48px)
  "SETTLED." (orange #F97316, 48px)
- Below: "Trustless escrow for Africa's local service economy." in Inter regular 15px, slate-400
- Subtle horizontal rule (slate-700, thin)
- Contact: "team@penivera.com" in Inter, white

Add a thin slide-number indicator (e.g. "3 / 10") bottom-right in JetBrains Mono, 11px, muted. Keep all transitions as clean cross-fades (200ms). No bouncing, no scaling, no parallax. The entire deck should feel like a Cloudflare product announcement — clinical precision, strategic use of color, every word earning its place.
```
