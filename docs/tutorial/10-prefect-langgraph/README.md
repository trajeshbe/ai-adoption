# Tutorial 10: Prefect 3 + LangGraph — Agent Orchestration

> **Objective:** Learn to build AI agent workflows using LangGraph state machines orchestrated by Prefect pipelines.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Prefect Core Concepts](#2-prefect-core-concepts)
3. [LangGraph Core Concepts](#3-langgraph-core-concepts)
4. [Installation & Setup](#4-installation--setup)
5. [Exercises](#5-exercises)
6. [How It's Used in Our Project](#6-how-its-used-in-our-project)
7. [Best Practices & Further Reading](#7-best-practices--further-reading)

---

## 1. Introduction

### What is Workflow Orchestration?

Orchestration manages the execution of multi-step pipelines: retry on failure, schedule runs, track history, handle dependencies.

### Prefect + LangGraph: How They Work Together

- **LangGraph** defines *what* the agent does (state machine, tool calls, decisions)
- **Prefect** manages *how/when* it runs (scheduling, retries, monitoring, deployment)

```
Prefect Flow:
  ├── Task: Validate input
  ├── Task: Run LangGraph agent    ← The AI logic lives here
  ├── Task: Store results
  └── Task: Send notification
```

---

## 2. Prefect Core Concepts

### Flows and Tasks

```python
from prefect import flow, task

@task(retries=3, retry_delay_seconds=10)
def fetch_data(url: str) -> dict:
    """Tasks are the units of work. They can retry, cache, and log."""
    import httpx
    return httpx.get(url).json()

@task
def process_data(data: dict) -> str:
    return f"Processed {len(data)} items"

@flow(name="data-pipeline", log_prints=True)
def my_pipeline(url: str):
    """Flows orchestrate tasks. They track state and handle errors."""
    data = fetch_data(url)
    result = process_data(data)
    print(result)
    return result
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Retries** | Automatically retry failed tasks |
| **Caching** | Cache task results to avoid re-computation |
| **Scheduling** | Run flows on a cron schedule |
| **Deployments** | Package and deploy flows to run anywhere |
| **Artifacts** | Store results, metrics, and outputs |
| **Automations** | Trigger actions based on flow states |
| **Work Pools** | Route work to specific infrastructure |

---

## 3. LangGraph Core Concepts

### State Machines for AI Agents

LangGraph models agents as **graphs** where:
- **Nodes** = functions that process/modify state
- **Edges** = transitions between nodes
- **State** = shared data that flows through the graph

```
[Start] → [Analyze Query] → [Should use tools?]
                                ├── Yes → [Call Tool] → [Process Result] → [Should use tools?]
                                └── No  → [Generate Response] → [End]
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **State** | TypedDict that holds all agent data |
| **Node** | Function that takes state, returns updates |
| **Edge** | Connection between nodes |
| **Conditional Edge** | Routes based on state (if/else) |
| **Checkpoint** | Save/restore state (persistence) |
| **Human-in-the-loop** | Pause for human approval |

---

## 4. Installation & Setup

```bash
pip install prefect langgraph langchain-core langchain-openai

# Start Prefect server (UI)
prefect server start
# Open http://localhost:4200

# Or use Prefect Cloud
# prefect cloud login
```

---

## 5. Exercises

### Exercise 1: Basic Prefect Flow

```python
# exercise1.py
from prefect import flow, task, get_run_logger
from datetime import datetime
import time

@task(retries=2, retry_delay_seconds=5)
def validate_input(prompt: str) -> str:
    logger = get_run_logger()
    if len(prompt) < 3:
        raise ValueError("Prompt too short")
    logger.info(f"Validated prompt: {prompt[:50]}...")
    return prompt

@task(cache_key_fn=lambda context, params: f"embed-{hash(params['text'])}")
def generate_embedding(text: str) -> list[float]:
    """Cached — same text returns same embedding without recomputing."""
    import random
    time.sleep(0.5)  # Simulate embedding generation
    return [random.random() for _ in range(384)]

@task
def search_knowledge_base(embedding: list[float], top_k: int = 3) -> list[str]:
    return [
        "Kubernetes manages container workloads",
        "Pods are the smallest deployable units in K8s",
        "Services expose pods to network traffic",
    ][:top_k]

@task
def generate_response(prompt: str, context: list[str]) -> str:
    context_str = "\n".join(context)
    return f"Based on: {context_str}\n\nAnswer: This is a response to '{prompt}'"

@flow(name="rag-pipeline", log_prints=True)
def rag_flow(prompt: str) -> str:
    validated = validate_input(prompt)
    embedding = generate_embedding(validated)
    context = search_knowledge_base(embedding)
    response = generate_response(validated, context)
    print(f"Generated response ({len(response)} chars)")
    return response

# Run
if __name__ == "__main__":
    result = rag_flow("What is Kubernetes?")
    print(result)
```

---

### Exercise 2: Prefect Deployment with Scheduling

```python
# exercise2.py
from prefect import flow, task
from prefect.deployments import Deployment

@task
def check_model_health(endpoint: str) -> dict:
    import httpx
    try:
        r = httpx.get(f"{endpoint}/health", timeout=5)
        return {"endpoint": endpoint, "status": "healthy", "code": r.status_code}
    except Exception as e:
        return {"endpoint": endpoint, "status": "unhealthy", "error": str(e)}

@flow(name="model-health-check")
def health_check_flow():
    endpoints = [
        "http://vllm-service:8000",
        "http://llama-cpp-svc:8080",
        "http://embedding-service:8001",
    ]
    results = []
    for endpoint in endpoints:
        result = check_model_health(endpoint)
        results.append(result)
        status = "OK" if result["status"] == "healthy" else "FAIL"
        print(f"  [{status}] {endpoint}")

    unhealthy = [r for r in results if r["status"] != "healthy"]
    if unhealthy:
        print(f"WARNING: {len(unhealthy)} unhealthy endpoints!")
    return results

# Create deployment (run every 5 minutes)
if __name__ == "__main__":
    health_check_flow.serve(
        name="model-health-monitor",
        cron="*/5 * * * *",
    )
```

---

### Exercise 3: LangGraph — Simple Chatbot with Memory

```python
# exercise3.py
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

# Define state
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
    summary: str

# Define nodes
def chatbot(state: ChatState) -> dict:
    """Generate response based on messages."""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    # In production, call your LLM here
    response = f"I received your message: '{last_message}'. How can I help further?"
    return {"messages": [{"role": "assistant", "content": response}]}

def should_summarize(state: ChatState) -> str:
    """Decide if we should summarize (every 5 messages)."""
    if len(state["messages"]) > 5:
        return "summarize"
    return "respond"

def summarize(state: ChatState) -> dict:
    """Summarize conversation to keep context manageable."""
    msg_texts = [m.content for m in state["messages"][-5:]]
    summary = f"Previous conversation covered: {', '.join(msg_texts[:3])}"
    return {"summary": summary, "messages": state["messages"][-2:]}

# Build graph
graph = StateGraph(ChatState)
graph.add_node("chatbot", chatbot)
graph.add_node("summarize", summarize)

graph.set_entry_point("chatbot")
graph.add_conditional_edges("chatbot", should_summarize, {
    "summarize": "summarize",
    "respond": END,
})
graph.add_edge("summarize", END)

app = graph.compile()

# Run
result = app.invoke({
    "messages": [{"role": "user", "content": "What is Kubernetes?"}],
    "summary": "",
})
print(result["messages"][-1].content)
```

---

### Exercise 4: LangGraph Agent with Tool Calling

```python
# exercise4.py
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import json

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# Define tools
def search_docs(query: str) -> str:
    """Search the knowledge base."""
    # Simulated search results
    results = {
        "kubernetes": "Kubernetes is a container orchestration platform that automates deployment.",
        "docker": "Docker packages applications into containers for consistent environments.",
        "default": f"No specific results found for '{query}'.",
    }
    for key, value in results.items():
        if key in query.lower():
            return value
    return results["default"]

def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    try:
        result = eval(expression)  # In production, use a safe evaluator
        return str(result)
    except:
        return "Error evaluating expression"

TOOLS = {"search_docs": search_docs, "calculate": calculate}

def agent(state: AgentState) -> dict:
    """Decide whether to use a tool or respond directly."""
    last_msg = state["messages"][-1]
    content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # Simple heuristic (in production, LLM decides)
    if "search" in content.lower() or "what is" in content.lower():
        return {"messages": [AIMessage(
            content="",
            tool_calls=[{"id": "1", "name": "search_docs", "args": {"query": content}}],
        )]}
    elif any(c in content for c in "+-*/"):
        return {"messages": [AIMessage(
            content="",
            tool_calls=[{"id": "1", "name": "calculate", "args": {"expression": content}}],
        )]}
    else:
        return {"messages": [AIMessage(content=f"I can help with that: {content}")]}

def execute_tools(state: AgentState) -> dict:
    """Execute the tools the agent decided to use."""
    last_msg = state["messages"][-1]
    results = []
    for call in last_msg.tool_calls:
        tool_fn = TOOLS[call["name"]]
        result = tool_fn(**call["args"])
        results.append(ToolMessage(content=result, tool_call_id=call["id"]))
    return {"messages": results}

def should_use_tools(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "end"

# Build graph
graph = StateGraph(AgentState)
graph.add_node("agent", agent)
graph.add_node("tools", execute_tools)

graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_use_tools, {"tools": "tools", "end": END})
graph.add_edge("tools", "agent")  # After tools, go back to agent

app = graph.compile()

# Test
result = app.invoke({"messages": [HumanMessage(content="What is Kubernetes?")]})
for msg in result["messages"]:
    role = type(msg).__name__
    print(f"[{role}] {msg.content[:100]}")
```

---

### Exercise 5: Multi-Agent System

```python
# exercise5.py
from typing import Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

class ResearchState(TypedDict):
    messages: Annotated[list, add_messages]
    research: str
    draft: str
    feedback: str
    iteration: int

def researcher(state: ResearchState) -> dict:
    """Research agent — gathers information."""
    query = state["messages"][-1].content if state["messages"] else ""
    research = f"Research findings on '{query}':\n1. Key concept A\n2. Key concept B\n3. Key concept C"
    return {"research": research}

def writer(state: ResearchState) -> dict:
    """Writer agent — creates content from research."""
    research = state["research"]
    draft = f"Draft article:\n\nBased on our research:\n{research}\n\nIn conclusion, this topic is important."
    return {"draft": draft, "iteration": state.get("iteration", 0) + 1}

def reviewer(state: ResearchState) -> dict:
    """Reviewer agent — provides feedback."""
    draft = state["draft"]
    if state.get("iteration", 0) < 2:
        feedback = "Needs more detail. Please expand on concept B."
    else:
        feedback = "APPROVED — ready to publish."
    return {"feedback": feedback}

def should_revise(state: ResearchState) -> str:
    if "APPROVED" in state.get("feedback", ""):
        return "publish"
    return "revise"

# Build multi-agent graph
graph = StateGraph(ResearchState)
graph.add_node("researcher", researcher)
graph.add_node("writer", writer)
graph.add_node("reviewer", reviewer)

graph.set_entry_point("researcher")
graph.add_edge("researcher", "writer")
graph.add_edge("writer", "reviewer")
graph.add_conditional_edges("reviewer", should_revise, {
    "revise": "writer",
    "publish": END,
})

app = graph.compile()

result = app.invoke({
    "messages": [{"role": "user", "content": "Write about microservices"}],
    "research": "", "draft": "", "feedback": "", "iteration": 0,
})

print(f"Final draft (after {result['iteration']} iterations):")
print(result["draft"])
```

---

### Exercise 6: Prefect + LangGraph Integration

```python
# exercise6.py
from prefect import flow, task
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    result: str

def process_query(state: AgentState) -> dict:
    msg = state["messages"][-1]
    content = msg.content if hasattr(msg, "content") else str(msg)
    return {"result": f"Processed: {content}"}

agent_graph = StateGraph(AgentState)
agent_graph.add_node("process", process_query)
agent_graph.set_entry_point("process")
agent_graph.add_edge("process", END)
agent_app = agent_graph.compile()

@task(retries=2)
def validate_request(prompt: str) -> str:
    if not prompt.strip():
        raise ValueError("Empty prompt")
    return prompt

@task
def check_cache(prompt: str) -> str | None:
    # Check semantic cache (Redis)
    return None  # Cache miss

@task(timeout_seconds=60)
def run_agent(prompt: str) -> str:
    """Execute LangGraph agent within a Prefect task."""
    result = agent_app.invoke({
        "messages": [{"role": "user", "content": prompt}],
        "result": "",
    })
    return result["result"]

@task
def store_result(prompt: str, response: str):
    # Store in cache and database
    print(f"Stored: {prompt[:50]} → {response[:50]}")

@flow(name="agent-pipeline", log_prints=True)
def agent_flow(prompt: str) -> str:
    validated = validate_request(prompt)

    cached = check_cache(validated)
    if cached:
        print("Cache hit!")
        return cached

    response = run_agent(validated)
    store_result(validated, response)
    return response

if __name__ == "__main__":
    result = agent_flow("Explain service meshes")
    print(f"Result: {result}")
```

---

### Exercise 7: RAG Agent Pipeline

```python
# exercise7.py
from prefect import flow, task
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

class RAGState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    documents: list[str]
    answer: str
    needs_more_context: bool

def retrieve(state: RAGState) -> dict:
    """Retrieve relevant documents."""
    query = state["query"]
    docs = [
        f"Document about {query}: Key information here.",
        f"Related content: More details about {query}.",
    ]
    return {"documents": docs}

def generate(state: RAGState) -> dict:
    """Generate answer from documents."""
    docs = state["documents"]
    query = state["query"]
    context = "\n".join(docs)
    answer = f"Based on {len(docs)} documents about '{query}': {context[:200]}"
    return {"answer": answer, "needs_more_context": len(docs) < 3}

def check_quality(state: RAGState) -> str:
    if state.get("needs_more_context"):
        return "retrieve_more"
    return "done"

# Build RAG graph
rag_graph = StateGraph(RAGState)
rag_graph.add_node("retrieve", retrieve)
rag_graph.add_node("generate", generate)
rag_graph.set_entry_point("retrieve")
rag_graph.add_edge("retrieve", "generate")
rag_graph.add_conditional_edges("generate", check_quality, {
    "retrieve_more": "retrieve",
    "done": END,
})
rag_app = rag_graph.compile()

@task
def embed_query(query: str) -> list[float]:
    return [0.1] * 384  # Placeholder

@task(timeout_seconds=120)
def execute_rag(query: str) -> str:
    result = rag_app.invoke({
        "messages": [], "query": query,
        "documents": [], "answer": "",
        "needs_more_context": False,
    })
    return result["answer"]

@flow(name="rag-agent")
def rag_pipeline(question: str) -> str:
    embedding = embed_query(question)
    answer = execute_rag(question)
    print(f"Answer: {answer[:200]}")
    return answer

if __name__ == "__main__":
    rag_pipeline("How does vLLM handle GPU memory?")
```

---

### Exercise 8: Human-in-the-Loop

```python
# exercise8.py
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

class ApprovalState(TypedDict):
    messages: Annotated[list, add_messages]
    action: str
    approved: bool | None
    result: str

def propose_action(state: ApprovalState) -> dict:
    msg = state["messages"][-1]
    content = msg.content if hasattr(msg, "content") else str(msg)
    return {"action": f"Deploy model based on: {content}"}

def check_approval(state: ApprovalState) -> str:
    if state.get("approved") is True:
        return "execute"
    elif state.get("approved") is False:
        return "rejected"
    return "wait"  # Interrupt here for human input

def execute_action(state: ApprovalState) -> dict:
    return {"result": f"Executed: {state['action']}"}

def reject_action(state: ApprovalState) -> dict:
    return {"result": f"Rejected: {state['action']}"}

graph = StateGraph(ApprovalState)
graph.add_node("propose", propose_action)
graph.add_node("execute", execute_action)
graph.add_node("rejected", reject_action)

graph.set_entry_point("propose")
graph.add_conditional_edges("propose", check_approval, {
    "execute": "execute",
    "rejected": "rejected",
    "wait": END,
})
graph.add_edge("execute", END)
graph.add_edge("rejected", END)

# Use checkpointer for persistence across interruptions
checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

# Step 1: Propose (pauses at approval)
config = {"configurable": {"thread_id": "deploy-1"}}
result = app.invoke(
    {"messages": [{"role": "user", "content": "Deploy llama-3.1"}],
     "action": "", "approved": None, "result": ""},
    config,
)
print(f"Proposed: {result['action']}")

# Step 2: Human approves (resume with updated state)
result = app.invoke(
    {"approved": True},
    config,
)
print(f"Result: {result['result']}")
```

---

## 6. How It's Used in Our Project

- **Agent DAG** — LangGraph defines multi-step agent workflows (research → analyze → respond)
- **Prefect orchestration** — Schedules, monitors, and retries agent executions
- **RAG pipeline** — Document retrieval + LLM generation as a Prefect flow
- **Health monitoring** — Scheduled Prefect flows check model endpoints
- **Human approval** — LangGraph checkpoints enable approval gates for deployments

---

## 7. Best Practices & Further Reading

### Best Practices

1. **Keep LangGraph nodes small** — each node does one thing
2. **Use Prefect tasks for I/O** — database, API calls, file operations
3. **Set timeouts** on LLM-calling tasks (they can hang)
4. **Use checkpointing** for long-running agents
5. **Log extensively** — both Prefect and LangGraph support structured logging
6. **Test graphs independently** before wrapping in Prefect flows

### Further Reading

- [Prefect Documentation](https://docs.prefect.io/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
