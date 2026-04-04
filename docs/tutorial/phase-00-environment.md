# Phase 0: Environment Setup

## Summary

Set up the DevContainer development environment and install the complete toolchain. By the end of this phase you will have a reproducible, containerized workspace with all CLI tools, language runtimes, and extensions pre-configured.

## Learning Objectives

- Understand DevContainer configuration and lifecycle hooks
- Configure Docker-in-Docker for nested container builds
- Verify all toolchain binaries (Python, Node, Go, kubectl, helm, etc.)
- Set up editor extensions for linting, formatting, and type checking

## Key Commands

```bash
# Rebuild the DevContainer from scratch
devcontainer up --workspace-folder .

# Verify toolchain versions
python --version && node --version && go version

# Run the environment smoke test
make check-env
```

## Slash Command

Run `/00-setup-env` in Claude Code to begin this phase.

## Next Phase

[Phase 1: API Layer](phase-01-api-layer.md)
