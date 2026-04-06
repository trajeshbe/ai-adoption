#!/usr/bin/env python3
"""
Load Test: Ramping 1 -> 30 concurrent users against AI Agent Platform.
Captures per-request metrics, system utilization, and GPU stats.
"""

import asyncio
import aiohttp
import json
import time
import subprocess
import csv
import os
import random
import statistics
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

GATEWAY_URL = "http://localhost:8050/graphql"
AGENT_EXECUTE_URL = "http://localhost:8053/agents/execute"
RESULTS_DIR = Path("/tmp/loadtest-results")
RESULTS_DIR.mkdir(exist_ok=True)

QUESTIONS = [
    "What is the best sci-fi movie?",
    "Tell me about The Matrix",
    "Who directed Inception?",
    "Recommend a comedy movie",
    "Tell me about Star Wars",
    "What is Blade Runner about?",
    "Who played Batman in The Dark Knight?",
    "Tell me about Interstellar",
    "Recommend a thriller movie",
    "What is Alien about?",
    "Who directed Pulp Fiction?",
    "Tell me about the Terminator",
    "Name 3 movies by Spielberg",
    "What is 2001 A Space Odyssey about?",
    "Who won best picture in 2020?",
]

AGENT_ID = "00000000-0000-0000-0000-000000000001"

# Ramp schedule: (duration_seconds, target_concurrency)
RAMP_SCHEDULE = [
    (15, 5),    # 0-15s:   ramp to 5 users
    (15, 10),   # 15-30s:  ramp to 10 users
    (15, 15),   # 30-45s:  ramp to 15 users
    (15, 20),   # 45-60s:  ramp to 20 users
    (15, 25),   # 60-75s:  ramp to 25 users
    (15, 30),   # 75-90s:  ramp to 30 users
    (30, 30),   # 90-120s: sustain 30 users
    (15, 15),   # 120-135s: ramp down to 15
    (15, 0),    # 135-150s: ramp down to 0
]

@dataclass
class RequestResult:
    timestamp: float
    user_id: int
    e2e_ms: float
    llm_ms: float
    http_code: int
    success: bool
    question: str
    concurrent_users: int

results: list[RequestResult] = []
active_users = 0
target_users = 0
test_start = 0.0

async def capture_system_metrics(stop_event: asyncio.Event):
    """Capture CPU, memory, GPU metrics every 5 seconds."""
    metrics_file = RESULTS_DIR / "system_metrics.csv"
    with open(metrics_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["elapsed_s", "cpu_pct", "mem_used_mb", "mem_total_mb",
                          "gpu_util_pct", "gpu_mem_mb", "gpu_temp_c",
                          "active_users", "target_users"])
        while not stop_event.is_set():
            elapsed = time.time() - test_start
            try:
                cpu = subprocess.run(
                    ["sh", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"],
                    capture_output=True, text=True, timeout=5
                ).stdout.strip()
                mem = subprocess.run(
                    ["sh", "-c", "free -m | awk '/Mem:/{print $3,$2}'"],
                    capture_output=True, text=True, timeout=5
                ).stdout.strip().split()
                gpu = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,temperature.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5
                ).stdout.strip().split(",")
                writer.writerow([
                    f"{elapsed:.0f}", cpu,
                    mem[0] if len(mem) > 0 else "", mem[1] if len(mem) > 1 else "",
                    gpu[0].strip() if len(gpu) > 0 else "",
                    gpu[1].strip() if len(gpu) > 1 else "",
                    gpu[2].strip() if len(gpu) > 2 else "",
                    active_users, target_users
                ])
                f.flush()
            except Exception:
                pass
            await asyncio.sleep(5)

async def send_request(session: aiohttp.ClientSession, user_id: int, concurrent: int) -> RequestResult:
    """Send a single chat request via GraphQL."""
    question = random.choice(QUESTIONS)
    payload = {
        "query": 'mutation SendMessage($input: SendMessageInput!) { sendMessage(input: $input) { id content role latencyMs } }',
        "variables": {
            "input": {
                "agentId": AGENT_ID,
                "content": question,
            }
        }
    }
    start = time.time()
    try:
        async with session.post(GATEWAY_URL, json=payload, timeout=aiohttp.ClientTimeout(total=90)) as resp:
            body = await resp.json()
            e2e_ms = (time.time() - start) * 1000
            llm_ms = 0.0
            success = False
            if body.get("data", {}).get("sendMessage"):
                llm_ms = body["data"]["sendMessage"].get("latencyMs", 0)
                success = True
            return RequestResult(
                timestamp=time.time() - test_start,
                user_id=user_id,
                e2e_ms=e2e_ms,
                llm_ms=llm_ms,
                http_code=resp.status,
                success=success,
                question=question,
                concurrent_users=concurrent,
            )
    except Exception as e:
        e2e_ms = (time.time() - start) * 1000
        return RequestResult(
            timestamp=time.time() - test_start,
            user_id=user_id,
            e2e_ms=e2e_ms,
            llm_ms=0,
            http_code=0,
            success=False,
            question=question,
            concurrent_users=concurrent,
        )

async def user_loop(session: aiohttp.ClientSession, user_id: int, stop_event: asyncio.Event):
    """Simulate a single user sending requests in a loop."""
    global active_users
    active_users += 1
    try:
        while not stop_event.is_set():
            result = await send_request(session, user_id, active_users)
            results.append(result)
            status = "OK" if result.success else "FAIL"
            print(f"  [{result.timestamp:6.0f}s] User {user_id:2d} | {status} | e2e={result.e2e_ms:7.0f}ms llm={result.llm_ms:7.0f}ms | concurrent={result.concurrent_users} | {result.question[:30]}")
            # Think time
            await asyncio.sleep(random.uniform(1, 3))
    except asyncio.CancelledError:
        pass
    finally:
        active_users -= 1

async def run_load_test():
    global target_users, test_start, active_users

    print("=" * 70)
    print(" LOAD TEST: Ramping 1 → 30 Concurrent Users")
    print(" VM: n1-standard-8 + NVIDIA T4 (16 GB VRAM)")
    print(" LLM: Ollama qwen2.5:1.5b on GPU")
    print(f" Results: {RESULTS_DIR}")
    print("=" * 70)
    print()

    # Ramp schedule display
    print(" Ramp Schedule:")
    t = 0
    for dur, tgt in RAMP_SCHEDULE:
        print(f"   {t:3d}s - {t+dur:3d}s : {tgt} concurrent users")
        t += dur
    print()

    test_start = time.time()
    stop_event = asyncio.Event()
    user_tasks: dict[int, asyncio.Task] = {}
    next_user_id = 1

    # Start metrics collection
    metrics_task = asyncio.create_task(capture_system_metrics(stop_event))

    connector = aiohttp.TCPConnector(limit=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        for phase_dur, phase_target in RAMP_SCHEDULE:
            target_users = phase_target
            elapsed = time.time() - test_start
            print(f"\n[{elapsed:5.0f}s] === Ramping to {phase_target} concurrent users ===")

            # Scale up
            while len(user_tasks) < phase_target:
                uid = next_user_id
                next_user_id += 1
                task = asyncio.create_task(user_loop(session, uid, stop_event))
                user_tasks[uid] = task

            # Scale down
            while len(user_tasks) > phase_target:
                uid, task = user_tasks.popitem()
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=2)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

            # Hold this phase
            await asyncio.sleep(phase_dur)

        # Clean up all remaining
        stop_event.set()
        for uid, task in user_tasks.items():
            task.cancel()
        await asyncio.gather(*user_tasks.values(), return_exceptions=True)

    metrics_task.cancel()
    try:
        await metrics_task
    except asyncio.CancelledError:
        pass

    # ---- Analysis ----
    analyze_results()

def analyze_results():
    if not results:
        print("No results!")
        return

    total = len(results)
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    e2e_times = [r.e2e_ms for r in successes]
    llm_times = [r.llm_ms for r in successes if r.llm_ms > 0]

    test_duration = max(r.timestamp for r in results) - min(r.timestamp for r in results)
    rps = total / test_duration if test_duration > 0 else 0

    def pct(data, p):
        if not data:
            return 0
        s = sorted(data)
        k = (len(s) - 1) * p / 100
        f = int(k)
        c = min(f + 1, len(s) - 1)
        return s[f] + (k - f) * (s[c] - s[f])

    report = []
    report.append("")
    report.append("=" * 70)
    report.append(" LOAD TEST RESULTS")
    report.append("=" * 70)
    report.append(f" VM Config:         n1-standard-8 (8 vCPU, 30 GB RAM)")
    report.append(f" GPU:               NVIDIA T4 (16 GB VRAM)")
    report.append(f" LLM:               Ollama qwen2.5:1.5b")
    report.append(f" Test Duration:     {test_duration:.0f}s")
    report.append(f" Peak Concurrency:  30 users")
    report.append("=" * 70)
    report.append("")
    report.append(" THROUGHPUT")
    report.append(f"   Total Requests:    {total}")
    report.append(f"   Successful:        {len(successes)}")
    report.append(f"   Failed:            {len(failures)}")
    report.append(f"   Success Rate:      {len(successes)*100/total:.1f}%")
    report.append(f"   Requests/sec:      {rps:.2f}")
    report.append("")

    if e2e_times:
        report.append(" END-TO-END LATENCY (client → gateway → agent-engine → LLM → back)")
        report.append(f"   Mean:              {statistics.mean(e2e_times):,.0f} ms")
        report.append(f"   Median (p50):      {pct(e2e_times, 50):,.0f} ms")
        report.append(f"   p90:               {pct(e2e_times, 90):,.0f} ms")
        report.append(f"   p95:               {pct(e2e_times, 95):,.0f} ms")
        report.append(f"   p99:               {pct(e2e_times, 99):,.0f} ms")
        report.append(f"   Min:               {min(e2e_times):,.0f} ms")
        report.append(f"   Max:               {max(e2e_times):,.0f} ms")
        if len(e2e_times) > 1:
            report.append(f"   Std Dev:           {statistics.stdev(e2e_times):,.0f} ms")
        report.append("")

    if llm_times:
        report.append(" LLM INFERENCE LATENCY (Ollama + T4 GPU)")
        report.append(f"   Mean:              {statistics.mean(llm_times):,.0f} ms")
        report.append(f"   Median (p50):      {pct(llm_times, 50):,.0f} ms")
        report.append(f"   p90:               {pct(llm_times, 90):,.0f} ms")
        report.append(f"   p95:               {pct(llm_times, 95):,.0f} ms")
        report.append(f"   Min:               {min(llm_times):,.0f} ms")
        report.append(f"   Max:               {max(llm_times):,.0f} ms")
        report.append("")

    # Per-concurrency breakdown
    report.append(" LATENCY BY CONCURRENCY LEVEL")
    report.append(f"   {'Users':>5} | {'Reqs':>5} | {'Avg E2E':>10} | {'p95 E2E':>10} | {'Avg LLM':>10} | {'Success%':>8}")
    report.append(f"   {'-----':>5} | {'-----':>5} | {'----------':>10} | {'----------':>10} | {'----------':>10} | {'--------':>8}")

    concurrency_buckets = {}
    for r in results:
        bucket = ((r.concurrent_users - 1) // 5 + 1) * 5
        bucket = min(bucket, 30)
        concurrency_buckets.setdefault(bucket, []).append(r)

    for bucket in sorted(concurrency_buckets.keys()):
        reqs = concurrency_buckets[bucket]
        ok = [r for r in reqs if r.success]
        ok_e2e = [r.e2e_ms for r in ok]
        ok_llm = [r.llm_ms for r in ok if r.llm_ms > 0]
        if ok_e2e:
            report.append(f"   {bucket:>5} | {len(reqs):>5} | {statistics.mean(ok_e2e):>8,.0f}ms | {pct(ok_e2e, 95):>8,.0f}ms | {statistics.mean(ok_llm):>8,.0f}ms | {len(ok)*100/len(reqs):>7.0f}%")
        else:
            report.append(f"   {bucket:>5} | {len(reqs):>5} | {'N/A':>10} | {'N/A':>10} | {'N/A':>10} | {0:>7.0f}%")

    report.append("")

    # GPU metrics summary
    metrics_file = RESULTS_DIR / "system_metrics.csv"
    if metrics_file.exists():
        gpu_utils = []
        gpu_mems = []
        cpu_utils = []
        with open(metrics_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    if row["gpu_util_pct"]:
                        gpu_utils.append(float(row["gpu_util_pct"]))
                    if row["gpu_mem_mb"]:
                        gpu_mems.append(float(row["gpu_mem_mb"]))
                    if row["cpu_pct"]:
                        cpu_utils.append(float(row["cpu_pct"]))
                except (ValueError, KeyError):
                    pass

        if gpu_utils:
            report.append(" SYSTEM RESOURCE UTILIZATION (sampled every 5s)")
            report.append(f"   CPU:     avg={statistics.mean(cpu_utils):.1f}%  max={max(cpu_utils):.1f}%")
            report.append(f"   GPU:     avg={statistics.mean(gpu_utils):.1f}%  max={max(gpu_utils):.1f}%")
            report.append(f"   GPU Mem: avg={statistics.mean(gpu_mems):.0f} MB  max={max(gpu_mems):.0f} MB / 15,360 MB")
            report.append("")

    report.append("=" * 70)

    output = "\n".join(report)
    print(output)

    # Save
    with open(RESULTS_DIR / "summary.txt", "w") as f:
        f.write(output)

    # Save per-request CSV
    with open(RESULTS_DIR / "requests.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["elapsed_s", "user_id", "e2e_ms", "llm_ms", "http_code", "success", "concurrent_users", "question"])
        for r in results:
            writer.writerow([f"{r.timestamp:.1f}", r.user_id, f"{r.e2e_ms:.0f}", f"{r.llm_ms:.0f}", r.http_code, r.success, r.concurrent_users, r.question])

    print(f"\nResults saved to {RESULTS_DIR}/")

if __name__ == "__main__":
    asyncio.run(run_load_test())
