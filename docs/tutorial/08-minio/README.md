# Tutorial 08: MinIO — S3-Compatible Object Storage

> **Objective:** Learn MinIO for storing documents, model artifacts, and other binary objects in our AI platform.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Core Concepts](#2-core-concepts)
3. [Installation & Setup](#4-installation--setup)
4. [MinIO Client (mc)](#4-minio-client-mc)
5. [Exercises](#5-exercises)
6. [Kubernetes Deployment](#6-kubernetes-deployment)
7. [How It's Used in Our Project](#7-how-its-used-in-our-project)
8. [Best Practices & Further Reading](#8-best-practices--further-reading)

---

## 1. Introduction

### What is Object Storage?

Object storage stores data as **objects** (files + metadata) in flat **buckets** — no folders or hierarchy. Each object has a unique key.

```
Bucket: "documents"
├── reports/annual-2025.pdf     (key = "reports/annual-2025.pdf")
├── manuals/user-guide.md       (key = "manuals/user-guide.md")
└── images/logo.png             (key = "images/logo.png")
```

Unlike file systems, there are no real directories — the `/` in keys is just a naming convention.

### What is MinIO?

**MinIO** is an open-source, S3-compatible object storage server. Any tool or SDK that works with AWS S3 works with MinIO — just change the endpoint URL.

### Why MinIO?

- **S3-compatible** — Use boto3, AWS CLI, any S3 SDK
- **Self-hosted** — Data stays on your infrastructure
- **High performance** — Designed for AI/ML workloads
- **Kubernetes-native** — MinIO Operator for easy deployment

---

## 2. Core Concepts

| Concept | Description |
|---------|-------------|
| **Bucket** | Container for objects (like a top-level folder) |
| **Object** | A file + metadata stored in a bucket |
| **Key** | Unique identifier for an object within a bucket |
| **Versioning** | Keep multiple versions of the same object |
| **Presigned URL** | Temporary URL for secure access without credentials |
| **Lifecycle Policy** | Auto-delete or transition objects after N days |
| **Multipart Upload** | Upload large files in chunks (>5MB recommended) |
| **Server-Side Encryption** | Encrypt objects at rest |

---

## 3. Installation & Setup

### Docker (Single Node)

```bash
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=secretpassword" \
  -v minio-data:/data \
  minio/minio server /data --console-address ":9001"

# Console UI: http://localhost:9001
# API endpoint: http://localhost:9000
```

### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"
services:
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: secretpassword
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  minio-data:
```

---

## 4. MinIO Client (mc)

```bash
# Install mc
curl https://dl.min.io/client/mc/release/linux-amd64/mc -o mc
chmod +x mc && sudo mv mc /usr/local/bin/

# Configure alias
mc alias set local http://localhost:9000 admin secretpassword

# Basic operations
mc ls local                           # List buckets
mc mb local/documents                 # Create bucket
mc cp file.pdf local/documents/       # Upload file
mc ls local/documents/                # List objects
mc cat local/documents/file.pdf       # Download/view
mc rm local/documents/file.pdf        # Delete
mc du local/documents                 # Disk usage

# Recursive operations
mc cp --recursive ./data/ local/documents/data/
mc mirror ./local-dir local/documents/backup/

# Bucket policy
mc anonymous set download local/documents   # Make public
mc anonymous set none local/documents       # Make private
```

---

## 5. Exercises

### Exercise 1: Setup and Create Buckets

```bash
# Start MinIO
docker compose up -d

# Configure mc
mc alias set local http://localhost:9000 admin secretpassword

# Create buckets for our AI platform
mc mb local/documents      # Raw uploaded documents
mc mb local/chunks         # Processed document chunks
mc mb local/models         # Model artifacts
mc mb local/logs           # Application logs

# List buckets
mc ls local

# Set versioning on documents bucket
mc version enable local/documents
```

---

### Exercise 2: Upload/Download with mc CLI

```bash
# Create sample files
echo "This is a test document about Kubernetes." > k8s-doc.txt
echo "Machine learning guide for beginners." > ml-guide.txt

# Upload files
mc cp k8s-doc.txt local/documents/guides/
mc cp ml-guide.txt local/documents/guides/

# List with details
mc ls local/documents/guides/ --recursive

# Download
mc cp local/documents/guides/k8s-doc.txt ./downloaded.txt

# View content
mc cat local/documents/guides/k8s-doc.txt

# Copy between buckets
mc cp local/documents/guides/k8s-doc.txt local/chunks/

# Check versioning
echo "Updated content" > k8s-doc.txt
mc cp k8s-doc.txt local/documents/guides/
mc ls --versions local/documents/guides/k8s-doc.txt
```

---

### Exercise 3: Python boto3 Client

```python
# minio_client.py
import boto3
from botocore.client import Config

# Create S3-compatible client pointing to MinIO
s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="admin",
    aws_secret_access_key="secretpassword",
    config=Config(signature_version="s3v4"),
)

# List buckets
response = s3.list_buckets()
print("Buckets:")
for bucket in response["Buckets"]:
    print(f"  - {bucket['Name']}")

# Upload a file
s3.upload_file("./sample.txt", "documents", "uploads/sample.txt")
print("Uploaded sample.txt")

# Upload with metadata
s3.upload_file(
    "./sample.txt",
    "documents",
    "uploads/sample-with-meta.txt",
    ExtraArgs={
        "Metadata": {
            "source": "tutorial",
            "content-type": "text/plain",
            "processed": "false",
        }
    },
)

# List objects in bucket
response = s3.list_objects_v2(Bucket="documents", Prefix="uploads/")
for obj in response.get("Contents", []):
    print(f"  {obj['Key']} ({obj['Size']} bytes)")

# Download a file
s3.download_file("documents", "uploads/sample.txt", "./downloaded.txt")

# Read object directly
response = s3.get_object(Bucket="documents", Key="uploads/sample.txt")
content = response["Body"].read().decode("utf-8")
print(f"Content: {content}")

# Delete object
s3.delete_object(Bucket="documents", Key="uploads/sample.txt")
```

---

### Exercise 4: Presigned URLs

```python
# presigned_urls.py
import boto3
from botocore.client import Config

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="admin",
    aws_secret_access_key="secretpassword",
    config=Config(signature_version="s3v4"),
)

# Generate presigned URL for download (valid 1 hour)
download_url = s3.generate_presigned_url(
    "get_object",
    Params={"Bucket": "documents", "Key": "guides/k8s-doc.txt"},
    ExpiresIn=3600,
)
print(f"Download URL (1h): {download_url}")

# Generate presigned URL for upload (valid 15 minutes)
upload_url = s3.generate_presigned_url(
    "put_object",
    Params={"Bucket": "documents", "Key": "user-uploads/file.pdf"},
    ExpiresIn=900,
)
print(f"Upload URL (15m): {upload_url}")

# Frontend can use this URL directly:
# fetch(uploadUrl, { method: 'PUT', body: file })
```

---

### Exercise 5: Bucket Notifications (Webhook on Upload)

```python
# Configure bucket notification to trigger processing
import json
import boto3
from botocore.client import Config

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="admin",
    aws_secret_access_key="secretpassword",
    config=Config(signature_version="s3v4"),
)

# In production, configure via mc:
# mc event add local/documents arn:minio:sqs::_:webhook --event put --suffix .pdf

# Python listener (simplified — in production use webhook endpoint)
# This polls for new objects
import time

seen_keys = set()

while True:
    response = s3.list_objects_v2(Bucket="documents", Prefix="uploads/")
    for obj in response.get("Contents", []):
        if obj["Key"] not in seen_keys:
            seen_keys.add(obj["Key"])
            print(f"New file detected: {obj['Key']} ({obj['Size']} bytes)")
            # Trigger processing pipeline
            process_document(obj["Key"])
    time.sleep(5)

def process_document(key: str):
    """Download, chunk, embed, and store in pgvector."""
    response = s3.get_object(Bucket="documents", Key=key)
    content = response["Body"].read().decode("utf-8")
    print(f"Processing: {key} ({len(content)} chars)")
    # 1. Split into chunks
    # 2. Generate embeddings
    # 3. Store in pgvector
    # 4. Move original to "processed" prefix
    s3.copy_object(
        Bucket="documents",
        CopySource=f"documents/{key}",
        Key=key.replace("uploads/", "processed/"),
    )
```

---

### Exercise 6: Store and Retrieve Model Artifacts

```python
# model_artifacts.py
import boto3
import json
import os
from botocore.client import Config
from datetime import datetime

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="admin",
    aws_secret_access_key="secretpassword",
    config=Config(signature_version="s3v4"),
)

def save_model(model_name: str, version: str, model_path: str, metrics: dict):
    """Save model artifact with metadata."""
    key = f"{model_name}/{version}/model.bin"

    # Upload model file
    s3.upload_file(
        model_path,
        "models",
        key,
        ExtraArgs={
            "Metadata": {
                "model-name": model_name,
                "version": version,
                "created": datetime.utcnow().isoformat(),
            }
        },
    )

    # Save metrics alongside
    s3.put_object(
        Bucket="models",
        Key=f"{model_name}/{version}/metrics.json",
        Body=json.dumps(metrics, indent=2),
        ContentType="application/json",
    )
    print(f"Saved {model_name} v{version}")

def load_model(model_name: str, version: str, download_path: str):
    """Download model artifact."""
    key = f"{model_name}/{version}/model.bin"
    s3.download_file("models", key, download_path)

    # Get metrics
    response = s3.get_object(Bucket="models", Key=f"{model_name}/{version}/metrics.json")
    metrics = json.loads(response["Body"].read())
    print(f"Loaded {model_name} v{version}, metrics: {metrics}")
    return metrics

def list_models():
    """List all model versions."""
    response = s3.list_objects_v2(Bucket="models", Delimiter="/")
    for prefix in response.get("CommonPrefixes", []):
        model_name = prefix["Prefix"].rstrip("/")
        versions = s3.list_objects_v2(Bucket="models", Prefix=f"{model_name}/", Delimiter="/")
        for v in versions.get("CommonPrefixes", []):
            print(f"  {v['Prefix']}")
```

---

### Exercise 7: Document Ingestion Pipeline

```python
# document_pipeline.py
import boto3
import hashlib
from pathlib import Path
from botocore.client import Config

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
    aws_access_key_id="admin",
    aws_secret_access_key="secretpassword",
    config=Config(signature_version="s3v4"),
)

class DocumentPipeline:
    def __init__(self):
        self.bucket = "documents"

    def upload(self, file_path: str) -> dict:
        """Upload document and return metadata."""
        path = Path(file_path)
        content = path.read_bytes()
        file_hash = hashlib.sha256(content).hexdigest()[:16]

        key = f"raw/{file_hash}/{path.name}"
        s3.upload_file(
            str(path),
            self.bucket,
            key,
            ExtraArgs={
                "Metadata": {
                    "original-name": path.name,
                    "content-hash": file_hash,
                    "size-bytes": str(len(content)),
                },
                "ContentType": self._guess_type(path.suffix),
            },
        )
        return {"key": key, "hash": file_hash, "size": len(content)}

    def chunk_and_store(self, key: str, chunk_size: int = 1000):
        """Download, chunk, and re-upload as individual chunks."""
        response = s3.get_object(Bucket=self.bucket, Key=key)
        text = response["Body"].read().decode("utf-8")

        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

        for i, chunk in enumerate(chunks):
            chunk_key = key.replace("raw/", "chunks/") + f".chunk-{i:04d}"
            s3.put_object(
                Bucket=self.bucket,
                Key=chunk_key,
                Body=chunk.encode("utf-8"),
                Metadata={"chunk-index": str(i), "total-chunks": str(len(chunks))},
            )

        print(f"Stored {len(chunks)} chunks for {key}")
        return len(chunks)

    def _guess_type(self, suffix: str) -> str:
        types = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown"}
        return types.get(suffix, "application/octet-stream")

# Usage
pipeline = DocumentPipeline()
result = pipeline.upload("./sample-doc.txt")
pipeline.chunk_and_store(result["key"])
```

---

## 6. Kubernetes Deployment

```yaml
# minio-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: minio
  namespace: ai-platform
spec:
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: minio/minio
          args: ["server", "/data", "--console-address", ":9001"]
          env:
            - name: MINIO_ROOT_USER
              valueFrom:
                secretKeyRef:
                  name: minio-credentials
                  key: access-key
            - name: MINIO_ROOT_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: minio-credentials
                  key: secret-key
          ports:
            - containerPort: 9000
            - containerPort: 9001
          volumeMounts:
            - name: data
              mountPath: /data
          readinessProbe:
            httpGet:
              path: /minio/health/ready
              port: 9000
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: minio-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: minio
  namespace: ai-platform
spec:
  selector:
    app: minio
  ports:
    - name: api
      port: 9000
    - name: console
      port: 9001
```

---

## 7. How It's Used in Our Project

- **Document storage** — Users upload PDFs/docs → stored in MinIO → chunked → embedded → pgvector
- **Model artifacts** — GGUF model files stored in MinIO, downloaded by llama.cpp pods
- **Presigned URLs** — Frontend gets temporary upload URLs, uploads directly to MinIO
- **Combined with pgvector** — Raw files in MinIO, vector representations in PostgreSQL

---

## 8. Best Practices & Further Reading

### Best Practices

1. **Use versioning** for important buckets (documents, models)
2. **Set lifecycle policies** to auto-delete old temporary files
3. **Use presigned URLs** instead of proxying through your API
4. **Encrypt at rest** for sensitive data
5. **Use multipart upload** for files >100MB

### Further Reading

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [MinIO Client Reference](https://min.io/docs/minio/linux/reference/minio-mc.html)
