# LICS Infrastructure

[![Infrastructure CI](https://github.com/rsongphon/Primates-lics/workflows/Infrastructure%20CI/badge.svg)](https://github.com/rsongphon/Primates-lics/actions)
[![Terraform](https://img.shields.io/badge/Terraform-1.6+-purple.svg)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28+-blue.svg)](https://kubernetes.io/)

Infrastructure as Code (IaC) for the LICS platform, providing automated provisioning and management of cloud resources, container orchestration, and configuration management.

## 🛠️ Tech Stack

- **Infrastructure**: Terraform 1.6+
- **Orchestration**: Kubernetes 1.28+
- **Configuration**: Ansible
- **Cloud**: AWS (primary), Azure, GCP support
- **Monitoring**: Prometheus, Grafana, Alertmanager
- **Service Mesh**: Istio
- **GitOps**: ArgoCD
- **Secrets**: HashiCorp Vault / AWS Secrets Manager

## 📁 Structure

```
infrastructure/
├── terraform/              # Terraform configurations
│   ├── environments/        # Environment-specific configs
│   │   ├── dev/            # Development environment
│   │   ├── staging/        # Staging environment
│   │   └── prod/           # Production environment
│   ├── modules/            # Reusable Terraform modules
│   │   ├── eks/            # EKS cluster module
│   │   ├── rds/            # Database module
│   │   ├── vpc/            # Networking module
│   │   └── monitoring/     # Monitoring stack
│   └── shared/             # Shared resources
├── kubernetes/             # Kubernetes manifests
│   ├── base/               # Base configurations
│   ├── overlays/           # Kustomize overlays
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── charts/             # Helm charts
└── ansible/                # Configuration management
    ├── playbooks/          # Ansible playbooks
    ├── roles/              # Ansible roles
    └── inventory/          # Environment inventories
```

## 🚀 Quick Start

### Prerequisites

- **Terraform** 1.6+
- **kubectl** 1.28+
- **Helm** 3.10+
- **Ansible** 6.0+
- **AWS CLI** (if using AWS)
- **Docker** (for local testing)

### Initial Setup

1. **Clone and navigate**
   ```bash
   cd infrastructure
   ```

2. **Configure cloud credentials**
   ```bash
   # AWS
   aws configure

   # Or set environment variables
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-west-2
   ```

3. **Initialize Terraform**
   ```bash
   cd terraform/environments/dev
   terraform init
   ```

4. **Plan and apply infrastructure**
   ```bash
   # Review planned changes
   terraform plan

   # Apply changes
   terraform apply
   ```

5. **Configure kubectl**
   ```bash
   # Update kubeconfig for EKS
   aws eks update-kubeconfig --region us-west-2 --name lics-dev-cluster
   ```

6. **Deploy applications**
   ```bash
   cd ../../kubernetes
   kubectl apply -k overlays/dev/
   ```

## ☁️ Cloud Architecture

### AWS Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Region    │  │   Region    │  │   Region    │         │
│  │   us-west-2 │  │   us-east-1 │  │   eu-west-1 │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    VPC (10.0.0.0/16)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Public Subnet  │  │  Private Subnet │                  │
│  │  10.0.1.0/24    │  │  10.0.2.0/24    │                  │
│  │                 │  │                 │                  │
│  │  ┌─────────────┐│  │  ┌─────────────┐│                  │
│  │  │     ALB     ││  │  │ EKS Workers ││                  │
│  │  └─────────────┘│  │  └─────────────┘│                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Private Subnet │  │  Private Subnet │                  │
│  │  10.0.3.0/24    │  │  10.0.4.0/24    │                  │
│  │                 │  │                 │                  │
│  │  ┌─────────────┐│  │  ┌─────────────┐│                  │
│  │  │     RDS     ││  │  │   ElastiCache││                  │
│  │  └─────────────┘│  │  └─────────────┘│                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### Resource Overview

- **Compute**: EKS cluster with managed node groups
- **Database**: RDS PostgreSQL with TimescaleDB extension
- **Cache**: ElastiCache Redis
- **Storage**: S3 buckets for object storage
- **Networking**: VPC with public/private subnets, NAT Gateway
- **Load Balancing**: Application Load Balancer (ALB)
- **DNS**: Route 53 for domain management
- **Monitoring**: CloudWatch, Prometheus, Grafana

## 🏗️ Terraform

### Module Structure

```hcl
# terraform/modules/eks/main.tf
resource "aws_eks_cluster" "lics" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.public_access_cidrs
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy,
    aws_iam_role_policy_attachment.vpc_resource_controller,
  ]
}

resource "aws_eks_node_group" "workers" {
  cluster_name    = aws_eks_cluster.lics.name
  node_group_name = "${var.cluster_name}-workers"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = var.private_subnet_ids

  instance_types = var.instance_types
  capacity_type  = var.capacity_type

  scaling_config {
    desired_size = var.desired_capacity
    max_size     = var.max_capacity
    min_size     = var.min_capacity
  }

  update_config {
    max_unavailable = 1
  }
}
```

### Environment Configuration

```hcl
# terraform/environments/dev/main.tf
module "vpc" {
  source = "../../modules/vpc"

  name               = "lics-dev"
  cidr               = "10.0.0.0/16"
  availability_zones = ["us-west-2a", "us-west-2b", "us-west-2c"]

  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnets = ["10.0.4.0/24", "10.0.5.0/24", "10.0.6.0/24"]

  enable_nat_gateway = true
  enable_vpn_gateway = false

  tags = local.common_tags
}

module "eks" {
  source = "../../modules/eks"

  cluster_name       = "lics-dev"
  kubernetes_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  node_groups = {
    workers = {
      instance_types = ["t3.medium"]
      min_capacity   = 1
      max_capacity   = 5
      desired_capacity = 2
    }
  }
}
```

### State Management

```hcl
# terraform/environments/dev/backend.tf
terraform {
  backend "s3" {
    bucket         = "lics-terraform-state-dev"
    key            = "dev/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "lics-terraform-locks"
  }
}
```

## ☸️ Kubernetes

### Application Deployment

```yaml
# kubernetes/base/backend/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lics-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lics-backend
  template:
    metadata:
      labels:
        app: lics-backend
    spec:
      containers:
      - name: backend
        image: lics/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: lics-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service Configuration

```yaml
# kubernetes/base/backend/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: lics-backend
spec:
  selector:
    app: lics-backend
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
```

### Ingress Configuration

```yaml
# kubernetes/base/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lics-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - host: api.lics.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: lics-backend
            port:
              number: 80
  - host: app.lics.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: lics-frontend
            port:
              number: 80
```

### Kustomization

```yaml
# kubernetes/overlays/dev/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: lics-dev

resources:
- ../../base

patchesStrategicMerge:
- deployment-patch.yaml
- configmap-patch.yaml

images:
- name: lics/backend
  newTag: dev-latest
- name: lics/frontend
  newTag: dev-latest

replicas:
- name: lics-backend
  count: 2
- name: lics-frontend
  count: 2
```

## 📊 Monitoring Stack

### Prometheus Configuration

```yaml
# kubernetes/base/monitoring/prometheus.yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: prometheus
spec:
  serviceAccountName: prometheus
  serviceMonitorSelector:
    matchLabels:
      team: lics
  resources:
    requests:
      memory: 400Mi
  retention: 30d
  storage:
    volumeClaimTemplate:
      spec:
        storageClassName: gp2
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "LICS System Overview",
    "panels": [
      {
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends{datname=\"lics\"}"
          }
        ]
      }
    ]
  }
}
```

## 🔐 Security

### Network Policies

```yaml
# kubernetes/base/security/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: lics-backend-netpol
spec:
  podSelector:
    matchLabels:
      app: lics-backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: lics-frontend
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
```

### Pod Security Standards

```yaml
# kubernetes/base/security/pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: lics-restricted
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## 🎯 Deployment Strategies

### Blue-Green Deployment

```yaml
# kubernetes/base/deployments/blue-green.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: lics-backend
spec:
  replicas: 3
  strategy:
    blueGreen:
      activeService: lics-backend-active
      previewService: lics-backend-preview
      autoPromotionEnabled: false
      scaleDownDelaySeconds: 30
      prePromotionAnalysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: lics-backend-preview
      postPromotionAnalysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: lics-backend-active
  template:
    spec:
      containers:
      - name: backend
        image: lics/backend:latest
```

### Canary Deployment

```yaml
# kubernetes/base/deployments/canary.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: lics-frontend
spec:
  replicas: 5
  strategy:
    canary:
      steps:
      - setWeight: 20
      - pause: {duration: 10m}
      - setWeight: 50
      - pause: {duration: 10m}
      - setWeight: 80
      - pause: {duration: 10m}
      trafficRouting:
        istio:
          virtualService:
            name: lics-frontend-vs
          destinationRule:
            name: lics-frontend-dr
```

## 🧪 Testing

### Infrastructure Testing

```bash
# Terraform validation
terraform fmt -check -recursive
terraform validate

# Security scanning
checkov -d terraform/

# Cost estimation
infracost diff --path terraform/environments/prod
```

### Kubernetes Testing

```bash
# Validate manifests
kubectl apply --dry-run=client -f kubernetes/base/

# Security scanning
kubesec scan kubernetes/base/backend/deployment.yaml

# Policy testing
conftest verify --policy policy/ kubernetes/base/
```

## 📚 Runbooks

### Common Operations

#### Scale Application
```bash
# Scale backend replicas
kubectl scale deployment lics-backend --replicas=5

# Using Kustomize
kustomize edit set replicas lics-backend=5
kubectl apply -k overlays/prod/
```

#### Database Backup
```bash
# Create RDS snapshot
aws rds create-db-snapshot \
  --db-instance-identifier lics-prod-db \
  --db-snapshot-identifier lics-prod-backup-$(date +%Y%m%d)
```

#### Rolling Update
```bash
# Update image
kubectl set image deployment/lics-backend backend=lics/backend:v2.0.0

# Monitor rollout
kubectl rollout status deployment/lics-backend
```

## 🚨 Disaster Recovery

### Backup Strategy
- **Database**: Automated daily snapshots with 30-day retention
- **Configuration**: Git-based IaC with version control
- **Secrets**: HashiCorp Vault with automated backup
- **Application Data**: S3 cross-region replication

### Recovery Procedures
1. **RTO (Recovery Time Objective)**: 4 hours
2. **RPO (Recovery Point Objective)**: 1 hour
3. **Multi-region failover**: Automated DNS switching
4. **Database recovery**: Point-in-time recovery capability

## 🤝 Contributing

1. Follow Terraform best practices
2. Use proper resource tagging
3. Implement proper RBAC
4. Test infrastructure changes
5. Document architectural decisions

See the main [Contributing Guide](../CONTRIBUTING.md) for more details.

## 📚 Additional Resources

- [Terraform Documentation](https://www.terraform.io/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs)
- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [Helm Documentation](https://helm.sh/docs/)
- [Istio Documentation](https://istio.io/latest/docs/)