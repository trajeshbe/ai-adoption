"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Wrench } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ToolCall } from "@/types";

interface ToolCallCardProps {
  toolCall: ToolCall;
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  let formattedArgs: string;
  try {
    formattedArgs = JSON.stringify(JSON.parse(toolCall.arguments), null, 2);
  } catch {
    formattedArgs = toolCall.arguments;
  }

  return (
    <Card className="mt-2 overflow-hidden border-border/50">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "flex w-full items-center gap-2 px-3 py-2 text-left text-sm",
          "hover:bg-muted/50 transition-colors",
        )}
      >
        {expanded ? (
          <ChevronDown className="h-4 w-4 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0" />
        )}
        <Wrench className="h-4 w-4 shrink-0 text-muted-foreground" />
        <Badge variant="secondary" className="font-mono text-xs">
          {toolCall.toolName}
        </Badge>
      </button>

      {expanded && (
        <div className="border-t px-3 py-2 space-y-2 text-sm">
          <div>
            <p className="font-medium text-muted-foreground mb-1">Arguments</p>
            <pre className="rounded bg-muted p-2 text-xs overflow-x-auto whitespace-pre-wrap">
              {formattedArgs}
            </pre>
          </div>
          {toolCall.result && (
            <div>
              <p className="font-medium text-muted-foreground mb-1">Result</p>
              <pre className="rounded bg-muted p-2 text-xs overflow-x-auto whitespace-pre-wrap">
                {toolCall.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
