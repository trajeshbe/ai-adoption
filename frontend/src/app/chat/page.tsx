"use client";

import { useState, useRef, useEffect } from "react";

const GRAPHQL_URL =
  process.env.NEXT_PUBLIC_GRAPHQL_URL || "http://localhost:8050/graphql";

const AGENTS = [
  {
    id: "00000000-0000-0000-0000-000000000001",
    name: "Movie Quiz Bot",
    type: "QUIZ",
    icon: "🎬",
    placeholder: "Ask about movies...",
    systemPrompt:
      "You are a fun movie trivia quiz bot. When the user asks about movies, provide interesting facts and trivia. Engage them with quiz-style questions.",
    tools: [],
    config: {
      model: "qwen2.5:1.5b",
      provider: "Ollama",
      endpoint: "http://aiadopt-ollama:11434/v1",
    },
  },
  {
    id: "00000000-0000-0000-0000-000000000002",
    name: "Weather Agent",
    type: "WEATHER",
    icon: "🌤️",
    placeholder: "Ask about the weather in any city...",
    systemPrompt:
      "You are a helpful weather assistant. When the user asks about weather in a city, use the get_weather tool to fetch real-time data and present it in a clear, friendly format.",
    tools: [
      {
        name: "get_weather",
        description: "Get current weather conditions for a city",
        api: "https://wttr.in/{city}?format=j1",
        fallback: "Mock data (London, New York, Tokyo preloaded)",
        parameters: { city: { type: "string", required: true, description: "City name" } },
        returns: {
          city: "string",
          temperature: "string (e.g. 19°C)",
          condition: "string (e.g. Sunny)",
          humidity: "string (e.g. 68%)",
          wind: "string (e.g. 11 km/h NE)",
        },
      },
    ],
    config: {
      model: "qwen2.5:1.5b",
      provider: "Ollama",
      endpoint: "http://aiadopt-ollama:11434/v1",
      weatherApi: "https://wttr.in",
      timeout: "5s",
      fallbackMode: "Mock data when API unreachable",
    },
  },
  {
    id: "00000000-0000-0000-0000-000000000003",
    name: "Document Assistant",
    type: "RAG",
    icon: "📄",
    placeholder: "Ask questions about uploaded documents...",
    systemPrompt:
      "You are a document assistant. Use the search_documents tool to find relevant information from the uploaded knowledge base, then answer the user's question based on the retrieved context.",
    tools: [
      {
        name: "search_documents",
        description: "Search uploaded documents using semantic similarity",
        api: "http://document-service:8051/documents/search",
        fallback: "Returns empty results if no documents uploaded",
        parameters: { query: { type: "string", required: true, description: "Search query" }, top_k: { type: "integer", required: false, description: "Number of results (default: 5)" } },
        returns: { chunks: "array of { content, score, document_id }" },
      },
    ],
    config: {
      model: "qwen2.5:1.5b",
      provider: "Ollama",
      endpoint: "http://aiadopt-ollama:11434/v1",
      vectorDb: "PostgreSQL + pgvector",
      embeddingDim: 384,
      distanceMetric: "cosine",
      documentStore: "MinIO (S3-compatible)",
    },
  },
];

interface Message {
  id: string;
  role: "USER" | "ASSISTANT";
  content: string;
  costUsd?: number;
  latencyMs?: number;
  toolCalls?: { toolName: string; arguments: string; result: string }[];
}

function makeUUID() {
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c) =>
    (+c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))).toString(16)
  );
}

export default function ChatPage() {
  const [agentIdx, setAgentIdx] = useState(0);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(makeUUID);
  const [showConfig, setShowConfig] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const agent = AGENTS[agentIdx];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const switchAgent = (idx: number) => {
    setAgentIdx(idx);
    setMessages([]);
    setSessionId(makeUUID());
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "USER", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(GRAPHQL_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: `mutation SendMessage($input: SendMessageInput!) {
            sendMessage(input: $input) {
              id role content costUsd latencyMs
              toolCalls { toolName arguments result }
            }
          }`,
          variables: {
            input: { agentId: agent.id, sessionId, content: text },
          },
        }),
      });
      const json = await res.json();
      if (json.errors) throw new Error(json.errors[0].message);
      const reply = json.data.sendMessage;
      setMessages((prev) => [
        ...prev,
        {
          id: reply.id,
          role: "ASSISTANT",
          content: reply.content,
          costUsd: reply.costUsd,
          latencyMs: reply.latencyMs,
          toolCalls: reply.toolCalls,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { id: Date.now().toString(), role: "ASSISTANT", content: `Error: ${err instanceof Error ? err.message : String(err)}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-10rem)]">
      {/* Main chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Agent Selector */}
        <div className="flex items-center gap-2 mb-4">
          {AGENTS.map((a, idx) => (
            <button
              key={a.id}
              onClick={() => switchAgent(idx)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                idx === agentIdx
                  ? "bg-blue-600 text-white shadow"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              <span>{a.icon}</span>
              <span className="hidden sm:inline">{a.name}</span>
            </button>
          ))}
          <button
            onClick={() => setShowConfig(!showConfig)}
            className={`ml-auto flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              showConfig ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            <span>&#9881;</span>
            <span className="hidden sm:inline">Config</span>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto rounded-lg border bg-white p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-center text-gray-400 pt-8">
              {agent.icon} {agent.name} — {agent.placeholder}
            </p>
          )}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "USER" ? "justify-end" : "justify-start"}`}
            >
              <div className="max-w-[75%] space-y-2">
                <div
                  className={`rounded-2xl px-4 py-2 text-sm ${
                    msg.role === "USER"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-900"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>

                {msg.toolCalls && msg.toolCalls.length > 0 && (
                  <div className="space-y-1">
                    {msg.toolCalls.map((tc, i) => (
                      <div key={i} className="rounded-lg border bg-amber-50 px-3 py-2 text-xs">
                        <p className="font-semibold text-amber-800">Tool: {tc.toolName}</p>
                        <p className="text-gray-600 mt-1">Args: {tc.arguments}</p>
                        <p className="text-gray-800 mt-1">Result: {tc.result}</p>
                      </div>
                    ))}
                  </div>
                )}

                {msg.role === "ASSISTANT" && (msg.costUsd || msg.latencyMs) && (
                  <p className="text-xs text-gray-400">
                    {msg.latencyMs ? `${Math.round(msg.latencyMs)}ms` : ""}
                    {msg.costUsd ? ` · $${msg.costUsd.toFixed(4)}` : ""}
                  </p>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl px-4 py-2 text-sm text-gray-500 animate-pulse">
                {agent.icon} Thinking...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex gap-2 mt-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder={agent.placeholder}
            disabled={loading}
            className="flex-1 rounded-lg border px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>

      {/* Config Panel */}
      {showConfig && (
        <div className="w-80 shrink-0 overflow-y-auto rounded-lg border bg-white p-4 space-y-4 text-sm">
          <div className="flex items-center justify-between border-b pb-2">
            <h2 className="font-bold text-base">{agent.icon} {agent.name}</h2>
            <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-mono text-blue-700">{agent.type}</span>
          </div>

          {/* System Prompt */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-1">System Prompt</h3>
            <p className="rounded bg-gray-50 p-2 text-xs text-gray-600 leading-relaxed">{agent.systemPrompt}</p>
          </div>

          {/* LLM Config */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-1">LLM Configuration</h3>
            <div className="rounded bg-gray-50 p-2 space-y-1">
              {Object.entries(agent.config).map(([key, val]) => (
                <div key={key} className="flex justify-between text-xs">
                  <span className="text-gray-500">{key}</span>
                  <span className="font-mono text-gray-800 text-right max-w-[60%] truncate" title={String(val)}>{String(val)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Tools */}
          {agent.tools.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-700 mb-1">Tools ({agent.tools.length})</h3>
              {agent.tools.map((tool) => (
                <div key={tool.name} className="rounded border bg-gray-50 p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-amber-600 font-bold text-xs">&#9881;</span>
                    <span className="font-mono font-semibold text-xs">{tool.name}</span>
                  </div>
                  <p className="text-xs text-gray-600">{tool.description}</p>

                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">API Endpoint</p>
                    <p className="font-mono text-xs bg-white rounded border px-2 py-1 text-blue-700 break-all">{tool.api}</p>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Fallback</p>
                    <p className="text-xs text-gray-600">{tool.fallback}</p>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Parameters</p>
                    <div className="bg-white rounded border p-2 space-y-1">
                      {Object.entries(tool.parameters).map(([param, info]) => (
                        <div key={param} className="flex items-start gap-2 text-xs">
                          <span className="font-mono text-purple-700 shrink-0">{param}</span>
                          <span className="text-gray-400">:</span>
                          <span className="text-gray-600">
                            {(info as { type: string; description: string; required?: boolean }).type}
                            {(info as { required?: boolean }).required && <span className="text-red-500 ml-1">*</span>}
                            <span className="text-gray-400 ml-1">— {(info as { description: string }).description}</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Response Schema</p>
                    <pre className="bg-white rounded border p-2 text-xs text-gray-700 overflow-x-auto">
{JSON.stringify(tool.returns, null, 2)}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          )}

          {agent.tools.length === 0 && (
            <div>
              <h3 className="font-semibold text-gray-700 mb-1">Tools</h3>
              <p className="text-xs text-gray-400 italic">No tools — direct LLM conversation</p>
            </div>
          )}

          {/* Architecture */}
          <div>
            <h3 className="font-semibold text-gray-700 mb-1">Request Flow</h3>
            <div className="rounded bg-gray-50 p-2 font-mono text-xs text-gray-600 space-y-0.5">
              <p>Browser</p>
              <p className="text-gray-400 pl-2">&#8595; GraphQL mutation</p>
              <p className="pl-2">Gateway (:8050)</p>
              <p className="text-gray-400 pl-4">&#8595; HTTP POST /agents/execute</p>
              <p className="pl-4">Agent Engine (:8053)</p>
              <p className="text-gray-400 pl-6">&#8595; LangGraph StateGraph</p>
              <p className="pl-6">Ollama (:20434)</p>
              <p className="text-gray-400 pl-8">&#8595; qwen2.5:1.5b</p>
              {agent.tools.length > 0 && (
                <>
                  <p className="text-gray-400 pl-6">&#8595; tool calls</p>
                  <p className="pl-6">{agent.tools.map(t => t.name).join(", ")}</p>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
