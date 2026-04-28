# Project Progress Report: Advanced Cybersecurity Sandbox Platform

## 1. Project Overview
The "Advanced Cybersecurity Sandbox Platform" is a production-grade, multi-layered environment designed for advanced cybersecurity operations. The primary objective of this project is to build a highly secure, modular orchestration layer that safely isolates and analyzes malicious software, untrusted AI-generated code, and suspicious web content. 

Unlike traditional sandboxes, this platform aims to serve both defensive security operations (such as malware triage and threat hunting) and secure development needs. The core objectives include:
*   **Malware Analysis with Evasion Resistance:** Detonating suspicious files securely and analyzing their behavior.
*   **AI/LLM Agent Sandboxing:** Providing a secure execution environment for autonomous AI agents and untrusted code.
*   **Real-time Behavioral Monitoring:** Capturing system-level telemetry using eBPF and detecting anomalies.
*   **Threat Intelligence Integration:** Creating a closed-loop security operation by pulling from and pushing to Threat Intelligence platforms.
*   **Remote Browser Isolation (RBI) & Document Sanitization:** Ensuring zero-trust web interactions and safe file handling.

The architecture relies on a multi-layer isolation strategy (Hypervisor → Container → Userspace) and integrates best-in-class open-source components, ensuring maximum security maturity and minimal development risk.

---

## 2. Work Completed
Significant progress has been made in establishing the foundation layer and finalizing the core platform architecture. The following tasks and components have been successfully accomplished:

### Infrastructure and Deployment Architecture
*   **Docker Orchestration:** Developed a robust, containerized deployment strategy using Docker Compose. We established different deployment profiles, including a lightweight `dev` profile for rapid testing and a `full` stack profile for production, ensuring scalability and ease of deployment.
*   **Database Design & Implementation:** Deployed a PostgreSQL database to serve as the central repository for storing analysis verdicts, indicators of compromise (IOCs), and telemetry data. The schema has been fully designed and integrated into the startup process.

### Backend API & Core Services
*   **REST API Development:** Implemented comprehensive FastAPI-based REST endpoints for submitting files (`/api/v1/samples`), batch processing, retrieving analysis reports, sanitizing documents, and managing AI sandbox execution requests.
*   **Authentication System:** Developed a robust API key authentication system utilizing PostgreSQL's `pgcrypto` for secure, hashed key storage.
*   **Abstract Client Pattern:** Integrated external security services (like CAPEv2, MISP, E2B, Kasm, and Dangerzone) using an Abstract Client Pattern, allowing seamless switching between `simulated` mock modes and `live` production modes via environment variables.

### Frontend Analyst Dashboard
*   **User Interface Development:** Built a responsive, multi-page web dashboard using HTML and Jinja2 templates. 
*   **Interactive Features:** Created interfaces for the main Overview Dashboard, Sample Management, IOC tracking, MITRE ATT&CK coverage, and a dedicated AI Sandbox execution portal.
*   **UI/API Integration:** Successfully bridged the frontend JavaScript with the backend APIs. Added dynamic upload cards and interactive code execution text areas that seamlessly communicate with the backend to display real-time execution results and `stdout` logs.

### AI Sandbox & Document Sanitization
*   **AI Orchestrator:** Implemented the AI agent orchestration framework with strict tool denylists and network egress throttling to ensure isolated, safe execution of untrusted scripts.
*   **Document Sanitization Integration:** Integrated the backend logic to convert untrusted PDFs and Office documents into safe, pixel-based PDFs, removing potentially harmful macros.

---

## 3. Challenges Faced
During the development of the platform, several technical challenges were encountered and successfully resolved:

1.  **Frontend/Backend Communication and Authorization Failures:**
    *   *Problem:* Multiple interactive frontend UI components (such as the AI Sandbox execution terminal and Advanced Features dashboard) were failing silently and returning `401 Unauthorized` errors.
    *   *Handling:* We discovered that the frontend JavaScript `fetch` calls were missing the necessary API authorization headers. This was resolved by injecting the session `api_key` securely into the Jinja2 context during page rendering, and updating all `fetch()` operations to dynamically include the `Authorization: Bearer <api_key>` header.

2.  **Database Foreign Key Constraint Violations During Sanitization:**
    *   *Problem:* An internal server error (`insert or update on table "audit_log" violates foreign key constraint`) prevented document sanitization. The system was using a hardcoded, fake UUID for the master admin account during API requests, which did not exist in the relational database.
    *   *Handling:* The `verify_api_key` authentication flow was refactored. The system now dynamically fetches and validates the real `admin` user ID from the database when the master API key is utilized, successfully satisfying the foreign key constraints.

3.  **Resource Constraints for Nested Virtualization:**
    *   *Problem:* Running the full CAPEv2 malware detonation stack requires KVM nested virtualization and massive memory overhead, which hindered rapid local development.
    *   *Handling:* We introduced the `simulated` mode for external services and created the minimal `docker-compose.dev.yml` file. This allows developers to work on the UI and API layers without needing a dedicated 16GB+ RAM server.

---

## 4. Work in Progress
Currently, the team is actively working on the **Behavioral Monitoring Layer** and establishing the background worker processes:

*   **Background Worker Integration:** Finalizing the background worker process (`src/worker/main.py`) responsible for polling the sample queue, orchestrating the CAPEv2 detonation, and coordinating the multi-step analysis pipeline.
*   **eBPF Telemetry Pipeline:** Integrating the Azazel eBPF runtime tracer to capture kernel-level system calls from containerized analysis environments.
*   **Machine Learning Classifier Setup:** Preparing the training pipeline for the XGBoost + SHAP machine learning classifier, which will be used to reduce false-positive detection rates based on historical API call n-grams and process tree embeddings.

---

## 5. Next Steps
The planned work for the upcoming phases of the project includes:

*   **Phase 4 - Remote Browser Isolation (RBI):** Fully deploying Kasm Workspaces for containerized desktop streaming, enabling analysts to safely browse suspicious URLs and conduct zero-trust web research.
*   **Phase 5 - Advanced Deception & Honeypots:** Integrating DRAKVUF for hypervisor-level malware introspection and deploying Cowrie SSH/Telnet honeypots to actively generate local threat intelligence and automatically build threat actor playbooks.
*   **Production Hardening & Kubernetes:** Transitioning the deployment architecture from Docker Compose to Kubernetes (Helm charts) to support elastic scaling, and investigating Enarx for confidential computing enclaves (hardware-backed security).
*   **Red Team Testing:** Conducting formal Red Team exercises and chaos engineering tests to simulate sandbox escape attempts and validate the platform's isolation integrity.

---

## 6. Team Contribution
*Note: Adjust the names and roles below to accurately reflect your group members.*

| Team Member Name | Role & Core Contributions |
| :--- | :--- |
| **[Student Name 1]** | **Lead Backend Engineer:** Designed the REST APIs, developed the API authentication mechanisms, and implemented the backend logic for the AI Sandbox and Document Sanitization modules. |
| **[Student Name 2]** | **Frontend Developer:** Built the Jinja2 HTML templates, designed the responsive dashboard UI, and successfully integrated JavaScript fetch calls to communicate with the REST APIs. |
| **[Student Name 3]** | **DevOps & Security Engineer:** Configured the Docker Compose environments, set up the PostgreSQL database schemas, and resolved the database constraint and API integration bugs. |
| **[Student Name 4]** | **ML & Infrastructure Engineer:** Currently leading the background worker integration, researching the eBPF telemetry pipeline, and planning the machine learning false-positive classifier. |
