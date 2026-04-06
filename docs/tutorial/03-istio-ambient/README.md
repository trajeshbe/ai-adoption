# Tutorial 03: Istio Ambient Service Mesh

> **Objective:** Learn how Istio ambient mode provides mTLS, traffic management, and observability without sidecar proxies.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [Architecture](#3-architecture)
4. [Installation & Setup](#4-installation--setup)
5. [Exercises](#5-exercises)
6. [Observability](#6-observability)
7. [How It's Used in Our Project](#7-how-its-used-in-our-project)
8. [Troubleshooting](#8-troubleshooting)
9. [Best Practices & Further Reading](#9-best-practices--further-reading)

---

## 1. Introduction

### What is a Service Mesh?

A **service mesh** is an infrastructure layer that handles service-to-service communication. Instead of each service implementing its own security, retries, and observability, the mesh handles it transparently.

```
Without mesh:   Service A ──[HTTP]──> Service B   (no encryption, no retries)
With mesh:      Service A ──[mTLS]──> Service B   (encrypted, retried, traced, authorized)
```

### What is Istio?

**Istio** is the most popular service mesh for Kubernetes. It provides:

- **mTLS** — Automatic encryption between all services
- **Traffic management** — Canary deployments, fault injection, retries
- **Observability** — Distributed tracing, metrics, access logs
- **Security** — Authorization policies (who can call what)

### Sidecar Mode vs Ambient Mode

**Traditional sidecar mode:** Injects an Envoy proxy container into every pod.

```
Pod: [Your App Container] + [Envoy Sidecar]   ← doubles resource usage!
```

**Ambient mode (new):** Uses shared per-node proxies instead of per-pod sidecars.

```
Node: [ztunnel] handles L4 (mTLS) for ALL pods on this node
      [waypoint proxy] handles L7 (HTTP routing) per namespace/service (optional)
```

| Feature | Sidecar Mode | Ambient Mode |
|---------|-------------|--------------|
| Resource overhead | High (1 proxy per pod) | Low (1 ztunnel per node) |
| Startup latency | Slower (sidecar init) | Normal (no injection) |
| Complexity | Pod mutation, ordering issues | Simple enrollment |
| L7 features | Always on | Optional (waypoint) |
| mTLS | Per-pod Envoy | Per-node ztunnel |

---

## 2. Core Concepts

### 2.1 mTLS (Mutual TLS)

Normal TLS: Client verifies server identity (HTTPS websites).
Mutual TLS: Both sides verify each other's identity.

```
Service A ←─[mTLS]─→ Service B
  "I am A"              "I am B"
  "Prove it"            "Prove it"
  [certificate]         [certificate]
  "Verified!"           "Verified!"
  ← encrypted communication →
```

Istio manages certificates automatically — no manual cert management.

### 2.2 Traffic Management

Control how traffic flows between services:

- **Traffic shifting** — Send 90% to v1, 10% to v2 (canary)
- **Fault injection** — Add artificial delays or errors (chaos testing)
- **Retries** — Automatically retry failed requests
- **Timeouts** — Set per-route timeouts
- **Circuit breaking** — Stop sending to overwhelmed services

### 2.3 Authorization Policies

Control who can access what:

```yaml
# Only the frontend can call the API
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-access
spec:
  selector:
    matchLabels:
      app: api-server
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/default/sa/frontend"]
```

### 2.4 L4 vs L7

| Layer | What It Sees | ztunnel | waypoint |
|-------|-------------|---------|----------|
| **L4** (Transport) | TCP connections, IP addresses | Yes | — |
| **L7** (Application) | HTTP headers, paths, methods | — | Yes |

- **ztunnel** handles L4: mTLS, TCP metrics, basic authorization
- **waypoint proxy** handles L7: HTTP routing, header-based policies, retries

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Kubernetes Cluster                                       │
│                                                           │
│  Control Plane:                                           │
│  ┌──────────────┐                                         │
│  │   istiod      │  ← Manages certs, config, xDS         │
│  └──────┬───────┘                                         │
│         │ pushes config                                    │
│         ▼                                                  │
│  Data Plane (per node):                                    │
│  ┌──────────────┐                                         │
│  │   ztunnel     │  ← L4 proxy: mTLS for all pods on node │
│  └──────────────┘                                         │
│                                                           │
│  Data Plane (optional, per namespace/service):            │
│  ┌──────────────┐                                         │
│  │   waypoint    │  ← L7 proxy: HTTP routing, policies    │
│  └──────────────┘                                         │
│                                                           │
│  Workloads:                                               │
│  ┌─────┐ ┌─────┐ ┌─────┐                                 │
│  │Pod A│ │Pod B│ │Pod C│  ← No sidecars!                  │
│  └─────┘ └─────┘ └─────┘                                 │
└──────────────────────────────────────────────────────────┘
```

**How a request flows in ambient mode:**

1. Pod A sends request to Pod B
2. ztunnel on Node A intercepts → establishes mTLS tunnel
3. ztunnel on Node B receives → delivers to Pod B
4. If L7 features needed → request goes through waypoint proxy first

---

## 4. Installation & Setup

### Install Istio with Ambient Profile

```bash
# Download istioctl
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.23.0 sh -
export PATH=$PWD/istio-1.23.0/bin:$PATH

# Install with ambient profile
istioctl install --set profile=ambient --skip-confirmation

# Verify installation
istioctl verify-install
kubectl get pods -n istio-system

# You should see:
# - istiod (control plane)
# - ztunnel (DaemonSet — one per node)
# - istio-cni (DaemonSet — network setup)
```

### Enroll a Namespace

```bash
# Label a namespace to include it in the mesh
kubectl label namespace default istio.io/dataplane-mode=ambient

# Verify enrollment
kubectl get namespace default --show-labels | grep istio

# All pods in 'default' namespace now have mTLS automatically!
```

---

## 5. Exercises

### Exercise 1: Install Istio Ambient and Enroll a Namespace

```bash
# 1. Create a test namespace
kubectl create namespace mesh-demo

# 2. Deploy two sample services
cat <<EOF | kubectl apply -n mesh-demo -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sleep
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sleep
  template:
    metadata:
      labels:
        app: sleep
    spec:
      serviceAccountName: sleep
      containers:
        - name: sleep
          image: curlimages/curl
          command: ["/bin/sleep", "infinity"]
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sleep
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: httpbin
spec:
  replicas: 1
  selector:
    matchLabels:
      app: httpbin
  template:
    metadata:
      labels:
        app: httpbin
    spec:
      serviceAccountName: httpbin
      containers:
        - name: httpbin
          image: docker.io/kennethreitz/httpbin
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: httpbin
---
apiVersion: v1
kind: Service
metadata:
  name: httpbin
spec:
  selector:
    app: httpbin
  ports:
    - port: 8000
      targetPort: 80
EOF

# 3. Enroll the namespace in the mesh
kubectl label namespace mesh-demo istio.io/dataplane-mode=ambient

# 4. Verify ztunnel is handling traffic
kubectl exec -n mesh-demo deploy/sleep -- curl -s httpbin.mesh-demo:8000/headers
# Look for "X-Forwarded-Client-Cert" header — proves mTLS is active
```

---

### Exercise 2: Verify mTLS is Working

```bash
# Check if mTLS is active between services
istioctl proxy-config all -n mesh-demo

# Set strict mTLS (reject non-mTLS connections)
cat <<EOF | kubectl apply -n mesh-demo -f -
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: strict-mtls
spec:
  mtls:
    mode: STRICT
EOF

# Try calling from outside the mesh — should fail
kubectl run test-pod --image=curlimages/curl --rm -it --restart=Never -- \
  curl -s httpbin.mesh-demo:8000/status/200
# This should fail because the test-pod is not in the mesh

# Call from inside the mesh — should succeed
kubectl exec -n mesh-demo deploy/sleep -- curl -s httpbin.mesh-demo:8000/status/200
# Returns 200 OK
```

---

### Exercise 3: Traffic Shifting (Canary Deployment)

```bash
# Deploy two versions of a service
cat <<EOF | kubectl apply -n mesh-demo -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo-v1
spec:
  replicas: 1
  selector:
    matchLabels:
      app: echo
      version: v1
  template:
    metadata:
      labels:
        app: echo
        version: v1
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo
          args: ["-text=v1"]
          ports:
            - containerPort: 5678
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echo-v2
spec:
  replicas: 1
  selector:
    matchLabels:
      app: echo
      version: v2
  template:
    metadata:
      labels:
        app: echo
        version: v2
    spec:
      containers:
        - name: echo
          image: hashicorp/http-echo
          args: ["-text=v2"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: echo
spec:
  selector:
    app: echo
  ports:
    - port: 80
      targetPort: 5678
EOF

# Deploy a waypoint for L7 traffic management
istioctl waypoint apply -n mesh-demo --enroll-namespace

# Create traffic split: 90% v1, 10% v2
cat <<EOF | kubectl apply -n mesh-demo -f -
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: echo-canary
spec:
  hosts:
    - echo
  http:
    - route:
        - destination:
            host: echo
            subset: v1
          weight: 90
        - destination:
            host: echo
            subset: v2
          weight: 10
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: echo-versions
spec:
  host: echo
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
EOF

# Test traffic distribution
for i in $(seq 1 20); do
  kubectl exec -n mesh-demo deploy/sleep -- curl -s echo.mesh-demo/
done
# ~18 should return "v1", ~2 should return "v2"
```

---

### Exercise 4: Fault Injection

```yaml
# fault-injection.yaml — Simulate slow LLM responses
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: echo-faults
  namespace: mesh-demo
spec:
  hosts:
    - echo
  http:
    - fault:
        delay:
          percentage:
            value: 50      # 50% of requests
          fixedDelay: 3s   # 3 second delay
        abort:
          percentage:
            value: 10      # 10% of requests
          httpStatus: 503  # Return 503
      route:
        - destination:
            host: echo
```

```bash
kubectl apply -f fault-injection.yaml

# Test — some requests will be slow, some will fail with 503
for i in $(seq 1 10); do
  time kubectl exec -n mesh-demo deploy/sleep -- curl -s -o /dev/null -w "%{http_code}" echo.mesh-demo/
done
```

---

### Exercise 5: Authorization Policies

```yaml
# auth-policy.yaml — Only 'sleep' can access 'httpbin'
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin-access
  namespace: mesh-demo
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/mesh-demo/sa/sleep"]
      to:
        - operation:
            methods: ["GET"]
            paths: ["/headers", "/status/*", "/get"]

---
# Deny all other access by default
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: mesh-demo
spec:
  {}   # Empty spec = deny all
```

```bash
kubectl apply -f auth-policy.yaml

# This should work (sleep → httpbin GET /headers)
kubectl exec -n mesh-demo deploy/sleep -- curl -s httpbin.mesh-demo:8000/headers

# This should be denied (POST not allowed)
kubectl exec -n mesh-demo deploy/sleep -- curl -s -X POST httpbin.mesh-demo:8000/post

# This should be denied (path not allowed)
kubectl exec -n mesh-demo deploy/sleep -- curl -s httpbin.mesh-demo:8000/anything
```

---

### Exercise 6: Request Timeouts and Retries

```yaml
# timeout-retry.yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: echo-resilience
  namespace: mesh-demo
spec:
  hosts:
    - echo
  http:
    - route:
        - destination:
            host: echo
      timeout: 5s              # Fail after 5 seconds
      retries:
        attempts: 3            # Retry up to 3 times
        perTryTimeout: 2s      # Each attempt times out at 2s
        retryOn: "5xx,reset,connect-failure,retriable-4xx"
```

```bash
kubectl apply -f timeout-retry.yaml

# With fault injection active, retries will help recover from transient failures
kubectl exec -n mesh-demo deploy/sleep -- curl -s echo.mesh-demo/
```

---

### Exercise 7: Waypoint Proxy for L7 Features

```bash
# Deploy a waypoint proxy for the namespace
istioctl waypoint apply -n mesh-demo --enroll-namespace

# Verify waypoint is running
kubectl get pods -n mesh-demo -l istio.io/gateway-name

# Deploy a service-specific waypoint
istioctl waypoint apply -n mesh-demo --name httpbin-waypoint

# Attach waypoint to a service
kubectl label service httpbin -n mesh-demo \
  istio.io/use-waypoint=httpbin-waypoint

# Now L7 policies apply specifically to httpbin
# Check waypoint logs
kubectl logs -n mesh-demo -l istio.io/gateway-name=httpbin-waypoint -f
```

---

## 6. Observability

### Kiali Dashboard

```bash
# Install Kiali (service mesh visualization)
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.23/samples/addons/kiali.yaml

# Access dashboard
istioctl dashboard kiali
```

Kiali shows:
- Service topology graph (who calls whom)
- Traffic flow rates and error rates
- mTLS status between services
- Configuration validation

### Prometheus Metrics

Key metrics from Istio:

```promql
# Request rate by service
rate(istio_requests_total{destination_service_namespace="mesh-demo"}[5m])

# P99 latency
histogram_quantile(0.99, rate(istio_request_duration_milliseconds_bucket[5m]))

# Error rate
rate(istio_requests_total{response_code=~"5.."}[5m]) / rate(istio_requests_total[5m])
```

### Distributed Tracing

```bash
# Install Jaeger for tracing
kubectl apply -f https://raw.githubusercontent.com/istio/istio/release-1.23/samples/addons/jaeger.yaml

istioctl dashboard jaeger
```

---

## 7. How It's Used in Our Project

In the AI platform, Istio ambient provides:

- **mTLS everywhere** — All service-to-service communication is encrypted
- **Traffic management** — Canary deployments for new model versions
- **Authorization** — Only the agent engine can call vLLM/llama.cpp
- **Fault injection** — Testing resilience of the circuit breaker
- **Observability** — Distributed traces across the entire request path
- **No sidecar overhead** — Ambient mode saves resources on GPU nodes (critical for vLLM)

---

## 8. Troubleshooting

```bash
# Check mesh status
istioctl analyze -n mesh-demo

# Verify a pod is in the mesh
istioctl ztunnel-config workloads

# Debug ztunnel
kubectl logs -n istio-system -l app=ztunnel --tail=100

# Check mTLS status
istioctl authn tls-check <pod-name> -n mesh-demo

# Verify waypoint routing
istioctl proxy-config routes deploy/waypoint -n mesh-demo
```

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| mTLS not working | Namespace not enrolled | `kubectl label ns <ns> istio.io/dataplane-mode=ambient` |
| L7 policies not applying | No waypoint deployed | `istioctl waypoint apply -n <ns>` |
| Connection refused | AuthorizationPolicy too strict | Check `istioctl analyze` |
| High latency | Waypoint bottleneck | Scale waypoint replicas |

---

## 9. Best Practices & Further Reading

### Best Practices

1. **Start with ambient mode** for new deployments — simpler, less overhead
2. **Use strict mTLS** — reject plaintext connections
3. **Deploy waypoints only when needed** — L7 features add latency
4. **Test fault injection** before production to validate resilience
5. **Use authorization policies** — default deny, explicit allow
6. **Monitor with Kiali** — catch misconfigurations early

### Further Reading

- [Istio Documentation](https://istio.io/latest/docs/)
- [Istio Ambient Mode Guide](https://istio.io/latest/docs/ambient/)
- [Istio by Example](https://istiobyexample.dev/)
- [Envoy Proxy Docs](https://www.envoyproxy.io/docs)
