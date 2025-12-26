# Helm Chart for Onyx

Deploy Onyx to Kubernetes using Helm.

## Prerequisites

- Kubernetes cluster (1.24+)
- Helm 3.x
- `kubectl` configured for your cluster

## Quick Start

```bash
# Add dependencies
helm dependency update ./charts/onyx

# Install Onyx
helm install onyx ./charts/onyx --namespace onyx --create-namespace

# Install with custom values
helm install onyx ./charts/onyx -f my-values.yaml --namespace onyx --create-namespace
```

## Chart Structure

```
deployment/helm/
└── charts/
    └── onyx/
        ├── Chart.yaml          # Chart metadata and dependencies
        ├── values.yaml         # Default configuration values
        ├── templates/          # Kubernetes manifests
        └── templates_disabled/ # Optional components
```

## Dependencies

The chart includes these optional dependencies (enabled by default):

| Dependency | Description | Condition |
|------------|-------------|-----------|
| cloudnative-pg | PostgreSQL operator | `postgresql.enabled` |
| vespa | Search engine | `vespa.enabled` |
| ingress-nginx | Ingress controller | `nginx.enabled` |
| redis | Cache | `redis.enabled` |
| minio | Object storage | `minio.enabled` |
| code-interpreter | Code execution sandbox | `codeInterpreter.enabled` |

## Configuration

Key configuration options in `values.yaml`:

### Global Settings

```yaml
global:
  version: "latest"        # Onyx version
  pullPolicy: "IfNotPresent"
```

### Resource Allocation

```yaml
vespa:
  resources:
    requests:
      cpu: 4000m
      memory: 8000Mi
    limits:
      cpu: 8000m
      memory: 32000Mi

inferenceCapability:
  resources:
    requests:
      cpu: 2000m
      memory: 3Gi
```

### Storage

```yaml
postgresql:
  cluster:
    storage:
      size: 10Gi

vespa:
  volumeClaimTemplates:
    - spec:
        resources:
          requests:
            storage: 30Gi
```

### Autoscaling

```yaml
autoscaling:
  engine: hpa  # or 'keda' for KEDA ScaledObjects
```

## Common Operations

```bash
# Upgrade release
helm upgrade onyx ./charts/onyx --namespace onyx

# View current values
helm get values onyx --namespace onyx

# Uninstall
helm uninstall onyx --namespace onyx
```

## Using External Services

To use external PostgreSQL, Redis, or S3:

```yaml
postgresql:
  enabled: false

redis:
  enabled: false

minio:
  enabled: false
```

Then configure connection details via environment variables or secrets.

## Documentation

For detailed deployment guides, see: https://docs.onyx.app/deployment/overview
