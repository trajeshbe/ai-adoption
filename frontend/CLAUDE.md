# Frontend -- Next.js 14 + Tailwind + Shadcn/ui

## Purpose
Web UI for the AI Agent Platform. Chat interface, agent management, document upload,
workflow visualization, cost tracking, and observability dashboards.

## Tech
Next.js 14 (App Router), Tailwind CSS 3.4+, Shadcn/ui, urql (GraphQL client),
React Flow (DAG visualization), Vitest + Playwright

## Key Directories
- `src/app/` -- App Router pages (layout, agents, chat, documents, workflows, costs, observability)
- `src/components/ui/` -- Shadcn/ui primitives (button, card, dialog, input)
- `src/components/chat/` -- ChatWindow, MessageBubble, StreamingIndicator, ToolCallCard
- `src/components/agents/` -- AgentCard, AgentForm, AgentList
- `src/components/documents/` -- UploadDropzone, DocumentList
- `src/components/layout/` -- Navbar, Sidebar, Footer
- `src/lib/graphql/` -- urql client, queries, mutations, subscriptions
- `src/lib/hooks/` -- useAgents, useChat, useCosts, useDocuments

## Patterns
- Server components for static pages (agents list, documents)
- Client components for interactive UI (chat, file upload)
- GraphQL subscriptions for streaming chat responses
- All data fetching via custom hooks wrapping urql

## Run
`pnpm dev` (port 3000)

## Test
`pnpm test` (Vitest) / `pnpm test:e2e` (Playwright)
