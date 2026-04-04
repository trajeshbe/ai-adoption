"use client";

import Link from "next/link";
import { Bot, Calendar } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { Agent, AgentType } from "@/types";

const agentTypeBadgeColor: Record<AgentType, string> = {
  WEATHER: "bg-blue-100 text-blue-800 hover:bg-blue-100",
  QUIZ: "bg-purple-100 text-purple-800 hover:bg-purple-100",
  RAG: "bg-green-100 text-green-800 hover:bg-green-100",
  CUSTOM: "bg-gray-100 text-gray-800 hover:bg-gray-100",
};

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const formattedDate = new Date(agent.createdAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Link href={`/agents/${agent.id}`}>
      <Card className="h-full transition-shadow hover:shadow-md cursor-pointer">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Bot className="h-5 w-5" />
              {agent.name}
            </CardTitle>
            <Badge className={cn("text-xs font-medium", agentTypeBadgeColor[agent.agentType])}>
              {agent.agentType}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <CardDescription className="line-clamp-2">
            {agent.instructions || "No instructions provided."}
          </CardDescription>
        </CardContent>
        <CardFooter>
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            {formattedDate}
          </p>
        </CardFooter>
      </Card>
    </Link>
  );
}
