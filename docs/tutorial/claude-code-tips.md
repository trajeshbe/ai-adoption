# Claude Code Tips: From Basics to Advanced

> **45 practical tips for getting the most out of Claude Code**, curated from
> [ykdojo/claude-code-tips](https://github.com/ykdojo/claude-code-tips) and
> contextualized with examples from this AI Agent Platform.
>
> See also: [Claude Code Guide](claude-code-guide.md) for installation, configuration, and
> the full development lifecycle with Claude Code.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Context Management](#2-context-management)
3. [Productivity & Workflow](#3-productivity--workflow)
4. [Git & GitHub Mastery](#4-git--github-mastery)
5. [Testing & Verification](#5-testing--verification)
6. [Research & Exploration](#6-research--exploration)
7. [Advanced Patterns](#7-advanced-patterns)
8. [Writing & Communication](#8-writing--communication)
9. [Philosophy & Mindset](#9-philosophy--mindset)
10. [Quick Reference](#10-quick-reference)

---

## 1. Getting Started

### Tip: Learn the essential slash commands

Type `/` to see all built-in commands. The most useful ones:

| Command | What it does |
|---------|-------------|
| `/usage` | Check your rate limits and token usage |
| `/stats` | GitHub-style activity graph of your Claude Code usage |
| `/clear` | Clear conversation and start fresh |
| `/compact` | Summarize conversation to free context space |
| `/copy` | Copy Claude's last response to clipboard as markdown |
| `/plan` | Enter plan mode for architectural decisions |
| `/fork` | Fork the current session to try a different approach |
| `/release-notes` | See what's new in the latest version |

**In this repo**, we also have 11 custom slash commands for the tutorial phases:

```bash
/00-setup-env          # Phase 0: Environment bootstrap
/01-scaffold-api       # Phase 1: GraphQL API gateway
/02-scaffold-frontend  # Phase 2: Next.js frontend
# ... see docs/tutorial/README.md for all phases
```

> **Reference:** [Tutorial Phases](README.md) | [Claude Code Guide - Skills & Commands](claude-code-guide.md#8-skills-custom-slash-commands)

### Tip: Talk to Claude Code with your voice

Voice input is significantly faster than typing. Options:

- **Built-in voice mode** — Claude Code now has native voice support
- **superwhisper** (Mac) — [superwhisper.com](https://superwhisper.com/)
- **Local Whisper models** — accurate enough even with occasional typos; Claude understands intent

Works even when whispering into earphones — useful in shared spaces or on planes.

### Tip: Set up terminal aliases

Since you'll use the terminal more with Claude Code, set up shortcuts in `~/.zshrc` or `~/.bashrc`:

```bash
alias c='claude'
alias ch='claude --chrome'
alias co='code'

# Resume conversations
# c -c    → continue last conversation
# c -r    → pick from recent conversations
```

### Tip: Install the dx plugin

The [ykdojo/claude-code-tips](https://github.com/ykdojo/claude-code-tips) repo is also
a Claude Code plugin with useful slash commands:

```bash
claude plugin marketplace add ykdojo/claude-code-tips
claude plugin install dx@ykdojo
```

| Skill | Description |
|-------|-------------|
| `/dx:gha <url>` | Analyze GitHub Actions failures |
| `/dx:handoff` | Create handoff documents for context continuity |
| `/dx:clone` | Clone conversations to branch off |
| `/dx:half-clone` | Half-clone to reduce context |
| `/dx:review-claudemd` | Review conversations to improve CLAUDE.md |

---

## 2. Context Management

### Tip: Context is like milk — best served fresh

Claude Code performs best at the start of a conversation when context is clean.
As the conversation grows longer, performance can degrade.

**Best practice:** Start a new conversation for each new topic or task.

### Tip: Proactively compact your context

Don't wait for automatic compaction. Create a **handoff document** before starting fresh:

```
> Put the current plan and progress in HANDOFF.md. Explain what you've tried,
  what worked, what didn't, so the next agent with fresh context can pick up
  where you left off.
```

Then start a new conversation and point it at the handoff file.

**Alternative:** Use plan mode (`Shift+Tab` or `/plan`). Ask Claude to gather context
and create a comprehensive plan, then clear context and start fresh with the plan.

**In this repo**, we used this technique extensively — the 10-phase tutorial was built
across many sessions, each starting with clear context about what was already complete.

### Tip: Slim down the system prompt

Claude Code's system prompt + tool definitions consume ~19k tokens (~10% of 200k context)
before you even start. You can reduce this:

1. **Lazy-load MCP tools** — add to `~/.claude/settings.json`:
   ```json
   {
     "env": {
       "ENABLE_TOOL_SEARCH": "true"
     }
   }
   ```

2. **Keep CLAUDE.md concise** — every word counts. Our root
   [CLAUDE.md](../../CLAUDE.md) is ~142 lines covering the entire 16-component stack.

### Tip: Keep CLAUDE.md simple and review it periodically

Start with no CLAUDE.md at all. Only add rules when you find yourself repeating
the same instruction to Claude Code.

**In this repo**, the CLAUDE.md hierarchy is structured by scope:

| Level | File | Purpose |
|-------|------|---------|
| Root | [`CLAUDE.md`](../../CLAUDE.md) | Project overview, conventions, build commands |
| Services | [`services/CLAUDE.md`](../../services/CLAUDE.md) | Shared service patterns |
| Per-service | [`services/gateway/CLAUDE.md`](../../services/gateway/CLAUDE.md) | Service-specific endpoints, patterns |
| Frontend | [`frontend/CLAUDE.md`](../../frontend/CLAUDE.md) | Pages, components, build-time env vars |
| Infra | [`infra/CLAUDE.md`](../../infra/CLAUDE.md) | K8s, Helm, Terraform structure |

Each file is as concise as possible while providing the context Claude needs.

> **Reference:** [Claude Code Guide - Rules That Shape Behavior](claude-code-guide.md#5-rules-that-shape-behavior)

### Tip: Understand CLAUDE.md vs Skills vs Slash Commands vs Plugins

| Mechanism | Loaded when | Who invokes it | Best for |
|-----------|-------------|---------------|----------|
| **CLAUDE.md** | Every conversation | Automatic | Project conventions, constraints |
| **Skills** | When relevant | Claude (auto) or user | Token-efficient contextual knowledge |
| **Slash Commands** | On demand | User (`/command`) | Repeatable workflows at your pace |
| **Plugins** | On install | Bundles all of the above | Shareable toolkits |

---

## 3. Productivity & Workflow

### Tip: Break down large problems into smaller ones

This is the single most important skill. It's the same as traditional software engineering.

**Example from this repo:** Building the OpenAI provider feature required changes across
7 files in 4 layers. Instead of one massive prompt, the work was broken down:

```
1. Add openai_api_key to Settings (config.py)           → 1 file
2. Add factory method to LLMClient (llm_client.py)      → 1 file
3. Accept LLM config in ExecuteRequest (main.py)         → 1 file
4. Wire through agent_flow (agent_flow.py)               → 1 file
5. Add LLMConfigInput to GraphQL schema (schema.py)      → 1 file
6. Pass config in resolver (chat.py)                      → 1 file
7. Add UI provider selector (page.tsx)                    → 1 file
```

Each step was small, testable, and built on the previous one.

### Tip: Multitask with terminal tabs

Run multiple Claude Code instances for parallel work. The **cascade** method:
open a new tab on the right for each new task, sweep left to right checking progress.

Focus on at most 3-4 tasks at a time.

### Tip: Use Git worktrees for parallel branch work

Work on multiple branches simultaneously without conflicts:

```bash
# Ask Claude Code to create a worktree
> "Create a git worktree for feature/add-caching and start working on
   Redis semantic cache integration"
```

Each worktree is a separate directory with its own branch — combine with the
cascade tab method for maximum parallelism.

### Tip: Invest in your own workflow

The best Claude Code users customize their environment:

- **CLAUDE.md** files tuned to your project (this repo has 12)
- **Custom slash commands** for repeatable tasks (this repo has 11)
- **Terminal aliases** for quick access
- **Status line** customization showing model, branch, token usage

> **Reference:** [Claude Code Guide - Settings](claude-code-guide.md#7-settings--configuration)

### Tip: Automation of automation

Whenever you repeat the same task, automate it:

- Repeating the same instruction? → Add it to CLAUDE.md
- Running the same workflow? → Create a slash command
- Same verification steps? → Create a test script

**In this repo**, the CI/CD pipeline ([`.github/workflows/`](../../.github/workflows/))
automates lint → test → scan → deploy → smoke test — built entirely with Claude Code.

### Tip: Navigate and edit the input box efficiently

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Jump to beginning of line |
| `Ctrl+E` | Jump to end of line |
| `Option+Left/Right` | Jump by word |
| `Ctrl+W` | Delete previous word |
| `Ctrl+U` | Delete to beginning of line |
| `Ctrl+K` | Delete to end of line |
| `Ctrl+G` | Open prompt in external editor |
| `Ctrl+V` | Paste image from clipboard |
| `\` + Enter | Insert newline (multi-line input) |

### Tip: Get output out of the terminal

| Method | When to use |
|--------|-------------|
| `/copy` | Copy last response as markdown |
| `pbcopy` (Mac) | Send output to clipboard programmatically |
| Write to file | Create a .md file and open in VS Code |
| Open URL | Ask Claude to open a URL in your browser |

---

## 4. Git & GitHub Mastery

### Tip: Let Claude Code handle Git

Ask Claude to commit, branch, create PRs — you don't have to write commit messages manually.

**In this repo**, every commit uses the pattern:
```
<description of what changed and why>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Best practices:
- **Allow pull automatically**, but review push — push is riskier
- **Create draft PRs** — let Claude handle creation, review before marking ready
- **Use `gh` CLI** — Claude can create PRs, check CI status, investigate failures

### Tip: Disable commit/PR attribution (optional)

If you don't want the `Co-Authored-By` trailer, add to `~/.claude/settings.json`:

```json
{
  "attribution": {
    "commit": "",
    "pr": ""
  }
}
```

**In this repo**, we keep attribution enabled for traceability — it makes AI contributions
visible in `git log` and `git blame`, which is an
[enterprise governance best practice](../getting-started-enterprise-ai-adoption.md#91-git-attribution).

### Tip: Interactive PR reviews

Claude Code is an excellent interactive PR reviewer:

```bash
> "Review PR #42 — go file by file, focusing on security and
   architectural consistency with our existing patterns"
```

You control the pace: general overview first, then drill into specific files.

### Tip: Use Claude Code as a DevOps engineer

For GitHub Actions CI failures, just point Claude at the URL:

```bash
> "Dig into this CI failure: https://github.com/merit-data-tech/ai-adoption/actions/runs/24067446299
   Find the root cause — was it a specific commit, a flaky test, or a config issue?"
```

**In this repo**, we iteratively fixed 7 CI/CD issues across 4 commits until the
pipeline was fully green — all driven by Claude Code investigating failures.

> **Reference:** [CI/CD Pipeline Runbook](../runbooks/cicd-pipeline.md)

---

## 5. Testing & Verification

### Tip: Write lots of tests (and use TDD)

TDD works exceptionally well with Claude Code:

1. Write tests first → make sure they fail
2. Commit the tests
3. Ask Claude to write code to make them pass
4. Review the tests yourself to ensure they're meaningful

**In this repo**, every service has `tests/unit/` and `tests/integration/` directories.
The CI pipeline runs them per-service to avoid conftest collisions:

```yaml
# From .github/workflows/ci.yml
for svc in services/*/; do
  if [ -d "${svc}tests/unit" ]; then
    (cd "$svc" && uv run pytest tests/unit/ -v --tb=short)
  fi
done
```

> **Reference:** [CLAUDE.md - Testing Strategy](../../CLAUDE.md)

### Tip: Complete the write-test cycle for autonomous tasks

For Claude Code to run autonomously (e.g., `git bisect`), it needs a way to verify
results. The pattern: write → run → check output → repeat.

For web apps, use **Playwright MCP** or **Claude's native browser** (`/chrome`):

```markdown
# In CLAUDE.md for browser testing:
- Use `read_page` to get element refs from the accessibility tree
- Use `find` to locate elements by description
- Click/interact using `ref`, not coordinates
- NEVER take screenshots unless explicitly requested
```

### Tip: Master different ways of verifying output

| Method | Best for |
|--------|----------|
| Run tests | Automated verification of correctness |
| Visual Git client | Reviewing multi-file changes |
| Draft PR | Seeing the full diff in GitHub UI |
| "Double check everything" | Ask Claude to verify its own claims |
| Accessibility tree | Browser-based verification |

A powerful verification prompt:
> "Double check everything — every single claim in what you produced. At the end,
> make a table of what you were able to verify."

---

## 6. Research & Exploration

### Tip: Claude Code as a research tool

Claude Code replaces many research workflows. Give it the right access:

| Information source | How to access |
|-------------------|---------------|
| Codebase | Direct file reading (built-in) |
| GitHub (PRs, issues, CI) | `gh` CLI |
| Blocked websites (Reddit) | Gemini CLI as fallback |
| Private channels | Slack MCP, Gmail MCP |
| Scientific papers | paper-search plugin |
| Web pages | `Cmd+A` → copy → paste into Claude |

### Tip: Cmd+A / Ctrl+A for blocked content

When Claude can't fetch a URL directly:

1. Open the page in your browser
2. Select all (`Cmd+A` on Mac, `Ctrl+A` elsewhere)
3. Copy and paste into Claude Code

**Tricks for specific platforms:**
- **Gmail threads:** Click "Print All" → select from print preview
- **YouTube:** Click "Show transcript" → select all
- **Reddit:** Use Gemini CLI as a fallback (see below)

### Tip: Use Gemini CLI as a fallback for blocked sites

Create a skill that uses Gemini CLI to fetch content Claude can't access:

```bash
# Install Gemini CLI, then create a skill at:
# ~/.claude/skills/reddit-fetch/SKILL.md
```

Or install the dx plugin which includes this: `claude plugin install dx@ykdojo`

### Tip: Search through conversation history

Your conversations are stored in `~/.claude/projects/` as `.jsonl` files:

```bash
# Find conversations mentioning "GraphQL"
grep -l -i "graphql" ~/.claude/projects/-home-merit-kiaa-ai-adoption/*.jsonl

# Find today's conversations about a topic
find ~/.claude/projects/ -name "*.jsonl" -mtime 0 -exec grep -l -i "deploy" {} \;
```

Or just ask Claude directly: *"What did we discuss about the deploy pipeline today?"*

---

## 7. Advanced Patterns

### Tip: Containers for long-running risky tasks

Run Claude Code in a container with `--dangerously-skip-permissions` for autonomous work:

- Use [SafeClaw](https://github.com/ykdojo/safeclaw) for easy container management
- Spin up multiple isolated sessions with web terminals
- Your local Claude Code can orchestrate a container Claude via tmux

**Pattern:**
```
Local Claude Code → tmux session → Container → Claude Code (skip-permissions)
  ↕ (send-keys / capture-pane)
```

### Tip: Run bash commands and subagents in the background

- Press `Ctrl+B` to move a long-running command to background
- Claude Code checks on it later using `BashOutput`
- Customize subagents: specify count, model (Opus/Sonnet/Haiku), background vs foreground

### Tip: Manual exponential backoff for long-running jobs

For Docker builds or CI runs, ask Claude to check with increasing intervals:

```
> "Check the deploy workflow status every minute, then every 2 minutes,
   then every 4 minutes, until it completes"
```

More token-efficient than `gh run watch` which outputs continuously.

**In this repo**, we used this pattern to monitor deploy pipeline runs:
```bash
# Token-efficient CI check
gh run view <run-id> --repo merit-data-tech/ai-adoption | head -15
```

### Tip: Clone/fork conversations

Try different approaches without losing your original thread:

- **`/fork`** — fork from within a conversation
- **`--fork-session`** — use with `--resume` or `--continue`
- **Half-clone** — keep only the later half to reduce context

### Tip: Use `realpath` for absolute paths

When pointing Claude at files in other directories:

```bash
realpath services/gateway/src/gateway/schema.py
# → /home/merit/kiaa/ai-adoption/services/gateway/src/gateway/schema.py
```

### Tip: Audit your approved commands

Periodically check what commands you've auto-approved:

```bash
npx cc-safe .
```

Detects risky patterns like `sudo`, `rm -rf`, `git reset --hard`, `docker run --privileged`.

---

## 8. Writing & Communication

### Tip: Claude Code as a writing assistant

Use voice input for the first draft, then refine interactively:

1. Give Claude all the context about what you're writing
2. Dictate detailed instructions via voice → first draft
3. Go through it line by line: *"I like this part. Move this section there.
   Change this line to emphasize X."*
4. Terminal on the left, editor on the right

**In this repo**, all 55+ documentation files (23,000+ lines) were written this way.

### Tip: Markdown is powerful

With Claude Code, markdown is the most efficient document format:

- Claude reads and writes it natively
- Version-controlled alongside code
- Renders in GitHub, VS Code, and most platforms

**In this repo**, every doc is markdown — from ADRs to runbooks to this tips guide.

### Tip: Use Notion to preserve links when pasting

- **From web → Claude:** If you have text with links (from Slack, etc.), paste into
  Notion first → copy from Notion → paste into Claude (preserves links as markdown)
- **From Claude → web:** Paste markdown into Notion → copy from Notion into the
  destination platform (preserves formatting)

---

## 9. Philosophy & Mindset

### Tip: Choose the right level of abstraction

It's not binary between "vibe coding" and "reviewing every line":

- **High-level (vibe coding):** Fine for one-time scripts, prototypes, non-critical code
- **Medium:** Review architecture and key decisions, trust implementation details
- **Deep dive:** Line-by-line review for security, core business logic, shared libraries

**In this repo**, we use deep review for `schema.py` (API contract) and `llm_client.py`
(circuit breaker), but lighter review for documentation and test boilerplate.

### Tip: Be braver in the unknown

Claude Code lets you work effectively in unfamiliar territory. Even in unknown languages
or frameworks, you can iteratively explore and solve problems.

**Example:** This repo spans Python (FastAPI, Prefect, LangGraph), TypeScript (Next.js),
YAML (K8s, GitHub Actions), HCL (Terraform), and Rego (OPA policies) — all built with
Claude Code regardless of the developer's primary language expertise.

### Tip: Spend time planning, but also prototype quickly

- Use **plan mode** (`Shift+Tab`) for architectural decisions
- **Prototype first** to validate technology choices
- Then implement properly with the validated approach

**In this repo**, we used plan mode to design the
[DevOps pipeline](../runbooks/cicd-pipeline.md) before implementing it — resulting
in a plan that covered CI gate, UAT approval, SSH deploy, and smoke tests.

### Tip: Simplify overcomplicated code

Claude Code has a bias toward writing more code than necessary. Periodically ask:

- *"Why did you add this extra abstraction?"*
- *"Can we simplify this? We don't need the extra configurability."*
- *"This helper function is only called once — inline it."*

### Tip: The best way to get better is by using it

The "billion token rule" — like the 10,000 hour rule, but for AI. Use Claude Code
for everything: code, docs, research, DevOps, writing. The intuition for what
works and what doesn't comes from practice.

### Tip: Claude Code is the universal interface

It's not just for coding. Use it for:

- **Video editing** (via ffmpeg)
- **Audio transcription** (via Whisper)
- **CSV analysis** (via Python/pandas)
- **Disk cleanup** and system maintenance
- **Any digital task** — Claude will figure out the right tool

---

## 10. Quick Reference

### Essential keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Tab` / `Shift+Tab` | Toggle plan mode |
| `Ctrl+B` | Send running command to background |
| `Ctrl+C` | Cancel current operation |
| `Ctrl+G` | Edit prompt in external editor |
| `Ctrl+V` | Paste image |
| `Esc` | Cancel current input |

### Essential slash commands

| Command | Action |
|---------|--------|
| `/usage` | Check rate limits |
| `/stats` | Activity statistics |
| `/compact` | Compress conversation |
| `/clear` | Start fresh |
| `/copy` | Copy last response |
| `/plan` | Enter plan mode |
| `/fork` | Fork conversation |
| `/chrome` | Toggle browser integration |
| `/mcp` | Manage MCP servers |
| `/permissions` | Manage allowed/denied tools |

### Recommended settings (`~/.claude/settings.json`)

```json
{
  "env": {
    "ENABLE_TOOL_SEARCH": "true"
  },
  "permissions": {
    "allow": ["Read(~/.claude)"]
  }
}
```

### Quick setup (from ykdojo/claude-code-tips)

```bash
bash <(curl -s https://raw.githubusercontent.com/ykdojo/claude-code-tips/main/scripts/setup.sh)
```

Configures: dx plugin, status line, lazy-load MCP tools, aliases, and more.

---

## Further Reading

- **Source:** [ykdojo/claude-code-tips](https://github.com/ykdojo/claude-code-tips) — Original 45 tips by YK Dojo
- **Video:** [Claude Code Masterclass](https://youtu.be/9UdZhTnMrTA) — Lessons from 31 months of agentic coding
- **Newsletter:** [Agentic Coding with Discipline and Skill](https://agenticcoding.substack.com/)
- **This repo's guide:** [Claude Code Guide](claude-code-guide.md) — Install, configure, develop, test, deploy
- **Enterprise adoption:** [Getting Started: Enterprise AI Adoption](../getting-started-enterprise-ai-adoption.md) — Enterprise roadmap with Turing framework
- **Anthropic docs:** [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)

---

*Curated from [ykdojo/claude-code-tips](https://github.com/ykdojo/claude-code-tips) and
contextualized for the AI Agent Platform. Built with [Claude Code](https://claude.ai/code).*
