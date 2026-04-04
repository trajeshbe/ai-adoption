"use client";

import ReactFlow, {
  Background,
  Controls,
  type Node,
  type Edge,
} from "reactflow";
import "reactflow/dist/style.css";

const nodeColors: Record<string, string> = {
  input: "#3b82f6",
  router: "#8b5cf6",
  tool: "#f59e0b",
  llm: "#10b981",
  output: "#6366f1",
};

const makeNodeStyle = (type: string) => ({
  background: nodeColors[type] ?? "#6b7280",
  color: "#fff",
  border: "none",
  borderRadius: 8,
  padding: "8px 16px",
  fontSize: 13,
  fontWeight: 600,
});

const nodes: Node[] = [
  {
    id: "user-input",
    type: "input",
    data: { label: "User Input" },
    position: { x: 250, y: 0 },
    style: makeNodeStyle("input"),
  },
  {
    id: "agent-router",
    data: { label: "Agent Router" },
    position: { x: 230, y: 100 },
    style: makeNodeStyle("router"),
  },
  {
    id: "weather-tool",
    data: { label: "Weather Tool" },
    position: { x: 0, y: 220 },
    style: makeNodeStyle("tool"),
  },
  {
    id: "quiz-logic",
    data: { label: "Quiz Logic" },
    position: { x: 220, y: 220 },
    style: makeNodeStyle("tool"),
  },
  {
    id: "rag-retrieval",
    data: { label: "RAG Retrieval" },
    position: { x: 440, y: 220 },
    style: makeNodeStyle("tool"),
  },
  {
    id: "llm",
    data: { label: "LLM" },
    position: { x: 250, y: 340 },
    style: makeNodeStyle("llm"),
  },
  {
    id: "response",
    type: "output",
    data: { label: "Response" },
    position: { x: 250, y: 440 },
    style: makeNodeStyle("output"),
  },
];

const edges: Edge[] = [
  { id: "e-input-router", source: "user-input", target: "agent-router", animated: true },
  { id: "e-router-weather", source: "agent-router", target: "weather-tool" },
  { id: "e-router-quiz", source: "agent-router", target: "quiz-logic" },
  { id: "e-router-rag", source: "agent-router", target: "rag-retrieval" },
  { id: "e-weather-llm", source: "weather-tool", target: "llm" },
  { id: "e-quiz-llm", source: "quiz-logic", target: "llm" },
  { id: "e-rag-llm", source: "rag-retrieval", target: "llm" },
  { id: "e-llm-response", source: "llm", target: "response", animated: true },
];

export function DagViewer() {
  return (
    <div className="h-[560px] w-full rounded-lg border bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
