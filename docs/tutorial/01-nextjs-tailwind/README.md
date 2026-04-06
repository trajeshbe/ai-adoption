# Tutorial 01: Next.js 14 + Tailwind CSS

> **Objective:** Learn how to build modern web UIs with Next.js and Tailwind CSS — the frontend stack of our AI platform.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [Tailwind CSS Deep Dive](#3-tailwind-css-deep-dive)
4. [Project Setup](#4-project-setup)
5. [Exercises](#5-exercises)
6. [Advanced Topics](#6-advanced-topics)
7. [How It's Used in Our Project](#7-how-its-used-in-our-project)
8. [Best Practices](#8-best-practices)
9. [Further Reading](#9-further-reading)

---

## 1. Introduction

### What is Next.js?

**Next.js** is a React-based framework for building full-stack web applications. While React itself is a library for building UI components, Next.js adds:

- **File-based routing** — each file in `app/` becomes a URL route
- **Server-Side Rendering (SSR)** — pages render on the server for faster loads and SEO
- **API Routes** — build backend endpoints inside your frontend project
- **Server Components** — components that run on the server, reducing client-side JavaScript

Think of React as the engine and Next.js as the car — it gives you everything you need to drive.

### What is Tailwind CSS?

**Tailwind CSS** is a utility-first CSS framework. Instead of writing custom CSS classes:

```css
/* Traditional CSS */
.btn-primary {
  background-color: blue;
  padding: 8px 16px;
  border-radius: 4px;
  color: white;
}
```

You compose utility classes directly in your HTML/JSX:

```jsx
<button className="bg-blue-500 px-4 py-2 rounded text-white">Click me</button>
```

### Why Together?

| Feature | Benefit |
|---------|---------|
| Next.js App Router | Modern React patterns with server/client split |
| Tailwind CSS | Rapid UI development without CSS file bloat |
| TypeScript | Type safety across the full stack |
| Built-in optimizations | Image, font, and bundle optimization out of the box |

---

## 2. Core Concepts

### 2.1 App Router & File-Based Routing

In Next.js 14, the `app/` directory defines your routes:

```
app/
├── page.tsx            → /
├── about/
│   └── page.tsx        → /about
├── chat/
│   └── page.tsx        → /chat
├── docs/
│   └── [slug]/
│       └── page.tsx    → /docs/any-value (dynamic)
└── layout.tsx          → Shared layout for all pages
```

**Key files:**
- `page.tsx` — The UI for a route
- `layout.tsx` — Shared wrapper (persists across navigation)
- `loading.tsx` — Loading UI (shown while page loads)
- `error.tsx` — Error boundary
- `not-found.tsx` — 404 page

### 2.2 Server Components vs Client Components

By default, all components in the `app/` directory are **Server Components**:

```tsx
// This runs on the SERVER (default)
// Can access databases, file system, environment variables
export default async function DashboardPage() {
  const data = await db.query("SELECT * FROM metrics"); // Direct DB access!
  return <div>{data.map(d => <p key={d.id}>{d.name}</p>)}</div>;
}
```

Add `"use client"` to make a **Client Component** (runs in the browser):

```tsx
"use client"; // This runs in the BROWSER

import { useState } from "react";

export default function Counter() {
  const [count, setCount] = useState(0); // useState needs the browser
  return (
    <button onClick={() => setCount(count + 1)}>
      Clicked {count} times
    </button>
  );
}
```

**When to use which:**

| Server Component | Client Component |
|-----------------|-----------------|
| Fetch data | Interactive UI (clicks, inputs) |
| Access backend resources | Use browser APIs (localStorage, etc.) |
| Keep sensitive info on server | Use React hooks (useState, useEffect) |
| Reduce client-side JS | Event listeners |

### 2.3 React Hooks Refresher

```tsx
"use client";
import { useState, useEffect, useContext, useRef, useMemo } from "react";

function Example() {
  // useState — manage local state
  const [name, setName] = useState("");

  // useEffect — side effects (API calls, subscriptions)
  useEffect(() => {
    fetch("/api/user").then(r => r.json()).then(setName);
  }, []); // [] = run once on mount

  // useRef — reference DOM elements or persist values across renders
  const inputRef = useRef<HTMLInputElement>(null);

  // useMemo — expensive computations, only recalculate when deps change
  const greeting = useMemo(() => `Hello, ${name}!`, [name]);

  return <input ref={inputRef} value={name} onChange={e => setName(e.target.value)} />;
}
```

### 2.4 SSR, SSG, and ISR

| Strategy | What It Means | When To Use |
|----------|---------------|-------------|
| **SSR** (Server-Side Rendering) | Page rendered on every request | Dynamic data (user dashboards) |
| **SSG** (Static Site Generation) | Page rendered at build time | Content that rarely changes (docs) |
| **ISR** (Incremental Static Regeneration) | Static + revalidate after N seconds | Blog posts, product pages |

```tsx
// SSR — fresh data on every request (default for async components)
export default async function Page() {
  const data = await fetch("https://api.example.com/data", { cache: "no-store" });
  return <div>{/* ... */}</div>;
}

// SSG — cached forever (default for non-async)
export default async function Page() {
  const data = await fetch("https://api.example.com/data", { cache: "force-cache" });
  return <div>{/* ... */}</div>;
}

// ISR — revalidate every 60 seconds
export default async function Page() {
  const data = await fetch("https://api.example.com/data", { next: { revalidate: 60 } });
  return <div>{/* ... */}</div>;
}
```

### 2.5 Layouts

Layouts wrap pages and persist across navigation (no re-render):

```tsx
// app/layout.tsx — Root layout (required)
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white">
        <nav className="p-4 border-b border-gray-800">AI Platform</nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
```

---

## 3. Tailwind CSS Deep Dive

### 3.1 Utility-First Approach

Tailwind provides utility classes for every CSS property:

```jsx
// Spacing: p-{size}, m-{size}, px-{size}, py-{size}
<div className="p-4 mx-auto mt-8">

// Colors: text-{color}-{shade}, bg-{color}-{shade}
<p className="text-blue-500 bg-gray-900">

// Flexbox: flex, items-center, justify-between, gap-{size}
<div className="flex items-center justify-between gap-4">

// Grid: grid, grid-cols-{n}, gap-{size}
<div className="grid grid-cols-3 gap-6">

// Typography: text-{size}, font-{weight}, leading-{size}
<h1 className="text-3xl font-bold leading-tight">

// Borders: border, border-{color}, rounded-{size}
<div className="border border-gray-700 rounded-lg">

// Sizing: w-{size}, h-{size}, max-w-{size}
<div className="w-full max-w-4xl h-screen">
```

### 3.2 Responsive Design

Tailwind uses mobile-first breakpoints with prefix modifiers:

```jsx
// Mobile first, then scale up
<div className="
  w-full          /* Mobile: full width */
  md:w-1/2        /* Medium screens (768px+): half width */
  lg:w-1/3        /* Large screens (1024px+): third width */
  xl:w-1/4        /* XL screens (1280px+): quarter width */
">
```

| Prefix | Min Width | Typical Device |
|--------|-----------|----------------|
| (none) | 0px | Mobile |
| `sm:` | 640px | Small tablet |
| `md:` | 768px | Tablet |
| `lg:` | 1024px | Laptop |
| `xl:` | 1280px | Desktop |
| `2xl:` | 1536px | Large desktop |

### 3.3 Dark Mode

```jsx
// tailwind.config.ts
export default {
  darkMode: "class", // or "media" for OS preference
  // ...
};

// Usage: dark: prefix
<div className="bg-white dark:bg-gray-900 text-black dark:text-white">
  <p className="text-gray-600 dark:text-gray-400">Adapts to dark mode!</p>
</div>
```

### 3.4 Common Patterns

```jsx
// Card
<div className="rounded-xl border border-gray-700 bg-gray-800 p-6 shadow-lg">
  <h3 className="text-lg font-semibold">Card Title</h3>
  <p className="mt-2 text-gray-400">Card content here.</p>
</div>

// Badge
<span className="inline-flex items-center rounded-full bg-green-500/10 px-2 py-1 text-xs font-medium text-green-400">
  Active
</span>

// Input field
<input
  className="w-full rounded-lg border border-gray-600 bg-gray-800 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
  placeholder="Type here..."
/>

// Hover & transition
<button className="rounded bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-500 active:bg-blue-700">
  Click Me
</button>
```

### 3.5 Custom Theme

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eff6ff",
          500: "#3b82f6",
          900: "#1e3a5f",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
```

---

## 4. Project Setup

### Step-by-step from scratch:

```bash
# 1. Create a new Next.js project with Tailwind
npx create-next-app@latest my-ai-app --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# 2. Navigate into the project
cd my-ai-app

# 3. Start the development server
npm run dev

# Open http://localhost:3000
```

### Project structure:

```
my-ai-app/
├── src/
│   └── app/
│       ├── globals.css      ← Tailwind directives
│       ├── layout.tsx        ← Root layout
│       ├── page.tsx          ← Home page (/)
│       └── favicon.ico
├── public/                   ← Static assets
├── tailwind.config.ts        ← Tailwind configuration
├── next.config.ts            ← Next.js configuration
├── tsconfig.json             ← TypeScript configuration
└── package.json
```

### globals.css:

```css
@tailwind base;
@tailwind components;
@tailwind layer utilities;

/* Custom utility classes (use sparingly) */
@layer components {
  .btn-primary {
    @apply rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-500;
  }
}
```

---

## 5. Exercises

### Exercise 1: Static Page with Tailwind Styling

Create a landing page for the AI platform.

```tsx
// src/app/page.tsx
export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 to-gray-900">
      {/* Hero Section */}
      <section className="mx-auto max-w-5xl px-6 py-24 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-white">
          Enterprise AI Platform
        </h1>
        <p className="mt-6 text-xl text-gray-400">
          Build, deploy, and monitor AI agents at scale.
        </p>
        <div className="mt-10 flex justify-center gap-4">
          <a
            href="/chat"
            className="rounded-lg bg-blue-600 px-6 py-3 text-lg font-semibold text-white transition hover:bg-blue-500"
          >
            Try Chat
          </a>
          <a
            href="/docs"
            className="rounded-lg border border-gray-600 px-6 py-3 text-lg font-semibold text-gray-300 transition hover:border-gray-400"
          >
            Read Docs
          </a>
        </div>
      </section>

      {/* Features Grid */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-8 md:grid-cols-3">
          {[
            { title: "Multi-Model", desc: "vLLM + llama.cpp with automatic failover" },
            { title: "Observable", desc: "OpenTelemetry traces across every request" },
            { title: "Cost-Aware", desc: "Real-time $/inference with OpenCost" },
          ].map((feature) => (
            <div
              key={feature.title}
              className="rounded-xl border border-gray-800 bg-gray-900 p-6"
            >
              <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
              <p className="mt-2 text-gray-400">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
```

**What you learn:** Tailwind utility classes, responsive grid, gradients, hover states, mapping over data.

---

### Exercise 2: Dynamic Routing with [slug] Pages

```tsx
// src/app/docs/[slug]/page.tsx

// Define which slugs to pre-render at build time
export function generateStaticParams() {
  return [
    { slug: "getting-started" },
    { slug: "architecture" },
    { slug: "deployment" },
  ];
}

const docs: Record<string, { title: string; content: string }> = {
  "getting-started": {
    title: "Getting Started",
    content: "Welcome to the AI platform. This guide walks you through setup...",
  },
  architecture: {
    title: "Architecture",
    content: "The platform uses a microservices architecture with Kubernetes...",
  },
  deployment: {
    title: "Deployment",
    content: "We use Argo CD for GitOps-based continuous deployment...",
  },
};

export default function DocPage({ params }: { params: { slug: string } }) {
  const doc = docs[params.slug];

  if (!doc) {
    return (
      <div className="flex h-screen items-center justify-center text-gray-400">
        <p>Document not found.</p>
      </div>
    );
  }

  return (
    <article className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-4xl font-bold text-white">{doc.title}</h1>
      <p className="mt-6 text-lg leading-relaxed text-gray-300">{doc.content}</p>
      <a href="/docs" className="mt-8 inline-block text-blue-400 hover:underline">
        ← Back to docs
      </a>
    </article>
  );
}
```

```tsx
// src/app/docs/page.tsx — Docs index page
import Link from "next/link";

const docLinks = [
  { slug: "getting-started", title: "Getting Started" },
  { slug: "architecture", title: "Architecture" },
  { slug: "deployment", title: "Deployment" },
];

export default function DocsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold text-white">Documentation</h1>
      <ul className="mt-8 space-y-4">
        {docLinks.map((doc) => (
          <li key={doc.slug}>
            <Link
              href={`/docs/${doc.slug}`}
              className="block rounded-lg border border-gray-700 p-4 text-blue-400 transition hover:border-blue-500 hover:bg-gray-800"
            >
              {doc.title}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

**What you learn:** Dynamic routes with `[slug]`, `generateStaticParams()`, `Link` component, conditional rendering.

---

### Exercise 3: Client Component — Interactive Counter

```tsx
// src/app/counter/page.tsx
"use client";

import { useState, useEffect } from "react";

export default function CounterPage() {
  const [count, setCount] = useState(0);
  const [history, setHistory] = useState<{ value: number; time: string }[]>([]);

  // Log every change to history
  useEffect(() => {
    if (count !== 0) {
      setHistory((prev) => [
        { value: count, time: new Date().toLocaleTimeString() },
        ...prev.slice(0, 9), // Keep last 10
      ]);
    }
  }, [count]);

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="text-2xl font-bold text-white">Counter</h1>

      <div className="mt-8 flex items-center gap-4">
        <button
          onClick={() => setCount((c) => c - 1)}
          className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-500"
        >
          −
        </button>
        <span className="text-4xl font-mono font-bold text-white">{count}</span>
        <button
          onClick={() => setCount((c) => c + 1)}
          className="rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-500"
        >
          +
        </button>
        <button
          onClick={() => setCount(0)}
          className="rounded-lg border border-gray-600 px-4 py-2 text-gray-300 hover:bg-gray-800"
        >
          Reset
        </button>
      </div>

      {/* History */}
      {history.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold uppercase text-gray-500">History</h2>
          <ul className="mt-2 space-y-1">
            {history.map((entry, i) => (
              <li key={i} className="text-sm text-gray-400">
                {entry.time} → <span className="font-mono">{entry.value}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

**What you learn:** `"use client"`, `useState`, `useEffect`, event handlers, conditional rendering.

---

### Exercise 4: API Route That Returns JSON

```tsx
// src/app/api/health/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    status: "healthy",
    version: "1.0.0",
    timestamp: new Date().toISOString(),
    services: {
      frontend: "up",
      api: "up",
      database: "up",
    },
  });
}
```

```tsx
// src/app/api/chat/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const { prompt } = await request.json();

  if (!prompt || typeof prompt !== "string") {
    return NextResponse.json(
      { error: "prompt is required and must be a string" },
      { status: 400 }
    );
  }

  // In production, this calls our FastAPI/GraphQL backend
  // For now, simulate a response
  const reply = `You asked: "${prompt}". This is a simulated AI response.`;

  return NextResponse.json({
    reply,
    model: "simulated",
    tokens: { prompt: prompt.split(" ").length, completion: reply.split(" ").length },
  });
}
```

Test it:

```bash
# Health check
curl http://localhost:3000/api/health | jq

# Chat
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Kubernetes?"}' | jq
```

**What you learn:** Next.js Route Handlers, `NextRequest`/`NextResponse`, HTTP methods, input validation.

---

### Exercise 5: Chat UI with Streaming Responses

```tsx
// src/app/chat/page.tsx
"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsStreaming(true);

    // Add empty assistant message for streaming
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No reader available");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = {
            ...last,
            content: last.content + chunk,
          };
          return updated;
        });
      }
    } catch (error) {
      console.error("Stream error:", error);
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-bold text-white">AI Chat</h1>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {messages.length === 0 && (
            <p className="text-center text-gray-500">
              Start a conversation with the AI assistant.
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-200"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {isStreaming && (
            <div className="flex justify-start">
              <span className="animate-pulse text-gray-500">●●●</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input */}
      <footer className="border-t border-gray-800 px-6 py-4">
        <div className="mx-auto flex max-w-3xl gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            className="flex-1 rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            placeholder="Ask anything..."
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </footer>
    </div>
  );
}
```

Streaming API route:

```tsx
// src/app/api/chat/stream/route.ts
import { NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  const { prompt } = await request.json();

  // Simulate streaming response (in production, this proxies to FastAPI)
  const words = `Here is a response to your question about "${prompt}". 
  In production, this would stream from our vLLM backend through the 
  FastAPI GraphQL layer. Each token arrives as it is generated, providing 
  a responsive user experience.`.split(" ");

  const stream = new ReadableStream({
    async start(controller) {
      for (const word of words) {
        controller.enqueue(new TextEncoder().encode(word + " "));
        await new Promise((r) => setTimeout(r, 50)); // Simulate token delay
      }
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Transfer-Encoding": "chunked",
    },
  });
}
```

**What you learn:** Streaming with `ReadableStream`, `useRef` for auto-scroll, keyboard events, disabled states, complex state management.

---

### Exercise 6: Dashboard Layout with Sidebar Navigation

```tsx
// src/app/dashboard/layout.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: "📊" },
  { href: "/dashboard/models", label: "Models", icon: "🤖" },
  { href: "/dashboard/agents", label: "Agents", icon: "⚡" },
  { href: "/dashboard/costs", label: "Costs", icon: "💰" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-800 bg-gray-900">
        <div className="p-6">
          <h2 className="text-lg font-bold text-white">AI Platform</h2>
        </div>
        <nav className="space-y-1 px-3">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-blue-600/20 text-blue-400"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                }`}
              >
                <span>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">{children}</main>
    </div>
  );
}
```

```tsx
// src/app/dashboard/page.tsx
export default function DashboardOverview() {
  const stats = [
    { label: "Total Requests", value: "12,847", change: "+12%" },
    { label: "Avg Latency", value: "245ms", change: "-8%" },
    { label: "Cost Today", value: "$34.50", change: "+3%" },
    { label: "Active Models", value: "4", change: "0%" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-white">Dashboard Overview</h1>
      <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-gray-800 bg-gray-900 p-6"
          >
            <p className="text-sm text-gray-400">{stat.label}</p>
            <p className="mt-2 text-3xl font-bold text-white">{stat.value}</p>
            <p
              className={`mt-1 text-sm ${
                stat.change.startsWith("+")
                  ? "text-green-400"
                  : stat.change.startsWith("-")
                    ? "text-red-400"
                    : "text-gray-500"
              }`}
            >
              {stat.change} from yesterday
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**What you learn:** Nested layouts, `usePathname()`, active link styling, responsive grid, conditional CSS classes.

---

### Exercise 7: Form with Validation and Server Action

```tsx
// src/app/feedback/page.tsx
"use client";

import { useState } from "react";

interface FormErrors {
  name?: string;
  email?: string;
  message?: string;
}

export default function FeedbackPage() {
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  function validate(formData: FormData): FormErrors {
    const errors: FormErrors = {};
    const name = formData.get("name") as string;
    const email = formData.get("email") as string;
    const message = formData.get("message") as string;

    if (!name || name.length < 2) errors.name = "Name must be at least 2 characters";
    if (!email || !email.includes("@")) errors.email = "Valid email is required";
    if (!message || message.length < 10)
      errors.message = "Message must be at least 10 characters";

    return errors;
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    const validationErrors = validate(formData);
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) return;

    setLoading(true);
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(formData)),
        headers: { "Content-Type": "application/json" },
      });

      if (res.ok) setSubmitted(true);
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="mx-auto max-w-md px-6 py-16 text-center">
        <h2 className="text-2xl font-bold text-green-400">Thank you!</h2>
        <p className="mt-2 text-gray-400">Your feedback has been submitted.</p>
        <button
          onClick={() => setSubmitted(false)}
          className="mt-6 text-blue-400 hover:underline"
        >
          Submit another
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="text-2xl font-bold text-white">Send Feedback</h1>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-300">Name</label>
          <input
            name="name"
            className={`mt-1 w-full rounded-lg border bg-gray-800 px-4 py-2 text-white focus:outline-none ${
              errors.name ? "border-red-500" : "border-gray-700 focus:border-blue-500"
            }`}
          />
          {errors.name && <p className="mt-1 text-sm text-red-400">{errors.name}</p>}
        </div>

        {/* Email */}
        <div>
          <label className="block text-sm font-medium text-gray-300">Email</label>
          <input
            name="email"
            type="email"
            className={`mt-1 w-full rounded-lg border bg-gray-800 px-4 py-2 text-white focus:outline-none ${
              errors.email ? "border-red-500" : "border-gray-700 focus:border-blue-500"
            }`}
          />
          {errors.email && <p className="mt-1 text-sm text-red-400">{errors.email}</p>}
        </div>

        {/* Message */}
        <div>
          <label className="block text-sm font-medium text-gray-300">Message</label>
          <textarea
            name="message"
            rows={4}
            className={`mt-1 w-full rounded-lg border bg-gray-800 px-4 py-2 text-white focus:outline-none ${
              errors.message ? "border-red-500" : "border-gray-700 focus:border-blue-500"
            }`}
          />
          {errors.message && (
            <p className="mt-1 text-sm text-red-400">{errors.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
        >
          {loading ? "Submitting..." : "Submit Feedback"}
        </button>
      </form>
    </div>
  );
}
```

**What you learn:** Form handling, client-side validation, loading states, error display, FormData API.

---

## 6. Advanced Topics

### 6.1 Middleware

```tsx
// src/middleware.ts
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  // Redirect unauthenticated users
  const token = request.cookies.get("auth-token");
  if (!token && request.nextUrl.pathname.startsWith("/dashboard")) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Add request ID header for tracing
  const response = NextResponse.next();
  response.headers.set("x-request-id", crypto.randomUUID());
  return response;
}

export const config = {
  matcher: ["/dashboard/:path*", "/api/:path*"],
};
```

### 6.2 Image Optimization

```tsx
import Image from "next/image";

<Image
  src="/logo.png"
  alt="AI Platform Logo"
  width={200}
  height={50}
  priority          // Load immediately (above the fold)
/>
```

### 6.3 Error Boundaries

```tsx
// src/app/dashboard/error.tsx
"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <h2 className="text-xl font-bold text-red-400">Something went wrong</h2>
        <p className="mt-2 text-gray-400">{error.message}</p>
        <button
          onClick={reset}
          className="mt-4 rounded bg-blue-600 px-4 py-2 text-white"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
```

### 6.4 Loading States with Suspense

```tsx
// src/app/dashboard/loading.tsx
export default function Loading() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
    </div>
  );
}
```

---

## 7. How It's Used in Our Project

In our AI platform:

- **`app/chat/page.tsx`** — The main chat interface where users interact with AI agents
- **`app/dashboard/`** — Monitoring dashboard showing model performance, costs, and metrics
- **API routes** proxy requests to the FastAPI + GraphQL backend (Strawberry)
- **Server Components** fetch data directly for dashboards (no API round-trip)
- **Streaming** is used for real-time token-by-token LLM responses via `ReadableStream`
- **Tailwind** ensures consistent dark theme across all pages

### Connection to Backend:

```tsx
// Example: Calling our GraphQL API from a Server Component
const GRAPHQL_URL = process.env.API_URL + "/graphql";

async function fetchModels() {
  const res = await fetch(GRAPHQL_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: `{ models { id name status latencyP99 } }`,
    }),
    next: { revalidate: 30 }, // ISR: refresh every 30s
  });
  return res.json();
}
```

---

## 8. Best Practices

1. **Use Server Components by default** — only add `"use client"` when you need interactivity
2. **Co-locate related files** — keep components, styles, and tests near their route
3. **Use `loading.tsx` and `error.tsx`** for every route segment
4. **Prefer `Link` over `<a>`** for client-side navigation
5. **Extract reusable components** to `src/components/`
6. **Use environment variables** for API URLs (`NEXT_PUBLIC_` prefix for client-side)
7. **Test with React Testing Library** and Vitest/Jest

---

## 9. Further Reading

- [Next.js Documentation](https://nextjs.org/docs)
- [Next.js App Router Guide](https://nextjs.org/docs/app)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/)
- [Vercel Next.js Examples](https://github.com/vercel/next.js/tree/canary/examples)
