"use client";

import { use } from "react";
import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = use(params);

  return (
    <div className="h-full">
      <ChatWindow sessionId={sessionId} />
    </div>
  );
}
