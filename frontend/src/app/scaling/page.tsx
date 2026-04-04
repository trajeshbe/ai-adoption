"use client";

import { useEffect, useState, useCallback } from "react";

const GRAPHQL_URL =
  process.env.NEXT_PUBLIC_GRAPHQL_URL || "http://localhost:8050/graphql";
const BASE_URL = GRAPHQL_URL.replace("/graphql", "");
const METRICS_URL = `${BASE_URL}/metrics`;
const K8S_URL = `${BASE_URL}/k8s`;

interface ServiceHealth {
  name: string;
  url: string;
  status: "healthy" | "unhealthy";
  response_time_ms: number;
  uptime_seconds: number;
}

interface ScalingEvent {
  timestamp: number;
  service: string;
  action: string;
  instances: number;
}

interface MetricsData {
  services: ServiceHealth[];
  total_requests: number;
  total_errors: number;
  active_connections: number;
  avg_latency_ms: number;
  requests_per_second: number;
  error_rate: number;
  uptime_seconds: number;
  scaling_events: ScalingEvent[];
  instance_distribution: Record<string, number>;
}

interface K8sPod {
  name: string;
  app: string;
  status: string;
  ready: boolean;
  restarts: number;
  ip: string;
  node: string;
}

interface K8sHpa {
  name: string;
  min_replicas: number;
  max_replicas: number;
  current_replicas: number;
  desired_replicas: number;
  cpu_utilization: number | null;
}

interface K8sNode {
  name: string;
  status: string;
  cpu_capacity: string;
  memory_capacity: string;
}

interface K8sData {
  cluster: string;
  pods: K8sPod[];
  hpas: K8sHpa[];
  nodes: K8sNode[];
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className={`inline-block h-3 w-3 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`} />
  );
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

export default function ScalingPage() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [k8s, setK8s] = useState<K8sData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [mRes, kRes] = await Promise.all([
        fetch(METRICS_URL),
        fetch(K8S_URL),
      ]);
      if (mRes.ok) setMetrics(await mRes.json());
      if (kRes.ok) setK8s(await kRes.json());
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch");
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 3000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const podsByApp: Record<string, K8sPod[]> = {};
  (k8s?.pods ?? []).forEach((p) => {
    (podsByApp[p.app] ??= []).push(p);
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Kubernetes Scaling Dashboard</h1>
          <p className="text-sm text-gray-500">
            Cluster: <span className="font-mono">{k8s?.cluster ?? "connecting..."}</span>
            {" "}&bull; Polling every 3s
          </p>
        </div>
        <div className="text-right text-xs text-gray-400">
          {lastUpdated && <span>Updated: {lastUpdated.toLocaleTimeString()}</span>}
          {error && <span className="ml-2 text-red-500">{error}</span>}
        </div>
      </div>

      {/* Cluster Overview */}
      {k8s && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Cluster Nodes</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {k8s.nodes.map((node) => (
              <div key={node.name} className="rounded-lg border bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono font-semibold text-sm">{node.name}</span>
                  <StatusDot ok={node.status === "Ready"} />
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                  <div>CPU: <span className="font-mono">{node.cpu_capacity} cores</span></div>
                  <div>Memory: <span className="font-mono">{node.memory_capacity}</span></div>
                  <div>Status: <span className="font-semibold text-green-700">{node.status}</span></div>
                  <div>Pods: <span className="font-mono">{k8s.pods.length}</span></div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* HPA Auto-Scaling */}
      {k8s && k8s.hpas.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Horizontal Pod Autoscaler (HPA)</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {k8s.hpas.map((hpa) => {
              const pct = hpa.cpu_utilization ?? 0;
              const scaling = hpa.desired_replicas > hpa.current_replicas;
              return (
                <div key={hpa.name} className={`rounded-lg border bg-white p-4 shadow-sm ${scaling ? "border-green-500 ring-1 ring-green-200" : ""}`}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-semibold">{hpa.name}</span>
                    {scaling && (
                      <span className="rounded bg-green-100 text-green-800 px-2 py-0.5 text-xs font-bold animate-pulse">
                        SCALING UP
                      </span>
                    )}
                  </div>
                  {/* Replica gauge */}
                  <div className="flex items-center gap-3 mb-3">
                    <div className="flex gap-1">
                      {Array.from({ length: hpa.max_replicas }).map((_, i) => (
                        <div
                          key={i}
                          className={`h-8 w-6 rounded ${
                            i < hpa.current_replicas
                              ? "bg-blue-500"
                              : i < hpa.desired_replicas
                              ? "bg-blue-200 animate-pulse"
                              : "bg-gray-100"
                          }`}
                          title={i < hpa.current_replicas ? "Running" : i < hpa.desired_replicas ? "Scaling" : "Available"}
                        />
                      ))}
                    </div>
                    <span className="text-sm font-mono">
                      {hpa.current_replicas}/{hpa.max_replicas}
                    </span>
                  </div>
                  {/* CPU bar */}
                  <div className="mb-1">
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>CPU Utilization</span>
                      <span className="font-mono">{pct != null ? `${pct}%` : "N/A"} / 50% target</span>
                    </div>
                    <div className="h-3 rounded bg-gray-100 overflow-hidden">
                      <div
                        className={`h-full rounded transition-all duration-700 ${
                          pct > 80 ? "bg-red-500" : pct > 50 ? "bg-amber-500" : "bg-green-500"
                        }`}
                        style={{ width: `${Math.min(pct ?? 0, 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-2">
                    <span>Min: {hpa.min_replicas}</span>
                    <span>Max: {hpa.max_replicas}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Pods */}
      {k8s && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Pods ({k8s.pods.length})</h2>
          <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-2 text-left">Pod</th>
                  <th className="px-4 py-2 text-left">App</th>
                  <th className="px-4 py-2 text-center">Status</th>
                  <th className="px-4 py-2 text-center">Ready</th>
                  <th className="px-4 py-2 text-center">Restarts</th>
                  <th className="px-4 py-2 text-left">IP</th>
                </tr>
              </thead>
              <tbody>
                {k8s.pods.map((pod) => (
                  <tr key={pod.name} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{pod.name}</td>
                    <td className="px-4 py-2">
                      <span className="rounded bg-blue-100 text-blue-800 px-2 py-0.5 text-xs font-medium">{pod.app}</span>
                    </td>
                    <td className="px-4 py-2 text-center">
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${
                        pod.status === "Running" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
                      }`}>{pod.status}</span>
                    </td>
                    <td className="px-4 py-2 text-center">
                      <StatusDot ok={pod.ready} />
                    </td>
                    <td className="px-4 py-2 text-center font-mono">{pod.restarts}</td>
                    <td className="px-4 py-2 font-mono text-xs text-gray-500">{pod.ip}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Service Health */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Service Health (Host)</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(metrics?.services ?? []).map((svc) => (
            <div key={svc.name} className="rounded-lg border bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-sm">{svc.name}</span>
                <StatusDot ok={svc.status === "healthy"} />
              </div>
              <p className="text-xs text-gray-400 mb-1">{svc.url}</p>
              <div className="flex justify-between text-xs">
                <span>Response: <span className="font-mono">{svc.response_time_ms > 0 ? `${svc.response_time_ms}ms` : "--"}</span></span>
                <span>Uptime: <span className="font-mono">{svc.uptime_seconds > 0 ? formatUptime(svc.uptime_seconds) : "--"}</span></span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Live Metrics */}
      {metrics && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Live Traffic Metrics</h2>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard label="Active Connections" value={`${metrics.active_connections}`} />
            <MetricCard label="Requests/sec" value={`${metrics.requests_per_second}`} />
            <MetricCard label="Avg Latency" value={`${metrics.avg_latency_ms}ms`} />
            <MetricCard label="Total Requests" value={metrics.total_requests.toLocaleString()} />
          </div>
        </section>
      )}
    </div>
  );
}

function MetricCard({ label, value, alert = false }: { label: string; value: string; alert?: boolean }) {
  return (
    <div className={`rounded-lg border bg-white p-4 shadow-sm ${alert ? "border-red-500" : ""}`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-xl font-bold font-mono ${alert ? "text-red-500" : ""}`}>{value}</p>
    </div>
  );
}
