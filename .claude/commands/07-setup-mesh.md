# Phase 7: Service Mesh -- Zero-Trust Networking with Istio Ambient + Contour

## What You Will Learn
- Istio ambient mesh (no sidecars) for mTLS and traffic management
- Contour/Envoy for L7 ingress with HTTPProxy CRDs
- AuthorizationPolicies for service-to-service access control
- Canary deployments via Istio VirtualService traffic splitting
- Why ambient mesh over sidecar injection

## Prerequisites
- Phase 6 complete (All services instrumented with OTEL)
- Kubernetes cluster (Kind/k3d for local, GKE/EKS for cloud)
- Understanding of TLS and network policies

## Background: Why Istio Ambient Over Sidecar?
Traditional Istio injects an Envoy sidecar into every pod. For 6 services x 2 replicas,
that's 12 extra containers consuming ~128MB each = 1.5GB of overhead. Istio ambient mode
(GA since Istio 1.22) uses a per-node ztunnel DaemonSet for L4 mTLS and optional
waypoint proxies for L7 features. This cuts resource overhead by 60-80% while providing
identical zero-trust networking guarantees.

See: docs/architecture/adr/005-istio-ambient-mesh.md

## Step-by-Step Instructions

### Step 1: Install Istio in Ambient Mode
Create `infra/helm/values/istio.yaml` and install:
```bash
istioctl install --set profile=ambient
kubectl label namespace agent-platform istio.io/dataplane-mode=ambient
```

### Step 2: Install Contour Ingress Controller
Create `infra/helm/values/contour.yaml`:
```yaml
envoy:
  service:
    type: LoadBalancer
contour:
  replicas: 2
```

**Why Contour?** Same Envoy data plane as Istio = consistent proxy behavior and metrics.
HTTPProxy CRDs are more expressive than standard Ingress (weighted routing, header matching).

### Step 3: Create HTTPProxy Ingress Routes
```yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: agent-platform-ingress
spec:
  virtualhost:
    fqdn: agent-platform.local
    tls:
      secretName: agent-platform-tls
  routes:
    - conditions:
        - prefix: /graphql
      services:
        - name: gateway
          port: 8000
    - conditions:
        - prefix: /
      services:
        - name: frontend
          port: 3000
```

### Step 4: Enable Strict mTLS
```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict-mtls
  namespace: agent-platform
spec:
  mtls:
    mode: STRICT
```

All service-to-service traffic is now encrypted with mutual TLS. No code changes needed.

### Step 5: Create AuthorizationPolicies
```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-gateway-to-services
spec:
  selector:
    matchLabels:
      app: agent-engine
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/agent-platform/sa/gateway"]
      to:
        - operation:
            methods: ["POST", "GET"]
```

Create similar policies for each service pair. Default deny + explicit allow = zero-trust.

### Step 6: Canary Deployment Setup
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: gateway-canary
spec:
  hosts:
    - gateway
  http:
    - route:
        - destination:
            host: gateway
            subset: stable
          weight: 90
        - destination:
            host: gateway
            subset: canary
          weight: 10
```

This routes 10% of traffic to the canary version for safe rollouts.

## Verification
```bash
# Verify mTLS
istioctl proxy-config secret deploy/gateway | grep ACTIVE  # Should show cert

# Test authorization
kubectl exec deploy/frontend -- curl http://agent-engine:8003/healthz
# Should be DENIED (frontend can't talk directly to agent-engine)

kubectl exec deploy/gateway -- curl http://agent-engine:8003/healthz
# Should be ALLOWED (gateway -> agent-engine is permitted)

# Check Kiali service graph (if installed)
istioctl dashboard kiali
```

## Key Concepts Taught
1. **Ambient mesh** -- Per-node ztunnel vs per-pod sidecar
2. **mTLS everywhere** -- Encrypted service-to-service without code changes
3. **AuthorizationPolicy** -- Zero-trust: deny all, allow explicitly
4. **HTTPProxy** -- Expressive ingress routing with Envoy
5. **Canary deployments** -- Progressive traffic shifting for safe rollouts

## What's Next
Phase 8 (`/08-setup-gitops`) implements Argo CD for GitOps and Tekton for CI/CD.
Git becomes the single source of truth for all deployments.
