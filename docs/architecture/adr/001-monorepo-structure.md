# ADR-001: Monorepo Structure with Kustomize for Application Manifests

## Status: Accepted

## Date: 2026-04-04

## Context

The KIAA AI Adoption platform comprises 5 backend services (gateway, agent-orchestrator,
inference-router, cost-tracker, auth), 1 frontend SPA, shared libraries (common models,
utilities, SDK clients), infrastructure-as-code (Terraform, Kubernetes manifests), and
a comprehensive test suite (unit, integration, e2e). We needed a repository strategy that
supports rapid iteration across tightly coupled services while maintaining clear ownership
boundaries and reproducible deployments.

Teams frequently make changes that span multiple services simultaneously -- for example,
adding a new field to the agent execution model touches the shared library, the
agent-orchestrator service, the GraphQL gateway, and the frontend. These atomic
cross-service changes are a primary workflow, not an edge case.

## Decision

We adopt a monorepo layout using a single Git repository with the following top-level
structure: `services/`, `frontend/`, `libs/`, `infra/`, `tests/`, and `docs/`. Kubernetes
application manifests use Kustomize with base/overlay patterns (dev, staging, prod).
Helm is reserved exclusively for third-party dependencies (PostgreSQL, Redis, Prometheus)
installed via umbrella charts in `infra/helm/`.

## Consequences

**Positive:**
- Atomic commits across service boundaries eliminate version-skew issues during
  cross-cutting changes and remove the need for coordinated multi-repo releases.
- Shared libraries (`libs/common`, `libs/sdk`) are consumed as path dependencies,
  enabling immediate feedback without publish-and-update cycles.
- A single CI pipeline (GitHub Actions) runs affected-service detection via path filters,
  keeping build times proportional to the change scope rather than the full repo.
- Kustomize overlays produce transparent, diffable YAML -- reviewers see exactly what
  changes in each environment without reverse-engineering Helm template logic.
- `kustomize build` output is plain Kubernetes YAML, simplifying debugging with
  `kubectl diff` and GitOps reconciliation via ArgoCD.

**Negative:**
- Repository size will grow over time; we mitigate with shallow clones in CI and
  Git LFS for large binary assets (model weights, test fixtures).
- All teams share a single trunk; branch protection rules and CODEOWNERS files are
  critical to prevent unintended cross-team interference.
- Kustomize's patch-based approach can become verbose for highly parameterized
  deployments, though strategic use of components and replacements alleviates this.

## Alternatives Considered

- **Polyrepo (one repo per service):** Rejected because cross-service changes would
  require synchronized PRs across 5+ repos, increasing coordination cost and risk of
  partial deployments. Shared library versioning would add significant overhead.
- **Full Helm for all manifests (including our services):** Rejected because Helm's
  Go templating obscures the final rendered manifests, making PR reviews harder for
  application-level changes. Helm excels for packaging reusable third-party charts
  but adds unnecessary indirection for manifests we fully control.
