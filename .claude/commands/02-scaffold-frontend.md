# Phase 2: Frontend -- Build a Next.js + Tailwind Chat UI from Scratch

## What You Will Learn
- Next.js 14 App Router architecture (layouts, pages, server/client components)
- Tailwind CSS + Shadcn/ui for production-grade design system
- GraphQL client setup with urql for queries, mutations, and subscriptions
- Real-time streaming chat via GraphQL subscriptions over WebSocket
- Component-driven development with Vitest + React Testing Library

## Prerequisites
- Phase 1 complete (Gateway service running at localhost:8000/graphql)
- Node.js 20+, pnpm installed

## Background: Why Next.js App Router?
The App Router (introduced in Next.js 13.4) enables React Server Components,
streaming, and nested layouts. Server Components reduce client-side JavaScript
by rendering on the server. For our AI platform, the agent list and document
pages are server-rendered (fast initial load), while the chat interface is a
client component (real-time streaming).

## Step-by-Step Instructions

### Step 1: Initialize the Next.js Project
```bash
cd frontend
pnpm create next-app@14 . --typescript --tailwind --eslint --app --src-dir \
  --import-alias "@/*" --no-turbo
```

### Step 2: Install Dependencies
```bash
pnpm add @urql/core urql graphql @urql/exchange-graphcache
pnpm add @radix-ui/react-slot class-variance-authority clsx tailwind-merge
pnpm add lucide-react reactflow
pnpm add -D vitest @testing-library/react @testing-library/jest-dom
pnpm add -D @playwright/test @graphql-codegen/cli
```

**Why urql over Apollo?** urql is lighter (~5KB vs ~30KB), has better TypeScript
support, and its exchange architecture makes caching and subscriptions composable.
For a chat app with streaming, urql's subscription support is simpler.

### Step 3: Set Up Shadcn/ui Design System
```bash
pnpm dlx shadcn-ui@latest init
pnpm dlx shadcn-ui@latest add button card dialog input textarea
pnpm dlx shadcn-ui@latest add dropdown-menu avatar badge separator scroll-area
```

**Why Shadcn/ui?** It's not a component library -- it's copy-pasted, customizable
components built on Radix UI primitives. You own the code. No version lock-in.
Tailwind-native styling.

### Step 4: Create the Layout Shell

Create `frontend/src/app/layout.tsx` -- Root layout with:
- GraphQL provider (urql)
- Navigation sidebar
- Top navbar with user info
- Theme support (dark/light)

Create layout components:
- `src/components/layout/Navbar.tsx` -- Top bar with project name, user avatar
- `src/components/layout/Sidebar.tsx` -- Nav links: Dashboard, Agents, Chat, Documents, Workflows, Costs, Observability
- `src/components/layout/Footer.tsx` -- Version, docs link

### Step 5: Set Up GraphQL Client

Create `src/lib/graphql/client.ts`:
```typescript
import { Client, cacheExchange, fetchExchange, subscriptionExchange } from 'urql';
import { createClient as createWSClient } from 'graphql-ws';

const wsClient = createWSClient({
  url: 'ws://localhost:8000/graphql',
});

export const client = new Client({
  url: 'http://localhost:8000/graphql',
  exchanges: [
    cacheExchange,
    fetchExchange,
    subscriptionExchange({
      forwardSubscription: (request) => ({
        subscribe: (sink) => ({
          unsubscribe: wsClient.subscribe(request, sink),
        }),
      }),
    }),
  ],
});
```

Create query documents in `src/lib/graphql/`:
- `queries.ts` -- listAgents, getAgent, listDocuments, getCosts
- `mutations.ts` -- createAgent, sendMessage, uploadDocument
- `subscriptions.ts` -- onChatMessage (streaming chat responses)

### Step 6: Build the Chat Interface

This is the core UI. Create these components in `src/components/chat/`:

- `ChatWindow.tsx` -- Main container: message list + input bar + streaming indicator
- `MessageBubble.tsx` -- Renders user/assistant messages with markdown support
- `StreamingIndicator.tsx` -- Animated typing dots while LLM generates
- `ToolCallCard.tsx` -- Shows when agent invokes a tool (weather API, search, etc.)

**Key pattern:** The chat uses a GraphQL subscription for real-time streaming.
When the user sends a message (mutation), the subscription pushes response tokens
as they arrive from the LLM.

### Step 7: Build Agent Management Pages

- `src/app/agents/page.tsx` -- Grid of AgentCards showing all agents
- `src/app/agents/new/page.tsx` -- Form to create a new agent (name, type, instructions)
- `src/app/agents/[id]/page.tsx` -- Agent detail with config and chat history

Components:
- `src/components/agents/AgentCard.tsx` -- Card showing agent name, type, status
- `src/components/agents/AgentForm.tsx` -- Create/edit form with validation
- `src/components/agents/AgentList.tsx` -- Grid container with filtering

### Step 8: Build Document Management Page

- `src/app/documents/page.tsx` -- Upload area + document list
- `src/components/documents/UploadDropzone.tsx` -- Drag-and-drop file upload
- `src/components/documents/DocumentList.tsx` -- Table with filename, chunks, date

### Step 9: Build Placeholder Pages

Create page shells for later phases:
- `src/app/workflows/page.tsx` -- "Agent DAG visualization coming in Phase 4"
- `src/app/costs/page.tsx` -- "Cost tracking dashboard coming in Phase 9"
- `src/app/observability/page.tsx` -- "Grafana dashboards coming in Phase 6"

### Step 10: Create Custom Hooks

Create hooks in `src/lib/hooks/`:
- `useAgents.ts` -- Wraps listAgents query with loading/error states
- `useChat.ts` -- Manages chat state, sends messages, subscribes to responses
- `useCosts.ts` -- Fetches cost data for dashboard
- `useDocuments.ts` -- Manages document upload and listing

### Step 11: Write Component Tests

Create `frontend/tests/components/ChatWindow.test.tsx`:
```typescript
import { render, screen } from '@testing-library/react';
import { ChatWindow } from '@/components/chat/ChatWindow';

describe('ChatWindow', () => {
  it('renders message input', () => {
    render(<ChatWindow sessionId="test" />);
    expect(screen.getByPlaceholderText(/type a message/i)).toBeInTheDocument();
  });

  it('displays messages', () => {
    render(<ChatWindow sessionId="test" messages={mockMessages} />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

### Step 12: Create the Frontend CLAUDE.md

Create `frontend/CLAUDE.md` with frontend-specific context.

### Step 13: Create the Dockerfile

Multi-stage build (from merit-aiml frontend/Dockerfile pattern):
```dockerfile
FROM node:20-alpine AS base
FROM base AS deps
# Install dependencies
FROM deps AS builder
# Build the app
FROM base AS runner
# Production image
```

## Verification
```bash
cd frontend && pnpm dev
# Open http://localhost:3000
# - Dashboard page loads
# - Sidebar navigation works
# - Agents page shows AgentCards (mock data from gateway)
# - Chat page shows ChatWindow with input
# - Send a message -- see mock response from gateway

pnpm test  # Component tests pass
```

## Key Concepts Taught
1. **App Router** -- Server vs client components, when to use each
2. **GraphQL subscriptions** -- Real-time data over WebSocket for streaming chat
3. **Shadcn/ui** -- Ownable design system built on Radix primitives
4. **Hooks pattern** -- Encapsulate data fetching + state in reusable hooks
5. **Component-driven dev** -- Build/test components in isolation, compose into pages

## What's Next
Phase 3 (`/03-setup-data-layer`) adds persistent storage: pgvector for document
embeddings, Redis VSS for semantic caching, MinIO for file storage. The mock data
in your gateway will be replaced with real database-backed storage.
