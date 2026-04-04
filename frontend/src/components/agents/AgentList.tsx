"use client";

import Link from "next/link";
import { AlertCircle, Bot, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAgents } from "@/lib/hooks/useAgents";
import { AgentCard } from "./AgentCard";

function AgentListSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="h-48 animate-pulse">
          <CardContent className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="h-5 w-32 rounded bg-muted" />
              <div className="h-5 w-16 rounded bg-muted" />
            </div>
            <div className="space-y-2">
              <div className="h-4 w-full rounded bg-muted" />
              <div className="h-4 w-2/3 rounded bg-muted" />
            </div>
            <div className="h-3 w-24 rounded bg-muted" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function AgentList() {
  const { agents, loading, error } = useAgents();

  if (loading) {
    return <AgentListSkeleton />;
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="flex items-center gap-3 p-6 text-destructive">
          <AlertCircle className="h-5 w-5" />
          <p>Failed to load agents: {error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!agents || agents.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-4 p-12 text-center">
          <Bot className="h-12 w-12 text-muted-foreground" />
          <div>
            <h3 className="text-lg font-semibold">No agents yet</h3>
            <p className="text-sm text-muted-foreground">
              Get started by creating your first AI agent.
            </p>
          </div>
          <Button asChild>
            <Link href="/agents/new">
              <Plus className="mr-2 h-4 w-4" />
              Create your first agent
            </Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}
