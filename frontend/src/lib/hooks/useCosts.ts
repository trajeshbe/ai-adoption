"use client";

import { useQuery } from "urql";
import { GET_COST_SUMMARY, LIST_INFERENCE_COSTS } from "@/lib/graphql/queries";
import type { CostSummary, InferenceCost } from "@/types";

export function useCosts(period: string = "30d", limit: number = 50) {
  const [{ data: summaryData, fetching: summaryFetching, error: summaryError }] =
    useQuery<{ costSummary: CostSummary }>({
      query: GET_COST_SUMMARY,
      variables: { period },
    });

  const [{ data: costsData, fetching: costsFetching, error: costsError }] =
    useQuery<{ inferenceCosts: InferenceCost[] }>({
      query: LIST_INFERENCE_COSTS,
      variables: { limit },
    });

  return {
    summary: summaryData?.costSummary,
    costs: costsData?.inferenceCosts ?? [],
    loading: summaryFetching || costsFetching,
    error: summaryError?.message || costsError?.message,
  };
}
