# ADR-003: vLLM with CPU Fallback for LLM Inference

## Status: Accepted

## Date: 2026-04-04

## Context

The platform must serve LLM inference for multiple use cases: interactive chat (latency
sensitive, p99 < 2s TTFT), batch agent execution (throughput sensitive, tolerant of
5-10s latency), and RAG-augmented document Q&A. Peak load projections estimate 200+
concurrent inference requests. GPU availability in our Kubernetes cluster is not
guaranteed -- nodes may be preempted (spot instances) or unavailable during scaling
events. The system must degrade gracefully rather than return errors when GPUs are
temporarily unavailable.

## Decision

We deploy vLLM on KubeRay clusters as the primary GPU-accelerated inference engine.
A CPU fallback tier runs llama.cpp (via llama-cpp-python server) on standard compute
nodes. A circuit breaker pattern in the inference-router service detects GPU tier
failures (latency spikes > 10s, error rate > 5%) and redirects traffic to the CPU tier
with automatic recovery probing every 30 seconds.

vLLM is configured with continuous batching, PagedAttention, and tensor parallelism
across multi-GPU nodes. KubeRay provides elastic scaling based on pending request
queue depth, scaling from 1 to 8 GPU workers.

## Consequences

**Positive:**
- vLLM's continuous batching achieves 2-4x throughput improvement over static batching
  by dynamically interleaving requests at the iteration level, maximizing GPU utilization.
- PagedAttention reduces KV-cache memory waste by up to 90%, enabling longer context
  windows and higher concurrency on the same GPU hardware.
- KubeRay elastic scaling responds to demand within 60-90 seconds, and Ray's built-in
  object store enables efficient model weight sharing across workers.
- CPU fallback ensures the platform never fully loses inference capability. While CPU
  inference is 10-50x slower, it handles low-priority batch work and keeps interactive
  features minimally functional during GPU outages.
- The circuit breaker prevents cascade failures where slow GPU responses consume all
  connection pool resources.

**Negative:**
- Running two inference stacks (vLLM + llama.cpp) doubles the operational surface area
  for model deployment -- every model update must be validated on both backends.
- CPU inference quality may differ slightly from GPU inference due to different
  quantization strategies (GPTQ/AWQ on GPU vs GGUF on CPU), requiring validation.
- KubeRay adds Kubernetes CRD complexity and requires familiarity with Ray's
  distributed computing model for debugging.
- GPU spot instance preemption can cause request failures during the circuit breaker
  detection window (up to 30 seconds of degraded responses before failover).

## Alternatives Considered

- **Cloud LLM APIs only (OpenAI, Anthropic):** Eliminates infrastructure complexity
  but creates vendor lock-in, provides no cost control at scale, and raises data
  sovereignty concerns for sensitive enterprise workloads.
- **TensorRT-LLM:** Highest raw performance on NVIDIA hardware, but significantly
  more complex build pipeline (engine compilation per model/GPU combination) and
  less flexible than vLLM's broader model support.
- **Triton Inference Server:** Powerful multi-framework serving, but heavier
  operational overhead. vLLM's focused LLM optimization (PagedAttention, continuous
  batching) outperforms Triton's general-purpose approach for our LLM-only workload.
