# Frontend -- Next.js 14 + Tailwind + Shadcn/ui

## Purpose
Web UI for the AI Agent Platform. Chat interface with 3 agent types (Quiz, Weather, RAG),
agent management, document upload, workflow visualization, cost tracking,
observability dashboards, and live Kubernetes scaling dashboard.

## Tech
Next.js 14 (App Router), Tailwind CSS 3.4+, Shadcn/ui, React Flow (DAG visualization),
Vitest + Playwright. GraphQL via direct fetch() to gateway.

## Key Pages
- `/` -- Dashboard with overview cards linking to all features
- `/chat` -- Self-contained chat UI with agent selector, config panel, tool call display
- `/agents` -- Agent list, create, and detail views
- `/documents` -- Document upload dropzone and list
- `/workflows` -- DAG visualization (React Flow)
- `/costs` -- Cost tracking dashboard
- `/observability` -- Traces, logs, metrics dashboards
- `/scaling` -- Live Kubernetes scaling dashboard (polls /metrics + /k8s every 3s)

## Key Directories
- `src/app/` -- App Router pages (all routes above)
- `src/components/ui/` -- Shadcn/ui primitives (button, card, dialog, input)
- `src/components/layout/` -- Navbar (8 nav items), Sidebar (8 items with icons)
- `src/lib/graphql/` -- GraphQL client, queries, mutations, subscriptions
- `src/lib/hooks/` -- useAgents, useChat, useCosts, useDocuments

## Patterns
- Server components for static pages (agents list, documents)
- Client components for interactive UI (chat, scaling dashboard)
- Chat page uses direct fetch() to GraphQL endpoint (no urql dependency)
- Scaling page polls gateway /metrics and /k8s endpoints every 3 seconds
- UUID generation via crypto.getRandomValues (SSR-compatible)
- NEXT_PUBLIC_GRAPHQL_URL is build-time (must rebuild, not just restart)

## Key Implementation Details
- Chat page (`src/app/chat/page.tsx`): Self-contained with agent selector,
  config panel (gear button), tool call cards (amber), latency/cost badges
- Scaling page (`src/app/scaling/page.tsx`): Cluster nodes, HPA gauges,
  pods table, service health, live traffic metrics
- Navbar/Sidebar include Chat and Scaling links with active state detection
- Next.js 14 uses `useParams()` hook (NOT `use(params)` which is Next.js 15)

## Run
```bash
# Development
NEXT_PUBLIC_GRAPHQL_URL=http://<host-ip>:8050/graphql pnpm dev

# Production build
NEXT_PUBLIC_GRAPHQL_URL=http://<host-ip>:8050/graphql npx next build
NEXT_PUBLIC_GRAPHQL_URL=http://<host-ip>:8050/graphql npx next start -p 8055 -H 0.0.0.0
```

## Test
`pnpm test` (Vitest) / `pnpm test:e2e` (Playwright)
