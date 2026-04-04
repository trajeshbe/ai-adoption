# ============================================================================
# DevContainer: AI Agent Platform Development Environment
# Base: Python 3.11 + Node 20 + All CLI tools for cloud-native AI development
#
# Derived from: github.com/trajeshbe/merit-aiml (kiaa-gpu branch)
# ============================================================================

FROM mcr.microsoft.com/devcontainers/python:3.11-bookworm

ARG NODE_VERSION=20
ARG PNPM_VERSION=9
ARG UV_VERSION=0.5
ARG KUBECTL_VERSION=1.30.0
ARG HELM_VERSION=3.16.0
ARG SKAFFOLD_VERSION=2.13.0
ARG K9S_VERSION=0.32.0
ARG MIRRORD_VERSION=3.120.0

# ── System dependencies (from merit-aiml backend/Dockerfile) ─────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    wget \
    git \
    jq \
    yq \
    unzip \
    gnupg2 \
    lsb-release \
    ca-certificates \
    # OCR + document processing (from merit-aiml requirements)
    tesseract-ocr \
    poppler-utils \
    libmagic1 \
    # Playwright system deps
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# ── Node.js + pnpm ──────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm@${PNPM_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# ── Python tooling: uv (fast pip replacement) ───────────────────────────
RUN pip install --no-cache-dir uv>=${UV_VERSION}

# ── kubectl ─────────────────────────────────────────────────────────────
RUN curl -fsSLo /usr/local/bin/kubectl \
    "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && chmod +x /usr/local/bin/kubectl

# ── Helm ────────────────────────────────────────────────────────────────
RUN curl -fsSL https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz \
    | tar xz -C /usr/local/bin --strip-components=1 linux-amd64/helm

# ── Skaffold ────────────────────────────────────────────────────────────
RUN curl -fsSLo /usr/local/bin/skaffold \
    "https://storage.googleapis.com/skaffold/releases/v${SKAFFOLD_VERSION}/skaffold-linux-amd64" \
    && chmod +x /usr/local/bin/skaffold

# ── k9s (Kubernetes TUI) ───────────────────────────────────────────────
RUN curl -fsSL "https://github.com/derailed/k9s/releases/download/v${K9S_VERSION}/k9s_Linux_amd64.tar.gz" \
    | tar xz -C /usr/local/bin k9s

# ── mirrord (local-to-remote debugging) ─────────────────────────────────
RUN curl -fsSL https://raw.githubusercontent.com/metalbear-co/mirrord/main/scripts/install.sh | bash

# ── Tekton CLI ──────────────────────────────────────────────────────────
RUN curl -fsSL https://github.com/tektoncd/cli/releases/latest/download/tkn_Linux_x86_64.tar.gz \
    | tar xz -C /usr/local/bin tkn

# ── Argo CD CLI ─────────────────────────────────────────────────────────
RUN curl -fsSLo /usr/local/bin/argocd \
    "https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64" \
    && chmod +x /usr/local/bin/argocd

# ── Pre-commit ──────────────────────────────────────────────────────────
RUN pip install --no-cache-dir pre-commit

# ── Claude Code CLI (from merit-aiml .devcontainer) ─────────────────────
RUN npm install -g @anthropic-ai/claude-code

# Set workspace
WORKDIR /workspace
