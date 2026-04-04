#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# load-test.sh – Simulate concurrent users hitting the chat GraphQL API
# ---------------------------------------------------------------------------

NUM_USERS="${NUM_USERS:-10}"
DURATION_SECONDS="${DURATION_SECONDS:-30}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8050}"
GRAPHQL_ENDPOINT="${GATEWAY_URL}/graphql"

# Temporary directory for per-request metrics
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# ---- Questions & agent IDs ------------------------------------------------

QUESTIONS=(
  "What is the best sci-fi movie?"
  "Tell me about The Matrix"
  "Who directed Inception?"
  "What is the weather in Tokyo?"
  "Recommend a comedy movie"
  "What is the weather in London?"
  "Tell me about Star Wars"
  "Who won best picture in 2020?"
  "What is the weather in New York?"
  "Name 3 movies by Spielberg"
)

MOVIE_AGENT="00000000-0000-0000-0000-000000000001"
WEATHER_AGENT="00000000-0000-0000-0000-000000000002"

# Map question index -> agent (weather questions at indices 3, 5, 8)
agent_for_index() {
  case "$1" in
    3|5|8) echo "$WEATHER_AGENT" ;;
    *)     echo "$MOVIE_AGENT" ;;
  esac
}

# ---- Helper: build JSON payload -------------------------------------------

build_payload() {
  local question="$1"
  local agent_id="$2"
  # Use printf + jq-free JSON escaping (question text is safe ASCII here)
  cat <<EOJSON
{"query":"mutation SendMessage(\$input: SendMessageInput!) { sendMessage(input: \$input) { id role content latencyMs } }","variables":{"input":{"agentId":"${agent_id}","message":"${question}"}}}
EOJSON
}

# ---- Simulated user loop --------------------------------------------------

run_user() {
  local user_id="$1"
  local end_time="$2"
  local user_dir="${WORK_DIR}/user_${user_id}"
  mkdir -p "$user_dir"
  local req_num=0

  while [ "$(date +%s)" -lt "$end_time" ]; do
    # Pick a random question
    local idx=$(( RANDOM % ${#QUESTIONS[@]} ))
    local question="${QUESTIONS[$idx]}"
    local agent_id
    agent_id="$(agent_for_index "$idx")"

    local payload
    payload="$(build_payload "$question" "$agent_id")"

    req_num=$((req_num + 1))
    local result_file="${user_dir}/req_${req_num}"

    # Time the request; capture HTTP status code
    local http_code
    local start_ms end_ms elapsed_ms
    start_ms="$(date +%s%N)"

    http_code="$(curl -s -o /dev/null -w '%{http_code}' \
      --max-time 30 \
      -X POST \
      -H 'Content-Type: application/json' \
      -d "$payload" \
      "$GRAPHQL_ENDPOINT" 2>/dev/null || echo "000")"

    end_ms="$(date +%s%N)"
    elapsed_ms=$(( (end_ms - start_ms) / 1000000 ))

    echo "${http_code} ${elapsed_ms}" > "$result_file"

    # Random delay 3-5 seconds before next request
    local delay=$(( (RANDOM % 3) + 3 ))
    sleep "$delay"
  done
}

# ---- Main ------------------------------------------------------------------

echo "============================================"
echo " Load Test – Chat GraphQL API"
echo "============================================"
echo " Gateway URL   : ${GRAPHQL_ENDPOINT}"
echo " Concurrent users : ${NUM_USERS}"
echo " Duration      : ${DURATION_SECONDS}s"
echo "============================================"
echo ""

START_TIME="$(date +%s)"
END_TIME=$(( START_TIME + DURATION_SECONDS ))

echo "[$(date '+%H:%M:%S')] Starting ${NUM_USERS} simulated users …"

# Launch user processes in background
pids=()
for i in $(seq 1 "$NUM_USERS"); do
  run_user "$i" "$END_TIME" &
  pids+=($!)
done

# Wait for all users to finish
for pid in "${pids[@]}"; do
  wait "$pid" 2>/dev/null || true
done

echo "[$(date '+%H:%M:%S')] All users finished."
echo ""

# ---- Collect & report results ---------------------------------------------

total=0
success=0
failed=0
total_ms=0
min_ms=999999999
max_ms=0

for f in "$WORK_DIR"/user_*/req_*; do
  [ -f "$f" ] || continue
  read -r code ms < "$f"
  total=$((total + 1))
  total_ms=$((total_ms + ms))

  if [ "$code" -ge 200 ] 2>/dev/null && [ "$code" -lt 300 ] 2>/dev/null; then
    success=$((success + 1))
  else
    failed=$((failed + 1))
  fi

  if [ "$ms" -lt "$min_ms" ]; then min_ms="$ms"; fi
  if [ "$ms" -gt "$max_ms" ]; then max_ms="$ms"; fi
done

if [ "$total" -gt 0 ]; then
  avg_ms=$((total_ms / total))
else
  avg_ms=0
  min_ms=0
  max_ms=0
fi

echo "============================================"
echo " Load Test Summary"
echo "============================================"
printf " Total requests  : %d\n" "$total"
printf " Successful (2xx): %d\n" "$success"
printf " Failed          : %d\n" "$failed"
printf " Avg response    : %d ms\n" "$avg_ms"
printf " Min response    : %d ms\n" "$min_ms"
printf " Max response    : %d ms\n" "$max_ms"
if [ "$total" -gt 0 ]; then
  success_pct=$(( (success * 100) / total ))
  printf " Success rate    : %d%%\n" "$success_pct"
fi
echo "============================================"
