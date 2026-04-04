"use client";

import { DollarSign } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { InferenceCost } from "@/types";

const MODEL_COLORS: Record<string, string> = {
  "gpt-4": "bg-violet-500",
  "gpt-3.5-turbo": "bg-sky-500",
  "claude-3-opus": "bg-amber-500",
  "claude-3-sonnet": "bg-orange-500",
  "llama-3": "bg-emerald-500",
  "mistral": "bg-rose-500",
};

function getModelColor(model: string): string {
  const key = Object.keys(MODEL_COLORS).find((k) =>
    model.toLowerCase().includes(k)
  );
  return key ? MODEL_COLORS[key] : "bg-primary";
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

function formatTokens(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k`;
  return count.toString();
}

interface CostChartProps {
  costs: InferenceCost[];
}

export function CostChart({ costs }: CostChartProps) {
  if (costs.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-2 py-12">
          <DollarSign className="h-10 w-10 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No inference cost data yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  const maxCost = Math.max(...costs.map((c) => c.totalCostUsd));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Inference Costs by Model</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {costs.map((cost, i) => {
          const widthPct =
            maxCost > 0 ? (cost.totalCostUsd / maxCost) * 100 : 0;
          const colorClass = getModelColor(cost.model);

          return (
            <div key={`${cost.model}-${i}`} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium truncate">{cost.model}</span>
                <span className="shrink-0 text-muted-foreground">
                  {formatCost(cost.totalCostUsd)}
                </span>
              </div>

              <div className="h-6 w-full overflow-hidden rounded-md bg-muted">
                <div
                  className={cn("h-full rounded-md transition-all", colorClass)}
                  style={{ width: `${Math.max(widthPct, 2)}%` }}
                />
              </div>

              <div className="flex gap-4 text-xs text-muted-foreground">
                <span>
                  Prompt: {formatTokens(cost.promptTokens)} tokens
                </span>
                <span>
                  Completion: {formatTokens(cost.completionTokens)} tokens
                </span>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
