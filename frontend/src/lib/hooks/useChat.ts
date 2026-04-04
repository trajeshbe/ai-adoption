"use client";

import { useState, useCallback } from "react";
import { useMutation } from "urql";
import { SEND_MESSAGE } from "@/lib/graphql/mutations";
import type { ChatMessage } from "@/types";

// Default agent UUID for the movie quiz bot
const DEFAULT_AGENT_ID = "00000000-0000-0000-0000-000000000001";

export function useChat(sessionId: string) {
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const [, executeSend] = useMutation(SEND_MESSAGE);

  const sendMessage = useCallback(
    async (content: string) => {
      // Add user message immediately for responsive UI
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "USER",
        content,
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      try {
        const result = await executeSend({
          input: {
            agentId: DEFAULT_AGENT_ID,
            sessionId,
            content,
          },
        });
        if (result.error) throw result.error;
        const assistantMsg = result.data?.sendMessage as ChatMessage;
        if (assistantMsg) {
          setMessages((prev) => [...prev, assistantMsg]);
        }
        return assistantMsg;
      } catch (err) {
        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "ASSISTANT",
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
          createdAt: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, executeSend]
  );

  return {
    messages,
    session: null,
    loading: false,
    isLoading,
    error: null,
    sendMessage,
  };
}
