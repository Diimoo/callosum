# AWS ECS Fargate CloudFormation Deployment

Deploy Onyx to AWS using ECS Fargate with CloudFormation templates.

## Overview

This deployment creates a fully managed Onyx stack on AWS ECS Fargate, including:

- ECS Cluster with Fargate tasks
- EFS for persistent storage
- ACM certificates for SSL
- All required Onyx services

## Prerequisites

- AWS CLI configured with appropriate credentials
- `jq` installed for JSON processing
- An AWS account with permissions for ECS, EFS, ACM, CloudFormation

## Quick Start

1. Configure `onyx_config.jsonl`:
   ```jsonl
   {
     "Environment": "production",
     "AWSRegion": "us-east-2",
     "S3Bucket": "your-config-bucket"
   }
   ```

2. Deploy:
   ```bash
   ./deploy.sh
   ```

3. To uninstall:
   ```bash
   ./uninstall.sh
   ```

## Configuration

Edit `onyx_config.jsonl` with your settings:

| Parameter | Description |
|-----------|-------------|
| `Environment` | Environment name (required) |
| `AWSRegion` | AWS region (default: us-east-2) |
| `S3Bucket` | S3 bucket for configs (default: onyx-ecs-fargate-configs) |

## Templates

### Infrastructure Templates

| Template | Description |
|----------|-------------|
| `onyx_efs_template.yaml` | EFS file system for persistent storage |
| `onyx_cluster_template.yaml` | ECS cluster configuration |
| `onyx_acm_template.yaml` | ACM certificate for SSL |

### Service Templates (in `services/`)

| Template | Description |
|----------|-------------|
| `onyx_postgres_service_template.yaml` | PostgreSQL database |
| `onyx_redis_service_template.yaml` | Redis cache |
| `onyx_vespaengine_service_template.yaml` | Vespa search engine |
| `onyx_model_server_indexing_service_template.yaml` | Indexing model server |
| `onyx_model_server_inference_service_template.yaml` | Inference model server |
| `onyx_backend_api_server_service_template.yaml` | API server |
| `onyx_backend_background_server_service_template.yaml` | Background worker |
| `onyx_web_server_service_template.yaml` | Web frontend |
| `onyx_nginx_service_template.yaml` | Nginx reverse proxy |

## Deployment Order

The `deploy.sh` script deploys templates in this order:

1. **Infrastructure**: EFS → Cluster → ACM
2. **Services**: Postgres → Redis → Vespa → Model Servers → Backend → Web → Nginx

## Scripts

- **`deploy.sh`**: Deploy or update the entire stack
- **`uninstall.sh`**: Remove all CloudFormation stacks

## Customization

Modify individual service templates in `services/` to adjust:

- Task CPU/memory allocations
- Container environment variables
- Health check configurations
- Scaling policies

## Documentation

For complete AWS deployment documentation, see: https://docs.onyx.app/deployment/overview
