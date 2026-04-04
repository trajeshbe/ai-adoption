# C4 Level 1: System Context Diagram

## Overview

This diagram shows the AI Agent Platform in the context of its users and the external systems it depends on.

```
                         +------------------+
                         |    Engineers     |
                         | (Dev / Platform) |
                         +--------+---------+
                                  |
                          deploy, configure,
                           monitor, debug
                                  |
                                  v
+------------------+    +---------------------+    +---------------------+
|                  |    |                     |    |                     |
|    End Users     +--->+   AI Agent Platform +--->+   Weather APIs      |
|  (Chat / Upload) |    |                     |    | (OpenWeatherMap,    |
|                  |    |  Weather Bot        |    |  WeatherAPI.com)    |
+------------------+    |  Quiz Bot           |    +---------------------+
                        |  RAG Assistant      |
                        |                     |    +---------------------+
                        |  GraphQL API        +--->+   HuggingFace Hub   |
                        |  LLM Inference      |    | (Model downloads,   |
                        |  Vector Search      |    |  tokenizers)        |
                        |  Observability      |    +---------------------+
                        |  GitOps / CI/CD     |
                        |                     |    +---------------------+
                        +----------+----------+    |   Cloud Providers   |
                                   |               | (S3-compatible,     |
                                   +-------------->+  container registry,|
                                                   |  DNS)               |
                                                   +---------------------+
```

## Actors

| Actor | Description |
|---|---|
| **End Users** | Interact with the platform through a web chat interface. They send prompts, upload documents, and receive AI-generated responses. |
| **Engineers** | Platform and application developers who deploy, configure, and monitor the system. They use GitOps workflows and observability dashboards. |

## External Systems

| System | Interaction |
|---|---|
| **Weather APIs** | The Weather Bot calls external weather services to retrieve real-time forecasts and conditions. |
| **HuggingFace Hub** | Model weights and tokenizer files are downloaded during LLM runtime initialization. |
| **Cloud Providers** | S3-compatible storage, container image registries, and DNS resolution for production deployments. |
