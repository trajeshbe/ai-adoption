# How This Platform Was Built with Claude Code

A comprehensive guide for fresh graduates on AI-assisted software development.
Covers installation, configuration, and a developer roadmap from first install to
production deployment -- with real examples from this AI Agent Platform.

---

## Table of Contents

**Part I: Getting Started with Claude Code**

1. [Developer Roadmap](#1-developer-roadmap)
2. [Installation & Setup](#2-installation--setup)
3. [What is Claude Code?](#3-what-is-claude-code)
4. [Available Platforms](#4-available-platforms)
5. [Keyboard Shortcuts & CLI Reference](#5-keyboard-shortcuts--cli-reference)

**Part II: Configuration & Customization**

6. [CLAUDE.md -- The Project Brain](#6-claudemd----the-project-brain)
7. [Auto Memory](#7-auto-memory)
8. [Rules System](#8-rules-system)
9. [Settings & Configuration](#9-settings--configuration)

**Part III: Skills, Hooks & Extensions**

10. [Custom Skills System](#10-custom-skills-system)
11. [Slash Commands -- Tutorial Phases](#11-slash-commands----tutorial-phases)
12. [Hooks -- Automation](#12-hooks----automation)
13. [MCP Servers -- External Data](#13-mcp-servers----external-data)
14. [Subagents & Multi-Session Workflows](#14-subagents--multi-session-workflows)

**Part IV: Building with Claude Code (This Project)**

15. [How This App Was Built with Claude Code](#15-how-this-app-was-built-with-claude-code)
16. [The AI-Assisted Development Workflow](#16-the-ai-assisted-development-workflow)
17. [Architecture Decision Records (ADRs)](#17-architecture-decision-records-adrs)

**Part V: Production & Best Practices**

18. [CI/CD Integration](#18-cicd-integration)
19. [Best Practices for AI-Assisted Development](#19-best-practices-for-ai-assisted-development)
20. [What Claude Code Can and Cannot Do](#20-what-claude-code-can-and-cannot-do)

---

## 1. Developer Roadmap

A structured learning path from first install to production deployment. Each stage
builds on the previous one.

```
Stage 1: INSTALL & EXPLORE (Day 1)
  │  Install Claude Code, learn the CLI, explore a codebase
  │
Stage 2: CONFIGURE (Day 1-2)
  │  Write CLAUDE.md, set up rules, configure settings
  │
Stage 3: DEVELOP (Day 2-7)
  │  Build features, debug errors, refactor code
  │  Use skills, slash commands, and subagents
  │
Stage 4: TEST (Day 7-10)
  │  Generate unit/integration/e2e tests
  │  Run load tests, fix failures with Claude Code
  │
Stage 5: DEPLOY (Day 10-14)
  │  CI/CD integration, Kubernetes manifests, GitOps
  │  Domain setup, HTTPS, monitoring
  │
Stage 6: SCALE & AUTOMATE (Ongoing)
     Hooks, MCP servers, custom skills, team workflows
     Multi-agent orchestration, scheduled tasks
```

### Stage 1: Install & Explore

**Goal:** Get Claude Code running and comfortable navigating a codebase.

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Navigate to any project
cd ~/my-project

# Start Claude Code
claude

# Try these first commands:
#   "What does this project do?"
#   "Show me the main entry point"
#   "What dependencies does this project use?"
#   "Explain the architecture"
```

At this stage, use Claude Code as an **intelligent code reader**. Ask questions,
explore files, understand how things connect. Don't write code yet -- build your
mental model first.

### Stage 2: Configure

**Goal:** Set up CLAUDE.md and project-specific configuration so Claude Code
generates code that fits your project's patterns.

```bash
# Auto-generate an initial CLAUDE.md
claude /init

# Review and refine the generated file
# Add: conventions, build commands, testing strategy, architecture overview
```

Key files to create:
- `CLAUDE.md` -- Project overview and conventions (see [Section 6](#6-claudemd----the-project-brain))
- `.claude/settings.json` -- Permission rules and model preferences
- `.claude/rules/` -- Modular instructions for specific file types

### Stage 3: Develop

**Goal:** Build features using AI pair programming. This is the core workflow.

```bash
# Describe what you want
claude "Create a new API endpoint that returns user analytics grouped by date"

# Debug an error
claude "Here's the error: [paste traceback]. Fix it."

# Refactor
claude "Convert the callback-based auth middleware to async/await"

# Use a slash command for guided builds
claude /01-scaffold-api
```

At this stage, read [Section 16](#16-the-ai-assisted-development-workflow) for the
full development workflow with examples from this project.

### Stage 4: Test

**Goal:** Generate comprehensive tests and verify AI-generated code works correctly.

```bash
# Generate unit tests
claude "Write unit tests for the user analytics endpoint"

# Generate integration tests
claude "Write integration tests for the database layer using testcontainers"

# Fix failing tests
claude "These tests fail: [paste output]. Fix the implementation."

# Generate load tests
claude "Create a load test script that simulates 30 concurrent users"
```

This project demonstrates all testing layers -- see the load test at
`tests/load/loadtest_gpu_30users.py` and results in
`docs/testing/load-test-gcp-gpu-30-users.md`.

### Stage 5: Deploy

**Goal:** Use Claude Code to generate infrastructure code and deploy to production.

```bash
# Generate Kubernetes manifests
claude "Create Kustomize manifests for the gateway service with HPA auto-scaling"

# Generate Docker Compose for staging
claude "Add a Caddy reverse proxy to docker-compose.yml for HTTPS"

# Generate CI/CD pipeline
claude "Create a GitHub Actions workflow that builds, tests, and deploys on push to main"

# Set up domain and HTTPS
claude "Configure Caddy to serve ai-adoption.uk with automatic Let's Encrypt certificates"
```

This project's deployment journey is documented in:
- `docs/runbooks/domain-setup.md` -- Domain + HTTPS configuration
- `docs/runbooks/gcp-vm-operations.md` -- VM operations
- `docs/testing/gcp-gpu-setup-scaling-testing.md` -- GPU VM + scaling demo

### Stage 6: Scale & Automate

**Goal:** Advanced workflows for teams and production systems.

- **Hooks**: Automate quality gates (block commits without tests, enforce linting)
- **MCP Servers**: Connect to Jira, Slack, databases for live context
- **Custom Skills**: Package repeatable workflows (`/deploy-staging`, `/hotfix`)
- **Subagents**: Parallelize large refactors across the codebase
- **Scheduled Tasks**: Automated code reviews, dependency updates, monitoring

Each of these features is covered in detail in the sections below.

---

## 2. Installation & Setup

### System Requirements

- **Node.js 18+** (for npm install)
- **Operating System**: macOS, Linux, or Windows (WSL recommended)
- **Anthropic account**: Sign up at https://console.anthropic.com

### Install Claude Code

```bash
# Option 1: npm (recommended)
npm install -g @anthropic-ai/claude-code

# Option 2: Homebrew (macOS/Linux)
brew install claude-code

# Option 3: WinGet (Windows)
winget install Anthropic.ClaudeCode
```

### First Run

```bash
# Navigate to your project
cd ~/my-project

# Start Claude Code (will prompt for authentication on first run)
claude

# Or run a one-shot command
claude "What does this project do?"

# Or pipe input
cat error.log | claude -p "What went wrong?"
```

### Authentication

On first run, Claude Code opens a browser for authentication. You can authenticate
using:

- **Claude account** (claude.ai)
- **Anthropic Console** (console.anthropic.com)
- **Third-party providers**: Amazon Bedrock, Google Vertex AI, Microsoft Foundry

```bash
# Switch accounts
/login

# Check current account
/config
```

### Auto-Updates

Native installs (npm) auto-update automatically. Package manager installs (Homebrew,
WinGet) require manual updates:

```bash
# npm: auto-updates by default
# Homebrew: brew upgrade claude-code
# WinGet: winget upgrade Anthropic.ClaudeCode
```

---

## 3. What is Claude Code?

### The Tool

Claude Code is Anthropic's command-line interface for AI-assisted software development.
It is not a chatbot with a coding hobby. It is a full development partner that lives
inside your terminal, reads your codebase, generates production-quality code, debugs
errors in real time, and explains its reasoning every step of the way.

You install it, open a terminal in your project directory, and start describing what
you want to build in plain English. Claude Code reads your files, understands your
project structure, and writes code that fits your existing patterns. It is like pair
programming with a senior engineer who has read every file in your repository and
never forgets a convention.

### How It Works

The core loop is straightforward:

1. **You describe intent in natural language.** "Create a FastAPI service with a
   GraphQL endpoint that returns a list of AI agents."
2. **Claude Code reads your project context.** It examines CLAUDE.md files, existing
   code, configuration, and directory structure to understand conventions.
3. **It generates code that follows your patterns.** If your project uses the app
   factory pattern, it generates an app factory. If you use Pydantic Settings for
   config, it uses Pydantic Settings.
4. **You review, test, and iterate.** Paste an error message, and Claude Code
   analyzes the stack trace and produces a fix.

This is not copy-pasting from Stack Overflow. Claude Code generates code that is
aware of your specific project -- your imports, your directory structure, your naming
conventions, your dependencies.

### Vibe Coding and AI Pair Programming

"Vibe coding" is a term that has emerged to describe the experience of building
software by describing your intent and letting an AI generate the implementation.
You focus on the *what* and the *why* while the AI handles the *how*.

But here is the important nuance: vibe coding does not mean abdicating responsibility.
It means operating at a higher level of abstraction. Instead of typing
`async def create_app() -> FastAPI:` character by character, you say "create a FastAPI
app factory with GraphQL, health endpoints, and CORS middleware." You still need to
understand what an app factory is, why health endpoints matter, and what CORS does.
The AI accelerates your output; it does not replace your understanding.

Think of it as the difference between writing assembly code and writing Python. Python
did not make understanding computation unnecessary -- it raised the abstraction level
so you could think about problems instead of registers. Claude Code raises the
abstraction level again so you can think about architecture instead of syntax.

---

## 4. Available Platforms

Claude Code runs on multiple platforms. Choose the one that fits your workflow.

| Platform | Best For | Key Features |
|----------|----------|-------------|
| **Terminal CLI** | Full-featured development | Piping, scripting, one-shot commands, background agents |
| **VS Code Extension** | Integrated IDE workflow | Inline diffs, @-mentions, plan review, conversation history |
| **JetBrains IDEs** | IntelliJ/PyCharm/WebStorm users | Interactive diff viewing, selection context sharing |
| **Desktop App** | Standalone sessions | Visual diff review, parallel sessions, scheduling |
| **Web Interface** (claude.ai/code) | Async/remote work | Run on cloud infrastructure, continues when offline |
| **Chrome Extension** (beta) | Web app testing | Connect to browser for testing and automation |
| **Mobile** (Claude iOS app) | On-the-go monitoring | Web access, remote control of sessions |

### Terminal CLI (Primary)

The CLI is the most powerful interface. It supports:

```bash
# Interactive mode (REPL)
claude

# One-shot command
claude "add error handling to the auth middleware"

# Piping (stdin → Claude → stdout)
git diff | claude -p "review this diff for security issues"
cat error.log | claude -p "what went wrong?"

# Continue last conversation
claude -c

# Resume a specific session
/resume
```

### VS Code Extension

Install from the VS Code marketplace. Key features:

- **Inline diffs**: See changes as colored diffs in the editor before accepting
- **@-mentions**: Reference files, symbols, or selections with `@filename`
- **Plan review**: Review Claude's implementation plan before execution
- **Conversation history**: Browse and resume past sessions

### IDE Integrations (JetBrains)

Available for IntelliJ IDEA, PyCharm, WebStorm, and other JetBrains IDEs:

- Interactive diff viewing with accept/reject per change
- Share selected code as context
- Keyboard shortcuts integrated with IDE keymap

---

## 5. Keyboard Shortcuts & CLI Reference

### Keyboard Shortcuts

Press `?` in the Claude Code REPL to see all shortcuts.

| Shortcut | Action |
|----------|--------|
| `?` | Show all shortcuts |
| `Tab` | Autocomplete commands and file paths |
| `↑` | Command history |
| `Ctrl+C` | Cancel current operation |
| `Ctrl+D` | Exit Claude Code |
| `Escape` | Cancel current input |

### Built-in Commands

| Command | Description |
|---------|-------------|
| `/help` | Available commands and skills |
| `/login` | Switch accounts |
| `/clear` | Clear conversation history |
| `/memory` | View and manage CLAUDE.md and auto memory |
| `/config` | Open settings interface |
| `/compact` | Summarize conversation (free up context window) |
| `/init` | Auto-generate CLAUDE.md for your project |
| `/resume` | Continue previous conversation |
| `/schedule` | Create scheduled tasks |
| `/desktop` | Hand off to desktop app |
| `/fast` | Toggle fast output mode (same model, faster) |

### CLI Flags

```bash
claude "task"              # One-shot command
claude -p "task"           # Print mode (for piping, no interactive UI)
claude -c                  # Continue last conversation
claude --model opus        # Use specific model
claude --output-format json  # JSON output for scripting
```

---

## 6. CLAUDE.md -- The Project Brain

### What is CLAUDE.md?

Every time you start a conversation with Claude Code in a directory, it looks for a
file named `CLAUDE.md`. This file is the project's memory. It tells Claude Code what
this project is, how it is structured, what conventions to follow, and what commands
are available. Without it, Claude Code is a brilliant engineer who just walked into
your codebase with zero context. With it, Claude Code is a team member who has read
the onboarding documentation.

### The Hierarchical Strategy

This project uses **12 CLAUDE.md files** organized in a hierarchy. This is not
accidental -- it is a deliberate strategy to give Claude Code the right amount of
context at the right scope.

```
ai_adoption/
  CLAUDE.md                          # Root: project overview, all conventions
  services/
    CLAUDE.md                        # All services: shared patterns, ports, commands
    gateway/
      CLAUDE.md                      # Gateway: schema-first, resolvers, middleware
    agent-engine/
      CLAUDE.md                      # Agent engine: LangGraph, Prefect, registry
    document-service/
      CLAUDE.md                      # Document service: MinIO, pgvector, chunking
    cache-service/
      CLAUDE.md                      # Cache service: Redis VSS, semantic cache
    cost-tracker/
      CLAUDE.md                      # Cost tracker: OpenCost, per-inference cost
  frontend/
    CLAUDE.md                        # Frontend: Next.js, Tailwind, urql, hooks
  libs/
    CLAUDE.md                        # Shared libraries: py-common, ts-common
  infra/
    CLAUDE.md                        # Infrastructure: Kustomize, Helm, Argo CD, OPA
  tests/
    CLAUDE.md                        # Cross-cutting tests: e2e, load, chaos, security
  docs/
    CLAUDE.md                        # Documentation: ADRs, tutorials, runbooks
```

**Why a hierarchy?** When you are working on the gateway service and ask Claude Code
to add a new resolver, it reads:

1. The **root CLAUDE.md** -- knows the overall architecture and conventions
2. The **services/CLAUDE.md** -- knows all services use the app factory pattern and
   expose `/healthz` endpoints
3. The **services/gateway/CLAUDE.md** -- knows the gateway uses schema-first design,
   resolvers live in `resolvers/`, and the run command is `uv run uvicorn ...`

This layered context means Claude Code generates a resolver that fits the project
perfectly -- correct imports, correct patterns, correct directory placement.

### What Goes in Each CLAUDE.md

**Root CLAUDE.md (under 200 lines):** The big picture. Project overview, architecture
diagram, monorepo layout, coding conventions, build commands, testing strategy, and
the list of tutorial phases. This is what every Claude Code conversation starts with.

Here is the conventions section from our root CLAUDE.md:

```
## Conventions
- Python: 3.11+, uv for deps, ruff lint+format, mypy strict, pytest
- TypeScript: strict mode, ESLint+Prettier, Vitest+Playwright
- Services: /healthz and /readyz endpoints, OTEL traces via libs/py-common/telemetry.py
- Config: Environment variables via Pydantic Settings (12-factor)
- API: GraphQL schema-first -- edit services/gateway/src/gateway/schema.py first
- K8s: Kustomize base/overlays. Never raw kubectl apply. Helm for third-party only.
- GitOps: All changes via Argo CD sync. Git is the single source of truth.
```

These six lines save hundreds of corrections. Without them, Claude Code might generate
a REST endpoint instead of GraphQL, use pip instead of uv, or create a raw Kubernetes
manifest instead of a Kustomize overlay.

**Directory-level CLAUDE.md (services/, infra/, libs/):** Scope-specific patterns.
The services CLAUDE.md documents the port assignments, the shared app factory pattern,
and the standard test/run commands for every Python service. The infra CLAUDE.md
documents the Kustomize rules and the prohibition on raw `kubectl apply`.

**Service-level CLAUDE.md (gateway/, agent-engine/):** Deep technical context. The
gateway CLAUDE.md lists key files (main.py, schema.py, resolvers/), patterns
(schema-first, dependency injection, circuit breaker), and the exact run command.

### Why This Matters

CLAUDE.md files are the single most important thing you can write for AI-assisted
development. They are the difference between Claude Code generating generic code and
generating code that belongs in your project. They are cheap to write (each one is
10-30 lines), and they pay for themselves immediately.

A well-written CLAUDE.md is more valuable than a README. A README is for humans who
browse GitHub. A CLAUDE.md is for an AI that is about to write code in your project.
It needs to be precise, not narrative. Conventions, not explanations. Commands, not
prose.

---

## 7. Auto Memory

### What Is Auto Memory?

Claude Code writes its own notes automatically during conversations. These notes
persist across sessions and help Claude remember what it learned about your project.

Auto memory is **enabled by default**. You do not need to configure it.

### How It Works

```
~/.claude/projects/<project-hash>/memory/
├── MEMORY.md          # Index file (loaded at session start, max 200 lines)
├── user_role.md       # Notes about you (role, preferences)
├── feedback_*.md      # Corrections and confirmed approaches
├── project_*.md       # Ongoing work, goals, decisions
└── reference_*.md     # Pointers to external systems
```

- **MEMORY.md** is the index. First 200 lines (or 25KB) are loaded at session start.
- Each memory file has YAML frontmatter with name, description, and type.
- Memory is **machine-local** -- it does not sync across devices or team members.
- Claude writes memories when it learns something non-obvious about you or the project.

### Types of Memories

| Type | What Gets Saved | Example |
|------|----------------|---------|
| **user** | Your role, expertise, preferences | "Deep Go expertise, new to React frontend" |
| **feedback** | Corrections and confirmed approaches | "Use real DB in integration tests, not mocks" |
| **project** | Ongoing goals, decisions, deadlines | "Merge freeze starts 2026-03-05 for mobile release" |
| **reference** | Pointers to external systems | "Pipeline bugs tracked in Linear project INGEST" |

### Managing Memory

```bash
# View what Claude remembers
/memory

# Ask Claude to remember something
"Remember that we use Redis Stack, not managed Redis, because no cloud provider supports RediSearch modules"

# Ask Claude to forget something
"Forget the note about the deployment freeze"
```

### Auto Memory vs CLAUDE.md

| | CLAUDE.md | Auto Memory |
|---|-----------|------------|
| **Who writes it** | You | Claude |
| **What it contains** | Instructions and conventions | Learnings and observations |
| **Shared via git** | Yes | No (machine-local) |
| **When to use** | Patterns you want enforced | Context Claude should remember |

---

## 8. Rules System

### What Are Rules?

Rules are modular instruction files in `.claude/rules/` that organize project
guidance into focused, path-specific files. They are an alternative to putting
everything in CLAUDE.md.

### Directory Structure

```
.claude/rules/
├── python.md          # Rules for all Python files
├── frontend.md        # Rules for frontend code
├── kubernetes.md      # Rules for K8s manifests
└── security.md        # Security-sensitive code rules
```

### Path-Specific Rules

Use YAML frontmatter to scope rules to specific file patterns:

```markdown
---
paths: ["services/**/*.py"]
---

# Python Service Rules
- Use the app factory pattern for all FastAPI services
- All services must expose /healthz and /readyz endpoints
- Use Pydantic Settings for configuration (12-factor)
- Use structlog for structured logging
```

When you open or edit a file matching `services/**/*.py`, these rules are
automatically loaded. Rules for unrelated files are **not loaded**, keeping
context focused.

### User-Level Rules

Personal rules that apply across all projects:

```
~/.claude/rules/
├── style.md           # Your personal coding style preferences
└── workflow.md        # Your preferred workflow (e.g., "always run tests after changes")
```

### Rules vs CLAUDE.md

| | CLAUDE.md | Rules |
|---|-----------|-------|
| **Loaded** | Always (every conversation) | Only when matching files are opened |
| **Scope** | Entire project | Specific file patterns |
| **Best for** | Architecture, conventions, commands | File-type-specific patterns |
| **Size** | Keep under 200 lines | As detailed as needed per topic |

---

## 9. Settings & Configuration

### Settings Hierarchy

Settings are loaded in priority order (higher overrides lower):

```
Managed (IT/org policy)     ← Cannot be overridden
  └── User (~/.claude/settings.json)
      └── Project (.claude/settings.json)  ← Shared via git
          └── Local (.claude/settings.local.json)  ← Gitignored
```

### Key Settings

```json
// .claude/settings.json (project-level, committed to git)
{
  "permissions": {
    "allow": [
      "Bash(make *)",
      "Bash(uv run *)",
      "Bash(docker compose *)",
      "Read(*)",
      "Write(services/**)",
      "Edit(services/**)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git push --force*)"
    ]
  }
}
```

### Permission Modes

| Mode | Behavior | When to Use |
|------|----------|-------------|
| **Full** | Claude can do anything without asking | Trusted environments, personal projects |
| **Ask** (default) | Approval dialogs for risky actions | Normal development |
| **Deny** | Specific tools/commands blocked | Team environments, security constraints |

### Environment Variables

```bash
# Model selection
CLAUDE_MODEL=claude-opus-4-6       # Use specific model

# Reasoning effort
CLAUDE_EFFORT=high                   # low, medium, high, max

# Third-party providers
ANTHROPIC_BASE_URL=...               # Custom API endpoint
AWS_REGION=us-east-1                 # For Bedrock
GOOGLE_CLOUD_PROJECT=...             # For Vertex AI
```

### Configure via REPL

```bash
# Open interactive settings
/config

# View current configuration
claude --print-config
```

---

## 10. Custom Skills System

### What Are Skills?

Skills are reusable workflows packaged as `SKILL.md` files. They go beyond simple
slash commands by supporting arguments, tool restrictions, subagent isolation, and
automatic invocation.

### Skill Locations

```
Enterprise managed skills         ← IT-controlled, cannot be overridden
~/.claude/skills/deploy/          ← Personal skills (all projects)
.claude/skills/hotfix/            ← Project skills (shared via git)
services/gateway/.claude/skills/  ← Nested skills (monorepo subdirectories)
```

### Anatomy of a Skill

```markdown
---
name: deploy-staging
description: Deploy the current branch to staging environment
disable-model-invocation: true     # Only user can invoke (risky action)
allowed-tools: ["Bash", "Read"]    # Tools Claude can use without asking
argument-hint: "[service-name]"    # CLI autocomplete hint
---

# Deploy to Staging

1. Run `make lint` and `make test` to verify the code is clean
2. Build Docker images: `docker compose build $ARGUMENTS`
3. Push images to registry: `docker push ...`
4. Update the staging Kustomize overlay
5. Trigger Argo CD sync
```

### Bundled Skills

Claude Code ships with built-in skills:

| Skill | What It Does |
|-------|-------------|
| `/batch` | Large-scale parallel changes across the codebase (uses git worktrees) |
| `/simplify` | Review code for quality, reuse, and efficiency improvements |
| `/debug` | Enable debug logging and troubleshoot issues |
| `/loop` | Run a prompt repeatedly on an interval |
| `/claude-api` | Load the Claude API reference material |

### Skill Features

- **Arguments**: `$ARGUMENTS` in the skill content is replaced with user input
- **Shell injection**: `` !`git status` `` runs a shell command and injects the output
- **Subagent isolation**: `context: fork` runs the skill in an isolated subagent
- **Model override**: `model: haiku` for faster, cheaper skill execution
- **Effort override**: `effort: low` for quick tasks

---

## 11. Slash Commands -- Tutorial Phases

### What Are Slash Commands?

Claude Code supports custom slash commands -- predefined prompts stored in
`.claude/commands/` that you invoke by typing a command like `/01-scaffold-api`.
Each command is a Markdown file containing detailed, step-by-step instructions for
Claude Code to follow.

This project has **11 custom slash commands**, one for each tutorial phase:

| Command                | Phase | What It Builds                                    |
|------------------------|-------|---------------------------------------------------|
| `/00-setup-env`        | 0     | DevContainer, Docker Compose, toolchain bootstrap |
| `/01-scaffold-api`     | 1     | FastAPI + Strawberry GraphQL gateway               |
| `/02-scaffold-frontend`| 2     | Next.js 14 + Tailwind + Shadcn/ui frontend        |
| `/03-setup-data-layer` | 3     | Postgres/pgvector, Redis VSS, MinIO               |
| `/04-build-agent-dag`  | 4     | Prefect + LangGraph agent orchestration            |
| `/05-setup-llm-runtime`| 5     | vLLM on KubeRay + llama.cpp CPU fallback          |
| `/06-add-observability`| 6     | OpenTelemetry, Grafana Tempo/Loki/Mimir           |
| `/07-setup-mesh`       | 7     | Istio ambient mesh + Contour/Envoy ingress        |
| `/08-setup-gitops`     | 8     | Argo CD + Tekton CI/CD pipelines                   |
| `/09-add-policy`       | 9     | OPA Gatekeeper + OpenCost governance               |
| `/10-harden`           | 10    | Load tests, chaos tests, security scans, SLOs     |

### How They Guide Complex Builds

Each slash command is a detailed blueprint. Take `/01-scaffold-api` as an example.
It contains:

- **What You Will Learn** -- Lists the concepts (schema-first design, app factory
  pattern, dependency injection)
- **Prerequisites** -- What must be done before this phase
- **Background** -- Why the technology choices were made (with links to ADRs)
- **Step-by-Step Instructions** -- 8-10 numbered steps, each with code templates,
  file paths, and explanations of *why* each step matters
- **Verification** -- Commands to confirm everything works
- **Key Concepts Taught** -- Summary of engineering principles covered

When you type `/01-scaffold-api` in Claude Code, it reads this entire document and
executes each step: creating files, writing code, setting up configurations. But
because it also reads the CLAUDE.md hierarchy, the code it generates follows all
project conventions automatically.

### The Power of Composable Phases

Each phase builds on the previous one. Phase 1 creates the API with mock data.
Phase 3 replaces the mocks with real databases. Phase 4 adds agent intelligence.
Phase 6 adds observability. This composability means you can:

- **Learn incrementally.** Each phase teaches 3-5 new concepts without overwhelming
  you.
- **Debug in isolation.** If Phase 4 breaks, you know Phases 1-3 work. The problem
  is in agent orchestration, not in your API or database layer.
- **Understand the architecture.** By building layer by layer, you see why each
  service exists and how they connect.

---

## 12. Hooks -- Automation

### What Are Hooks?

Hooks are automated actions that run at specific lifecycle events in Claude Code.
They can block destructive operations, enforce standards, and integrate with
external systems.

### Hook Types

| Type | What It Does | Example |
|------|-------------|---------|
| **Command** | Run a shell script (receives JSON via stdin) | Lint check before commit |
| **HTTP** | POST request to an external endpoint | Notify Slack on PR creation |
| **Prompt** | Single-turn Claude evaluation | "Does this change follow our conventions?" |
| **Agent** | Subagent with tool access | Verify test coverage for changed files |

### Key Events

| Event | When It Fires | Use Case |
|-------|--------------|----------|
| `PreToolUse` | Before any tool runs | Block `rm -rf`, enforce file patterns |
| `PostToolUse` | After a tool completes | Run linter after file edits |
| `UserPromptSubmit` | When user sends a message | Add context, validate requests |
| `SessionStart` | When a session begins | Set up dependencies, check env |
| `Stop` | When Claude finishes a response | Run tests, validate output |

### Configuration Example

```json
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "if": "Bash(rm *)",
        "type": "command",
        "command": "echo 'BLOCKED: Destructive delete requires confirmation' && exit 2"
      }
    ],
    "PostToolUse": [
      {
        "if": "Write(services/**/*.py)",
        "type": "command",
        "command": "cd services && uv run ruff check --fix"
      }
    ]
  }
}
```

### Exit Codes

- **0**: Success (proceed normally)
- **2**: Blocking error (stop the operation)
- **Other**: Non-blocking warning (log and continue)

---

## 13. MCP Servers -- External Data

### What Is MCP?

The **Model Context Protocol** (MCP) is an open standard for connecting AI tools
to external data sources. It lets Claude Code access live data from Jira, Slack,
Google Drive, databases, and custom APIs without you having to paste it in manually.

### How It Works

```
Claude Code ──MCP──→ MCP Server ──API──→ External Service
                     (local process)      (Jira, Slack, DB, etc.)
```

An MCP server is a small process that runs locally and exposes tools to Claude Code.
When Claude needs data from an external service, it calls the MCP server, which
fetches the data and returns it.

### Configuration

```json
// .claude/settings.json
{
  "mcpServers": {
    "jira": {
      "command": "npx",
      "args": ["@anthropic/mcp-server-jira"],
      "env": {
        "JIRA_URL": "https://company.atlassian.net",
        "JIRA_TOKEN": "${JIRA_API_TOKEN}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["@anthropic/mcp-server-postgres", "postgresql://localhost/mydb"]
    }
  }
}
```

### Common MCP Servers

| Server | What It Provides |
|--------|-----------------|
| **Filesystem** | Read/write files outside the project |
| **PostgreSQL** | Query databases directly |
| **Slack** | Read channels, send messages |
| **Google Drive** | Access documents and spreadsheets |
| **GitHub** | Issues, PRs, code search |
| **Jira** | Tickets, sprints, project data |

### Use in This Project

With an MCP server for PostgreSQL, Claude Code could directly query the agent
platform's database to debug issues:

```
"What are the most recent 10 chat sessions and their token counts?"
→ Claude calls the Postgres MCP server
→ Runs: SELECT * FROM chat_sessions ORDER BY created_at DESC LIMIT 10
→ Returns formatted results
```

---

## 14. Subagents & Multi-Session Workflows

### What Are Subagents?

Subagents are independent Claude Code instances that work on subtasks in parallel.
A lead agent delegates work to specialized subagents, then merges the results.

### How Subagents Work

```
Lead Agent (main session)
  ├── Subagent 1: "Refactor auth middleware"     ← git worktree A
  ├── Subagent 2: "Update all unit tests"         ← git worktree B
  └── Subagent 3: "Update documentation"          ← git worktree C
        │
        └── All results merged back to main session
```

### The /batch Skill

The `/batch` skill orchestrates parallel agents in git worktrees for large-scale
changes:

```bash
# Refactor all services to use the new logging format
claude /batch "Update all Python services to use structlog instead of print statements"
```

This creates separate worktrees, runs agents in parallel, and presents the combined
diff for review.

### Custom Agents

Define custom agents in `.claude/agents/`:

```markdown
# .claude/agents/reviewer.md
---
name: code-reviewer
description: Reviews code changes for security and performance issues
model: haiku
allowed-tools: ["Read", "Grep", "Glob"]
---

Review the provided code changes for:
1. Security vulnerabilities (OWASP Top 10)
2. Performance issues (N+1 queries, unnecessary allocations)
3. Error handling gaps
4. Missing input validation

Report findings as a numbered list with severity (HIGH/MEDIUM/LOW).
```

### Multi-Device Sessions

Claude Code sessions can be continued across devices:

```bash
# On your laptop: start work
claude "Begin refactoring the gateway service"

# On your phone (claude.ai/code): check progress
# Continue the session from the web interface

# Back on laptop: resume
claude -c    # Continue last conversation
/resume      # Or pick a specific session
```

### Scheduled Tasks

```bash
# Run a code review every morning at 9 AM
/schedule "Review all PRs opened in the last 24 hours" --cron "0 9 * * *"

# Run dependency audit weekly
/schedule "Check for security vulnerabilities in dependencies" --cron "0 0 * * 1"
```

---

## 15. How This App Was Built with Claude Code

This section walks through how Claude Code was actually used to build this platform.
These are not hypothetical examples -- this is the real process.

### Phase 1 -- API Layer: The Gateway Service

**What we told Claude Code:** "Build a FastAPI gateway service with Strawberry GraphQL.
Schema-first approach. App factory pattern. Mock data for now."

**What Claude Code generated:**

The FastAPI app factory in `services/gateway/src/gateway/main.py`:
```python
def create_app() -> FastAPI:
    app = FastAPI(title="Agent Platform Gateway", version="0.1.0")
    schema = strawberry.Schema(query=Query, mutation=Mutation)
    graphql_app = GraphQLRouter(schema)
    app.include_router(graphql_app, prefix="/graphql")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz():
        return {"status": "ready"}

    return app
```

Claude Code did not just write a hello-world FastAPI app. It:

- Used the **app factory pattern** (`create_app()` function) because CLAUDE.md
  specified it -- this makes the service testable by creating fresh app instances
  in each test.
- Added **`/healthz` and `/readyz` endpoints** because CLAUDE.md requires every
  service to have them -- Kubernetes uses these for liveness and readiness probes.
- Mounted **Strawberry GraphQL** on `/graphql` because the conventions specify
  schema-first GraphQL.
- Created the **full GraphQL schema** with types for Agent, ChatMessage, ChatSession,
  Document, and InferenceCost -- all with proper Strawberry decorators and Python
  type hints.
- Generated **stub resolvers** organized in `resolvers/agent.py`, `resolvers/chat.py`,
  `resolvers/document.py`, and `resolvers/cost.py` -- returning mock data so the
  frontend team could start building immediately.
- Added **middleware** for telemetry, auth (stub), and rate limiting.
- Created the **Dockerfile** with multi-stage builds.
- Wrote **unit tests** using Strawberry's test client.

All of this from a single natural-language prompt, guided by the slash command and
CLAUDE.md context.

### Phase 2 -- Frontend: The Next.js Chat Interface

**What we told Claude Code:** "Build the Next.js frontend with Tailwind and Shadcn/ui.
Chat interface with streaming. Agent management. GraphQL client."

**What Claude Code generated:**

- **Next.js 14 App Router** with the full page structure:
  - `src/app/layout.tsx` -- Root layout with GraphQL provider, sidebar, navbar
  - `src/app/agents/page.tsx` -- Agent grid with cards
  - `src/app/agents/[id]/page.tsx` -- Agent detail with dynamic routing
  - `src/app/agents/new/page.tsx` -- Agent creation form
  - `src/app/documents/page.tsx` -- Document upload and listing
  - Placeholder pages for workflows, costs, and observability

- **Tailwind + Shadcn/ui component library** -- Button, Card, Dialog, Input, Textarea,
  DropdownMenu, Avatar, Badge, Separator, ScrollArea. All installed and configured
  with the project's design tokens.

- **Chat interface components:**
  - `ChatWindow.tsx` -- The main container with message list, input bar, and streaming
    indicator
  - `MessageBubble.tsx` -- Renders user and assistant messages with markdown support
  - `StreamingIndicator.tsx` -- Animated typing dots during LLM generation
  - `ToolCallCard.tsx` -- Visual display when an agent invokes an external tool

- **GraphQL client integration** with urql:
  - `src/lib/graphql/client.ts` -- urql client with cache, fetch, and subscription
    exchanges
  - `src/lib/graphql/queries.ts` -- All query documents
  - `src/lib/graphql/mutations.ts` -- All mutation documents
  - `src/lib/graphql/subscriptions.ts` -- WebSocket subscription for chat streaming

- **Custom hooks** that encapsulate data fetching:
  - `useAgents()` -- Agent listing with loading and error states
  - `useChat()` -- Chat state management, message sending, response subscription
  - `useCosts()` -- Cost data fetching
  - `useDocuments()` -- Document upload and listing

Claude Code understood the distinction between server components (agent list, document
list -- static data, fast initial load) and client components (chat interface --
interactive, real-time streaming). It applied the correct `"use client"` directives
only where needed.

### Phase 4 -- Agent Engine: Intelligence Layer

**What we told Claude Code:** "Build the agent orchestration service. LangGraph state
machines for weather, quiz, and RAG agents. Wrap everything in Prefect flows for
retry and timeout. Circuit breaker for LLM failover."

**What Claude Code generated:**

- **Abstract base agent class** (`agents/base.py`) defining the contract:
  - `AgentInput` and `AgentOutput` Pydantic models
  - `BaseAgent` ABC with `run()` and `stream()` methods
  - This is the Strategy Pattern -- the gateway calls `agent.run(input)` without
    knowing or caring what type of agent it is

- **LangGraph state machines** for each agent type:
  - Weather agent: `parse_city` -> `fetch_weather` -> `generate_response`
  - Quiz agent: `generate_question` -> `evaluate_answer` -> `provide_feedback`
  - RAG agent: `embed_query` -> `retrieve_chunks` -> `build_prompt` -> `generate_response`
  - Each node is a pure function that transforms typed state, making agents testable
    and observable

- **LLM client with circuit breaker** (`llm_client.py`):
  ```python
  class LLMClient:
      def __init__(self, primary_url, fallback_url):
          self.primary = AsyncOpenAI(base_url=primary_url)   # vLLM (GPU)
          self.fallback = AsyncOpenAI(base_url=fallback_url)  # Ollama (CPU)

      async def chat(self, messages, **kwargs):
          try:
              if await self._is_healthy(self.primary):
                  return await self.primary.chat.completions.create(...)
          except Exception:
              pass  # Circuit breaker trips to fallback
          return await self.fallback.chat.completions.create(...)
  ```
  This pattern ensures the platform stays operational even when the GPU inference
  server goes down. The fallback to CPU-based Ollama is slower but keeps users
  unblocked.

- **Prefect flow wrapping** (`flows/agent_flow.py`) adding production reliability:
  - `retries=3` with exponential backoff (1s, 10s, 60s)
  - `timeout_seconds=120` to kill runaway LLM calls
  - `cache_key_fn` for deduplicating identical requests
  - Flow-level observability in the Prefect UI

- **Agent registry** (`registry.py`) using the Factory Pattern to map agent type
  strings to agent classes and graph builders.

- **Tool implementations** in `tools/` for weather API calls, web search, and
  calculator operations.

### Live Debugging Sessions

Building a platform with 5 microservices, a frontend, and Kubernetes infrastructure
means encountering real bugs. Here is where Claude Code truly earns its keep -- not
in the initial generation, but in the debugging.

**CORS issues:** The frontend at `localhost:3000` could not call the gateway at
`localhost:8000`. Claude Code diagnosed the missing `allow_origins` configuration
in the FastAPI CORS middleware and added the correct origins, methods, and headers.

**Next.js 14 vs 15 API differences:** The initial code used `use(params)` for
accessing route parameters (a Next.js 15 pattern). Claude Code identified the version
mismatch and refactored to `useParams()`, the correct hook for Next.js 14.

**Async/sync mutation mismatch:** GraphQL mutations were defined as synchronous
functions but called async service methods. Claude Code traced the stack to the
Strawberry resolver layer, identified that Strawberry supports async resolvers
natively, and converted the mutation resolvers to `async def`.

**UUID validation errors:** The browser was sending agent IDs in a format that
failed server-side UUID validation. Claude Code added proper UUID parsing with a
clear error message instead of an opaque 500 error.

**Prefect version conflicts:** The codebase was written against Prefect 3.x, but
some patterns from Prefect 2.x documentation had leaked in. Claude Code identified
the API differences (task decorator changes, flow runner changes) and updated all
usages to Prefect 3.x.

**GraphQL schema type mismatches:** The `latency_ms` field was defined as `int` in
the schema but the agent engine was returning `float` values. Claude Code identified
the mismatch, assessed the trade-offs (precision vs. schema clarity), and updated the
schema to use `float` with a renamed field `latency_ms` to maintain semantic clarity.

In each case, the debugging workflow was identical: paste the error, Claude Code reads
the stack trace, identifies the root cause, and produces a targeted fix. No searching
Stack Overflow. No reading documentation for 30 minutes. Paste, diagnose, fix, move on.

### Infrastructure: Kubernetes and Beyond

**What we told Claude Code:** "Create Kubernetes manifests for all services. HPA
auto-scaling. Minikube-compatible. Load test scripts."

**What Claude Code generated:**

- **Kustomize manifests** in `infra/k8s/base/` for every service: Deployment,
  Service, ConfigMap, resource limits, liveness/readiness probes using the `/healthz`
  and `/readyz` endpoints from each service.

- **HPA (Horizontal Pod Autoscaler)** configurations that scale services based on
  CPU and memory utilization, with sensible min/max replica counts.

- **Kustomize overlays** for different environments (dev, staging, prod) that patch
  the base manifests with environment-specific resource limits and replica counts.

- **Minikube setup scripts** for local Kubernetes development.

- **Load test scripts** using Locust to hammer the GraphQL endpoint and verify
  auto-scaling behavior.

- **A scaling dashboard** (React + polling) that visualizes pod counts, CPU usage,
  and request rates in real time during load tests.

- **An in-memory metrics collector** for development environments where a full
  Prometheus stack is overkill.

---

## 16. The AI-Assisted Development Workflow

Here is the workflow that was used to build this platform. If you adopt it, you will
be dramatically faster than traditional development while producing code of equal or
higher quality.

### Step 1: Describe What You Want in Natural Language

Be specific about the outcome, not the implementation. Good prompts:

- "Create a new GraphQL resolver that returns the total inference cost grouped by
  model name for the last 7 days."
- "Add a circuit breaker to the LLM client that falls back to Ollama after 3
  consecutive failures to the vLLM endpoint."
- "Write a Kustomize overlay for the staging environment that sets memory limits
  to 512Mi and replica count to 2."

Bad prompts:

- "Write some code." (Too vague)
- "Create a function called `get_costs` that takes a `start_date` parameter and
  queries the database using SQL." (Too prescriptive -- you are writing the code in
  English instead of letting Claude Code choose the right approach for your project)

### Step 2: Claude Code Reads Existing Context

Before generating a single line, Claude Code reads:

- Every CLAUDE.md file in the hierarchy from the root to your current directory
- The files you are currently editing or have recently mentioned
- Any code, errors, or context you paste into the conversation

This is why CLAUDE.md files are critical. They are the difference between a generic
answer and a project-specific answer.

### Step 3: Code Generation Following Project Conventions

Claude Code generates code that matches your project. In this platform:

- Python code uses type hints, Pydantic models, and async/await
- Services use the app factory pattern with FastAPI
- Configuration comes from environment variables via Pydantic Settings
- GraphQL types are defined in `schema.py` before resolvers are implemented
- Kubernetes manifests use Kustomize, never raw `kubectl apply`
- Tests live in `tests/unit/` and `tests/integration/` within each service

Claude Code does not need to be told these things every time. It reads them from
CLAUDE.md and applies them automatically.

### Step 4: Test and Iterate

After Claude Code generates code, you run it. Sometimes it works on the first try.
Sometimes there are errors. When there are errors, the workflow is:

1. Run the code
2. Copy the error message or stack trace
3. Paste it to Claude Code
4. Claude Code analyzes the error, identifies the root cause, and produces a fix
5. Apply the fix, run again
6. Repeat until it works

This iterative loop is fast -- typically 1-3 cycles for most issues. Claude Code
is particularly good at reading Python tracebacks, JavaScript error messages, and
Kubernetes event logs.

### Step 5: Fix Bugs in Real Time

The debugging experience with Claude Code is qualitatively different from traditional
debugging. Instead of:

1. Read the error message
2. Google the error message
3. Read 5 Stack Overflow answers
4. Try the highest-voted answer
5. It does not work because your context is different
6. Try the second answer
7. Eventually figure it out

You do:

1. Paste the error message
2. Get a fix that is specific to your codebase
3. Apply it
4. Move on

Claude Code has the advantage of seeing your actual code, your actual configuration,
and your actual error. It does not give you a generic answer. It gives you your answer.

### Step 6: Understand the Decisions

Claude Code does not just write code -- it explains why. When it chooses the factory
pattern over a module-level app instance, it explains that factory patterns make
testing easier. When it uses a circuit breaker for LLM calls, it explains that LLM
APIs are unreliable and you need graceful degradation.

This is valuable for learning. You are not just getting code -- you are getting a
running commentary on software engineering decisions from a system that has absorbed
a vast amount of engineering knowledge.

---

## 17. Architecture Decision Records (ADRs)

### How Claude Code Helped Write ADRs

This project has **7 Architecture Decision Records** in `docs/architecture/adr/`.
Each one documents a significant technical decision using a structured format:
Context, Decision, Consequences (positive and negative), and Alternatives Considered.

Claude Code helped write these ADRs by:

1. **Analyzing the actual codebase** to understand what decisions had been made
2. **Articulating the trade-offs** that led to each decision
3. **Documenting alternatives** that were considered and rejected, with clear
   reasoning for the rejection

The 7 ADRs in this project:

| ADR | Decision | Key Trade-off |
|-----|----------|---------------|
| 001 | Monorepo structure | Atomic changes vs. repo size complexity |
| 002 | GraphQL over REST | Flexible queries vs. caching complexity |
| 003 | vLLM with CPU fallback | GPU performance vs. availability |
| 004 | Prefect over Airflow | ML-native workflows vs. ecosystem size |
| 005 | Istio ambient mesh | No sidecars vs. maturity of ambient mode |
| 006 | pgvector over dedicated vector DB | Operational simplicity vs. scale limits |
| 007 | Redis semantic cache | Low-latency caching vs. cache invalidation complexity |

### Example: ADR-002 (GraphQL over REST)

Here is the reasoning Claude Code helped articulate for choosing GraphQL:

**Context:** The frontend presents composite views aggregating data from 4 different
backend services. A REST approach would require N parallel requests or a dedicated
Backend-for-Frontend service. The chat interface also requires streaming over
WebSocket regardless of the API paradigm.

**Decision:** Strawberry GraphQL on FastAPI. Strawberry's code-first, type-annotation
approach aligns with the Pydantic model ecosystem. Subscriptions over WebSocket handle
real-time chat streaming.

**Consequences:**
- Positive: Single round-trip for composite views, unified real-time mechanism,
  auto-generated TypeScript types for the frontend
- Negative: HTTP caching is harder (single POST endpoint), N+1 queries require
  DataLoaders, partial error handling differs from REST

**Alternatives rejected:**
- REST with BFF: Solves aggregation but adds a service to maintain
- gRPC-web: Excellent performance but requires Envoy proxy for browsers
- tRPC: TypeScript-native but incompatible with Python backends

This is the kind of documentation that engineering teams often skip because it takes
time. With Claude Code, writing an ADR takes minutes instead of hours.

---

## 18. CI/CD Integration

### GitHub Actions

Claude Code integrates directly with GitHub Actions for automated workflows.

#### Automated PR Review

```yaml
# .github/workflows/claude-review.yml
name: Claude Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Claude Code Review
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Review this PR for:
            1. Security vulnerabilities
            2. Performance issues
            3. Code style violations
            4. Missing tests
            Post findings as PR comments.
```

#### Automated Issue Triage

```yaml
# .github/workflows/claude-triage.yml
name: Issue Triage
on:
  issues:
    types: [opened]

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Analyze this issue and:
            1. Add appropriate labels (bug, feature, docs, etc.)
            2. Estimate complexity (S/M/L/XL)
            3. Suggest which service/component is affected
```

### GitLab CI/CD

Claude Code also works with GitLab pipelines:

```yaml
# .gitlab-ci.yml
claude-review:
  stage: review
  script:
    - npm install -g @anthropic-ai/claude-code
    - claude -p "Review the changes in this merge request for quality and security"
  only:
    - merge_requests
```

### How This Project Uses CI/CD

This project combines Claude Code with traditional CI/CD:

```
Developer pushes code
  │
  ├── GitHub Actions (CI)
  │   ├── Lint (ruff + mypy + eslint)
  │   ├── Unit tests (pytest + vitest)
  │   ├── Security scan (Trivy + OWASP ZAP)
  │   ├── Build Docker images
  │   └── Push to container registry
  │
  ├── Argo CD (GitOps)
  │   ├── Detects manifest changes in git
  │   ├── Syncs to Kubernetes cluster
  │   └── Progressive rollout with health checks
  │
  └── Claude Code (Review, optional)
      ├── Automated PR review
      ├── Suggest test improvements
      └── Flag architectural concerns
```

---

## 19. Best Practices for AI-Assisted Development

These practices were learned by building this platform. They apply to any project
using Claude Code or similar AI development tools.

### Write Good CLAUDE.md Files

This is the single highest-leverage thing you can do. A good CLAUDE.md is:

- **Specific, not generic.** "Python 3.11+, uv for deps, ruff lint+format" is useful.
  "Follow best practices" is useless.
- **Actionable.** Include exact commands: `uv run uvicorn gateway.main:create_app --factory --port 8000`
- **Convention-focused.** Document what patterns to use and what to avoid: "Kustomize
  base/overlays. Never raw kubectl apply."
- **Short.** The root CLAUDE.md should be under 200 lines. If it is longer, split
  context into directory-level CLAUDE.md files.

### Use Schema-First Design

Define your data contracts before implementing them. In this project, we defined
GraphQL types (Agent, ChatMessage, Document) before writing resolvers. This:

- Lets the frontend team start building against the schema immediately
- Gives Claude Code a clear target when generating resolver implementations
- Prevents the common failure mode of "the backend returns slightly different data
  than the frontend expects"

### Let AI Handle Boilerplate, Review the Patterns

Claude Code excels at generating repetitive code: CRUD resolvers, Kubernetes manifests,
test boilerplate, Dockerfile multi-stage builds, middleware setup. Let it handle these.

But **review the architectural patterns**. When Claude Code generates a circuit breaker,
verify that the failure thresholds make sense for your use case. When it generates HPA
configurations, verify that the CPU targets and replica ranges match your expected load.

The rule of thumb: trust the syntax, verify the semantics.

### Always Test AI-Generated Code

Claude Code generates code that is syntactically correct and follows patterns well.
But it can make logical errors, especially in:

- Edge cases in business logic
- Concurrency and race conditions
- Security-sensitive code (auth, input validation)
- Performance-critical paths

Run the tests. Write new tests for generated code. This project has a five-layer
testing strategy (unit, integration, e2e, load, chaos) precisely because every layer
of code -- human-written or AI-generated -- needs verification.

### Use AI for Debugging

This is arguably where Claude Code provides the most value per minute spent. The
workflow is simple:

1. Run your code
2. It fails with an error
3. Paste the error to Claude Code
4. Get a fix that is specific to your codebase
5. Apply it

Claude Code is particularly strong at:
- Python tracebacks (it identifies the root cause, not just the symptom)
- TypeScript type errors (it understands complex generic types)
- Kubernetes event logs (it maps pod events to configuration issues)
- Docker build failures (it traces layer dependencies)

### Trust but Verify

Claude Code is fast, knowledgeable, and consistent. It is also not infallible. It can:

- Hallucinate API methods that do not exist in the library version you are using
- Apply patterns from one framework to another where they do not fit
- Miss subtle security implications
- Generate code that works but is not the best approach for your scale

The correct mental model is: Claude Code is a very fast, very knowledgeable junior
engineer. It produces excellent first drafts that an experienced engineer should review.
As you gain experience, your ability to review effectively improves, and the
human-AI collaboration becomes more powerful.

---

## 20. What Claude Code Can and Cannot Do

### What Claude Code CAN Do

**Generate entire services from a description.** This platform has 5 Python
microservices and a Next.js frontend. Each one was initially generated by Claude Code
from a natural-language description guided by a slash command. The gateway service --
app factory, GraphQL schema, resolvers, middleware, Dockerfile, tests -- was generated
in a single session.

**Debug errors from stack traces.** Paste a Python traceback, a JavaScript error, or
a Kubernetes event log, and Claude Code identifies the root cause and produces a fix.
During this project's development, CORS issues, version mismatches, async/sync
conflicts, and schema type errors were all resolved this way.

**Write tests at every level.** Unit tests with pytest and Vitest, integration tests
with testcontainers, end-to-end tests with Playwright, load tests with Locust. Claude
Code generates tests that follow the existing test patterns in your project.

**Create Kubernetes manifests.** Deployments, Services, ConfigMaps, HPA configurations,
Kustomize overlays, Helm values files. Claude Code understands the Kubernetes resource
model and generates manifests with correct API versions, proper resource limits, and
working health probes.

**Follow project conventions consistently.** Once conventions are documented in
CLAUDE.md, Claude Code applies them across every file it generates. Every service
gets `/healthz` and `/readyz`. Every Python service uses the app factory pattern.
Every Kubernetes manifest uses Kustomize. Consistency is maintained across thousands
of lines of code without human vigilance.

**Explain code and architecture decisions.** Claude Code does not just write code. It
explains why it chose a particular pattern, what trade-offs exist, and what alternatives
were considered. This is invaluable for learning and for writing ADRs.

**Refactor across multiple files.** Rename a type, change an API contract, update a
pattern -- Claude Code can trace the implications across files and make coordinated
changes.

### What Claude Code CANNOT Do

**Access production systems or deploy code.** Claude Code operates on your local
filesystem. It cannot SSH into servers, access databases, or run deployment pipelines.
Deployment is handled by GitOps (Argo CD) -- you commit code, push to git, and the
deployment pipeline takes over.

**Replace understanding of fundamentals.** If you do not understand what a circuit
breaker is, you cannot evaluate whether Claude Code's circuit breaker implementation
is correct for your use case. If you do not understand Kubernetes resource limits,
you cannot judge whether the generated HPA configuration will work under your expected
load.

Claude Code accelerates engineers who understand the fundamentals. It does not
substitute for understanding the fundamentals.

**Make product decisions.** Claude Code does not know your users, your business
constraints, your performance requirements, or your budget. It can generate a service
that handles 10 requests per second or 10,000 requests per second -- but you need
to tell it which one you need and why.

**Guarantee security.** Claude Code can generate auth middleware, input validation,
and CORS configuration. But security requires threat modeling, penetration testing,
and domain-specific knowledge of attack vectors. Always have security-sensitive code
reviewed by a human with security expertise.

**Think about your system holistically across time.** Claude Code sees your codebase
at a point in time. It does not know your deployment history, your incident history,
or your team's operational strengths and weaknesses. Operational wisdom comes from
experience, not from code generation.

### The Goal: Amplify, Not Replace

The purpose of AI-assisted development is not to replace software engineers. It is to
amplify them. A junior engineer with Claude Code can produce code at the speed of a
mid-level engineer. A mid-level engineer with Claude Code can produce code at the
speed of a senior engineer. A senior engineer with Claude Code can build systems
that would normally require a team.

But in every case, the human brings something the AI cannot: judgment about what
to build, understanding of user needs, awareness of organizational context, and
accountability for the result.

The engineers who will thrive in the AI era are not those who memorize syntax or
type the fastest. They are those who:

1. **Understand systems deeply** -- so they can evaluate AI-generated architecture
2. **Communicate intent clearly** -- so they can guide AI effectively
3. **Think critically** -- so they can catch AI mistakes
4. **Learn continuously** -- so they can leverage each new AI capability

This platform was built to teach you all four of these skills. The code is real.
The architecture is production-grade. And every line was generated through a
collaboration between human intent and AI capability.

Welcome to the future of software engineering. It is not about coding less. It is
about building more.

---

---

## 21. End-to-End Lifecycle: Development to Deployment

This section walks through the **complete lifecycle** of building, testing, and
deploying a feature using Claude Code -- from initial idea to production URL.
Every step below was actually done in this project.

### The Lifecycle at a Glance

```
1. DEVELOP ──→ 2. TEST ──→ 3. CONTAINERIZE ──→ 4. DEPLOY ──→ 5. MONITOR
   Claude        Claude       Claude              Claude        Claude
   writes code   writes       generates            generates     helps debug
   & debugs      tests &      Dockerfiles &        K8s manifests production
   errors        load tests   compose files        & CI/CD       issues
```

### Step 1: Develop a Feature with Claude Code

**Real example: Adding the cost-tracker service to this platform.**

```bash
# Start Claude Code in the project root
cd ~/kiaa/ai-adoption
claude

# Describe the feature
> "Create a new microservice called cost-tracker that aggregates per-inference
>  costs from the agent engine. It should expose a GraphQL endpoint for the
>  frontend to query costs grouped by model, agent type, and time period."
```

**What Claude Code does:**

1. Reads `CLAUDE.md` -- knows the app factory pattern, port conventions, Pydantic Settings
2. Reads `services/CLAUDE.md` -- knows port 8054 is assigned to cost-tracker
3. Scaffolds the full service:
   ```
   services/cost-tracker/
   ├── src/cost_tracker/
   │   ├── __init__.py
   │   ├── main.py          # App factory with /healthz, /readyz
   │   ├── config.py         # Pydantic Settings (DATABASE_URL, etc.)
   │   ├── models.py         # SQLAlchemy models for cost records
   │   ├── schema.py         # Strawberry GraphQL types
   │   └── resolvers/
   │       └── cost.py       # Query resolvers (by model, agent, time)
   ├── tests/
   │   └── unit/
   │       └── test_resolvers.py
   ├── Dockerfile
   ├── pyproject.toml
   └── CLAUDE.md             # Service-specific context
   ```

4. Updates `docker-compose.yml` to add the cost-tracker service
5. Updates `services/gateway/` to forward cost queries to the new service

**Debugging in real time:**

```bash
# Run the service locally
> "Start the cost-tracker service and test the GraphQL endpoint"

# Claude runs the command, gets an import error
> ERROR: ModuleNotFoundError: No module named 'cost_tracker.config'

# Claude reads the traceback, identifies the issue (missing __init__.py in src/),
# fixes it, and re-runs -- all in the same conversation
```

### Step 2: Test with Claude Code

**Unit tests:**

```bash
> "Write comprehensive unit tests for the cost-tracker resolvers"
```

Claude generates tests using pytest, following the project's test patterns:

```python
# tests/unit/test_resolvers.py
import pytest
from cost_tracker.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_cost_by_model(client):
    response = client.post("/graphql", json={
        "query": "{ costByModel(days: 7) { model totalCost requestCount } }"
    })
    assert response.status_code == 200
    data = response.json()["data"]["costByModel"]
    assert isinstance(data, list)
```

**Integration tests:**

```bash
> "Write integration tests using testcontainers for the cost-tracker database layer"
```

**Load tests (real example from this project):**

```bash
> "Create a load test script that simulates 30 concurrent users hitting the
>  chat endpoint, ramping from 5 to 30 users over 150 seconds"
```

Claude generated `tests/load/loadtest_gpu_30users.py` -- a Python asyncio load test
that captured per-request latency, success rates, and GPU utilization at each
concurrency level. Results: 100% success at 15 users, dropping to 34% at 30 users
due to Ollama's serial inference bottleneck. This data directly informed the decision
to use vLLM with continuous batching in production.

**Fix failing tests:**

```bash
# Run tests
> "Run make test and fix any failures"

# Claude runs the tests, reads the output, and fixes each failure
# Typical: 1-3 fix cycles to get all tests passing
```

### Step 3: Containerize with Claude Code

```bash
> "Create a multi-stage Dockerfile for the cost-tracker service"
```

Claude generates a Dockerfile following the project's patterns:

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

FROM python:3.11-slim
WORKDIR /app
RUN useradd --create-home appuser
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
USER appuser
EXPOSE 8004
CMD [".venv/bin/uvicorn", "cost_tracker.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8004"]
```

```bash
> "Update docker-compose.yml to add the cost-tracker service"
```

Claude adds the service with correct port mapping, network, health check, and
dependencies -- matching the patterns of existing services.

### Step 4: Deploy with Claude Code

**Local deployment (Docker Compose):**

```bash
> "Start all services with Docker Compose and verify health endpoints"

# Claude runs:
docker compose up -d --build
# Then checks each service's /healthz endpoint
```

**Cloud deployment (GCP VM -- actual example from this project):**

```bash
> "Create a script to deploy the application on a GCP VM with Docker Compose
>  and Caddy for HTTPS"
```

Claude generated:
- `scripts/gcp-vm-start.sh` -- Starts VMs, deploys services, verifies health
- `scripts/gcp-vm-stop.sh` -- Stops services and VMs gracefully
- `scripts/gcp-vm-status.sh` -- Shows VM status, service health, GPU info
- `Caddyfile` -- Reverse proxy configuration for automatic HTTPS

**Domain and HTTPS setup (actual example):**

```bash
> "Configure Caddy to serve ai-adoption.uk with automatic Let's Encrypt
>  certificates behind Cloudflare proxy"
```

Claude helped configure:
1. Cloudflare DNS (A records pointing to VM IP)
2. Cloudflare SSL mode (Full -- not Flexible, which causes redirect loops)
3. Caddyfile (`:80` behind Cloudflare, not `{domain}` which causes ACME failures)
4. Docker Compose (caddy service with `--profile web`)
5. Environment variables (`SITE_DOMAIN`, `NEXT_PUBLIC_GRAPHQL_URL`)

Result: `https://ai-adoption.uk` serves the platform with dual-layer TLS
(Cloudflare edge + Let's Encrypt origin).

**Kubernetes deployment:**

```bash
> "Create Kustomize manifests for all services with HPA auto-scaling"
```

Claude generated the full K8s stack:
- Deployments, Services, ConfigMaps for every service
- HPA configurations (1-5 replicas, 50% CPU target)
- Kustomize overlays for dev/staging/prod
- Load test scripts to demonstrate auto-scaling

The auto-scaling was tested on a GCP GPU VM with minikube, demonstrating the full
HPA lifecycle: baseline → load spike → scale-up (1→2 pods) → load drop →
scale-down (2→1 pods). See `docs/architecture/autoscaling-deep-dive.md`.

### Step 5: Monitor and Debug Production Issues with Claude Code

```bash
# Check production logs
ssh merit@34.121.112.167 "docker logs aiadopt-gateway --tail 50"

# Paste logs to Claude Code
> "Here are the gateway logs. Why are some requests returning 502?"
```

Claude reads the logs, correlates timestamps, identifies the root cause (e.g.,
agent-engine OOM, Prefect timeout, Ollama serial queue), and suggests fixes.

**Real debugging examples from this project:**

| Issue | How Claude Code Fixed It |
|-------|-------------------------|
| Prefect ephemeral server timeout | Added `_direct_execute()` fallback bypassing Prefect |
| Frontend "Failed to fetch" errors | Identified wrong `NEXT_PUBLIC_GRAPHQL_URL` (build-time variable) |
| Caddy ACME cert failure behind Cloudflare | Changed Caddyfile from `{$SITE_DOMAIN}` to `:80` |
| Scaling dashboard empty | Connected gateway to minikube Docker network |
| HPA not triggering | Lowered resource requests from 100m to 30m CPU |
| `.env` file corrupted by Terraform | Diagnosed shell script leaking into .env, rewrote manually |

### The Complete Flow: One Feature, End to End

```
1. "Create a cost-tracker service"
   └── Claude scaffolds: main.py, schema.py, resolvers, Dockerfile, tests, CLAUDE.md

2. "Run the tests and fix failures"
   └── Claude runs pytest, reads errors, fixes 3 issues in 2 cycles

3. "Build the Docker image and add to compose"
   └── Claude writes Dockerfile, updates docker-compose.yml

4. "Deploy to the GCP VM"
   └── Claude SSH's guidance: git pull, docker compose up -d --build

5. "The /costs page shows 'Failed to fetch'"
   └── Claude: "Gateway needs a route to cost-tracker. Adding /costs* → cost-tracker:8004"

6. "Run a load test with 20 users"
   └── Claude generates load test, runs it, reports: "P95 latency 2.3s, 0 errors"

7. "Create K8s manifests with HPA"
   └── Claude: Deployment + Service + HPA + Kustomize overlay

8. "Set up monitoring alerts"
   └── Claude: Prometheus alert rules for error rate > 5%, latency P99 > 10s
```

Every step in this lifecycle was done in this project using Claude Code. The key
insight: Claude Code is not just a code generator. It is a development partner that
participates in every phase -- from initial design to production debugging.

---

## Appendix: Project File Reference

| Path | Description |
|------|-------------|
| `CLAUDE.md` | Root project context (83 lines) |
| `.claude/commands/*.md` | 11 slash commands for tutorial phases |
| `services/gateway/` | FastAPI + Strawberry GraphQL gateway |
| `services/agent-engine/` | Prefect + LangGraph agent orchestration |
| `services/document-service/` | MinIO + pgvector document service |
| `services/cache-service/` | Redis VSS semantic cache |
| `services/cost-tracker/` | OpenCost aggregation |
| `frontend/` | Next.js 14 + Tailwind + Shadcn/ui |
| `libs/py-common/` | Shared Python library (config, logging, telemetry) |
| `libs/ts-common/` | Shared TypeScript library (types, utils) |
| `infra/k8s/` | Kustomize base + overlays |
| `infra/argocd/` | Argo CD app-of-apps |
| `infra/tekton/` | Tekton CI/CD pipelines |
| `infra/policy/` | OPA Gatekeeper constraints |
| `docs/architecture/adr/` | 7 Architecture Decision Records |
| `docs/architecture/autoscaling-deep-dive.md` | HPA control loop, metrics pipeline, scaling algorithm |
| `docs/tutorial/` | Phase 0-10 tutorial documents |
| `docs/runbooks/domain-setup.md` | Domain + HTTPS setup (Cloudflare + Caddy) |
| `docs/runbooks/gcp-vm-operations.md` | VM start/stop, service management, troubleshooting |
| `docs/testing/` | Load test scripts and results |
| `scripts/gcp-vm-start.sh` | Start GCP VMs and deploy services |
| `scripts/gcp-vm-stop.sh` | Stop VMs and services gracefully |
| `scripts/gcp-vm-status.sh` | Check VM and service status |
| `tests/` | e2e, integration, load, chaos, security tests |
| `Caddyfile` | Caddy reverse proxy configuration for HTTPS |
