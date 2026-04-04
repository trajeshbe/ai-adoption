"use client";

import { Bot, User, DollarSign, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";
import { ToolCallCard } from "./ToolCallCard";

interface MessageBubbleProps {
  message: ChatMessage;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "USER";

  return (
    <div
      className={cn("flex w-full gap-2", isUser ? "justify-end" : "justify-start")}
    >
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
          <Bot className="h-4 w-4" />
        </div>
      )}

      <div className={cn("max-w-[75%] space-y-1", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2 text-sm leading-relaxed",
            isUser
              ? "bg-blue-600 text-white rounded-br-sm"
              : "bg-muted text-foreground rounded-bl-sm",
          )}
        >
          {message.content}
        </div>

        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-1">
            {message.toolCalls.map((tc, idx) => (
              <ToolCallCard key={`${tc.toolName}-${idx}`} toolCall={tc} />
            ))}
          </div>
        )}

        <div
          className={cn(
            "flex items-center gap-2 text-xs text-muted-foreground",
            isUser && "justify-end",
          )}
        >
          <span>{formatTimestamp(message.createdAt)}</span>

          {message.costUsd != null && (
            <Badge variant="outline" className="gap-1 text-xs py-0">
              <DollarSign className="h-3 w-3" />
              {message.costUsd.toFixed(4)}
            </Badge>
          )}

          {message.latencyMs != null && (
            <Badge variant="outline" className="gap-1 text-xs py-0">
              <Clock className="h-3 w-3" />
              {message.latencyMs}ms
            </Badge>
          )}
        </div>
      </div>

      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600">
          <User className="h-4 w-4 text-white" />
        </div>
      )}
    </div>
  );
}
