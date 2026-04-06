# Tutorial 15: OPA Gatekeeper — Kubernetes Policy Enforcement

> **Objective:** Learn to enforce security and governance policies on Kubernetes using OPA Gatekeeper.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [OPA & Rego](#2-opa--rego)
3. [Gatekeeper Concepts](#3-gatekeeper-concepts)
4. [Installation & Setup](#4-installation--setup)
5. [Exercises](#5-exercises)
6. [How It's Used in Our Project](#6-how-its-used-in-our-project)
7. [Testing & Further Reading](#7-testing--further-reading)

---

## 1. Introduction

### What is Policy-as-Code?

Instead of documenting rules in a wiki ("all pods must have resource limits"), you encode them as executable policies that are **automatically enforced**.

```
Without policy:  Developer forgets resource limits → Pod OOM kills, node crash
With Gatekeeper: kubectl apply → DENIED: "Container must set memory limit" → Fixed before deploy
```

### What is OPA?

**Open Policy Agent (OPA)** is a general-purpose policy engine. You write policies in **Rego** (a declarative language), and OPA evaluates them.

### What is Gatekeeper?

**Gatekeeper** is OPA integrated into Kubernetes as an admission controller. It intercepts every API request (`kubectl apply`, `create`, `update`) and checks it against your policies.

```
kubectl apply → [API Server] → [Gatekeeper Webhook] → ALLOW or DENY → [etcd]
```

---

## 2. OPA & Rego

### Rego Basics

```rego
# A simple rule
package example

# Deny if no labels
deny[msg] {
    input.kind == "Pod"
    not input.metadata.labels.team
    msg := "Pod must have a 'team' label"
}
```

### Rego Syntax

```rego
package kubernetes.policies

# Variables
name := input.metadata.name

# Conditions (AND — all must be true)
deny[msg] {
    input.kind == "Deployment"              # Is a Deployment
    input.spec.replicas < 2                 # Less than 2 replicas
    msg := sprintf("Deployment %s must have at least 2 replicas", [name])
}

# Iteration (check all containers)
deny[msg] {
    container := input.spec.containers[_]   # For each container
    not container.resources.limits.memory    # Missing memory limit
    msg := sprintf("Container %s must set memory limit", [container.name])
}

# Functions
is_privileged(container) {
    container.securityContext.privileged == true
}

# Helper with default
has_label(obj, label) {
    obj.metadata.labels[label]
}

# Negation
deny[msg] {
    not has_label(input, "team")
    msg := "Resource must have 'team' label"
}
```

---

## 3. Gatekeeper Concepts

### ConstraintTemplate

Defines a **reusable policy type** with Rego logic:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels

        deny[{"msg": msg}] {
          provided := {label | input.review.object.metadata.labels[label]}
          required := {label | label := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("Missing required labels: %v", [missing])
        }
```

### Constraint

Applies a template with specific parameters:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-team-label
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
    namespaces: ["ai-platform"]
  parameters:
    labels: ["team", "environment"]
```

### Enforcement Actions

| Action | Effect |
|--------|--------|
| `deny` | Block the request (default) |
| `warn` | Allow but log a warning |
| `dryrun` | Log only, don't enforce |

---

## 4. Installation & Setup

```bash
# Install Gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.15/deploy/gatekeeper.yaml

# Verify
kubectl get pods -n gatekeeper-system
kubectl get constrainttemplates

# Install OPA CLI (for testing)
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
chmod +x opa && sudo mv opa /usr/local/bin/
```

---

## 5. Exercises

### Exercise 1: Basic ConstraintTemplate — Required Labels

```yaml
# required-labels-template.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            labels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels

        deny[{"msg": msg}] {
          provided := {l | input.review.object.metadata.labels[l]}
          required := {l | l := input.parameters.labels[_]}
          missing := required - provided
          count(missing) > 0
          msg := sprintf("Missing labels: %v on %s/%s",
            [missing, input.review.object.kind, input.review.object.metadata.name])
        }
```

```yaml
# require-labels.yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-team-env-labels
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet"]
  parameters:
    labels: ["team", "environment"]
```

```bash
kubectl apply -f required-labels-template.yaml
kubectl apply -f require-labels.yaml

# Test — this should be DENIED
kubectl create deployment test --image=nginx
# Error: Missing labels: {"environment", "team"}

# This should succeed
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-ok
  labels:
    team: ml
    environment: dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
        - name: test
          image: nginx
EOF
```

---

### Exercise 2: Deny Containers Running as Root

```yaml
# no-root-template.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoroot
spec:
  crd:
    spec:
      names:
        kind: K8sNoRoot
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8snoroot

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.securityContext.runAsNonRoot
          msg := sprintf("Container %s must set runAsNonRoot: true", [container.name])
        }

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          container.securityContext.runAsUser == 0
          msg := sprintf("Container %s must not run as root (UID 0)", [container.name])
        }
```

```yaml
# no-root-constraint.yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sNoRoot
metadata:
  name: deny-root-containers
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet"]
    excludedNamespaces: ["kube-system", "gatekeeper-system"]
```

---

### Exercise 3: Enforce Resource Limits

```yaml
# resource-limits-template.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sresourcelimits
spec:
  crd:
    spec:
      names:
        kind: K8sResourceLimits
      validation:
        openAPIV3Schema:
          type: object
          properties:
            maxCPU:
              type: string
            maxMemory:
              type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sresourcelimits

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.resources.limits.cpu
          msg := sprintf("Container %s must set CPU limit", [container.name])
        }

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.resources.limits.memory
          msg := sprintf("Container %s must set memory limit", [container.name])
        }

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.resources.requests.cpu
          msg := sprintf("Container %s must set CPU request", [container.name])
        }

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.resources.requests.memory
          msg := sprintf("Container %s must set memory request", [container.name])
        }
```

```yaml
# resource-limits-constraint.yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sResourceLimits
metadata:
  name: require-resource-limits
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
    excludedNamespaces: ["kube-system"]
```

---

### Exercise 4: Restrict Container Registries

```yaml
# allowed-repos-template.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sallowedrepos
spec:
  crd:
    spec:
      names:
        kind: K8sAllowedRepos
      validation:
        openAPIV3Schema:
          type: object
          properties:
            repos:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sallowedrepos

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not startswith_any(container.image, input.parameters.repos)
          msg := sprintf("Container %s uses image %s from unauthorized registry. Allowed: %v",
            [container.name, container.image, input.parameters.repos])
        }

        startswith_any(str, prefixes) {
          prefix := prefixes[_]
          startswith(str, prefix)
        }
```

```yaml
# allowed-repos-constraint.yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sAllowedRepos
metadata:
  name: only-trusted-registries
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
      - apiGroups: ["apps"]
        kinds: ["Deployment", "StatefulSet"]
  parameters:
    repos:
      - "registry.example.com/"
      - "gcr.io/our-project/"
      - "ghcr.io/our-org/"
```

---

### Exercise 5: Block Privileged Containers

```yaml
# no-privileged-template.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8snoprivileged
spec:
  crd:
    spec:
      names:
        kind: K8sNoPrivileged
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8snoprivileged

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          container.securityContext.privileged
          msg := sprintf("Privileged containers not allowed: %s", [container.name])
        }

        deny[{"msg": msg}] {
          volume := input.review.object.spec.volumes[_]
          volume.hostPath
          msg := sprintf("hostPath volumes not allowed: %s", [volume.name])
        }

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          container.securityContext.capabilities.add[_] == "SYS_ADMIN"
          msg := sprintf("SYS_ADMIN capability not allowed: %s", [container.name])
        }
```

---

### Exercise 6: Custom Policy — LLM Model Version

```yaml
# model-version-template.yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8sllmmodelversion
spec:
  crd:
    spec:
      names:
        kind: K8sLLMModelVersion
      validation:
        openAPIV3Schema:
          type: object
          properties:
            allowedModels:
              type: array
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8sllmmodelversion

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          arg := container.args[_]
          startswith(arg, "--model")
          model_name := container.args[plus(i, 1)]
          not model_allowed(model_name)
          msg := sprintf("Model %s is not in the approved list: %v",
            [model_name, input.parameters.allowedModels])
        }

        deny[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          env := container.env[_]
          env.name == "MODEL_NAME"
          not model_allowed(env.value)
          msg := sprintf("Model %s is not approved. Allowed: %v",
            [env.value, input.parameters.allowedModels])
        }

        model_allowed(model) {
          allowed := input.parameters.allowedModels[_]
          contains(model, allowed)
        }
```

```yaml
# model-version-constraint.yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sLLMModelVersion
metadata:
  name: approved-models-only
spec:
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
    namespaces: ["ai-platform"]
  parameters:
    allowedModels:
      - "meta-llama/Meta-Llama-3"
      - "mistralai/Mistral"
      - "TinyLlama"
```

---

### Exercise 7: Audit Existing Violations

```bash
# Check for existing violations (dryrun mode)
kubectl get constraints -o wide

# See violations for a specific constraint
kubectl get k8srequiredlabels require-team-env-labels -o yaml

# Look at the status.violations field
kubectl get k8srequiredlabels require-team-env-labels -o jsonpath='{.status.violations}' | python -m json.tool

# Audit all constraints
for ct in $(kubectl get constraints -o name); do
  echo "=== $ct ==="
  kubectl get $ct -o jsonpath='{.status.totalViolations}' 2>/dev/null
  echo " violations"
done
```

Set enforcement to dryrun first, fix violations, then switch to deny:

```yaml
# Start with dryrun
spec:
  enforcementAction: dryrun  # Log only, don't block

# Then warn
spec:
  enforcementAction: warn    # Allow but warn

# Finally enforce
spec:
  enforcementAction: deny    # Block violations
```

---

### Exercise 8: Test Policies with OPA CLI

```bash
# Save Rego to a file
cat > policy.rego <<'EOF'
package k8srequiredlabels

deny[{"msg": msg}] {
  provided := {l | input.review.object.metadata.labels[l]}
  required := {l | l := input.parameters.labels[_]}
  missing := required - provided
  count(missing) > 0
  msg := sprintf("Missing labels: %v", [missing])
}
EOF

# Create test input
cat > input.json <<'EOF'
{
  "review": {
    "object": {
      "metadata": {
        "name": "test-app",
        "labels": {
          "app": "test"
        }
      }
    }
  },
  "parameters": {
    "labels": ["team", "environment"]
  }
}
EOF

# Evaluate
opa eval -d policy.rego -i input.json "data.k8srequiredlabels.deny"
# Should show: Missing labels: {"environment", "team"}

# Write unit tests
cat > policy_test.rego <<'EOF'
package k8srequiredlabels

test_deny_missing_labels {
  results := deny with input as {
    "review": {"object": {"metadata": {"labels": {"app": "test"}}}},
    "parameters": {"labels": ["team"]}
  }
  count(results) > 0
}

test_allow_all_labels {
  results := deny with input as {
    "review": {"object": {"metadata": {"labels": {"team": "ml", "env": "dev"}}}},
    "parameters": {"labels": ["team"]}
  }
  count(results) == 0
}
EOF

opa test . -v
```

---

## 6. How It's Used in Our Project

- **Required labels** — All resources must have `team` and `environment` labels
- **Resource limits** — Every container must set CPU/memory limits
- **Registry restrictions** — Only approved registries allowed
- **No root** — Containers must run as non-root
- **Model governance** — Only approved LLM models can be deployed
- **GPU limits** — Maximum GPU allocation per namespace

---

## 7. Testing & Further Reading

### Testing Best Practices

1. **Start with dryrun** — Find existing violations before enforcing
2. **Unit test with OPA CLI** — Test Rego logic before deploying
3. **Use warn first** — Let teams fix issues before blocking
4. **Exclude system namespaces** — Don't break kube-system
5. **Version your policies** — Store in Git alongside infrastructure code

### Further Reading

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Gatekeeper Documentation](https://open-policy-agent.github.io/gatekeeper/)
- [Rego Playground](https://play.openpolicyagent.org/)
- [Gatekeeper Library](https://open-policy-agent.github.io/gatekeeper-library/)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-reference/)
