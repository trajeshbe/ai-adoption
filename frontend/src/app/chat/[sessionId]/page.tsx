"use client";

import { useParams } from "next/navigation";
import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatSessionPage() {
  const params = useParams<{ sessionId: string }>();

  return (
    <div className="h-full">
      <ChatWindow sessionId={params.sessionId} />
    </div>
  );
}
