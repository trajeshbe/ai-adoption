# Network Topology

## Overview

The platform uses a layered network architecture: Contour/Envoy handles external ingress, Istio ambient mesh secures internal service-to-service traffic, and Kubernetes NetworkPolicies provide defense-in-depth isolation for sensitive workloads.

```
                         Internet
                            |
                            v
               +------------------------+
               |  Contour / Envoy       |
               |  Ingress Controller    |
               |  (TLS termination,     |
               |   path-based routing)  |
               +--------+--+--+--------+
                        |  |  |
           /graphql ----+  |  +---- /static
                           |
                      /ws (upgrade)
                           |
    ===========================================================
    |              Istio Ambient Mesh                          |
    |                                                          |
    |   +----------+    +---------+    +---------+             |
    |   | ztunnel  |    | ztunnel |    | ztunnel |             |
    |   | (node 1) |    | (node 2)|    | (node 3)|             |
    |   +-----+----+    +----+----+    +----+----+             |
    |         |              |              |                   |
    |   All pod-to-pod traffic is intercepted by the           |
    |   per-node ztunnel proxy. mTLS is automatic.             |
    |                                                          |
    ===========================================================
                           |
    +----------------------+-------------------------+
    |                      |                         |
    v                      v                         v
 +----------+      +--------------+         +----------------+
 | Namespace|      | Namespace    |         | Namespace      |
 | default  |      | ai-agents    |         | llm-runtime    |
 |          |      |              |         |                |
 | Frontend |      | Agent Engine |         | vLLM           |
 | API GW   |      | Prefect      |         | llama.cpp      |
 | Cache    |      |              |         |                |
 +----------+      +--------------+         +----------------+
```

## Ingress Layer: Contour / Envoy

| Resource | Purpose |
|---|---|
| `HTTPProxy` (Contour CRD) | Defines external routes with TLS, rate limiting, and retry policies |
| Envoy listeners | Accept connections on ports 80 (redirect) and 443 (TLS) |
| Health checks | Envoy active health checks against `/healthz` on each upstream |

## Service Mesh: Istio Ambient

Istio ambient mode eliminates sidecar proxies. Instead, a **ztunnel** DaemonSet runs one proxy per node that transparently intercepts all pod traffic.

| Feature | Implementation |
|---|---|
| mTLS | Automatic between all mesh workloads via ztunnel HBONE tunnels |
| Identity | SPIFFE IDs issued per service account |
| L4 AuthorizationPolicy | Enforced at the ztunnel level |
| L7 AuthorizationPolicy | Requires optional waypoint proxy per namespace |

## Authorization Policies

```yaml
# Allow frontend -> API gateway only
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-frontend-to-api
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-gateway
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/default/sa/frontend"]

# Allow agent engine -> LLM runtime only
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-agent-to-llm
  namespace: llm-runtime
spec:
  selector:
    matchLabels:
      app: vllm
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/ai-agents/sa/agent-engine"]
```

## NetworkPolicy: LLM Runtime Isolation

The `llm-runtime` namespace has strict NetworkPolicies that deny all traffic except from the `ai-agents` namespace. This prevents unauthorized access to GPU resources.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: llm-runtime-isolation
  namespace: llm-runtime
spec:
  podSelector: {}          # Apply to all pods in namespace
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ai-agents
      ports:
        - protocol: TCP
          port: 8080       # vLLM
        - protocol: TCP
          port: 8081       # llama.cpp
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53          # DNS only
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443         # Model downloads (HuggingFace)
```

## Summary

| Layer | Technology | Scope |
|---|---|---|
| External ingress | Contour + Envoy | Internet to cluster boundary |
| Service mesh | Istio ambient (ztunnel) | All intra-cluster pod traffic |
| Authorization | Istio AuthorizationPolicy | Per-service access rules |
| Network isolation | Kubernetes NetworkPolicy | Namespace-level firewall for LLM runtime |
