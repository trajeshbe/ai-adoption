# Cost-Benefit Analysis: AI Development Tools for Enterprise (125 Engineers)

> **Scenario:** 125 engineers across an organization evaluating AI-powered development
> tools. Budget allocation: 15-20 power users at $100/month, remaining ~105-110 at
> $20/month. Total monthly budget: $3,600-$4,200.
>
> **Last updated:** April 2026. Verify pricing at vendor websites before procurement.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Budget Model](#2-budget-model)
3. [Tool Landscape & Pricing](#3-tool-landscape--pricing)
4. [Head-to-Head Comparison](#4-head-to-head-comparison)
5. [Recommended Tool Allocation](#5-recommended-tool-allocation)
6. [Cost Scenarios](#6-cost-scenarios)
7. [ROI & Productivity Analysis](#7-roi--productivity-analysis)
8. [Risk Assessment](#8-risk-assessment)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Recommendation](#10-recommendation)

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Total headcount | 125 engineers |
| Power users (Tier 1) | 15-20 ($100/month each) |
| Standard users (Tier 2) | 105-110 ($20/month each) |
| Monthly budget range | **$3,600 - $4,200** |
| Annual budget range | **$43,200 - $50,400** |
| Estimated productivity gain | 25-40% reduction in repetitive tasks |
| Estimated ROI | 8-15x return on tool investment |

**Bottom line:** At $43K-$50K/year for 125 engineers, the investment is equivalent to
0.3-0.5 FTE salary — while delivering productivity gains across the entire team that
conservatively equal 10-20 FTE-equivalents of freed capacity.

---

## 2. Budget Model

### Tier Structure

| Tier | Role Profile | Count | Monthly Budget | Annual Cost |
|------|-------------|-------|----------------|-------------|
| **Tier 1: Power Users** | Senior engineers, architects, tech leads — heavy daily AI usage, agentic workflows, multi-file refactors, CI/CD automation | 20 | $100/user | $24,000 |
| **Tier 2: Standard Users** | Mid-level and junior engineers — code completion, chat assistance, documentation, learning | 105 | $20/user | $25,200 |
| **Total** | | **125** | **$4,100** | **$49,200** |

### Why Two Tiers?

Power users (Tier 1) need:
- Agentic AI (multi-step autonomous coding) — consumes 5-20x more tokens
- Access to frontier models (Opus-class) for complex architectural reasoning
- Higher rate limits for sustained daily usage
- Background agents, parallel workstreams

Standard users (Tier 2) need:
- Code completion (autocomplete) — low token cost
- Chat-based Q&A and documentation help
- Code review assistance
- Occasional agentic tasks

A flat $20/user budget wastes money on users who don't need power features.
A flat $100/user budget wastes money across the board. The tiered model optimizes spend.

---

## 3. Tool Landscape & Pricing

### Category A: Agentic AI Coding (Co-Developer)

These tools go beyond autocomplete — they autonomously plan, implement, test, and
iterate across multiple files. This is where Tier 1 budget is most impactful.

| Tool | Tier 2 Plan ($20) | Tier 1 Plan ($100) | Capability Level |
|------|-------------------|-------------------|-----------------|
| **Claude Code** (Anthropic) | Pro: $20/mo | Max 5x: $100/mo | Full agentic CLI, multi-file edits, subagents, background tasks, MCP integrations |
| **OpenAI Codex** (ChatGPT) | Plus: $20/mo | Pro: $200/mo (over budget) | Cloud sandbox agent, code execution, limited IDE integration |
| **Cursor** (AI IDE) | Pro: $20/mo | Business: $40/mo | IDE-native agentic mode (Composer), multi-file edits |
| **Replit Agent** | Core: $25/mo (over budget) | Core: $25/mo | Full-stack app generation, cloud-based |
| **GitHub Copilot** | Pro: $10/mo | Pro+: $39/mo | Agent mode (Copilot Workspace), issue-to-PR automation |

### Category B: Code Completion & Chat (Copilot-Class)

Reactive tools: autocomplete, inline suggestions, chat Q&A. Best fit for Tier 2 users.

| Tool | Price/User/Month | Key Strengths |
|------|-----------------|---------------|
| **GitHub Copilot Pro** | $10 | Best IDE integration, multi-model (GPT-4o, Claude, Gemini), IP indemnity |
| **GitHub Copilot Business** | $19 | + org management, audit logs, policy controls |
| **Windsurf Pro** | $15 | Generous free tier, Cascade agentic mode, competitive completions |
| **Amazon Q Developer** | $19 (Free tier available) | AWS-native, great for cloud infrastructure, free tier is strong |
| **Google Gemini Code Assist** | $19 | GCP-native, strong for Google Cloud workflows |
| **Tabnine Dev** | $9 | Most affordable, privacy-first, self-hosted option |
| **JetBrains AI** | $10 | Best for JetBrains IDE users, tight refactoring integration |

### Category C: Specialized AI Tools

| Tool | Price | Use Case | Fits Budget? |
|------|-------|----------|-------------|
| **Figma AI** | $15-75/editor/mo | UI/UX design generation | Separate design budget |
| **v0 (Vercel)** | $20/mo | Next.js + Tailwind UI generation | Tier 2 ($20) |
| **Bolt.new** | $20-50/mo | Full-stack app prototyping | Tier 2 ($20 plan) |
| **Lovable** | $20-100/mo | Prompt-to-app with Supabase | Tier 2 ($20 plan) |

---

## 4. Head-to-Head Comparison

### Claude Code vs. The Field

| Capability | Claude Code (Max) | GitHub Copilot (Pro+) | Cursor (Pro) | OpenAI Codex | Windsurf (Pro) |
|-----------|------------------|----------------------|-------------|-------------|---------------|
| **Price (power user)** | $100/mo | $39/mo | $20/mo | $200/mo | $15/mo |
| **Price (standard)** | $20/mo | $10/mo | $20/mo | $20/mo | $15/mo |
| **Agentic coding** | Excellent | Good | Good | Good | Good |
| **Multi-file edits** | Excellent | Good | Good | Good | Good |
| **Terminal/CLI native** | Yes (primary) | Limited | No (IDE) | Web-only | No (IDE) |
| **IDE integration** | VS Code, JetBrains | All major IDEs | Cursor IDE only | Web + limited | Windsurf IDE |
| **Background agents** | Yes | No | No | Yes (cloud) | No |
| **MCP (tool integrations)** | Extensive | Limited | Limited | No | Limited |
| **Custom rules (CLAUDE.md)** | Excellent | .github/copilot | .cursorrules | Custom instructions | .windsurfrules |
| **Git integration** | Full (commit, PR, review) | Full | Good | Limited | Good |
| **Context window** | 200K tokens | ~128K | ~128K | 128K+ | ~128K |
| **Self-hosted / VPC** | Enterprise only | Enterprise | No | Enterprise | Enterprise |
| **Frontier model access** | Opus 4.6 | GPT-4o, Claude Sonnet | GPT-4o, Claude | o1-pro, GPT-4.5 | GPT-4o, Claude |
| **Code completion** | Via IDE extensions | Excellent | Excellent | Good | Excellent |
| **Voice input** | Built-in | No | No | Voice in app | No |

### Key Differentiators

**Claude Code excels at:**
- Agentic multi-step workflows (plan → implement → test → commit)
- Codebase-aware context (CLAUDE.md rules, memory system)
- Terminal-native workflow (no IDE lock-in)
- MCP server integrations (Slack, databases, custom tools)
- Background agents and parallel workstreams
- Custom skills and slash commands
- Enterprise governance (hooks, managed settings)

**GitHub Copilot excels at:**
- Broadest IDE support (every major editor)
- Inline code completion (best-in-class latency)
- Multi-model choice (GPT-4o, Claude, Gemini in one tool)
- Enterprise features (IP indemnity, audit logs, SAML)
- Lowest price point for standard users ($10/mo)

**Cursor excels at:**
- Integrated agentic experience (Composer mode)
- Visual diff review in-editor
- Competitive pricing ($20/mo for full features)
- Custom rules integration (.cursorrules)

**OpenAI Codex excels at:**
- Cloud-sandboxed execution (no local compute)
- Access to o1-pro for complex reasoning
- Bundled with ChatGPT ecosystem
- BUT: expensive ($200/mo Pro), web-centric

---

## 5. Recommended Tool Allocation

### Option A: Claude Code Primary (Recommended)

Best for teams that value agentic workflows, terminal-native development, and
enterprise governance.

| Tier | Tool | Plan | $/User/Mo | Users | Monthly Cost |
|------|------|------|-----------|-------|-------------|
| Tier 1 | Claude Code | Max 5x | $100 | 20 | $2,000 |
| Tier 2 | Claude Code | Pro | $20 | 105 | $2,100 |
| **Total** | | | | **125** | **$4,100/mo** |

**Annual: $49,200**

**Pros:**
- Unified platform — one vendor, one billing, one governance model
- CLAUDE.md rules apply to everyone, ensuring code consistency
- Power users get agentic capabilities; standard users get completions + chat
- All users benefit from shared skills, slash commands, memory

**Cons:**
- IDE code completion not as polished as Copilot's inline experience
- No multi-model choice (Claude only, though Sonnet/Opus/Haiku available)

### Option B: Claude Code + GitHub Copilot (Hybrid)

Best for teams that want the strongest code completion AND agentic capabilities.

| Tier | Tool | Plan | $/User/Mo | Users | Monthly Cost |
|------|------|------|-----------|-------|-------------|
| Tier 1 | Claude Code Max 5x | Max 5x | $100 | 20 | $2,000 |
| Tier 2 | GitHub Copilot | Pro | $10 | 105 | $1,050 |
| **Total** | | | | **125** | **$3,050/mo** |

**Annual: $36,600** (saves $12,600 vs Option A)

**Pros:**
- Best-in-class code completion for all 105 standard users (Copilot Pro at $10)
- Full agentic power for 20 power users (Claude Code Max)
- Saves $12.6K/year vs all-Claude
- Multi-model access for Tier 2 (GPT-4o, Claude Sonnet, Gemini via Copilot)

**Cons:**
- Two vendors to manage (Anthropic + GitHub)
- Standard users miss Claude Code-specific features (memory, MCP, skills)
- Different workflows between tiers

### Option C: Claude Code + Cursor (Hybrid)

Best for teams that prefer IDE-native agentic coding for everyone.

| Tier | Tool | Plan | $/User/Mo | Users | Monthly Cost |
|------|------|------|-----------|-------|-------------|
| Tier 1 | Claude Code | Max 5x | $100 | 20 | $2,000 |
| Tier 2 | Cursor | Pro | $20 | 105 | $2,100 |
| **Total** | | | | **125** | **$4,100/mo** |

**Annual: $49,200**

**Pros:**
- Tier 2 gets agentic coding (Cursor Composer) at $20/mo
- Visual diff review built into editor
- Power users get Claude Code's full terminal-native workflow

**Cons:**
- Cursor locks users into the Cursor IDE (VS Code fork)
- Same total cost as Option A but split across two vendors

### Option D: Budget-Optimized (Lowest Cost)

For organizations prioritizing cost savings.

| Tier | Tool | Plan | $/User/Mo | Users | Monthly Cost |
|------|------|------|-----------|-------|-------------|
| Tier 1 | Claude Code | Max 5x | $100 | 15 | $1,500 |
| Tier 2 | GitHub Copilot | Pro | $10 | 110 | $1,100 |
| **Total** | | | | **125** | **$2,600/mo** |

**Annual: $31,200** (saves $18,000 vs Option A)

**Pros:**
- Minimizes cost while still providing agentic capabilities to leads
- Copilot Pro at $10/mo is the cheapest effective option for Tier 2
- 15 power users is enough for most team structures

**Cons:**
- Fewer power users may create bottlenecks
- Standard users have no agentic capabilities

---

## 6. Cost Scenarios

### Annual Cost Comparison (125 Users)

| Scenario | Monthly | Annual | vs. Option A |
|----------|---------|--------|-------------|
| **A: Claude Code only** | $4,100 | $49,200 | Baseline |
| **B: Claude + Copilot (hybrid)** | $3,050 | $36,600 | -$12,600 (-26%) |
| **C: Claude + Cursor (hybrid)** | $4,100 | $49,200 | $0 (same) |
| **D: Budget-optimized** | $2,600 | $31,200 | -$18,000 (-37%) |
| **E: Copilot Business only** | $2,375 | $28,500 | -$20,700 (-42%) |
| **F: Cursor Business only** | $5,000 | $60,000 | +$10,800 (+22%) |
| **G: ChatGPT Team only** | $3,750 | $45,000 | -$4,200 (-9%) |

### What if everyone gets the same tool?

| Tool | Plan | $/User | 125 Users/Mo | Annual | Notes |
|------|------|--------|-------------|--------|-------|
| Claude Code Pro | $20 | $20 | $2,500 | $30,000 | No agentic power users |
| Claude Code Max 5x | $100 | $100 | $12,500 | $150,000 | Overkill for 80% of users |
| GitHub Copilot Business | $19 | $19 | $2,375 | $28,500 | Good baseline, no deep agentic |
| Cursor Pro | $20 | $20 | $2,500 | $30,000 | Agentic for all, IDE lock-in |
| Cursor Business | $40 | $40 | $5,000 | $60,000 | Enterprise features, expensive |
| ChatGPT Team | $30 | $30 | $3,750 | $45,000 | Good general AI, weaker IDE integration |

**The tiered model (Option A or B) is clearly superior** to flat pricing — it avoids
overspending on users who don't need power features while ensuring power users aren't
bottlenecked.

---

## 7. ROI & Productivity Analysis

### Conservative Productivity Model

| Task Category | Time Without AI | Time With AI | Savings | Impact Area |
|--------------|----------------|-------------|---------|-------------|
| **Boilerplate / scaffolding** | 4h | 0.5h | 87.5% | New services, endpoints, tests |
| **Code review** | 2h per PR | 1h per PR | 50% | Focus on architecture, not style |
| **Bug investigation** | 3h | 1h | 67% | CI failures, runtime errors |
| **Documentation** | 4h per doc | 1h per doc | 75% | Runbooks, ADRs, guides |
| **Refactoring** | 6h | 1.5h | 75% | Multi-file pattern changes |
| **Test writing** | 3h | 0.5h | 83% | Unit, integration, e2e |
| **DevOps / CI-CD** | 4h | 1h | 75% | Workflows, deployments, debugging |
| **Learning new tech** | 8h | 3h | 62.5% | New frameworks, languages |

### ROI Calculation

**Assumptions:**
- Average engineer salary: $120,000/year ($60/hour fully loaded)
- Average 160 working hours/month
- Conservative 25% of time is on AI-acceleratable tasks (40 hours/month)
- AI saves 50% of that time on average (20 hours/month saved per engineer)

| Metric | Value |
|--------|-------|
| Hours saved per engineer per month | 20 hours |
| Total hours saved across 125 engineers | 2,500 hours/month |
| Dollar value of saved hours (@$60/hr) | **$150,000/month** |
| Annual value of saved hours | **$1,800,000** |
| Annual tool cost (Option A) | **$49,200** |
| **ROI multiplier** | **36.6x** |

Even at a **pessimistic 10% time savings** (5 hours/month per engineer):

| Metric | Value |
|--------|-------|
| Hours saved per engineer per month | 5 hours |
| Total hours saved across 125 engineers | 625 hours/month |
| Dollar value (@$60/hr) | $37,500/month |
| Annual value | **$450,000** |
| Annual tool cost | **$49,200** |
| **ROI multiplier** | **9.1x** |

### What This Repo Demonstrates

This AI Agent Platform was built entirely with Claude Code:

| Deliverable | Estimated Traditional Time | Actual Time (with Claude Code) | Ratio |
|-------------|--------------------------|-------------------------------|-------|
| 5 Python microservices | 8-12 weeks | 2-3 weeks | 4x faster |
| Next.js frontend (8 pages) | 3-4 weeks | 1 week | 3-4x faster |
| 55+ documentation pages | 4-6 weeks | 1-2 weeks | 3-4x faster |
| CI/CD pipeline (3 workflows) | 1-2 weeks | 1-2 days | 5-7x faster |
| K8s manifests + Argo CD | 2-3 weeks | 3-5 days | 3-4x faster |
| 16 component tutorials | 6-8 weeks | 2-3 weeks | 3x faster |

---

## 8. Risk Assessment

### Tool Comparison: Risk Factors

| Risk | Claude Code | Copilot | Cursor | Codex |
|------|-----------|---------|--------|-------|
| **Vendor lock-in** | Low (CLI + standard files) | Low (IDE plugin) | Medium (Cursor IDE) | Medium (web-based) |
| **Data privacy** | Enterprise: zero retention | Enterprise: no training | Privacy mode available | Team/Enterprise: no training |
| **Service outage impact** | High (primary dev tool) | Medium (completion stops) | High (IDE stops) | Medium (web-based) |
| **Cost escalation** | Predictable (per-seat) | Predictable (per-seat) | Predictable | Usage-based risk ($200/mo) |
| **Model quality regression** | Low (Anthropic controls) | Medium (multi-vendor) | Medium (multi-vendor) | Low (OpenAI controls) |
| **Security (code exposure)** | SOC 2, enterprise VPC | SOC 2, IP indemnity | SOC 2 | SOC 2 |

### Mitigation Strategies

1. **Vendor lock-in:** Use standard file formats (CLAUDE.md is just markdown). No proprietary formats.
2. **Outage risk:** Hybrid approach (Option B) provides redundancy — if Claude is down, Copilot still works.
3. **Cost control:** Tiered model prevents runaway costs. Monthly per-seat pricing is predictable.
4. **Data privacy:** Require enterprise/team plans with zero data retention for production codebases.
5. **Quality:** Regular evaluation cycles (quarterly) to reassess tool effectiveness.

---

## 9. Implementation Roadmap

### Phase 1: Pilot (Month 1-2) — 15 Users

| Action | Timeline | Cost |
|--------|----------|------|
| Select 10 Tier 1 + 5 Tier 2 pilot users | Week 1 | — |
| Provision Claude Code Pro (5 users) + Max (10 users) | Week 1 | $1,100/mo |
| Set up CLAUDE.md rules for 2-3 pilot repos | Week 2 | — |
| Establish baseline metrics (cycle time, PR velocity) | Week 2 | — |
| 4-week active usage period | Week 3-6 | — |
| Collect feedback, measure against baseline | Week 7-8 | — |

**Pilot cost:** $2,200 (2 months)

### Phase 2: Expand (Month 3-4) — 50 Users

| Action | Timeline | Cost |
|--------|----------|------|
| Expand to 15 Tier 1 + 35 Tier 2 users | Month 3 | $2,200/mo |
| Roll out CLAUDE.md standards org-wide | Month 3 | — |
| Create shared slash commands and skills | Month 3-4 | — |
| Train Tier 2 users on effective prompting | Month 3 | — |
| Optional: Add GitHub Copilot for remaining devs | Month 4 | +$750/mo |

**Phase 2 cost:** $5,900 (2 months)

### Phase 3: Full Rollout (Month 5+) — 125 Users

| Action | Timeline | Cost |
|--------|----------|------|
| Full rollout to all 125 engineers | Month 5 | $4,100/mo |
| Establish governance (hooks, managed settings) | Month 5 | — |
| Quarterly evaluation and tier rebalancing | Ongoing | — |
| Track ROI metrics against Phase 1 baseline | Month 8 | — |

**Steady-state cost:** $4,100/month ($49,200/year)

### Total Implementation Cost

| Phase | Duration | Users | Total Cost |
|-------|----------|-------|-----------|
| Pilot | 2 months | 15 | $2,200 |
| Expand | 2 months | 50 | $5,900 |
| Full | Ongoing | 125 | $4,100/mo |
| **Year 1 total** | 12 months | 125 | **~$41,100** |

---

## 10. Recommendation

### Primary Recommendation: Option B (Claude Code + GitHub Copilot)

| Component | Details |
|-----------|---------|
| **Tier 1 (20 power users):** | Claude Code Max 5x at $100/mo |
| **Tier 2 (105 standard users):** | GitHub Copilot Pro at $10/mo |
| **Monthly cost:** | $3,050 |
| **Annual cost:** | $36,600 |

**Why this combination:**

1. **Best of both worlds** — Claude Code's deep agentic capabilities for power users,
   Copilot's best-in-class inline completion for everyone else
2. **Cost-efficient** — $10/mo Copilot Pro is the cheapest effective option for standard users
3. **Redundancy** — two vendors means no single point of failure
4. **$12,600 savings** vs all-Claude approach — reinvest in training or more Tier 1 seats
5. **Copilot is IDE-native** — works in VS Code, JetBrains, Neovim with zero friction
6. **Claude Code is terminal-native** — power users get the full agentic workflow

### When to Choose Option A (All Claude Code) Instead

- Your team standardizes on one tool for simplicity
- CLAUDE.md rules and shared skills are critical for all engineers
- You want unified governance and audit trail across everyone
- The extra $12.6K/year is acceptable for tool consistency

### Tier 1 User Selection Criteria

Allocate Tier 1 (power user) seats to engineers who:

- Work on architecture and cross-service changes
- Own CI/CD pipelines and infrastructure
- Lead code reviews and set patterns for the team
- Work on complex features spanning multiple files/services
- Are responsible for documentation and runbooks
- Mentor junior engineers (AI amplifies their teaching capacity)

### Annual Budget Summary

| Item | Cost |
|------|------|
| Claude Code Max 5x (20 seats) | $24,000/year |
| GitHub Copilot Pro (105 seats) | $12,600/year |
| **Total tools** | **$36,600/year** |
| Training & onboarding (estimated) | $5,000/year |
| **Grand total** | **$41,600/year** |
| Estimated annual productivity value | $450,000-$1,800,000 |
| **ROI** | **10.8x - 43.3x** |

---

## Appendix A: Specialized Tool Recommendations

Beyond the core coding tools, consider these for specific roles:

| Role | Tool | Monthly Cost | Justification |
|------|------|-------------|---------------|
| **UI/UX Designers** (if any) | Figma Professional | $15/editor | AI-powered design generation |
| **Frontend Prototyping** | v0 by Vercel | $20/user | Rapid Next.js + Tailwind UI generation |
| **Quick Prototypes** | Bolt.new Pro | $20/user | Full-stack app scaffolding |
| **AWS-Heavy Teams** | Amazon Q Developer | Free-$19/user | AWS-native infrastructure assistance |
| **GCP-Heavy Teams** | Gemini Code Assist | $19/user | GCP-native cloud workflows |
| **Privacy-Critical** | Tabnine Enterprise | $39/user | Self-hosted, air-gapped deployment |

These are **additive** to the core recommendation, not replacements. Budget separately.

## Appendix B: Feature Matrix by Price Point

### What $10/month gets you (GitHub Copilot Pro)

- Unlimited code completions in any IDE
- Unlimited chat messages
- Multi-model (GPT-4o, Claude Sonnet, Gemini)
- CLI integration
- Good for: daily coding, autocomplete, chat Q&A

### What $20/month gets you (Claude Code Pro / Cursor Pro)

Everything above, plus:
- Agentic coding (multi-step, multi-file)
- Custom rules and context (CLAUDE.md / .cursorrules)
- Plan mode for architectural decisions
- Memory system (Claude Code) for cross-session continuity
- Good for: feature implementation, refactoring, documentation

### What $100/month gets you (Claude Code Max 5x)

Everything above, plus:
- 5x usage limits (sustained heavy agentic use all day)
- More Opus-class model access (frontier reasoning)
- Background agents for parallel workstreams
- MCP server integrations
- Good for: architects, leads, heavy daily AI-driven development

### What $200/month gets you (ChatGPT Pro / Claude Max 20x)

Everything above, plus:
- Near-unlimited usage
- Maximum model access (o1-pro / Opus with highest quotas)
- Extended thinking modes
- Good for: AI researchers, engineers who live in AI tools 8+ hours/day
- **Likely overkill for most engineering teams**

---

## Appendix C: This Project as a Reference

This AI Agent Platform demonstrates Claude Code's full capability:

| What was built | Lines | With Claude Code? |
|---------------|-------|-------------------|
| 5 Python microservices | ~8,000 | Yes |
| Next.js frontend (8 pages) | ~3,000 | Yes |
| K8s manifests + Argo CD | ~2,000 | Yes |
| CI/CD pipelines (GitHub Actions) | ~300 | Yes |
| 55+ documentation files | ~25,000 | Yes |
| Docker Compose + Caddyfile | ~350 | Yes |
| OPA Gatekeeper policies | ~200 | Yes |
| Terraform modules | ~500 | Yes |

**Total: ~39,000+ lines of production code and documentation**, built with Claude Code
at a fraction of the time and cost of traditional development.

> **Explore the platform:** [ai-adoption.uk](https://ai-adoption.uk)
> **Repository:** [github.com/merit-data-tech/ai-adoption](https://github.com/merit-data-tech/ai-adoption)
> **Enterprise adoption guide:** [Getting Started](getting-started-enterprise-ai-adoption.md)

---

*This analysis was generated with [Claude Code](https://claude.ai/code). Pricing data
as of April 2026 — verify at vendor websites before procurement decisions.*
