# WaterPulse — Kubernetes (kind) Setup Guide

This guide walks through deploying WaterPulse on a local **kind** (Kubernetes IN Docker) cluster. The setup produces the same result as `docker-compose up` — the app is accessible at `http://localhost` — but uses Kubernetes resources instead of Docker Compose.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Step-by-Step Walkthrough](#step-by-step-walkthrough)
- [Manifest Reference](#manifest-reference)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)
- [Cloud Deployment Path](#cloud-deployment-path)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Browser (http://localhost)                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ port 80
┌──────────────────────▼──────────────────────────────────────┐
│  NGINX Ingress Controller                                    │
│  (installed separately — replaces docker-compose Nginx)      │
│                                                              │
│  Routing rules:                                              │
│    /api/*        → backend-service:8000                      │
│    /docs         → backend-service:8000                      │
│    /openapi.json → backend-service:8000                      │
│    /*            → frontend-service:3000                     │
└───────┬───────────────────────────────┬─────────────────────┘
        │                               │
┌───────▼──────────┐          ┌─────────▼────────────┐
│  backend-service │          │  frontend-service    │
│  (ClusterIP)     │          │  (ClusterIP)         │
│  port 8000       │          │  port 3000           │
└───────┬──────────┘          └──────────────────────┘
        │
┌───────▼──────────┐
│  db-service      │
│  (ClusterIP)     │
│  port 5432       │
└───────┬──────────┘
        │
┌───────▼──────────┐
│  PostgreSQL 16   │
│  PVC: 2Gi        │
└──────────────────┘
```

### How it maps to Docker Compose

| Docker Compose Service | Kubernetes Resource(s) |
|------------------------|------------------------|
| `db:` | Deployment + Service + PVC |
| `backend:` | Deployment + Service |
| `frontend:` | Deployment + Service |
| `nginx:` | Ingress (handled by NGINX Ingress Controller) |
| `.env` file | Secret + ConfigMap |
| `pgdata` volume | PersistentVolumeClaim |
| Docker internal DNS | Kubernetes DNS (Service names) |

---

## Prerequisites

Install these tools before proceeding:

### 1. Docker Desktop
Already installed if you've been using docker-compose. Ensure it's running.

### 2. kind (Kubernetes IN Docker)
```bash
choco install kind
```
kind creates a Kubernetes cluster using Docker containers as "nodes." Each node is a Docker container that runs the Kubernetes components inside it.

### 3. kubectl (Kubernetes CLI)
```bash
choco install kubernetes-cli
```
kubectl is the command-line tool for interacting with any Kubernetes cluster. It sends commands to the cluster's API server.

### Verify installations
```bash
docker --version
kind --version
kubectl version --client
```

---

## Quick Start

Run these commands in order from the project root:

```bash
# 1. Create the kind cluster
kind create cluster --name waterpulse --config k8s/kind-cluster.yaml

# 2. Install the NGINX Ingress Controller (replaces our Nginx container)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# 3. Build Docker images and load them into kind
docker build -t waterpulse-backend:latest ./waterpulse-backend
docker build -t waterpulse-frontend:latest --build-arg NEXT_PUBLIC_API_URL=http://localhost ./waterpulse-frontend
kind load docker-image waterpulse-backend:latest --name waterpulse
kind load docker-image waterpulse-frontend:latest --name waterpulse

# Verify images were loaded into the kind node
docker exec waterpulse-control-plane crictl images | grep waterpulse

# 4. Create secrets (copy example and fill in real values first!)
cp k8s/secrets.yaml.example k8s/secrets.yaml
# Edit k8s/secrets.yaml — replace placeholders with base64-encoded values
# IMPORTANT: Values MUST be base64-encoded, not plain text!
#
# On PowerShell (Windows):
#   [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-value"))
#
# On Bash (Linux/Mac/Git Bash):
#   echo -n "your-value" | base64
#
# WARNING: Do NOT use "echo -n" in PowerShell — it does not suppress
# newlines the way Bash does, resulting in a hidden newline in the
# encoded value that will break database authentication.

# 5. Apply all manifests (order matters!)
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/db-pvc.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/db-service.yaml
kubectl wait --namespace waterpulse --for=condition=ready pod --selector=app=db --timeout=60s
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/job-historical-sync.yaml

# 6. Verify everything is running
kubectl get all -n waterpulse

# 7. (Optional) Run the historical sync now instead of waiting for Jan 1st
kubectl create job --from=cronjob/historical-sync manual-sync -n waterpulse
kubectl logs -f job/manual-sync -n waterpulse
```

Open **http://localhost** in your browser. The dashboard should load and display stations.

---

## Step-by-Step Walkthrough

### Step 1: Create the kind cluster

```bash
kind create cluster --name waterpulse --config k8s/kind-cluster.yaml
```

**What this does:**
- Creates a single Docker container that runs a full Kubernetes cluster inside it
- The `kind-cluster.yaml` config maps host port 80 into the cluster (so `http://localhost` reaches the Ingress Controller)
- Labels the node as `ingress-ready=true` (the Ingress Controller only runs on nodes with this label)

**Verify:**
```bash
kubectl cluster-info --context kind-waterpulse
kubectl get nodes
```

### Step 2: Install the NGINX Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
```

**What this does:**
- Installs the NGINX Ingress Controller into the `ingress-nginx` namespace
- The controller watches for Ingress resources and configures Nginx routing automatically
- This replaces the standalone Nginx container from docker-compose
- The kind-specific version is configured to use `hostPort` (mapping to the node's port 80)

**Wait for it to be ready:**
```bash
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```

### Step 3: Build and load images

```bash
docker build -t waterpulse-backend:latest ./waterpulse-backend
docker build -t waterpulse-frontend:latest --build-arg NEXT_PUBLIC_API_URL=http://localhost ./waterpulse-frontend
```

**Why `NEXT_PUBLIC_API_URL=http://localhost`?**
Next.js bakes `NEXT_PUBLIC_*` variables into the JavaScript at build time. With the Ingress, both the frontend and API are served from `localhost:80`, so the browser sends API requests to `http://localhost/api/*`, which the Ingress routes to the backend.

```bash
kind load docker-image waterpulse-backend:latest --name waterpulse
kind load docker-image waterpulse-frontend:latest --name waterpulse
```

**Why `kind load`?**
kind clusters can't pull images from your local Docker daemon — they run in an isolated Docker container. `kind load` copies your locally-built images into the kind node so Kubernetes can use them.

**Verify images were loaded:**
```bash
docker exec waterpulse-control-plane crictl images | grep waterpulse
```
You should see both `waterpulse-backend` and `waterpulse-frontend` in the output. If either is missing, re-run the `kind load` command for that image.

### Step 4: Create secrets

```bash
cp k8s/secrets.yaml.example k8s/secrets.yaml
```

Edit `k8s/secrets.yaml` and replace the placeholder values with base64-encoded secrets.

**Kubernetes Secrets require base64-encoded values, not plain text.** The encoding method depends on your shell:

**PowerShell (Windows):**
```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-postgres-password"))
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-jwt-secret-key"))
```

**Bash (Linux/Mac/Git Bash):**
```bash
echo -n "your-postgres-password" | base64
echo -n "your-jwt-secret-key" | base64
```

> **WARNING:** Do NOT use `echo -n` in PowerShell — it does not suppress newlines the way Bash does. The hidden newline gets base64-encoded into the value, resulting in a password like `MyPassword\n` that silently breaks database authentication. Always use the `[Convert]` method above on Windows.

Paste the encoded values into `k8s/secrets.yaml`. **Never commit this file** — it's already in `.gitignore`.

### Step 5: Apply manifests

The order matters because some resources depend on others:

```bash
# Namespace first — everything else goes inside it
kubectl apply -f k8s/namespace.yaml

# Secrets and ConfigMap — referenced by Deployments
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml

# Database — must be ready before backend starts
kubectl apply -f k8s/db-pvc.yaml
kubectl apply -f k8s/db-deployment.yaml
kubectl apply -f k8s/db-service.yaml

# Wait for database to be ready before starting the backend
kubectl wait --namespace waterpulse --for=condition=ready pod --selector=app=db --timeout=60s

# Backend — needs database running for migrations
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml

# Frontend — independent of backend (just serves static pages)
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml

# Ingress — routes external traffic to the services
kubectl apply -f k8s/ingress.yaml

# CronJob — annual historical sync (runs Jan 1st at 03:00 UTC)
kubectl apply -f k8s/job-historical-sync.yaml
```

### Step 6: Run the historical sync (optional)

The CronJob runs automatically every January 1st, but you'll want to populate the historical data now for percentile ratings to work. Trigger it manually:

```bash
kubectl create job --from=cronjob/historical-sync manual-sync -n waterpulse
```

Watch the progress:
```bash
kubectl logs -f job/manual-sync -n waterpulse
```

This takes several minutes as it fetches years of data for thousands of stations across Canada. When it finishes, clean up:
```bash
kubectl delete job manual-sync -n waterpulse
```

### Step 7: Verify

```bash
# Check all resources in the waterpulse namespace
kubectl get all -n waterpulse

# Expected output: 3 pods (db, backend, frontend), 3 services, 3 deployments
# All pods should show STATUS: Running and READY: 1/1
```

---

## Manifest Reference

| File | Kind | Purpose |
|------|------|---------|
| `kind-cluster.yaml` | kind config | Maps host port 80 into the cluster node, labels it for Ingress |
| `namespace.yaml` | Namespace | Isolates all WaterPulse resources in their own namespace |
| `secrets.yaml` | Secret | POSTGRES_PASSWORD and SECRET_KEY (base64-encoded, gitignored) |
| `secrets.yaml.example` | Secret | Template with placeholder values (safe to commit) |
| `configmap.yaml` | ConfigMap | Non-secret env vars: DB host, API URLs, scheduler interval, etc. |
| `db-pvc.yaml` | PersistentVolumeClaim | 2Gi storage for PostgreSQL data (survives pod restarts) |
| `db-deployment.yaml` | Deployment | PostgreSQL 16-alpine with Recreate strategy and health probes |
| `db-service.yaml` | Service (ClusterIP) | Internal DNS name `db-service` on port 5432 |
| `backend-deployment.yaml` | Deployment | FastAPI with envFrom ConfigMap, Secret refs, startup/readiness/liveness probes |
| `backend-service.yaml` | Service (ClusterIP) | Internal DNS name `backend-service` on port 8000 |
| `frontend-deployment.yaml` | Deployment | Next.js standalone server with health probes |
| `frontend-service.yaml` | Service (ClusterIP) | Internal DNS name `frontend-service` on port 3000 |
| `ingress.yaml` | Ingress | Path-based routing: `/api/*` → backend, `/*` → frontend |
| `job-historical-sync.yaml` | CronJob | Annual historical data sync (Jan 1st 03:00 UTC), can also be triggered manually |

---

## Common Operations

### View logs
```bash
# Backend logs (migrations, scheduler, API requests)
kubectl logs deployment/backend -n waterpulse

# Frontend logs (Next.js server)
kubectl logs deployment/frontend -n waterpulse

# Database logs (PostgreSQL)
kubectl logs deployment/db -n waterpulse

# Follow logs in real-time (like docker logs -f)
kubectl logs -f deployment/backend -n waterpulse
```

### Restart after code changes
```bash
# Backend
docker build -t waterpulse-backend:latest ./waterpulse-backend
kind load docker-image waterpulse-backend:latest --name waterpulse
kubectl rollout restart deployment/backend -n waterpulse

# Frontend
docker build -t waterpulse-frontend:latest --build-arg NEXT_PUBLIC_API_URL=http://localhost ./waterpulse-frontend
kind load docker-image waterpulse-frontend:latest --name waterpulse
kubectl rollout restart deployment/frontend -n waterpulse
```

### Open a database shell
```bash
kubectl exec -it deployment/db -n waterpulse -- psql -U waterpulse -d waterpulse
```

### Open a backend shell
```bash
kubectl exec -it deployment/backend -n waterpulse -- /bin/bash
```

### Check pod status and events
```bash
# Quick status
kubectl get pods -n waterpulse

# Detailed info (events, conditions, IP address)
kubectl describe pod -l app=backend -n waterpulse
```

### Update ConfigMap values
```bash
# Edit k8s/configmap.yaml, then:
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/backend -n waterpulse
# Pods don't automatically detect ConfigMap changes — a restart is needed.
```

### Delete everything and start fresh
```bash
# Delete all resources but keep the cluster
kubectl delete namespace waterpulse

# Or delete the entire cluster
kind delete cluster --name waterpulse
```

### Historical Sync (CronJob)

The historical data sync runs automatically every January 1st at 03:00 UTC via a Kubernetes CronJob. It rebuilds the percentile table with the latest 5 years of data for all of Canada. This replaces the APScheduler job that runs inside the backend — the CronJob approach is more reliable for long-running tasks because the pod has no health probes or Ingress timeouts.

**Apply the CronJob (one-time setup):**
```bash
kubectl apply -f k8s/job-historical-sync.yaml
```

**Check the CronJob schedule and last run:**
```bash
kubectl get cronjobs -n waterpulse

# Example output:
# NAME              SCHEDULE      SUSPEND   ACTIVE   LAST SCHEDULE   AGE
# historical-sync   0 3 1 1 *     False     0        <none>          5m
```

**Trigger a sync manually (without waiting for January 1st):**
```bash
# Create a one-off Job from the CronJob template
kubectl create job --from=cronjob/historical-sync manual-sync -n waterpulse
```

**Watch the sync progress in real-time:**
```bash
kubectl logs -f job/manual-sync -n waterpulse
```
This streams the log output as the sync runs — you'll see each province being processed, station counts, and the final summary.

**Check if the Job succeeded or failed:**
```bash
kubectl get jobs -n waterpulse

# Example output:
# NAME                             COMPLETIONS   DURATION   AGE
# manual-sync                      1/1           8m32s      10m
# historical-sync-28949060         1/1           9m15s      45d
```
`COMPLETIONS: 1/1` means success. `0/1` means it failed — check the logs.

**Read logs from a completed or failed Job:**
```bash
# For a manually triggered sync
kubectl logs job/manual-sync -n waterpulse

# Filter to only errors, warnings, and failures
kubectl logs job/manual-sync -n waterpulse | grep -i "error\|warning\|failed"

# For an automatically scheduled sync (name includes a timestamp)
kubectl get jobs -n waterpulse                           # Find the Job name
kubectl logs job/historical-sync-28949060 -n waterpulse  # Read its logs
```

**Clean up after a manual sync:**
```bash
kubectl delete job manual-sync -n waterpulse
```
Automatically scheduled Jobs are cleaned up by Kubernetes — it keeps the last 3 successful and 1 failed Job for log inspection.

**View CronJob history:**
```bash
# See all Jobs created by the CronJob (both auto and manual)
kubectl get jobs -n waterpulse -l job-name=historical-sync

# Detailed CronJob info (next scheduled run, active Jobs, history)
kubectl describe cronjob historical-sync -n waterpulse
```

### Delete database data (equivalent to `docker-compose down -v`)
```bash
kubectl delete pvc db-pvc -n waterpulse
# Then re-apply: kubectl apply -f k8s/db-pvc.yaml
# And restart the database: kubectl rollout restart deployment/db -n waterpulse
```

---

## Troubleshooting

### Pod stuck in `CrashLoopBackOff`
The container keeps crashing and Kubernetes keeps restarting it.
```bash
# Check logs to see why it's crashing
kubectl logs deployment/backend -n waterpulse --previous

# Check events for scheduling issues
kubectl describe pod -l app=backend -n waterpulse
```
Common causes:
- Database not ready (backend starts before PostgreSQL is accepting connections)
- Missing environment variables (Secret or ConfigMap not applied)
- Migration errors (check Alembic output in backend logs)

### Pod stuck in `ImagePullBackOff`
Kubernetes can't find the Docker image.
```bash
# Verify the image was loaded into kind
docker exec -it waterpulse-control-plane crictl images | grep waterpulse
```
Fix: rebuild and reload the image:
```bash
docker build -t waterpulse-backend:latest ./waterpulse-backend
kind load docker-image waterpulse-backend:latest --name waterpulse
```

### `http://localhost` not responding
1. Check the Ingress Controller is running:
   ```bash
   kubectl get pods -n ingress-nginx
   ```
2. Check the Ingress resource is applied:
   ```bash
   kubectl get ingress -n waterpulse
   ```
3. Check if port 80 is already in use (e.g., by IIS or another web server):
   ```bash
   netstat -ano | findstr :80   # Windows
lsof -i :80                 # macOS / Linux
   ```

### Backend can't connect to database
```bash
# Verify db pod is running
kubectl get pods -n waterpulse -l app=db

# Verify db service exists
kubectl get svc -n waterpulse

# Test DNS resolution from backend pod
kubectl exec deployment/backend -n waterpulse -- nslookup db-service
```

### Password authentication failed (FATAL: password authentication failed for user "waterpulse")
The most common cause is a **newline character embedded in the base64-encoded password**. This happens when using `echo -n` in PowerShell instead of Bash.

Verify the password values match between pods:
```bash
kubectl exec deployment/db -n waterpulse -- printenv POSTGRES_PASSWORD
kubectl exec deployment/backend -n waterpulse -- printenv DATABASE_URL
```
If the `DATABASE_URL` shows a line break in the middle, re-encode your secrets using the PowerShell `[Convert]` method (see Step 4 above), re-apply secrets, then reset the database:
```bash
kubectl apply -f k8s/secrets.yaml
kubectl delete pvc db-pvc -n waterpulse
kubectl apply -f k8s/db-pvc.yaml
kubectl rollout restart deployment/db -n waterpulse
kubectl rollout restart deployment/backend -n waterpulse
```

### Ingress returning 404 or 503
```bash
# Check Ingress Controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller

# Verify backend and frontend services have endpoints
kubectl get endpoints -n waterpulse
```
If endpoints show `<none>`, the Service selector doesn't match any pod labels.

---

## Cloud Deployment Path

These manifests are designed to work on any Kubernetes cluster with minimal changes. Here's what to adjust for cloud deployment:

### 1. Container registry
Replace `imagePullPolicy: IfNotPresent` with `Always` and push images to a registry:
```bash
# Example for Docker Hub
docker tag waterpulse-backend:latest yourusername/waterpulse-backend:latest
docker push yourusername/waterpulse-backend:latest
```
Update the `image:` fields in deployment manifests to use the registry path.

### 2. Secrets management
Replace the `secrets.yaml` file with your cloud provider's secrets manager:
- **AWS**: Use AWS Secrets Manager with the External Secrets Operator
- **GCP**: Use Secret Manager with the GCP Secrets Store CSI driver
- **Azure**: Use Key Vault with the Azure Key Vault Provider

### 3. Database
For production, use a managed database service instead of running PostgreSQL in a pod:
- **AWS**: Amazon RDS for PostgreSQL
- **GCP**: Cloud SQL for PostgreSQL
- **Azure**: Azure Database for PostgreSQL

Update `DATABASE_URL` and `DATABASE_URL_SYNC` in the ConfigMap (or use Secrets) to point to the managed instance. Remove `db-deployment.yaml`, `db-service.yaml`, and `db-pvc.yaml`.

### 4. Ingress
Cloud providers automatically provision load balancers when they see an Ingress resource:
- **AWS**: ALB Ingress Controller → Application Load Balancer
- **GCP**: GKE Ingress → Google Cloud Load Balancer
- **Azure**: Application Gateway Ingress Controller

Add a `host:` field to the Ingress rules for your domain, and configure TLS with cert-manager or your cloud provider's certificate service.

### 5. Storage
The PersistentVolumeClaim automatically provisions cloud storage:
- **AWS EKS**: EBS volumes
- **GCP GKE**: Persistent Disks
- **Azure AKS**: Managed Disks

No manifest changes needed — the storage provisioner is a cluster-level setting.
