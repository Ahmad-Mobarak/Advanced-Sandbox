# Project Properties: Advanced Cybersecurity Sandbox Platform

## 1. Project Overview & Key Components
The **Advanced Cybersecurity Sandbox Platform** is a comprehensive, asynchronous malware analysis and threat intelligence platform. It orchestrates multiple analysis engines (static, dynamic, behavioral, and machine learning) to safely detonate, observe, and classify suspicious files and URLs.

### 1.1 Core Technologies & Dependencies
- **Backend Framework:** FastAPI (Python 3.11)
- **Database:** PostgreSQL (via `asyncpg`), Redis (via `redis-py` for task queues and caching)
- **Frontend:** Jinja2 templates with a custom Glassmorphic CSS design system.
- **Machine Learning:** `xgboost`, `lightgbm`, `scikit-learn` (for anomaly detection and classification), and `shap` (for explainable AI).
- **Security & Crypto:** `bcrypt`, `python-jose`, `cryptography` (for dual-auth API keys and JWT session cookies).

### 1.2 Key Sub-Systems
- **Platform API (`src/api/`):** Handles file submissions, authentication, reporting, and webhook integrations.
- **Asynchronous Worker (`src/worker/main.py`):** Dedicated background processor that pulls tasks from PostgreSQL/Redis and orchestrates the multi-stage analysis pipeline.
- **AI Sandbox (`src/ai_sandbox/`):** Integrates the E2B Code Interpreter SDK for secure, ephemeral Python execution via gVisor microVMs.
- **Remote Browser Isolation (`src/isolation/kasm_client.py`):** Integrates Kasm Workspaces to provide disposable, cloud-based browsers for safe URL investigation.
- **File Sanitization (`src/isolation/dangerzone.py`):** Utilizes Docker-out-of-Docker (DooD) to run Dangerzone, stripping malicious active content from documents.
- **Observability (`src/observability/`):** Interfaces for eBPF (kernel-level syscall tracing) and Falco (container anomaly detection).

---

## 2. Technical Methodology

### 2.1 Design Patterns
- **Factory Pattern & Dependency Injection:** Extensively used in client wrappers (e.g., `get_ebpf_tracer()`, `get_kasm_client()`). This allows seamless switching between `simulated` (mocked/realistic generated data) and `live` (actual API integrations) modes based on `.env` configuration.
- **Event-Driven Architecture:** The worker operates on an asynchronous polling and event-driven model, updating task states (`pending` -> `processing` -> `completed`/`failed`) in the `submission_queue` table.
- **Role-Based Access Control (RBAC):** Middleware enforces `admin` vs `user` boundaries using JWT cookies and Bearer tokens.

### 2.2 Algorithms & ML Workflow
- **False Positive Reduction:** The system runs a trained ensemble model (LightGBM/XGBoost) over extracted behavioral features (API calls, network activity) to assign a "malicious probability."
- **Explainable AI (XAI):** SHAP (SHapley Additive exPlanations) values are computed to provide human-readable explanations (e.g., "Why did the model flag this? Because of `CreateProcessW` and `VirtualAllocEx`").
- **Sigma Rule Matching:** Security analytics are driven by transforming CAPEv2 JSON outputs into flat behavioral events and matching them against industry-standard Sigma rules.

---

## 3. System Operations & Data Flow

### 3.1 Internal Data Flow (Analysis Pipeline)
1. **Ingestion:** A user uploads a file via the UI or REST API. The file is saved to `/storage/samples/`, and a record is created in the `submission_queue`.
2. **Worker Pickup:** The `sandbox-worker` container polls the queue and locks the task.
3. **Pre-Analysis Enrichment:** Queries MISP for existing threat intelligence on the file hash.
4. **Static Analysis & Detonation:** 
   - Attempts live CAPEv2 detonation.
   - If CAPEv2 is offline or in simulated mode, it performs static analysis (entropy, Magic MIME, string extraction) to build a realistic behavioral profile.
5. **Observability Sync:** EBPF traces and Falco alerts are generated based on the file's behavior profile.
6. **Machine Learning Verification:** The generated behavioral data is fed into the ML model to get a confidence score and explainability metrics.
7. **Consolidation:** All findings (Sigma matches, ML score, eBPF traces) are aggregated, a final verdict is computed, and results are written to the `samples` database table.

### 3.2 External Interactions
- **Kasm API (`host.docker.internal:8443`):** Provisions ephemeral Chrome containers for RBI.
- **E2B API:** Communicates with remote microVMs for the AI Sandbox component.
- **Dangerzone Docker Daemon:** Spins up temporary, network-isolated containers on the host to convert PDFs/Docs to safe pixels and back to PDF.

---

## 4. Usage Guide & Setup Instructions

### 4.1 Environment Setup
1. Ensure Docker and Docker Desktop (with WSL2 backend enabled) are installed.
2. Review the `.env` file in the project root. Ensure modes are configured to your preference (e.g., `KASM_MODE=live` vs `simulated`).
3. Build and launch the environment:
   ```bash
   docker compose -f docker-compose.dev.yml up -d --build
   ```

### 4.2 Interacting with the Platform
1. **Login:** Access the dashboard at `http://localhost:8080/`. Use default credentials:
   - Admin: `admin` / `123123123123`
   - User: `user` / `123123123123`
2. **Submitting a Sample:** Navigate to the "Dashboard" and use the upload widget to submit a potentially malicious executable or document.
3. **Reviewing Results:** Go to the "Samples" tab to track the analysis state. Once complete, click "View" to see the comprehensive report, including ML Feedback and Sigma rule matches.
4. **Safe Browsing:** Navigate to "Isolation" (RBI), enter a suspicious URL, and click "Launch Safe Browser" to securely investigate it in an isolated Kasm container.
5. **Document Sanitization:** Use the Dangerzone UI component to upload a malicious document and download a flattened, harmless PDF version.
6. **Code Sandbox:** Navigate to the "AI Sandbox" to test custom Python analysis scripts in a highly restricted gVisor microVM.

---

## 5. UI Navigation & Page Architecture

### 5.1 Dashboard (`/`)
* **Purpose:** Acts as the primary command center and entry point for analysts.
* **Contents:** Features a drag-and-drop file upload widget and URL submission form. Displays high-level system metrics (e.g., total submissions, malicious vs. benign ratios) and a feed of the most recently submitted samples.
* **Role:** Facilitates the immediate ingestion of new files or URLs into the analysis queue.

### 5.2 Samples (`/samples`)
* **Purpose:** Serves as the historical archive and tracking system for all submitted files and URLs.
* **Contents:** A searchable, paginated table displaying `sample_id`, file name/URL, processing status, and final security verdict. Clicking a sample opens a deep-dive report containing Sigma rule matches, ML scores, and behavioral traces.
* **Role:** Provides analysts with visibility into the processing queue and serves as the gateway to detailed forensic reports.

### 5.3 IOCs (`/iocs`)
* **Purpose:** Centralizes all actionable threat intelligence extracted during sample detonation.
* **Contents:** Displays aggregated Indicators of Compromise (IOCs) such as malicious IP addresses, outbound C2 domains, dropped file hashes, and manipulated registry keys.
* **Role:** Critical for incident response. Analysts can export these indicators to update SIEMs, firewalls, and EDR platforms.

### 5.4 MITRE ATT&CK (`/mitre-attack`)
* **Purpose:** Maps the platform's behavioral findings to the industry-standard MITRE ATT&CK framework.
* **Contents:** A visual matrix highlighting specific Tactics (e.g., Persistence) and Techniques (e.g., Registry Run Keys) that the sandbox observed across recent malware samples.
* **Role:** Helps analysts understand the intent and capabilities of the malware in a standardized language.

### 5.5 AI Sandbox (`/ai-sandbox`)
* **Purpose:** Provides a safe, interactive, and ephemeral coding environment.
* **Contents:** Features a built-in code editor (Python) and an execution panel. The code executes remotely inside heavily restricted gVisor microVMs powered by E2B.
* **Role:** Allows security analysts to write custom scripts to unpack malware or test suspicious code snippets dynamically without risking their local workstations.

### 5.6 Isolation (`/isolation`)
* **Purpose:** Protects the analyst's machine from web-based threats and malicious active documents.
* **Contents:** Contains Remote Browser Isolation (RBI) powered by Kasm for safe browsing, and File Sanitization powered by Dangerzone for flattening malicious documents.
* **Role:** Provides air-gap tools for analysts to interact with live, weaponized threats safely.

### 5.7 ML Feedback (`/ml-feedback`)
* **Purpose:** Bridges the gap between the Machine Learning model and human analysts.
* **Contents:** Displays samples flagged by the anomaly detection model, showing the Confidence Score and SHAP values (explaining *why* the model made its decision).
* **Role:** Analysts can review decisions and mark them as Correct or False Positive, creating a feedback loop to retrain the models.

### 5.8 Advanced (`/advanced` / `/admin`)
* **Purpose:** The administrative and configuration backend of the platform.
* **Contents:** Contains system health diagnostics, Role-Based Access Control (RBAC) user management, and integration settings for advanced hypervisor introspection.
* **Role:** Allows platform administrators to manage API keys, configure environment variables, and monitor infrastructure health.
