export type AgentType = "WEATHER" | "QUIZ" | "RAG" | "CUSTOM";
export type MessageRole = "USER" | "ASSISTANT" | "SYSTEM" | "TOOL";

export interface Agent {
  id: string;
  name: string;
  agentType: AgentType;
  instructions: string;
  createdAt: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  toolCalls?: ToolCall[];
  costUsd?: number;
  latencyMs?: number;
  createdAt: string;
}

export interface ToolCall {
  toolName: string;
  arguments: string;
  result: string;
}

export interface ChatSession {
  id: string;
  agentId: string;
  messages: ChatMessage[];
  createdAt: string;
}

export interface Document {
  id: string;
  filename: string;
  contentType: string;
  chunkCount: number;
  createdAt: string;
}

export interface InferenceCost {
  totalCostUsd: number;
  promptTokens: number;
  completionTokens: number;
  model: string;
}

export interface CostSummary {
  totalCostUsd: number;
  totalInferences: number;
  avgCostPerInference: number;
  period: string;
}
