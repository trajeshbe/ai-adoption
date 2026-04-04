# Phase 5: LLM Runtime

## Summary

Deploy local LLM inference using vLLM for GPU-accelerated serving and llama.cpp as a lightweight CPU fallback. This phase configures model loading, quantization options, and an OpenAI-compatible API that the agent engine consumes transparently.

## Learning Objectives

- Deploy vLLM with a quantized model and PagedAttention
- Set up llama.cpp as a CPU-only inference backend
- Expose an OpenAI-compatible `/v1/chat/completions` endpoint
- Benchmark throughput and latency across backends

## Key Commands

```bash
# Start vLLM serving
python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-3-8B-Instruct

# Start llama.cpp server
./llama-server -m models/llama-3-8b-q4.gguf --port 8081

# Health check
curl http://localhost:8000/v1/models
```

## Slash Command

Run `/05-llm-runtime` in Claude Code to begin this phase.

## Next Phase

[Phase 6: Observability](phase-06-observability.md)
