"""In-memory metrics tracking for the gateway service.

Tracks request counts, error counts, latencies, and active connections
using simple counters and gauges. Thread-safe via threading locks.
"""

import threading
import time
from collections import deque
from typing import Any


class MetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self, latency_window: int = 100) -> None:
        self._lock = threading.Lock()
        self._total_requests: int = 0
        self._total_errors: int = 0
        self._active_connections: int = 0
        self._request_latencies: deque[float] = deque(maxlen=latency_window)
        self._start_time: float = time.time()
        self._scaling_events: deque[dict[str, Any]] = deque(maxlen=50)
        self._path_counts: dict[str, int] = {}
        self._instance_requests: dict[str, int] = {}

    def record_request(self, path: str, status: int, latency_ms: float) -> None:
        """Record a completed request.

        Args:
            path: The request path.
            status: HTTP status code.
            latency_ms: Request latency in milliseconds.
        """
        with self._lock:
            self._total_requests += 1
            if status >= 400:
                self._total_errors += 1
            self._request_latencies.append(latency_ms)
            self._path_counts[path] = self._path_counts.get(path, 0) + 1

    def increment_connections(self) -> None:
        """Increment active connection count."""
        with self._lock:
            self._active_connections += 1

    def decrement_connections(self) -> None:
        """Decrement active connection count."""
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)

    def record_scaling_event(self, service: str, action: str, instances: int) -> None:
        """Record a scaling event.

        Args:
            service: Name of the service that scaled.
            action: 'scale_up' or 'scale_down'.
            instances: New instance count.
        """
        with self._lock:
            self._scaling_events.append({
                "timestamp": time.time(),
                "service": service,
                "action": action,
                "instances": instances,
            })

    def record_instance_request(self, instance_id: str) -> None:
        """Record a request handled by a specific instance."""
        with self._lock:
            self._instance_requests[instance_id] = (
                self._instance_requests.get(instance_id, 0) + 1
            )

    def get_metrics(self) -> dict[str, Any]:
        """Return current metrics snapshot.

        Returns:
            Dictionary with all collected metrics.
        """
        with self._lock:
            uptime = time.time() - self._start_time
            latencies = list(self._request_latencies)
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            rps = self._total_requests / uptime if uptime > 0 else 0.0
            error_rate = (
                (self._total_errors / self._total_requests * 100)
                if self._total_requests > 0
                else 0.0
            )

            return {
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "active_connections": self._active_connections,
                "avg_latency_ms": round(avg_latency, 2),
                "requests_per_second": round(rps, 2),
                "error_rate": round(error_rate, 2),
                "uptime_seconds": round(uptime, 1),
                "scaling_events": list(self._scaling_events),
                "instance_distribution": dict(self._instance_requests),
                "path_counts": dict(self._path_counts),
            }


# Module-level singleton
metrics_collector = MetricsCollector()


def record_request(path: str, status: int, latency_ms: float) -> None:
    """Module-level convenience for recording a request."""
    metrics_collector.record_request(path, status, latency_ms)


def get_metrics() -> dict[str, Any]:
    """Module-level convenience for retrieving metrics."""
    return metrics_collector.get_metrics()
