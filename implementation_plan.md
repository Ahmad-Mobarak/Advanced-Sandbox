# Phase C: Production Readiness Implementation Plan

This document outlines the approach for completing Phase C of the Advanced Cybersecurity Sandbox Platform, focusing on observability interfaces, dashboard authentication, admin/ML interfaces, Kubernetes deployment, and security hardening.

## User Review Required

> [!WARNING]  
> **Authentication Flow Change**: I will modify the backend REST API to accept authentication via **HTTPOnly Cookies** in addition to `Authorization: Bearer` headers. This allows the frontend dashboard Javascript (`fetch` calls) to work securely without exposing API keys in the HTML source code. Is this dual-auth approach acceptable?

> [!IMPORTANT]  
> **ML Retraining Trigger**: For the Admin Panel's "Trigger ML Retraining" feature, I plan to invoke the `scripts/train_model.py` script as a background subprocess. This assumes the server has access to the python environment and data. Does this align with your expectations, or would you prefer a Celery/Queue-based approach?

## Proposed Changes

---

### Observability Layer

#### [MODIFY] [ebpf_tracer.py](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/observability/ebpf_tracer.py)
- Refactor into `AbstractEBPFTracer`, `RealEBPFTracer`, and `SimulatedEBPFTracer`.
- Update `RealEBPFTracer` to serve as a stub pointing to future Linux eBPF probes.

#### [MODIFY] [falco_monitor.py](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/observability/falco_monitor.py)
- Refactor into `AbstractFalcoMonitor`, `RealFalcoMonitor`, and `SimulatedFalcoMonitor`.
- Update `RealFalcoMonitor` to serve as a stub pointing to future Falco gRPC endpoints.

#### [MODIFY] [worker/main.py](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/worker/main.py)
- Read `EBPF_MODE` and `FALCO_MODE` from environment variables to initialize the correct observability clients instead of hardcoding `"simulated"`.

---

### Authentication & Security

#### [MODIFY] [schema.sql](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/database/schema.sql)
- Update the default `users` inserts:
  - `admin`: password `123123123123` (bcrypt hashed), role `admin`.
  - `user`: password `123123123123` (bcrypt hashed), role `analyst`.

#### [MODIFY] [config/auth.py](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/config/auth.py)
- Implement password verification logic in `LocalIdentityProvider`.
- Ensure `JWT_SECRET_KEY` is fully environment-driven with no fallback to insecure hardcoded keys in production.

#### [MODIFY] [api/submission.py](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/api/submission.py)
- Refactor `verify_api_key` middleware to check `request.cookies.get("access_token")` if the `Authorization` header is missing.
- Remove `AUTH DEBUG` logging that leaks token prefixes.
- Update RBAC checks to differentiate `admin` and `analyst` (`user`) roles.

#### [MODIFY] [dashboard.py](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/frontend/dashboard.py)
- Create `/login` (GET/POST) routes to issue JWT cookies.
- Add `/logout` route to clear cookies.
- Protect all dashboard routes (`/`, `/samples`, `/iocs`, etc.) requiring valid JWT cookies.
- Remove `api_key` from all template context dictionaries.

#### [MODIFY] Frontend Templates (`login.html`, `isolation.html`, `dashboard.html`, etc.)
- Create `login.html`.
- Remove `Authorization: Bearer {{ api_key }}` from `fetch` calls (the browser will automatically send the HttpOnly cookie).
- Conditionally render admin-only links in the navbar based on the `user.role`.

---

### Admin & ML Feedback UI

#### [MODIFY] [dashboard.py](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/frontend/dashboard.py)
- Add `/admin` route that checks for `admin` role. Returns system stats, user list, and queue info.
- Add `/api/v1/admin/retrain-ml` endpoint to trigger ML retraining.
- Add `/ml-feedback` route to view and submit feedback.

#### [NEW] [templates/admin.html](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/frontend/templates/admin.html)
- Dashboard section for: User/Role management, Queue monitoring, Sample management, ML retraining controls, and System overview.

#### [NEW] [templates/ml_feedback.html](file:///d:/My/Projects/graduation%20project2/sandbox-platform/src/frontend/templates/ml_feedback.html)
- Analyst UI to submit ground-truth verdicts for past samples, updating the `ml_feedback` table.

---

### Infrastructure & Documentation

#### [NEW] [docs/CAPEv2_DEPLOYMENT.md](file:///d:/My/Projects/graduation%20project2/sandbox-platform/docs/CAPEv2_DEPLOYMENT.md)
- Complete deployment documentation, configuration guide, health check procedures, and integration wiring details for CAPEv2 on dedicated Linux/KVM hardware.

#### [NEW] [k8s/base/](file:///d:/My/Projects/graduation%20project2/sandbox-platform/k8s/base/) and [k8s/overlays/prod/](file:///d:/My/Projects/graduation%20project2/sandbox-platform/k8s/overlays/prod/)
- Create complete Kubernetes manifests:
  - `deployment.yaml` (Platform & Worker)
  - `service.yaml`, `ingress.yaml`
  - `secrets.yaml` (sealed/example), `configmap.yaml`
  - `hpa.yaml` (Horizontal Pod Autoscaler)
  - `kustomization.yaml`

#### [MODIFY] [.env](file:///d:/My/Projects/graduation%20project2/sandbox-platform/.env)
- Scrub hardcoded secrets. Add `JWT_SECRET_KEY` variable.

## Verification Plan

### Automated/Manual Testing
1. Re-initialize the database schema and log in as `admin` and `user` with `123123123123`.
2. Verify session cookies are set and dashboard pages enforce login.
3. Verify the `user` account cannot access the `/admin` panel (HTTP 403).
4. Verify Javascript `fetch` calls (like in isolation) succeed using cookies instead of Bearer tokens.
5. Trigger the ML Retraining workflow from the Admin Panel and verify success.
6. Run Docker Compose to ensure no build or runtime failures with the refactored observability interfaces.
