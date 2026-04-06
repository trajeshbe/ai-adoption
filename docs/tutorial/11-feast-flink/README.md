# Tutorial 11: Feast + Apache Flink — Feature Store & Stream Processing

> **Objective:** Learn to manage ML features with Feast and compute real-time features with Apache Flink.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Feast Concepts](#2-feast-concepts)
3. [Flink Concepts](#3-flink-concepts)
4. [Installation & Setup](#4-installation--setup)
5. [Exercises](#5-exercises)
6. [How It's Used in Our Project](#6-how-its-used-in-our-project)
7. [Further Reading](#7-further-reading)

---

## 1. Introduction

### What is a Feature Store?

A feature store manages the data (features) used by ML models. It solves:
- **Training/serving skew** — Same feature computation for training and inference
- **Feature reuse** — Teams share features instead of recomputing
- **Point-in-time correctness** — Get features as they were at a specific time

### What is Feast?

**Feast** (Feature Store) is an open-source feature store that:
- Stores feature definitions as code
- Materializes features from offline (batch) to online (low-latency) stores
- Serves features via a Python SDK or HTTP API

### What is Apache Flink?

**Flink** is a distributed stream processing framework:
- Processes millions of events per second
- Supports event time processing with watermarks
- Exactly-once processing guarantees
- Both stream and batch processing

### How They Work Together

```
Raw Events → [Flink: compute features in real-time] → [Feast: store & serve features] → [Model: inference]
```

---

## 2. Feast Concepts

### Feature Repository Structure

```
feature_repo/
├── feature_store.yaml    ← Configuration
├── entities.py           ← Entity definitions (user, model, etc.)
├── features.py           ← Feature view definitions
└── data/                 ← Offline data sources
```

### Key Components

| Component | Description |
|-----------|-------------|
| **Entity** | The "who" — user, model, session (join key) |
| **Feature View** | Group of related features from one data source |
| **Data Source** | Where features come from (file, DB, stream) |
| **Online Store** | Low-latency store for serving (Redis, DynamoDB) |
| **Offline Store** | Historical store for training (BigQuery, file) |
| **Materialization** | Copy features from offline → online store |

### Feature Definition

```python
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64, String
from datetime import timedelta

# Entity — the key for looking up features
user = Entity(name="user_id", join_keys=["user_id"])

# Data source
user_stats_source = FileSource(
    path="data/user_stats.parquet",
    timestamp_field="event_timestamp",
)

# Feature view — a group of features
user_stats_fv = FeatureView(
    name="user_stats",
    entities=[user],
    schema=[
        Field(name="total_queries", dtype=Int64),
        Field(name="avg_latency_ms", dtype=Float32),
        Field(name="preferred_model", dtype=String),
        Field(name="cache_hit_rate", dtype=Float32),
    ],
    source=user_stats_source,
    ttl=timedelta(hours=24),  # Features older than 24h are stale
)
```

---

## 3. Flink Concepts

### Stream Processing Model

```
Source → [Operators: map, filter, window, aggregate] → Sink

Events → [Parse] → [Filter valid] → [Window 5min] → [Aggregate] → [Output]
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Event Time** | When the event actually happened |
| **Processing Time** | When the event is processed |
| **Watermark** | "All events before this time have arrived" |
| **Window** | Group events by time (tumbling, sliding, session) |
| **State** | Per-key data persisted across events |
| **Checkpoint** | Snapshot of state for fault tolerance |

### Window Types

```
Tumbling Window (5 min, no overlap):
|----5min----|----5min----|----5min----|

Sliding Window (5 min window, 1 min slide):
|----5min----|
   |----5min----|
      |----5min----|

Session Window (gap = 10 min):
|--events--|    10min gap    |--events--|
  session 1                    session 2
```

---

## 4. Installation & Setup

### Feast

```bash
pip install feast

# Initialize a feature repo
feast init feature_repo
cd feature_repo

# Apply feature definitions
feast apply

# Start the online feature server
feast serve
```

### Flink (Docker)

```bash
docker run -d --name flink-jobmanager \
  -p 8081:8081 \
  -e JOB_MANAGER_RPC_ADDRESS=flink-jobmanager \
  flink:1.18-java11 jobmanager

docker run -d --name flink-taskmanager \
  -e JOB_MANAGER_RPC_ADDRESS=flink-jobmanager \
  flink:1.18-java11 taskmanager

# Flink UI: http://localhost:8081
```

### PyFlink

```bash
pip install apache-flink
```

---

## 5. Exercises

### Exercise 1: Define a Feast Feature Repository

```python
# feature_store.yaml
"""
project: ai_platform
provider: local
registry: data/registry.db
online_store:
  type: redis
  connection_string: localhost:6379
offline_store:
  type: file
entity_key_serialization_version: 2
"""

# entities.py
from feast import Entity

user = Entity(
    name="user_id",
    join_keys=["user_id"],
    description="Platform user",
)

model = Entity(
    name="model_id",
    join_keys=["model_id"],
    description="AI model",
)
```

```python
# features.py
from feast import FeatureView, Field, FileSource
from feast.types import Float32, Int64, String, UnixTimestamp
from datetime import timedelta
from entities import user, model

# User activity features
user_activity_source = FileSource(
    path="data/user_activity.parquet",
    timestamp_field="event_timestamp",
)

user_activity = FeatureView(
    name="user_activity",
    entities=[user],
    schema=[
        Field(name="queries_last_hour", dtype=Int64),
        Field(name="queries_last_day", dtype=Int64),
        Field(name="avg_query_length", dtype=Float32),
        Field(name="preferred_model", dtype=String),
        Field(name="cache_hit_rate", dtype=Float32),
    ],
    source=user_activity_source,
    ttl=timedelta(hours=1),
)

# Model performance features
model_perf_source = FileSource(
    path="data/model_performance.parquet",
    timestamp_field="event_timestamp",
)

model_performance = FeatureView(
    name="model_performance",
    entities=[model],
    schema=[
        Field(name="p50_latency_ms", dtype=Float32),
        Field(name="p99_latency_ms", dtype=Float32),
        Field(name="error_rate", dtype=Float32),
        Field(name="requests_per_minute", dtype=Int64),
        Field(name="gpu_utilization", dtype=Float32),
    ],
    source=model_perf_source,
    ttl=timedelta(minutes=5),
)
```

```bash
# Apply to register features
feast apply

# Verify
feast feature-views list
feast entities list
```

---

### Exercise 2: Materialize Features

```python
# materialize.py
from feast import FeatureStore
from datetime import datetime, timedelta

store = FeatureStore(repo_path=".")

# Materialize from offline to online store
store.materialize(
    start_date=datetime.utcnow() - timedelta(days=7),
    end_date=datetime.utcnow(),
)

print("Materialization complete!")

# Incremental materialization (only new data)
store.materialize_incremental(end_date=datetime.utcnow())
```

---

### Exercise 3: Retrieve Features for Inference

```python
# serve_features.py
from feast import FeatureStore
import pandas as pd

store = FeatureStore(repo_path=".")

# Online serving — low latency for real-time inference
features = store.get_online_features(
    features=[
        "user_activity:queries_last_hour",
        "user_activity:preferred_model",
        "user_activity:cache_hit_rate",
        "model_performance:p99_latency_ms",
        "model_performance:error_rate",
    ],
    entity_rows=[
        {"user_id": "user-123", "model_id": "llama-3-70b"},
    ],
)

feature_dict = features.to_dict()
print("Online features:")
for key, values in feature_dict.items():
    print(f"  {key}: {values}")

# Offline serving — for training data
training_df = store.get_historical_features(
    features=[
        "user_activity:queries_last_hour",
        "user_activity:cache_hit_rate",
        "model_performance:p99_latency_ms",
    ],
    entity_df=pd.DataFrame({
        "user_id": ["user-123", "user-456"],
        "model_id": ["llama-3-70b", "llama-3-8b"],
        "event_timestamp": [datetime.utcnow(), datetime.utcnow()],
    }),
)

print("\nTraining data:")
print(training_df.to_pandas().head())
```

---

### Exercise 4: Flink Streaming Job

```python
# flink_wordcount.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import MapFunction, FlatMapFunction

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(1)

# Simple word count
class Tokenizer(FlatMapFunction):
    def flat_map(self, value, collector):
        for word in value.lower().split():
            collector.collect((word, 1))

# Create source
lines = env.from_collection([
    "kubernetes is a container orchestration platform",
    "docker packages applications in containers",
    "kubernetes manages docker containers at scale",
])

# Process
word_counts = (
    lines
    .flat_map(Tokenizer())
    .key_by(lambda x: x[0])
    .sum(1)
)

word_counts.print()
env.execute("Word Count")
```

---

### Exercise 5: Flink Real-time Feature Computation

```python
# flink_features.py
from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.window import TumblingEventTimeWindows
from pyflink.common.time import Time
from pyflink.datastream.functions import AggregateFunction, ProcessWindowFunction
import json

env = StreamExecutionEnvironment.get_execution_environment()
env.set_stream_time_characteristic(TimeCharacteristic.EventTime)

# Simulate inference events
events = env.from_collection([
    json.dumps({"user_id": "u1", "model": "llama-3", "latency_ms": 245, "tokens": 150, "ts": 1000}),
    json.dumps({"user_id": "u1", "model": "llama-3", "latency_ms": 189, "tokens": 80, "ts": 2000}),
    json.dumps({"user_id": "u2", "model": "llama-3", "latency_ms": 312, "tokens": 200, "ts": 1500}),
    json.dumps({"user_id": "u1", "model": "llama-3", "latency_ms": 156, "tokens": 120, "ts": 3000}),
])

# Parse events
def parse_event(raw):
    data = json.loads(raw)
    return (data["user_id"], data["latency_ms"], data["tokens"])

parsed = events.map(parse_event)

# Compute per-user features: avg latency, total tokens
class FeatureAggregator(AggregateFunction):
    def create_accumulator(self):
        return {"count": 0, "total_latency": 0, "total_tokens": 0}

    def add(self, value, acc):
        acc["count"] += 1
        acc["total_latency"] += value[1]
        acc["total_tokens"] += value[2]
        return acc

    def get_result(self, acc):
        avg_latency = acc["total_latency"] / max(acc["count"], 1)
        return {"count": acc["count"], "avg_latency": avg_latency, "total_tokens": acc["total_tokens"]}

    def merge(self, a, b):
        return {
            "count": a["count"] + b["count"],
            "total_latency": a["total_latency"] + b["total_latency"],
            "total_tokens": a["total_tokens"] + b["total_tokens"],
        }

features = (
    parsed
    .key_by(lambda x: x[0])  # Key by user_id
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(FeatureAggregator())
)

features.print()
env.execute("Feature Computation")
```

---

### Exercise 6: Push Flink Features to Feast

```python
# push_to_feast.py
from feast import FeatureStore
from datetime import datetime
import pandas as pd

store = FeatureStore(repo_path=".")

# Simulated features computed by Flink
computed_features = [
    {"user_id": "user-123", "queries_last_hour": 15, "avg_query_length": 42.5,
     "preferred_model": "llama-3-70b", "cache_hit_rate": 0.65,
     "event_timestamp": datetime.utcnow()},
    {"user_id": "user-456", "queries_last_hour": 8, "avg_query_length": 28.0,
     "preferred_model": "llama-3-8b", "cache_hit_rate": 0.80,
     "event_timestamp": datetime.utcnow()},
]

df = pd.DataFrame(computed_features)

# Push features to online store
store.push("user_activity_push_source", df)
print(f"Pushed {len(df)} feature rows to Feast")

# Verify they're available
features = store.get_online_features(
    features=["user_activity:queries_last_hour", "user_activity:cache_hit_rate"],
    entity_rows=[{"user_id": "user-123"}],
)
print(features.to_dict())
```

---

### Exercise 7: End-to-End Feature Pipeline

```python
# e2e_pipeline.py
from prefect import flow, task
from feast import FeatureStore
import pandas as pd
from datetime import datetime

@task
def compute_user_features(user_id: str) -> dict:
    """Compute features from recent activity (simulated Flink output)."""
    return {
        "user_id": user_id,
        "queries_last_hour": 12,
        "cache_hit_rate": 0.72,
        "preferred_model": "llama-3-70b",
        "event_timestamp": datetime.utcnow(),
    }

@task
def push_to_feast(features: dict):
    """Push computed features to Feast online store."""
    store = FeatureStore(repo_path="./feature_repo")
    df = pd.DataFrame([features])
    store.push("user_activity_push_source", df)

@task
def get_features_for_inference(user_id: str, model_id: str) -> dict:
    """Retrieve features for model inference."""
    store = FeatureStore(repo_path="./feature_repo")
    result = store.get_online_features(
        features=[
            "user_activity:queries_last_hour",
            "user_activity:cache_hit_rate",
            "model_performance:p99_latency_ms",
        ],
        entity_rows=[{"user_id": user_id, "model_id": model_id}],
    )
    return result.to_dict()

@task
def select_model(features: dict) -> str:
    """Use features to select the best model for this request."""
    cache_rate = features.get("cache_hit_rate", [0])[0] or 0
    p99 = features.get("p99_latency_ms", [0])[0] or 0

    if p99 > 500:
        return "llama-3-8b"  # Use smaller model if primary is slow
    return "llama-3-70b"

@flow(name="feature-driven-inference")
def inference_with_features(user_id: str, prompt: str):
    # Compute and store latest features
    features = compute_user_features(user_id)
    push_to_feast(features)

    # Retrieve features for decision making
    feature_vector = get_features_for_inference(user_id, "llama-3-70b")
    model = select_model(feature_vector)

    print(f"Selected model: {model} for user {user_id}")
    print(f"Features: {feature_vector}")
    return model

if __name__ == "__main__":
    inference_with_features("user-123", "What is Kubernetes?")
```

---

## 6. How It's Used in Our Project

- **User features** — Query history, cache hit rate, model preference → routing decisions
- **Model features** — Latency, error rate, GPU utilization → autoscaling triggers
- **Real-time Flink** — Computes sliding window aggregates from inference events
- **Feast serving** — Features served to agent engine for context-aware decisions
- **Training data** — Historical features for model evaluation and A/B test analysis

---

## 7. Further Reading

- [Feast Documentation](https://docs.feast.dev/)
- [Apache Flink Documentation](https://flink.apache.org/docs/)
- [PyFlink Documentation](https://nightlies.apache.org/flink/flink-docs-stable/docs/dev/python/overview/)
- [Feature Store Concepts](https://www.featurestore.org/)
