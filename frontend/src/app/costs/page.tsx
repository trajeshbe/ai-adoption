"use client";

import { DollarSign, TrendingUp, Activity } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCosts } from "@/lib/hooks/useCosts";
import { CostChart } from "@/components/costs/CostChart";

export default function CostsPage() {
  const { summary, costs, loading } = useCosts();

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2">
          <DollarSign className="h-6 w-6" />
          <h1 className="text-3xl font-bold tracking-tight">Cost Tracking</h1>
        </div>
        <p className="text-muted-foreground mt-1">
          Monitor inference costs and resource usage.
        </p>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Loading cost data...</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Cost
                </CardTitle>
                <DollarSign className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  ${summary?.totalCostUsd.toFixed(4) ?? "—"}
                </div>
                <CardDescription>
                  Period: {summary?.period ?? "—"}
                </CardDescription>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Inferences
                </CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {summary?.totalInferences ?? "—"}
                </div>
                <CardDescription>Requests processed</CardDescription>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Avg Cost / Inference
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  ${summary?.avgCostPerInference.toFixed(6) ?? "—"}
                </div>
                <Badge variant="secondary" className="mt-1">
                  per request
                </Badge>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Cost Over Time</CardTitle>
              <CardDescription>
                Inference cost trends for the current period.
              </CardDescription>
            </CardHeader>
            <CardContent className="min-h-[300px]">
              <CostChart costs={costs} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
