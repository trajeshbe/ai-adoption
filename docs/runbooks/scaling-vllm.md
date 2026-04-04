# Runbook: Scaling vLLM GPU Workers

## Purpose

When and how to scale vLLM inference workers to handle increased load or reduce latency.

---

## When to Scale

Monitor these signals in Grafana:

| Metric | Warning Threshold | Critical Threshold |
|---|---|---|
| `vllm_request_queue_length` | > 10 for 2 min | > 50 for 1 min |
| `vllm_gpu_utilization` | > 85% sustained 5 min | > 95% sustained 2 min |
| `vllm_time_to_first_token_p99` | > 3s | > 8s |
| `vllm_request_latency_p99` | > 10s | > 30s |

If any critical threshold is breached, scale immediately.

---

## How to Scale

### Option 1: Horizontal Scaling (add replicas)

```bash
# Check current replica count
kubectl get deployment vllm-server -n llm-runtime

# Scale up (each replica requires 1 GPU)
kubectl scale deployment vllm-server -n llm-runtime --replicas=3

# Verify new pods are running and model is loaded
kubectl get pods -n llm-runtime -l app=vllm -w
kubectl logs -n llm-runtime -l app=vllm --tail=20 | grep "Model loaded"
```

**Prerequisites**: Available GPU nodes in the cluster. If none, see Option 3.

### Option 2: Vertical Tuning (adjust serving parameters)

Modify the vLLM deployment without adding hardware:

```bash
# Increase max concurrent sequences (trades memory for throughput)
kubectl set env deployment/vllm-server -n llm-runtime \
  MAX_NUM_SEQS=512 \
  GPU_MEMORY_UTILIZATION=0.95

# Enable continuous batching optimizations
kubectl set env deployment/vllm-server -n llm-runtime \
  ENABLE_CHUNKED_PREFILL=true
```

### Option 3: Add GPU Nodes

If the cluster has no available GPU capacity:

```bash
# For cloud-managed clusters, scale the GPU node pool
# Example: GKE
gcloud container clusters resize CLUSTER_NAME \
  --node-pool gpu-pool \
  --num-nodes 3

# Verify new nodes are Ready and GPU-labeled
kubectl get nodes -l accelerator=nvidia-gpu
```

---

## Scaling Down

Scale down when all of the following are true for 15+ minutes:

- `vllm_gpu_utilization` < 30%
- `vllm_request_queue_length` == 0
- `vllm_request_latency_p99` < 2s

```bash
# Scale down to minimum (never below 1)
kubectl scale deployment vllm-server -n llm-runtime --replicas=1
```

---

## Fallback: CPU Inference via llama.cpp

If GPU capacity is exhausted and cannot be expanded, route overflow traffic to llama.cpp CPU workers:

```bash
# Scale llama.cpp replicas
kubectl scale deployment llama-server -n llm-runtime --replicas=4

# Update the agent engine to use the CPU fallback endpoint
kubectl set env deployment/agent-engine -n ai-agents \
  LLM_FALLBACK_URL=http://llama-server.llm-runtime:8081/v1
```

Note: CPU inference is 10-50x slower. Use only as a temporary measure.

---

## Validation

After any scaling action, verify:

1. `kubectl get pods -n llm-runtime` -- all pods Running
2. `curl http://vllm-server.llm-runtime:8080/v1/models` -- model listed
3. Grafana LLM dashboard -- latency decreasing, queue draining
