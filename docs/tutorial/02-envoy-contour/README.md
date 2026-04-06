# Tutorial 02: Envoy Proxy + Contour Ingress Controller

> **Objective:** Understand how external traffic reaches your services inside Kubernetes using Envoy and Contour.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [How Envoy Works](#3-how-envoy-works)
4. [Contour as Envoy Manager](#4-contour-as-envoy-manager)
5. [Installation & Setup](#5-installation--setup)
6. [Exercises](#6-exercises)
7. [Monitoring & Debugging](#7-monitoring--debugging)
8. [How It's Used in Our Project](#8-how-its-used-in-our-project)
9. [Best Practices](#9-best-practices)
10. [Further Reading](#10-further-reading)

---

## 1. Introduction

### What is an Ingress Controller?

When you deploy services in Kubernetes, they're only accessible inside the cluster. An **ingress controller** is the front door — it receives traffic from the internet and routes it to the correct internal service.

```
Internet → [Ingress Controller] → Service A (/api)
                                → Service B (/chat)
                                → Service C (/docs)
```

### What is Envoy?

**Envoy** is a high-performance, open-source proxy built by Lyft (now a CNCF graduated project). It handles:

- Load balancing across service instances
- TLS termination (HTTPS)
- Rate limiting
- Circuit breaking
- gRPC proxying
- HTTP/2 and HTTP/3 support
- Detailed observability (metrics, traces, access logs)

### What is Contour?

**Contour** is an ingress controller built on top of Envoy. It translates Kubernetes resources (Ingress, HTTPProxy) into Envoy configuration. Think of it as:

- **Envoy** = the high-performance engine
- **Contour** = the driver that tells Envoy what to do based on your Kubernetes configs

### Why Contour over nginx-ingress?

| Feature | Contour (Envoy) | nginx-ingress |
|---------|----------------|---------------|
| Protocol support | HTTP/1.1, HTTP/2, gRPC, WebSocket | HTTP/1.1, some HTTP/2 |
| Config model | CRD-based (HTTPProxy) | Annotations on Ingress |
| Multi-team routing | Built-in delegation | Complex annotation chains |
| Hot reload | Dynamic via xDS (zero downtime) | Config reload (brief disruption) |
| Observability | Built-in detailed metrics | Requires configuration |

---

## 2. Core Concepts

### 2.1 Reverse Proxy

A reverse proxy sits between clients and servers:

```
Client → [Reverse Proxy (Envoy)] → Backend Server
```

The client never talks directly to your backend. Benefits:
- **Security** — hide internal architecture
- **Load balancing** — distribute traffic across instances
- **TLS termination** — handle HTTPS in one place
- **Caching** — reduce backend load

### 2.2 TLS Termination

TLS termination means the proxy handles HTTPS encryption/decryption:

```
Client --[HTTPS]--> Envoy --[HTTP]--> Backend Pod
```

The backend doesn't need to handle certificates — Envoy does it all.

### 2.3 Load Balancing Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| Round Robin | Equal distribution | Most workloads |
| Least Connections | Send to least-busy server | Long-lived connections |
| Random | Random selection | Simple, low overhead |
| Ring Hash | Consistent hashing by key | Session affinity |
| Maglev | Google's consistent hash | Large-scale, stable routing |

### 2.4 Rate Limiting

Protect services from too many requests:

```yaml
# Allow 100 requests per minute per IP
rate_limit:
  requests_per_unit: 100
  unit: minute
```

### 2.5 Circuit Breaking

Prevent cascading failures by stopping requests to unhealthy backends:

```
Normal: Client → Envoy → Backend (healthy)
Circuit Open: Client → Envoy → 503 (backend overwhelmed, don't send more)
```

---

## 3. How Envoy Works

### 3.1 Architecture

```
                     ┌─────────────────────────────┐
                     │           ENVOY              │
Incoming    ┌────────┤                              │
Request ──▶ │Listener│──▶ Filter Chain ──▶ Router ──┼──▶ Cluster ──▶ Backend
            └────────┤                              │
                     │  Admin Interface (:9901)     │
                     └─────────────────────────────┘
```

### 3.2 Key Components

**Listeners** — Where Envoy listens for connections (e.g., port 80, 443)

```yaml
listeners:
  - name: http_listener
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8080
```

**Clusters** — Groups of backend endpoints (your Kubernetes services)

```yaml
clusters:
  - name: api_service
    type: STRICT_DNS
    load_assignment:
      cluster_name: api_service
      endpoints:
        - lb_endpoints:
            - endpoint:
                address:
                  socket_address:
                    address: api-service.default.svc.cluster.local
                    port_value: 8000
```

**Routes** — Rules that map requests to clusters

```yaml
routes:
  - match:
      prefix: "/api"
    route:
      cluster: api_service
  - match:
      prefix: "/"
    route:
      cluster: frontend_service
```

**Filters** — Middleware that processes requests (auth, rate limiting, compression)

### 3.3 xDS API (Dynamic Configuration)

Envoy supports dynamic configuration through the xDS protocol:

| API | Purpose |
|-----|---------|
| **LDS** (Listener Discovery) | Discover listeners |
| **RDS** (Route Discovery) | Discover routes |
| **CDS** (Cluster Discovery) | Discover clusters |
| **EDS** (Endpoint Discovery) | Discover endpoints |
| **SDS** (Secret Discovery) | Discover TLS certificates |

Contour acts as the xDS server — it watches Kubernetes resources and pushes config to Envoy dynamically (no restarts needed).

---

## 4. Contour as Envoy Manager

### 4.1 HTTPProxy CRD

Contour introduces the **HTTPProxy** Custom Resource Definition — a more powerful alternative to the standard Kubernetes Ingress:

```yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: my-app
spec:
  virtualhost:
    fqdn: app.example.com
    tls:
      secretName: app-tls-cert
  routes:
    - conditions:
        - prefix: /api
      services:
        - name: api-service
          port: 8000
    - conditions:
        - prefix: /
      services:
        - name: frontend
          port: 3000
```

### 4.2 HTTPProxy vs Ingress

| Feature | Ingress | HTTPProxy |
|---------|---------|-----------|
| Traffic splitting | No | Yes (weighted routing) |
| Header routing | Limited | Full support |
| Rate limiting | No | Yes |
| Delegation | No | Yes (multi-team) |
| Health checks | No | Custom health checks |
| Retry policy | No | Yes |
| Timeout config | No | Per-route timeouts |

---

## 5. Installation & Setup

### Install Contour with Helm

```bash
# Add the Contour Helm repository
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install Contour
helm install contour bitnami/contour \
  --namespace projectcontour \
  --create-namespace \
  --set envoy.kind=deployment \
  --set contour.replicas=2 \
  --set envoy.replicas=2

# Verify installation
kubectl get pods -n projectcontour
kubectl get svc -n projectcontour
```

### Install with manifests

```bash
# Apply Contour manifests directly
kubectl apply -f https://projectcontour.io/quickstart/contour.yaml

# Check the Envoy service (LoadBalancer or NodePort)
kubectl get svc envoy -n projectcontour
```

---

## 6. Exercises

### Exercise 1: Basic HTTPProxy Routing

Deploy a sample app and route traffic to it:

```yaml
# deploy-app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hello
  template:
    metadata:
      labels:
        app: hello
    spec:
      containers:
        - name: hello
          image: hashicorp/http-echo
          args:
            - "-text=Hello from the AI Platform!"
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: hello-svc
spec:
  selector:
    app: hello
  ports:
    - port: 80
      targetPort: 5678
---
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: hello-proxy
spec:
  virtualhost:
    fqdn: hello.local
  routes:
    - conditions:
        - prefix: /
      services:
        - name: hello-svc
          port: 80
```

```bash
# Apply and test
kubectl apply -f deploy-app.yaml

# Test (add hello.local to /etc/hosts pointing to Envoy's external IP)
ENVOY_IP=$(kubectl get svc envoy -n projectcontour -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -H "Host: hello.local" http://$ENVOY_IP/
```

---

### Exercise 2: TLS Termination with cert-manager

```yaml
# First, install cert-manager
# kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.yaml

# cluster-issuer.yaml — Let's Encrypt staging
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
      - http01:
          ingress:
            class: contour
---
# httpproxy-tls.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: secure-app
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-staging
spec:
  virtualhost:
    fqdn: app.example.com
    tls:
      secretName: app-tls-cert
  routes:
    - conditions:
        - prefix: /
      services:
        - name: frontend
          port: 3000
```

```bash
kubectl apply -f cluster-issuer.yaml
kubectl apply -f httpproxy-tls.yaml

# Verify certificate was issued
kubectl get certificate
kubectl describe certificate app-tls-cert
```

---

### Exercise 3: Path-Based and Header-Based Routing

```yaml
# multi-route.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: ai-platform
spec:
  virtualhost:
    fqdn: ai.example.com
  routes:
    # Route API requests to FastAPI backend
    - conditions:
        - prefix: /api
      services:
        - name: fastapi-service
          port: 8000

    # Route GraphQL to the same backend
    - conditions:
        - prefix: /graphql
      services:
        - name: fastapi-service
          port: 8000

    # Route based on header (internal admin tools)
    - conditions:
        - prefix: /admin
        - header:
            name: x-admin-key
            exact: "secret-admin-key"
      services:
        - name: admin-service
          port: 8080

    # Default: serve frontend
    - conditions:
        - prefix: /
      services:
        - name: frontend
          port: 3000
```

```bash
# Test path routing
curl http://ai.example.com/api/health
curl http://ai.example.com/graphql

# Test header routing
curl -H "x-admin-key: secret-admin-key" http://ai.example.com/admin
```

---

### Exercise 4: Rate Limiting

```yaml
# rate-limited-proxy.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: rate-limited-api
spec:
  virtualhost:
    fqdn: api.example.com
    rateLimitPolicy:
      local:
        requests: 100
        unit: minute
        burst: 20
  routes:
    - conditions:
        - prefix: /api/chat
      services:
        - name: chat-api
          port: 8000
      rateLimitPolicy:
        local:
          # Stricter limit on expensive LLM endpoints
          requests: 10
          unit: minute
          burst: 5

    - conditions:
        - prefix: /api
      services:
        - name: api-service
          port: 8000
```

```bash
# Test rate limiting with a burst of requests
for i in $(seq 1 20); do
  echo "Request $i: $(curl -s -o /dev/null -w '%{http_code}' http://api.example.com/api/chat)"
done
# After 10 requests, you should see 429 (Too Many Requests)
```

---

### Exercise 5: Weighted Traffic Splitting (Canary Deployments)

```yaml
# canary-deploy.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: canary-release
spec:
  virtualhost:
    fqdn: app.example.com
  routes:
    - conditions:
        - prefix: /
      services:
        # 90% traffic to stable version
        - name: frontend-stable
          port: 3000
          weight: 90
        # 10% traffic to canary version
        - name: frontend-canary
          port: 3000
          weight: 10
```

```bash
# Gradually shift traffic: 90/10 → 70/30 → 50/50 → 0/100
# Monitor error rates at each step before increasing canary weight

# Test traffic distribution
for i in $(seq 1 100); do
  curl -s http://app.example.com/ | grep -o "v[0-9]*"
done | sort | uniq -c
# Should show ~90 v1 and ~10 v2
```

---

### Exercise 6: CORS Configuration

```yaml
# cors-proxy.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: cors-enabled-api
spec:
  virtualhost:
    fqdn: api.example.com
    corsPolicy:
      allowCredentials: true
      allowOrigin:
        - "https://app.example.com"
        - "http://localhost:3000"       # Local development
      allowMethods:
        - GET
        - POST
        - OPTIONS
      allowHeaders:
        - Authorization
        - Content-Type
        - X-Request-ID
      exposeHeaders:
        - X-Request-ID
      maxAge: "10m"
  routes:
    - conditions:
        - prefix: /
      services:
        - name: api-service
          port: 8000
```

```bash
# Test CORS preflight
curl -i -X OPTIONS http://api.example.com/api/chat \
  -H "Origin: https://app.example.com" \
  -H "Access-Control-Request-Method: POST"

# Should see Access-Control-Allow-Origin in response headers
```

---

### Exercise 7: gRPC Routing for Model Serving

```yaml
# grpc-proxy.yaml
apiVersion: projectcontour.io/v1
kind: HTTPProxy
metadata:
  name: grpc-model-serving
spec:
  virtualhost:
    fqdn: models.example.com
    tls:
      secretName: models-tls
  routes:
    # Route gRPC traffic to vLLM
    - conditions:
        - prefix: /inference.v1.ModelService
      services:
        - name: vllm-service
          port: 8001
          protocol: h2c    # gRPC uses HTTP/2
      timeoutPolicy:
        response: 120s     # LLM inference can take a while

    # Route gRPC traffic to embedding service
    - conditions:
        - prefix: /embedding.v1.EmbeddingService
      services:
        - name: embedding-service
          port: 50051
          protocol: h2c
      timeoutPolicy:
        response: 30s
```

```bash
# Test with grpcurl
grpcurl -plaintext models.example.com:443 \
  inference.v1.ModelService/Predict

# List available gRPC services
grpcurl -plaintext models.example.com:443 list
```

---

## 7. Monitoring & Debugging

### Envoy Admin Interface

Envoy exposes an admin UI on port 9901:

```bash
# Port-forward to Envoy admin
kubectl port-forward -n projectcontour deploy/envoy 9901:9901

# View all routes
curl http://localhost:9901/config_dump | jq '.configs[] | select(.["@type"] | contains("route"))'

# Check cluster health
curl http://localhost:9901/clusters

# View stats
curl http://localhost:9901/stats | grep http.ingress_http

# Key metrics to watch:
# - envoy_http_downstream_rq_total — total requests
# - envoy_http_downstream_rq_xx — response codes (2xx, 4xx, 5xx)
# - envoy_cluster_upstream_rq_time — backend latency
```

### Prometheus Metrics

```yaml
# ServiceMonitor for scraping Envoy metrics
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: envoy-metrics
spec:
  selector:
    matchLabels:
      app: envoy
  endpoints:
    - port: metrics
      interval: 15s
```

### Access Logs

```bash
# View Envoy access logs
kubectl logs -n projectcontour -l app=envoy -f

# Log format includes: timestamp, method, path, response_code, duration, upstream_host
```

---

## 8. How It's Used in Our Project

In the AI platform, Contour/Envoy handles:

- **Frontend routing** — `/*` → Next.js service
- **API routing** — `/api/*` and `/graphql` → FastAPI service
- **TLS termination** — All external traffic is HTTPS
- **Rate limiting** — Protects LLM inference endpoints from abuse
- **gRPC routing** — Model serving endpoints use gRPC for efficiency
- **Health checks** — Active health checking on all backend services
- **Canary deployments** — Gradual rollout of new model versions

---

## 9. Best Practices

1. **Always use TLS** — Never expose HTTP endpoints publicly
2. **Set timeouts** — Configure per-route timeouts (especially for LLM endpoints)
3. **Enable rate limiting** — Protect expensive endpoints
4. **Use health checks** — Configure active health checks, not just Kubernetes readiness
5. **Monitor 5xx rates** — Alert on backend error rate increases
6. **Set retry policies** — Retry on 503 (service unavailable), not on 500 (server error)
7. **Use HTTPProxy over Ingress** — More features, better multi-team support

---

## 10. Further Reading

- [Envoy Proxy Documentation](https://www.envoyproxy.io/docs)
- [Contour Documentation](https://projectcontour.io/docs)
- [HTTPProxy Reference](https://projectcontour.io/docs/main/config/fundamentals/)
- [Envoy Architecture Overview](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/arch_overview)
- [cert-manager Documentation](https://cert-manager.io/docs/)
