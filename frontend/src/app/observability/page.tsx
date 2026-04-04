"use client";

import { Activity, CheckCircle, AlertTriangle, ExternalLink } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const statusCards = [
  {
    title: "Traces",
    description: "Distributed tracing via Grafana Tempo",
    status: "healthy" as const,
    url: "/grafana/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Tempo%22%5D",
  },
  {
    title: "Logs",
    description: "Centralized logs via Grafana Loki",
    status: "healthy" as const,
    url: "/grafana/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Loki%22%5D",
  },
  {
    title: "Metrics",
    description: "Prometheus metrics via Grafana Mimir",
    status: "healthy" as const,
    url: "/grafana/explore?orgId=1&left=%5B%22now-1h%22,%22now%22,%22Mimir%22%5D",
  },
];

function StatusIcon({ status }: { status: "healthy" | "degraded" | "down" }) {
  switch (status) {
    case "healthy":
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case "degraded":
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    case "down":
      return <AlertTriangle className="h-4 w-4 text-red-500" />;
  }
}

export default function ObservabilityPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <Activity className="h-6 w-6" />
          <h1 className="text-3xl font-bold tracking-tight">Observability</h1>
        </div>
        <p className="text-muted-foreground mt-1">
          Traces, logs, and metrics for the platform.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {statusCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {card.title}
              </CardTitle>
              <StatusIcon status={card.status} />
            </CardHeader>
            <CardContent>
              <CardDescription>{card.description}</CardDescription>
              <Badge variant="secondary" className="mt-2">
                {card.status}
              </Badge>
            </CardContent>
            <CardFooter>
              <Button variant="outline" size="sm" asChild>
                <a href={card.url} target="_blank" rel="noopener noreferrer">
                  Open
                  <ExternalLink className="ml-2 h-3 w-3" />
                </a>
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Grafana Dashboard</CardTitle>
          <CardDescription>
            Embedded overview dashboard. Ensure Grafana is running and accessible.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative w-full overflow-hidden rounded-md border bg-muted" style={{ height: 500 }}>
            <iframe
              src="/grafana/d/platform-overview/platform-overview?orgId=1&kiosk"
              className="absolute inset-0 h-full w-full"
              title="Grafana Dashboard"
              allowFullScreen
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
