"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation } from "urql";
import { LIST_CHAT_SESSIONS } from "@/lib/graphql/queries";
import { SEND_MESSAGE } from "@/lib/graphql/mutations";
import type { ChatMessage, ChatSession } from "@/types";

export function useChat(sessionId: string) {
  const [isLoading, setIsLoading] = useState(false);

  const [{ data, fetching, error }, reexecute] = useQuery<{
    chatSessions: ChatSession[];
  }>({
    query: LIST_CHAT_SESSIONS,
  });

  const [, executeSend] = useMutation(SEND_MESSAGE);

  const session = data?.chatSessions?.find((s) => s.id === sessionId);
  const messages = session?.messages ?? [];

  const sendMessage = useCallback(
    async (content: string) => {
      setIsLoading(true);
      try {
        const result = await executeSend({
          input: { sessionId, content },
        });
        if (result.error) throw result.error;
        reexecute({ requestPolicy: "network-only" });
        return result.data?.sendMessage as ChatMessage;
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, executeSend, reexecute]
  );

  return {
    messages,
    session,
    loading: fetching,
    isLoading,
    error: error?.message,
    sendMessage,
  };
}
