# Wave 0 audit — three backend URLs (canon-systems)

This report maps the three environment variables consumed by **canon-systems** (`src/canon_systems/shared.py`, `load_repo_context`) to their **git repository**, **source path**, and **deployment posture**. Citations use absolute paths on this machine (read-only verification, 2026-04-22).

Resolution order for URLs (per code): process environment, then `.canon/scoper-chat.env`, then `.canon/memory-layer.local.env`, then localhost defaults (`KNOWLEDGE_API_URL` → `http://localhost:8080`, `KNOWLEDGE_WORKER_URL` → `http://localhost:8091`, `MEMORY_ADAPTER_URL` → `http://localhost:8090`).

---

## `KNOWLEDGE_API_URL`

| Field | Value |
| --- | --- |
| **Git repo** | `canon-systems-v2` (local: `/Users/edwardwalker/localwork/canon-systems-v2`) |
| **Source path** | `/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-api` |
| **Container build** | `/Users/edwardwalker/localwork/canon-systems-v2/deploy/docker/Dockerfile.knowledge-api` — installs `services/knowledge-api`, `CMD` runs `uvicorn app.main:app` on port **8080** |
| **Deploy manifest** | `/Users/edwardwalker/localwork/canon-systems-v2/deploy/manifest.json` — service `knowledge-api`, ECR repository name `canon/knowledge-api` |
| **Deployment target (IaC)** | Terraform root `/Users/edwardwalker/localwork/canon-systems-v2/infra/terraform/main.tf` provisions ECR (module `ecr`) using repository list from `terraform.tfvars`; **four** repos are named there (`canon/jira-bridge`, `canon/knowledge-api`, `canon/knowledge-worker`, `canon/temporal-runtime`). Baseline ECS in the same root uses a **placeholder** container image by default (`variables.tf` default `public.ecr.aws/docker/library/nginx:alpine`), so **service wiring to the knowledge-api image is not fully expressed in the excerpted baseline**—the ECR slot and Dockerfile are the concrete artifacts for this URL. |

**Concrete artifacts:** `Dockerfile.knowledge-api`, `deploy/manifest.json`, `services/knowledge-api/README.md`, `infra/terraform/terraform.tfvars`.

---

## `KNOWLEDGE_WORKER_URL`

| Field | Value |
| --- | --- |
| **Git repo** | `canon-systems-v2` |
| **Source path** | `/Users/edwardwalker/localwork/canon-systems-v2/services/knowledge-worker` |
| **Container build** | `/Users/edwardwalker/localwork/canon-systems-v2/deploy/docker/Dockerfile.knowledge-worker` — copies **`services/memory-adapter`** and **`services/knowledge-worker`**, installs both; **`EXPOSE 8091`**; **`CMD`** runs `uvicorn knowledge_worker.main:app` on port **8091** (worker only; memory-adapter is not started by this `CMD`) |
| **Deploy manifest** | `/Users/edwardwalker/localwork/canon-systems-v2/deploy/manifest.json` — service `knowledge-worker`, ECR `canon/knowledge-worker` |
| **Deployment target (IaC)** | Same Terraform ECR list as knowledge-api (`terraform.tfvars` includes `canon/knowledge-worker`). Baseline ECS module remains image-placeholder unless overridden—see knowledge-api section. |

**Concrete artifacts:** `Dockerfile.knowledge-worker`, `deploy/manifest.json`, `services/knowledge-worker/README.md` (documents `GET /healthz`, `POST /jobs/project-memory`, `POST /jobs/capture-memory`).

---

## `MEMORY_ADAPTER_URL`

| Field | Value |
| --- | --- |
| **Git repo** | `canon-systems-v2` |
| **Source path** | `/Users/edwardwalker/localwork/canon-systems-v2/services/memory-adapter` (package under `src/memory_adapter` per service README) |
| **Local run (dev)** | `/Users/edwardwalker/localwork/canon-systems-v2/scripts/dev/run-memory-adapter.sh` — `uvicorn memory_adapter.main:app` on port **8090** |
| **Container image** | **Not** a separate service in `/Users/edwardwalker/localwork/canon-systems-v2/deploy/manifest.json` (only `knowledge-api`, `temporal-runtime`, `jira-bridge`, `knowledge-worker`). Adapter source is **bundled inside** the knowledge-worker image (`Dockerfile.knowledge-worker`) but the running container entrypoint is the worker on **8091**, not the adapter on **8090**. |
| **Deployment target (IaC)** | **No dedicated `memory-adapter` ECR repository** in `/Users/edwardwalker/localwork/canon-systems-v2/infra/terraform/terraform.tfvars`. **Do not infer** a production ECS service or URL for memory-adapter from current manifest/ECR list alone. |

**Concrete artifacts:** `services/memory-adapter/README.md`, `scripts/dev/run-memory-adapter.sh`, `deploy/docker/Dockerfile.knowledge-worker` (proves packaging context only).

---

## Open questions for Wave 0

1. **memory-adapter deployment** — Should `MEMORY_ADAPTER_URL` in team/staging/prod point to a **standalone** Fargate/Lambda service, a **sidecar** alongside the worker, or remain **local-only** until a later wave? The v2 manifest and four-repo ECR list do not currently name a deployable `memory-adapter` artifact.
2. **canon-platform Terraform vs. these URLs** — `/Users/edwardwalker/localwork/canon-platform/README.md` describes a **serverless** stack (Lambda, API Gateway, Amplify). None of the three URL variables are documented there as the backing store; confirm that **no** production `KNOWLEDGE_*` / `MEMORY_ADAPTER_*` endpoints are still routed through canon-platform Terraform (`canon-platform/infra/terraform`) to avoid a split-brain operations picture.
