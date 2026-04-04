# Data Flow Diagrams

## 1. Chat Request Flow

A user sends a chat message and receives a streamed AI response.

```
 User
  |
  | 1. Send chat message (WebSocket or HTTP)
  v
 Next.js Frontend
  |
  | 2. GraphQL mutation / subscription
  v
 Contour / Envoy Ingress
  |
  | 3. Route to backend (path: /graphql)
  v
 FastAPI + Strawberry Gateway
  |
  | 4. Check semantic cache
  v
 Cache Service -----> Redis VSS
  |                    |
  | cache miss         | cache hit -> return cached response (skip to step 8)
  v                    |
 Agent Engine (LangGraph)
  |
  | 5. Select tools, build prompt, manage state
  |
  | 6. Call LLM with prompt + tool results
  v
 LLM Runtime (vLLM or llama.cpp)
  |
  | 7. Stream tokens back
  v
 Agent Engine
  |
  | 7a. If tool call -> execute tool -> loop to step 6
  | 7b. If final answer -> continue
  |
  | 8. Stream response tokens to gateway
  v
 FastAPI Gateway
  |
  | 9. Forward stream to frontend via WebSocket / SSE
  v
 Next.js Frontend
  |
  | 10. Render tokens incrementally in chat UI
  v
 User sees response
```

### Cache Behavior

- On **cache hit**: the cached response is returned directly from Redis VSS, bypassing the agent engine and LLM runtime entirely.
- On **cache miss**: after the full response is generated, it is written back to Redis VSS keyed by a semantic hash of the query for future lookups.

---

## 2. Document Upload Flow

A user uploads a document that is chunked, embedded, and stored for RAG retrieval.

```
 User
  |
  | 1. Upload file via drag-and-drop or file picker
  v
 Next.js Frontend
  |
  | 2. GraphQL mutation: uploadDocument(file)
  v
 FastAPI Gateway
  |
  | 3. Receive multipart upload
  |
  +----------- 4a. Store raw file ------------> MinIO (S3 bucket)
  |                                              - bucket: documents
  |                                              - key: {user_id}/{doc_id}/{filename}
  |
  | 4b. Send file to document processing pipeline
  v
 Document Service
  |
  | 5. Extract text (PDF, DOCX, TXT, MD)
  | 6. Split into chunks (token-aware, overlapping)
  | 7. Generate embeddings via LLM Runtime or embedding model
  |
  +----------- 8. Store chunks + embeddings ---> PostgreSQL + pgvector
  |                                              - table: document_chunks
  |                                              - columns: id, doc_id, content,
  |                                                         embedding vector(1536),
  |                                                         metadata jsonb
  |
  | 9. Return document ID and chunk count
  v
 FastAPI Gateway
  |
  | 10. Return success response with doc metadata
  v
 Next.js Frontend
  |
  | 11. Show upload confirmation with chunk count
  v
 User sees confirmation
```

### Storage Summary

| Store | What | Purpose |
|---|---|---|
| MinIO | Raw uploaded files | Original document preservation, re-processing |
| PostgreSQL + pgvector | Text chunks + embedding vectors | Similarity search during RAG retrieval |
