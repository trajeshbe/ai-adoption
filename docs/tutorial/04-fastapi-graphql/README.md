# Tutorial 04: FastAPI + GraphQL (Strawberry)

> **Objective:** Build high-performance Python APIs with FastAPI and a schema-first GraphQL layer using Strawberry.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [FastAPI Deep Dive](#3-fastapi-deep-dive)
4. [Strawberry GraphQL](#4-strawberry-graphql)
5. [Project Setup](#5-project-setup)
6. [Exercises](#6-exercises)
7. [Testing](#7-testing)
8. [How It's Used in Our Project](#8-how-its-used-in-our-project)
9. [Best Practices & Further Reading](#9-best-practices--further-reading)

---

## 1. Introduction

### What is FastAPI?

**FastAPI** is a modern Python web framework for building APIs. It's:

- **Fast** — Built on Starlette (ASGI), comparable to Node.js and Go in performance
- **Type-safe** — Uses Python type hints for automatic validation
- **Auto-documented** — Generates OpenAPI (Swagger) docs automatically
- **Async-first** — Built for `async/await` from the ground up

### What is GraphQL?

**GraphQL** is a query language for APIs where the client asks for exactly what it needs:

```graphql
# REST: GET /api/models → returns ALL fields for ALL models
# GraphQL: ask for exactly what you need

query {
  models {
    id
    name
    status     # Only get these 3 fields
  }
}
```

### REST vs GraphQL

| Feature | REST | GraphQL |
|---------|------|---------|
| Endpoints | Many (`/users`, `/posts`, `/comments`) | One (`/graphql`) |
| Data fetching | Fixed response shape | Client chooses fields |
| Over-fetching | Common (get fields you don't need) | Never |
| Under-fetching | Common (need multiple requests) | Never |
| Versioning | `/api/v1/`, `/api/v2/` | Schema evolution |
| Real-time | Polling or WebSocket | Subscriptions |

### What is Strawberry?

**Strawberry** is a Python GraphQL library that uses type hints and dataclasses:

```python
import strawberry

@strawberry.type
class Model:
    id: int
    name: str
    status: str

@strawberry.type
class Query:
    @strawberry.field
    def models(self) -> list[Model]:
        return [Model(id=1, name="llama-3", status="active")]
```

---

## 2. Core Concepts

### 2.1 ASGI (Asynchronous Server Gateway Interface)

ASGI is the async successor to WSGI. It allows handling multiple requests concurrently:

```python
# WSGI (synchronous) — one request at a time per worker
def app(environ, start_response):
    # blocks until done
    data = fetch_from_db()
    return [data]

# ASGI (asynchronous) — many requests concurrently
async def app(scope, receive, send):
    # yields control while waiting
    data = await fetch_from_db()
    await send(data)
```

### 2.2 Type Hints & Pydantic

FastAPI uses Python type hints for automatic validation:

```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096)
    model: str = "llama-3-70b"
    temperature: float = Field(default=0.7, ge=0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)

# FastAPI automatically validates incoming JSON against this schema
# Invalid requests get a 422 error with detailed messages
```

### 2.3 Dependency Injection

FastAPI has a built-in dependency injection system:

```python
from fastapi import Depends

async def get_db():
    db = await connect_to_database()
    try:
        yield db
    finally:
        await db.close()

async def get_current_user(token: str = Header(...)):
    user = await verify_token(token)
    return user

@app.get("/dashboard")
async def dashboard(
    user = Depends(get_current_user),   # Injected!
    db = Depends(get_db),                # Injected!
):
    return await db.get_user_data(user.id)
```

### 2.4 async/await

```python
import asyncio

# Synchronous — blocks while waiting
def get_data():
    response = requests.get("https://api.example.com")  # Thread blocked!
    return response.json()

# Asynchronous — yields while waiting
async def get_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com")  # Thread free!
        return response.json()

# Run multiple async operations concurrently
async def get_all():
    models, costs, metrics = await asyncio.gather(
        get_models(),
        get_costs(),
        get_metrics(),
    )  # All three run at the same time!
```

---

## 3. FastAPI Deep Dive

### 3.1 Path Operations

```python
from fastapi import FastAPI, Path, Query, Body

app = FastAPI(title="AI Platform API", version="1.0.0")

# GET with path and query parameters
@app.get("/models/{model_id}")
async def get_model(
    model_id: int = Path(..., gt=0, description="The model ID"),
    include_metrics: bool = Query(False, description="Include performance metrics"),
):
    model = await fetch_model(model_id)
    if include_metrics:
        model.metrics = await fetch_metrics(model_id)
    return model

# POST with request body
@app.post("/chat", status_code=201)
async def create_chat(request: ChatRequest):
    response = await llm.generate(request.prompt, temperature=request.temperature)
    return {"reply": response}

# PUT for updates
@app.put("/models/{model_id}")
async def update_model(model_id: int, config: ModelConfig):
    return await update_model_config(model_id, config)

# DELETE
@app.delete("/models/{model_id}", status_code=204)
async def delete_model(model_id: int):
    await remove_model(model_id)
```

### 3.2 Middleware

```python
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{duration:.4f}"
        return response

app.add_middleware(TimingMiddleware)

# CORS middleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3.3 Error Handling

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

# Simple error
@app.get("/models/{model_id}")
async def get_model(model_id: int):
    model = await db.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model

# Custom exception handler
class ModelNotFoundError(Exception):
    def __init__(self, model_id: int):
        self.model_id = model_id

@app.exception_handler(ModelNotFoundError)
async def model_not_found_handler(request: Request, exc: ModelNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "model_not_found", "model_id": exc.model_id},
    )
```

### 3.4 Background Tasks

```python
from fastapi import BackgroundTasks

async def log_inference(prompt: str, response: str, duration: float):
    """Log inference to database (non-blocking)."""
    await db.insert_log(prompt=prompt, response=response, duration=duration)

@app.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    start = time.perf_counter()
    response = await llm.generate(request.prompt)
    duration = time.perf_counter() - start

    # Log in background — don't make user wait
    background_tasks.add_task(log_inference, request.prompt, response, duration)

    return {"reply": response}
```

---

## 4. Strawberry GraphQL

### 4.1 Defining Types

```python
import strawberry
from datetime import datetime

@strawberry.type
class Model:
    id: int
    name: str
    status: str
    version: str
    created_at: datetime

@strawberry.type
class InferenceResult:
    text: str
    tokens_used: int
    latency_ms: float
    model: str
    cost_usd: float

@strawberry.input
class ChatInput:
    prompt: str
    model: str = "llama-3-70b"
    temperature: float = 0.7
    max_tokens: int = 1024
```

### 4.2 Queries and Mutations

```python
@strawberry.type
class Query:
    @strawberry.field
    async def models(self) -> list[Model]:
        return await db.get_all_models()

    @strawberry.field
    async def model(self, id: int) -> Model | None:
        return await db.get_model(id)

    @strawberry.field
    async def health(self) -> str:
        return "ok"

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def chat(self, input: ChatInput) -> InferenceResult:
        result = await llm.generate(
            prompt=input.prompt,
            model=input.model,
            temperature=input.temperature,
        )
        return InferenceResult(
            text=result.text,
            tokens_used=result.tokens,
            latency_ms=result.latency,
            model=input.model,
            cost_usd=result.cost,
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

### 4.3 Subscriptions (Real-time)

```python
import asyncio
from typing import AsyncGenerator

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def chat_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream LLM tokens as they're generated."""
        async for token in llm.stream(prompt):
            yield token

    @strawberry.subscription
    async def model_metrics(self, model_id: int) -> AsyncGenerator[ModelMetrics, None]:
        """Stream live metrics for a model."""
        while True:
            metrics = await get_current_metrics(model_id)
            yield metrics
            await asyncio.sleep(1)

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
)
```

### 4.4 DataLoaders (N+1 Problem)

```python
from strawberry.dataloader import DataLoader

async def load_models(ids: list[int]) -> list[Model]:
    """Batch load models — called once with all IDs instead of N times."""
    return await db.get_models_by_ids(ids)

@strawberry.type
class Agent:
    id: int
    name: str
    model_id: int

    @strawberry.field
    async def model(self, info: strawberry.types.Info) -> Model:
        # Uses DataLoader — batches multiple agent.model lookups
        return await info.context["model_loader"].load(self.model_id)

# Setup in context
async def get_context():
    return {"model_loader": DataLoader(load_fn=load_models)}
```

---

## 5. Project Setup

```bash
# Create project
mkdir ai-api && cd ai-api
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn strawberry-graphql[fastapi] httpx pydantic

# Create main application
```

```python
# main.py
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

# Define schema
@strawberry.type
class Query:
    @strawberry.field
    def hello(self, name: str = "World") -> str:
        return f"Hello, {name}!"

schema = strawberry.Schema(query=Query)

# Create FastAPI app
app = FastAPI(title="AI Platform API")

# Mount GraphQL
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

# REST health check
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

```bash
# Run the server
uvicorn main:app --reload --port 8000

# Visit:
# - http://localhost:8000/docs         → Swagger UI (REST)
# - http://localhost:8000/graphql      → GraphiQL (GraphQL playground)
# - http://localhost:8000/health       → Health check
```

---

## 6. Exercises

### Exercise 1: Basic REST Endpoint with Pydantic Validation

```python
# exercise1.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime

app = FastAPI()

# Pydantic models for validation
class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")  # Semver
    type: str = Field(..., description="Model type: 'llm' or 'embedding'")
    parameters_b: float = Field(..., gt=0, description="Parameters in billions")

class ModelResponse(BaseModel):
    id: int
    name: str
    version: str
    type: str
    parameters_b: float
    created_at: datetime

# In-memory storage
models_db: dict[int, ModelResponse] = {}
next_id = 1

@app.post("/api/models", response_model=ModelResponse, status_code=201)
async def create_model(model: ModelCreate):
    global next_id
    db_model = ModelResponse(
        id=next_id,
        **model.model_dump(),
        created_at=datetime.utcnow(),
    )
    models_db[next_id] = db_model
    next_id += 1
    return db_model

@app.get("/api/models", response_model=list[ModelResponse])
async def list_models(type: str | None = None):
    models = list(models_db.values())
    if type:
        models = [m for m in models if m.type == type]
    return models

@app.get("/api/models/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int):
    if model_id not in models_db:
        raise HTTPException(status_code=404, detail="Model not found")
    return models_db[model_id]
```

```bash
# Test it:
curl -X POST http://localhost:8000/api/models \
  -H "Content-Type: application/json" \
  -d '{"name": "llama-3", "version": "3.1.0", "type": "llm", "parameters_b": 70.0}'

# Invalid request (bad version format):
curl -X POST http://localhost:8000/api/models \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "version": "bad", "type": "llm", "parameters_b": 7}'
# Returns 422 with validation error details
```

---

### Exercise 2: Async CRUD with SQLAlchemy

```python
# exercise2.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, String
from pydantic import BaseModel
from datetime import datetime

# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./models.db"
engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class ModelDB(Base):
    __tablename__ = "models"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="inactive")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

# Pydantic schemas
class ModelCreate(BaseModel):
    name: str
    status: str = "inactive"

class ModelOut(BaseModel):
    id: int
    name: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}

# Dependency
async def get_db():
    async with SessionLocal() as session:
        yield session

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/models", response_model=ModelOut, status_code=201)
async def create(data: ModelCreate, db: AsyncSession = Depends(get_db)):
    model = ModelDB(**data.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model

@app.get("/models", response_model=list[ModelOut])
async def list_all(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ModelDB))
    return result.scalars().all()

@app.get("/models/{id}", response_model=ModelOut)
async def get_one(id: int, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelDB, id)
    if not model:
        raise HTTPException(404, "Not found")
    return model

@app.put("/models/{id}", response_model=ModelOut)
async def update(id: int, data: ModelCreate, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelDB, id)
    if not model:
        raise HTTPException(404, "Not found")
    model.name = data.name
    model.status = data.status
    await db.commit()
    await db.refresh(model)
    return model

@app.delete("/models/{id}", status_code=204)
async def delete(id: int, db: AsyncSession = Depends(get_db)):
    model = await db.get(ModelDB, id)
    if not model:
        raise HTTPException(404, "Not found")
    await db.delete(model)
    await db.commit()
```

---

### Exercise 3: GraphQL Schema with Queries and Mutations

```python
# exercise3.py
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from datetime import datetime

# In-memory data store
agents_db = [
    {"id": 1, "name": "Research Agent", "model": "llama-3-70b", "status": "active", "runs": 142},
    {"id": 2, "name": "Code Agent", "model": "codellama-34b", "status": "active", "runs": 89},
    {"id": 3, "name": "Writer Agent", "model": "llama-3-8b", "status": "paused", "runs": 56},
]

@strawberry.type
class Agent:
    id: int
    name: str
    model: str
    status: str
    runs: int

@strawberry.input
class AgentInput:
    name: str
    model: str = "llama-3-70b"

@strawberry.type
class Query:
    @strawberry.field
    def agents(self, status: str | None = None) -> list[Agent]:
        results = agents_db
        if status:
            results = [a for a in results if a["status"] == status]
        return [Agent(**a) for a in results]

    @strawberry.field
    def agent(self, id: int) -> Agent | None:
        for a in agents_db:
            if a["id"] == id:
                return Agent(**a)
        return None

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_agent(self, input: AgentInput) -> Agent:
        new_id = max(a["id"] for a in agents_db) + 1
        agent = {
            "id": new_id,
            "name": input.name,
            "model": input.model,
            "status": "active",
            "runs": 0,
        }
        agents_db.append(agent)
        return Agent(**agent)

    @strawberry.mutation
    def toggle_agent(self, id: int) -> Agent | None:
        for a in agents_db:
            if a["id"] == id:
                a["status"] = "paused" if a["status"] == "active" else "active"
                return Agent(**a)
        return None

schema = strawberry.Schema(query=Query, mutation=Mutation)
app = FastAPI()
app.include_router(GraphQLRouter(schema), prefix="/graphql")
```

Test in GraphiQL (`http://localhost:8000/graphql`):

```graphql
# Query all active agents
query {
  agents(status: "active") {
    id
    name
    model
    runs
  }
}

# Create a new agent
mutation {
  createAgent(input: { name: "Summary Agent", model: "llama-3-8b" }) {
    id
    name
    status
  }
}

# Toggle agent status
mutation {
  toggleAgent(id: 1) {
    id
    name
    status
  }
}
```

---

### Exercise 4: GraphQL Subscriptions (Real-time Streaming)

```python
# exercise4.py
import strawberry
import asyncio
from typing import AsyncGenerator
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class Token:
    text: str
    index: int
    finished: bool

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Visit /graphql for the playground"

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def chat_stream(self, prompt: str) -> AsyncGenerator[Token, None]:
        """Simulate streaming LLM response token by token."""
        words = f"Here is a response to: {prompt}. The AI platform processes your query through the agent pipeline.".split()
        for i, word in enumerate(words):
            yield Token(text=word + " ", index=i, finished=i == len(words) - 1)
            await asyncio.sleep(0.1)

schema = strawberry.Schema(query=Query, subscription=Subscription)
app = FastAPI()
app.include_router(GraphQLRouter(schema), prefix="/graphql")
```

Test subscription in GraphiQL:

```graphql
subscription {
  chatStream(prompt: "What is Kubernetes?") {
    text
    index
    finished
  }
}
```

---

### Exercise 5: JWT Authentication Middleware

```python
# exercise5.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"

security = HTTPBearer()
app = FastAPI()

def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": int(payload["sub"]), "role": payload["role"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

def require_role(role: str):
    async def checker(user=Depends(get_current_user)):
        if user["role"] != role:
            raise HTTPException(403, f"Role '{role}' required")
        return user
    return checker

# Public endpoint
@app.post("/auth/login")
async def login(username: str, password: str):
    # In production, verify against database
    if username == "admin" and password == "secret":
        return {"token": create_token(1, "admin")}
    raise HTTPException(401, "Invalid credentials")

# Protected endpoint
@app.get("/api/me")
async def me(user=Depends(get_current_user)):
    return user

# Admin-only endpoint
@app.get("/api/admin/users")
async def admin_users(user=Depends(require_role("admin"))):
    return [{"id": 1, "name": "Admin User", "role": "admin"}]
```

---

### Exercise 6: File Upload for Document Ingestion

```python
# exercise6.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import hashlib

app = FastAPI()
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {"application/pdf", "text/plain", "text/markdown"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"File type '{file.content_type}' not allowed")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "File too large (max 10MB)")

    # Generate unique filename
    file_hash = hashlib.sha256(content).hexdigest()[:12]
    ext = Path(file.filename).suffix
    save_path = UPLOAD_DIR / f"{file_hash}{ext}"

    save_path.write_bytes(content)

    return {
        "filename": file.filename,
        "size_bytes": len(content),
        "hash": file_hash,
        "path": str(save_path),
        "status": "uploaded",
    }

@app.post("/api/documents/batch")
async def upload_batch(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        content = await file.read()
        results.append({
            "filename": file.filename,
            "size_bytes": len(content),
        })
    return {"uploaded": len(results), "files": results}
```

---

### Exercise 7: WebSocket for Streaming LLM Responses

```python
# exercise7.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.remove(websocket)

    async def send_json(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)

manager = ConnectionManager()

@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            prompt = data.get("prompt", "")

            # Send acknowledgment
            await manager.send_json(websocket, {
                "type": "start",
                "prompt": prompt,
            })

            # Simulate streaming LLM response
            words = f"Based on your question about {prompt}, here is a detailed response from our AI model.".split()
            for i, word in enumerate(words):
                await manager.send_json(websocket, {
                    "type": "token",
                    "text": word + " ",
                    "index": i,
                })
                await asyncio.sleep(0.05)

            # Send completion signal
            await manager.send_json(websocket, {
                "type": "done",
                "total_tokens": len(words),
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

Client-side JavaScript to test:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/chat");

ws.onopen = () => {
  ws.send(JSON.stringify({ prompt: "Explain Kubernetes" }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "token") process.stdout.write(data.text);
  if (data.type === "done") console.log("\n--- Done ---");
};
```

---

### Exercise 8: Dependency Injection Patterns

```python
# exercise8.py
from fastapi import FastAPI, Depends
from functools import lru_cache
from pydantic_settings import BaseSettings

# Settings with environment variables
class Settings(BaseSettings):
    llm_api_url: str = "http://localhost:8001"
    redis_url: str = "redis://localhost:6379"
    db_url: str = "postgresql+asyncpg://localhost/aiplatform"
    max_tokens: int = 4096

    model_config = {"env_prefix": "AI_"}

@lru_cache
def get_settings() -> Settings:
    return Settings()

# Service layer with dependencies
class LLMService:
    def __init__(self, settings: Settings):
        self.api_url = settings.llm_api_url
        self.max_tokens = settings.max_tokens

    async def generate(self, prompt: str) -> str:
        # In production, call vLLM API
        return f"Response from {self.api_url}: {prompt}"

class CacheService:
    def __init__(self, settings: Settings):
        self.redis_url = settings.redis_url

    async def get(self, key: str) -> str | None:
        return None  # Placeholder

    async def set(self, key: str, value: str, ttl: int = 300):
        pass

def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    return LLMService(settings)

def get_cache_service(settings: Settings = Depends(get_settings)) -> CacheService:
    return CacheService(settings)

app = FastAPI()

@app.post("/chat")
async def chat(
    prompt: str,
    llm: LLMService = Depends(get_llm_service),
    cache: CacheService = Depends(get_cache_service),
):
    # Check cache first
    cached = await cache.get(f"chat:{prompt}")
    if cached:
        return {"reply": cached, "source": "cache"}

    # Generate response
    reply = await llm.generate(prompt)
    await cache.set(f"chat:{prompt}", reply)
    return {"reply": reply, "source": "llm"}
```

---

## 7. Testing

```python
# test_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from exercise1 import app

@pytest.mark.asyncio
async def test_create_model():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/models", json={
            "name": "test-model",
            "version": "1.0.0",
            "type": "llm",
            "parameters_b": 7.0,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-model"
        assert data["id"] == 1

@pytest.mark.asyncio
async def test_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/models", json={
            "name": "",  # Too short
            "version": "bad",  # Invalid format
            "type": "llm",
            "parameters_b": -1,  # Negative
        })
        assert response.status_code == 422

# Testing GraphQL
@pytest.mark.asyncio
async def test_graphql_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/graphql", json={
            "query": "{ agents { id name status } }",
        })
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]["agents"]) > 0
```

```bash
# Run tests
pip install pytest pytest-asyncio httpx
pytest test_api.py -v
```

---

## 8. How It's Used in Our Project

In the AI platform, FastAPI + Strawberry serves as the **API gateway**:

- **GraphQL endpoint** (`/graphql`) — Primary API for the Next.js frontend
- **REST endpoints** — Health checks, file uploads, WebSocket connections
- **Subscriptions** — Real-time streaming of LLM responses
- **Dependency injection** — Database, Redis cache, LLM service injection
- **Middleware** — Request tracing (OpenTelemetry), timing, CORS
- **Background tasks** — Logging, cost calculation, metrics emission

---

## 9. Best Practices & Further Reading

### Best Practices

1. **Use Pydantic models** for all request/response validation
2. **Use async everywhere** — don't mix sync and async code
3. **Use dependency injection** for services, not global variables
4. **Add middleware** for cross-cutting concerns (tracing, timing, auth)
5. **Use DataLoaders** in GraphQL to avoid N+1 queries
6. **Version your API** if you have external consumers
7. **Write tests** with `httpx.AsyncClient`

### Further Reading

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Strawberry GraphQL Docs](https://strawberry.rocks/docs)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [GraphQL Specification](https://graphql.org/learn/)
- [SQLAlchemy Async Tutorial](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
