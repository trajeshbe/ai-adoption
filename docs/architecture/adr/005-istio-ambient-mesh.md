# ADR-005: Istio Ambient Mesh over Sidecar Mode

## Status: Accepted

## Date: 2026-04-04

## Context

The KIAA platform runs 15+ microservices and workloads on Kubernetes, requiring mutual
TLS (mTLS) for zero-trust inter-service communication, fine-grained authorization
policies (e.g., only the inference-router may call vLLM endpoints), traffic management
(canary deployments, traffic mirroring for shadow testing), and L7 observability
(distributed tracing, request-level metrics). The traditional Istio sidecar model injects
an Envoy proxy container into every pod, consuming 100-150 MB of memory and 0.1 CPU per
pod -- significant overhead when multiplied across 50+ pod replicas.

GPU inference pods are particularly sensitive to resource overhead; sidecar proxies on
these pods waste expensive GPU-node resources on proxy memory allocation.

## Decision

We deploy Istio in ambient mode (available as GA since Istio 1.22). Ambient mode replaces
per-pod sidecar proxies with two shared infrastructure layers: ztunnel (a per-node Layer 4
proxy handling mTLS and basic authorization) and optional waypoint proxies (per-namespace
or per-service Layer 7 proxies for advanced traffic management). Namespaces are enrolled
by labeling them with `istio.io/dataplane-mode: ambient`.

Waypoint proxies are deployed only for namespaces requiring L7 features (traffic splitting,
header-based routing, request-level authorization policies). The inference namespace
uses ztunnel-only for minimal overhead on GPU nodes.

## Consequences

**Positive:**
- Resource savings of 60-80% compared to sidecar mode. Ztunnel runs as a DaemonSet
  with a single instance per node (~50 MB) rather than per-pod Envoy instances.
  Across 50 pods on 10 nodes, this reduces mesh overhead from ~7.5 GB to ~500 MB.
- No sidecar injection eliminates pod startup ordering issues -- application containers
  no longer race with Envoy readiness, removing a common source of intermittent boot
  failures.
- mTLS is enforced transparently at the node level by ztunnel using HBONE (HTTP-based
  overlay network), providing the same SPIFFE identity and certificate rotation as
  sidecar mode without application awareness.
- Waypoint proxies can be scaled independently and upgraded without restarting
  application pods, decoupling mesh lifecycle from application lifecycle.
- GPU inference pods (vLLM, llama.cpp) benefit most: zero per-pod proxy overhead
  means all GPU-node memory is available for model weights and KV-cache.

**Negative:**
- Ambient mode is newer than sidecar mode; while GA, the ecosystem of tutorials,
  debugging guides, and community experience is smaller. Troubleshooting L4/L7
  split issues requires understanding the ztunnel/waypoint architecture.
- Some Envoy filters available in sidecar mode may not yet be supported in waypoint
  proxies. We must validate that our required AuthorizationPolicy features work in
  ambient mode during staging rollout.
- Per-node ztunnel means a node-level failure affects all pods on that node (blast
  radius is larger than per-pod sidecars), though Kubernetes node redundancy mitigates
  this risk.
- Waypoint proxy placement decisions (per-namespace vs per-service) require upfront
  planning and can affect authorization policy granularity.

## Alternatives Considered

- **Istio sidecar mode:** The proven default, but resource overhead is prohibitive at
  our scale, especially on GPU nodes. Sidecar lifecycle coupling with application pods
  complicates rolling updates and debugging.
- **Linkerd:** Lighter weight than Istio sidecars, with a simpler operational model.
  However, Linkerd lacks the traffic management sophistication we need (weighted
  routing, fault injection for chaos testing) and its future is uncertain after
  the CNCF graduation process changes.
- **Cilium service mesh:** eBPF-based approach with excellent performance, but L7
  policy capabilities are less mature than Istio's, and the team has deeper Envoy
  and Istio operational experience.
