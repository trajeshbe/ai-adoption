"use client";

import { cn } from "@/lib/utils";

interface InferenceCostBadgeProps {
  cost: number;
}

export function InferenceCostBadge({ cost }: InferenceCostBadgeProps) {
  const formatted = `$${cost.toFixed(4)}`;

  const colorClass =
    cost < 0.01
      ? "bg-green-100 text-green-700 border-green-200"
      : cost < 0.1
        ? "bg-yellow-100 text-yellow-700 border-yellow-200"
        : "bg-red-100 text-red-700 border-red-200";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold",
        colorClass
      )}
    >
      {formatted}
    </span>
  );
}
