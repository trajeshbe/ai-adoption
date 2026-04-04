# Troubleshoot -- Common Debugging Flows

## Usage
Run this command when something is broken. Follow the flow that matches your symptom.

## Symptom: Service Won't Start
1. Check logs: `kubectl logs deploy/<service-name> -n agent-platform`
2. Check events: `kubectl describe pod <pod-name> -n agent-platform`
3. Common causes:
   - Missing env var -> Check `.devcontainer/devcontainer.json` remoteEnv
   - Database not ready -> Check postgres healthcheck: `pg_isready -h localhost -U agent_platform`
   - Port already in use -> `lsof -i :<port>` and kill the process

## Symptom: GraphQL Query Returns Errors
1. Open GraphQL Playground: http://localhost:8000/graphql
2. Check the error message in the response
3. Check gateway logs: `kubectl logs deploy/gateway -n agent-platform`
4. Verify the resolver: read `services/gateway/src/gateway/resolvers/<domain>.py`
5. Test the downstream service directly: `curl http://<service>:port/healthz`

## Symptom: LLM Inference Slow or Failing
1. Check LLM health: `curl http://localhost:11434/api/tags` (Ollama) or vLLM `/health`
2. Check if circuit breaker tripped: look for "fallback" in agent-engine logs
3. Check GPU utilization: `nvidia-smi` or `kubectl top pods -l app=vllm`
4. Check model loaded: `curl http://localhost:11434/v1/models`

## Symptom: Semantic Cache Not Working
1. Check Redis connection: `redis-cli -h localhost PING`
2. Check index exists: `redis-cli FT._LIST`
3. Check cache entries: `redis-cli FT.SEARCH cache_idx "*" LIMIT 0 5`
4. Check threshold: cache-service may have similarity threshold too high (>0.95)

## Symptom: Document Upload Fails
1. Check MinIO health: `curl http://localhost:9000/minio/health/live`
2. Check MinIO console: http://localhost:9001 (minioadmin/minioadmin)
3. Check document-service logs for chunking/embedding errors
4. Verify pgvector extension: `psql -c "SELECT extname FROM pg_extension WHERE extname='vector';"`

## Symptom: Traces Not Appearing in Grafana
1. Check OTEL Collector: `kubectl logs deploy/otel-collector`
2. Check exporter endpoint: Tempo must be reachable at the configured URL
3. Verify instrumentation: check that `setup_telemetry()` is called in service `main.py`
4. Check Tempo directly: `curl http://localhost:3200/api/traces`

## General Debugging
- **View all pod status:** `kubectl get pods -n agent-platform -o wide`
- **View recent events:** `kubectl get events -n agent-platform --sort-by='.lastTimestamp'`
- **Enter a pod:** `kubectl exec -it deploy/<service> -- /bin/bash`
- **Port forward a service:** `kubectl port-forward svc/<service> <local>:<remote>`
- **Check resource usage:** `kubectl top pods -n agent-platform`
