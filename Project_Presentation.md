# Slide Deck: Advanced Cybersecurity Sandbox Platform
*A Technical Presentation on Ephemeral Detonation, Observability, and Machine Learning Analysis*

---

## Slide 1: Title Slide
### **Advanced Cybersecurity Sandbox Platform**
#### *Modern Asynchronous Malware Detonation & Hybrid Threat Intelligence*

**Presented by:** Graduation Project Team 2  
**Role within System:** Core Architecture, Machine Learning, and Cloud Orchestration  
 
---

## Slide 2: The Problem Space
### **Challenges in Modern Malware Analysis**
- **Evasion Tactics:** Modern malware easily detects standard sandbox environments by checking registry keys, screen resolution, or looking for debuggers.
- **Alert Fatigue:** High rates of false positives in automated signature detection overwhelm security teams.
- **Exposure Risks:** Analysts reviewing phishing links, executing scripts, or opening malware documents risk compromising their local network.

---

## Slide 3: Our Solution
### **A Comprehensive, Multi-layered Approach**
- **Multi-layered Sandbox:** Combines Static, Dynamic, Kernel (eBPF), and Hypervisor (DRAKVUF) analysis into a single pipeline.
- **Explainable ML:** Integrates XGBoost with SHAP to not only predict if a file is malicious, but to explain exactly *why*.
- **Air-Gapped Actions:** Incorporates Remote Browser Isolation (RBI) and automated Document Sanitization (CDR) to protect analysts during manual triage.

---

## Slide 4: System Architecture Overview
```
                         +-----------------------------+
                         |      FastAPI Frontend       |
                         |  (User & API Ingestion)     |
                         +--------------+--------------+
                                        |
                                        v (Enqueues Task)
                         +--------------+--------------+
                         |    PostgreSQL Queue / Redis |
                         +--------------+--------------+
                                        |
                                        v (Pulls Task)
                         +--------------+--------------+
                         |       Asynchronous Worker   |
                         +-------+------+-------+------+
                                 |      |       |
         +-----------------------+      |       +------------------------+
         v                              v                                v
+------------------+         +--------------------+            +-------------------+
| Detonation       |         | Telemetry & Kern   |            | ML Engine         |
| - CAPEv2 (Win)   |         | - eBPF Syscalls    |            | - XGBoost Classifier|
| - DRAKVUF (Xen)  |         | - Falco Alerts     |            | - SHAP Explainer  |
+------------------+         +--------------------+            +-------------------+
```

---

## Slide 5: The Lifetime of a Submission
### **End-to-End Analysis Pipeline**
1. **Ingestion:** API receives sample -> stores to secure storage -> pushes to DB queue.
2. **Pre-Analysis Enrichment:** Query MISP/ThreatIntel databases for existing hash reputations.
3. **Detonation Stage:** Detonate sample in CAPEv2 or generate context-aware static reports.
4. **Telemetry Extraction:** Collect kernel-level eBPF syscalls and Falco anomaly alerts.
5. **ML Verification:** Behavior telemetry parsed into features -> ML predicts malicious probability.
6. **Consolidation:** Aggregated metrics map to MITRE ATT&CK -> Write final verdict report.

---

## Slide 6: The Ingestion API & Queue
### **Scalable Task Management**
- **FastAPI Backend:** Provides high-performance, asynchronous endpoints for sample upload and status polling.
- **Redis & PostgreSQL:** Manages the submission queue, ensuring tasks are distributed evenly to workers without race conditions.
- **Priority Queuing:** Allows critical samples to jump the line, ensuring analysts get immediate results during an active incident.

---

## Slide 7: Pre-Analysis Enrichment
### **Threat Intelligence Integration**
- **MISP (Malware Information Sharing Platform):** 
  - Before detonating a file, the system checks its hash against global threat intelligence databases.
  - If the file is a known threat (e.g., WannaCry), the system instantly flags it, saving valuable compute resources.
- **Outcome:** Faster triage and immediate context for known adversaries.

---

## Slide 8: Static Analysis & Heuristics
### **Intelligent Pre-Detonation Checks**
- **MIME/Magic Parsing:** Accurately identifies file structures (PE, PDF, Office Macro, Scripts) regardless of the file extension.
- **Shannon Entropy Calculation:** Measures data randomness. High entropy strongly indicates the payload is packed or encrypted to evade detection.
- **Regex String Extraction:** Scans binary strings for suspicious APIs (`VirtualAlloc`, `ShellExecute`), hardcoded IP addresses, and command-line scripts.

---

## Slide 9: Dynamic Analysis
### **VM Detonation Layer (CAPEv2)**
- **Automated Execution:** An automated agent logs into a Windows virtual machine, runs the target sample, and monitors its behavior.
- **API Hooking:** Tracks process creation, registry modifications, file manipulations, and network requests.
- **Behavioral Logging:** Generates deep behavioral logs that are passed down the pipeline for Sigma rule matching.

---

## Slide 10: Hypervisor Introspection
### **Agentless Monitoring (DRAKVUF)**
- **The Evasion Problem:** Advanced malware checks for hooking libraries injected into the VM by standard sandboxes.
- **The DRAKVUF Solution:** Performs agentless monitoring directly from the Xen hypervisor level.
- **Capabilities:** Captures kernel memory dumps, kernel API tracing (e.g., `NtAllocateVirtualMemory`), and tracks injected processes *without* running any monitoring code inside the guest VM.

---

## Slide 11: Advanced Evasion Resistance
### **Adaptive Environments**
- **Dynamic Fingerprinting:** Malware often checks MAC addresses, CPU core counts, or specific usernames to detect virtual machines.
- **Randomized Profiles:** Our engine generates adaptive hardware profiles (randomized MACs, realistic CPU/RAM ratios) to trick the malware.
- **User Emulation:** Simulates human interactions (mouse movement, clicks, scrolling) to trigger malware that waits for user activity before unpacking its payload.

---

## Slide 12: Observability - eBPF System Call Tracer
### **Kernel-Level Visibility**
- **What is eBPF?** Extended Berkeley Packet Filter allows running sandboxed programs in the Linux kernel.
- **Our Implementation:** Hooks system calls directly in the kernel hosting the sandbox containers.
- **Tracking:** Monitors file descriptors, socket connections, namespace modifications, and executions (`execve`, `setns`). Rootkits cannot easily hide from eBPF.

---

## Slide 13: Observability - Falco Runtime Security
### **Securing the Sandbox Infrastructure**
- **Container Security:** When analyzing malware in Docker containers, there is a risk of container escape.
- **Falco Monitoring:** Uses behavioral rule sets to flag security events in real-time.
- **Alerts:** Instantly alerts administrators on sandbox container escape attempts, write violations in binary directories, and unexpected privilege escalations.

---

## Slide 14: Behavioral Analysis - Sigma Rules Engine
### **Standardizing Threat Detection**
- **What is Sigma?** The generic signature format for SIEM systems, acting like YARA but for log events.
- **Our Implementation:** The engine parses the behavioral logs from dynamic analysis and matches them against hundreds of Sigma rules.
- **MITRE ATT&CK Mapping:** Automatically maps broken rules (e.g., "Registry Run Key Persistence") to specific MITRE tactics (e.g., T1547.001), providing standardized intelligence.

---

## Slide 15: Machine Learning Classifier
### **The XGBoost Model**
- **The Goal:** Reduce false positives common in rigid signature-based detection.
- **Feature Extraction:** Converts raw telemetry into a 15-feature vector (e.g., API call entropy, process tree depth, file write ratio).
- **Classification:** An XGBoost model predicts the probability of the sample being malicious, classifying it as Malicious, Suspicious, or Benign based on dynamic thresholds.

---

## Slide 16: Explainable AI (SHAP Interpreter)
### **Why is the Model Flagging This?**
- **The Black-Box Problem:** Analysts cannot blindly trust an AI that just says "99% Malicious" without context.
- **SHAP (SHapley Additive exPlanations):** Measures the exact contribution of each behavioral feature to the final verdict.
- **Analyst Empowerment:** The dashboard shows exactly *why* the AI made its decision (e.g., "Flagged because of `VirtualAllocEx` API call (+0.3) and Network Beaconing (+0.2)").

---

## Slide 17: Threat Intelligence & IOC Extraction
### **Aggregating Threat Data**
- **Indicator Extraction:** Automatically extracts structured Indicators of Compromise (IOCs) from analyzed samples:
  - **Network:** Destination IPs, C2 domains, protocol ports.
  - **Host:** Modified registry keys, dropped file paths.
  - **Files:** Hashes (MD5, SHA1, SHA256) of dropped payloads.
- **Actionable Data:** This data is populated into a searchable database, allowing security teams to immediately block these indicators on their firewalls.

---

## Slide 18: Interactive Analyst Tools
### **The Need for Safe Spaces**
- **The Reality of Triage:** Automated analysis is not always enough. Analysts often need to manually view a phishing site, read a suspicious document, or run a decryption script.
- **The Danger:** Doing this on their local workstation is a massive security risk.
- **Our Solution:** A suite of air-gapped, containerized tools integrated directly into the platform dashboard.

---

## Slide 19: Remote Browser Isolation (RBI)
### **Air-Gapped Phishing Link Investigation**
- **Technology:** Integrated Kasm Workspaces.
- **Workflow:** The analyst enters a suspicious URL. The backend spawns an isolated, ephemeral browser container in the cloud.
- **Pixel Streaming:** The browser is rendered to the analyst's screen via WebRTC. Active web scripts and drive-by downloads execute in the remote container, keeping the analyst's endpoint completely safe.

---

## Slide 20: Document Sanitization (Dangerzone)
### **Eliminating Weaponized Documents**
- **Content Disarm and Reconstruction (CDR):** 
  1. Analyst uploads a suspicious PDF or Office document.
  2. An isolated container opens the document and converts every page into raw pixels (destroying macros, JavaScript, and embedded exploits).
  3. The pixels are rendered back into a clean, safe PDF.
- **Outcome:** The analyst safely downloads a functional copy of the document without risk of infection.

---

## Slide 21: AI Sandbox (E2B gVisor)
### **Secure Code Execution for Analysts**
- **The Need:** Analysts often write quick Python scripts to decrypt payloads or parse malicious configurations.
- **Technology:** E2B SDK integration utilizing gVisor microVMs.
- **Security:** gVisor provides a strong isolation boundary between the application and the host kernel. The analyst writes code in the browser, and it executes in an ephemeral, heavily restricted sandbox.

---

## Slide 22: Proactive Defense (Cowrie Honeypot)
### **Gathering Intelligence from Attackers**
- **Honeypot Integration:** Deploys a Cowrie SSH/Telnet honeypot to lure in automated attacks and human hackers.
- **Data Ingestion:** A webhook parser ingests events from the honeypot in real-time.
- **Automation:** Automatically extracts attacker IP addresses as new IOCs and automatically submits any malware dropped by the attacker into the platform's analysis queue.

---

## Slide 23: Database & Schema Design
### **Relational Data Integrity**
- **PostgreSQL:** Serves as the primary data store.
- **Schema Design:** Heavily normalized schema tracking `samples`, `behaviors`, `iocs`, `analysis_reports`, and `submission_queue`.
- **Views & Analytics:** Utilizes SQL views (e.g., `v_mitre_attack_coverage`) to rapidly generate dashboard statistics without expensive runtime aggregations.

---

## Slide 24: Admin Controls & RBAC
### **Platform Administration**
- **Role-Based Access Control:** Strict separation between standard Users (analysts) and Admins.
- **JWT Authentication:** Secure stateless authentication using HTTPOnly cookies.
- **Audit Logging:** Every critical action (submitting a sample, deleting a file, launching a Kasm session) is recorded in the `audit_log` table to ensure complete accountability.

---

## Slide 25: Development vs Live Modes
### **The Factory Pattern Architecture**
- **Flexibility:** The entire platform is built using the Factory software design pattern.
- **Modes:** Driven by `.env` variables, subsystems like eBPF, Falco, and DRAKVUF can run in `simulated` mode (for local development on Windows) or `live` mode (for production deployment on Linux servers).
- **Simulated Realism:** Simulated modes do not just return empty data; they generate context-aware, realistic telemetry for testing the UI and ML pipelines.

---

## Slide 26: Analyst Scenario (Part 1 - Triage)
### **Investigating a Malicious Invoice**
- **The Trigger:** An employee reports a suspicious email with an attachment named `urgent_invoice.pdf`.
- **Safe Preview:** The analyst uploads the document to the **Isolation** dashboard (Dangerzone). They download the sanitized PDF and confirm it looks like a real invoice, but suspect a hidden exploit.
- **Submission:** The analyst submits the original `urgent_invoice.pdf` to the main sandbox queue with High priority.

---

## Slide 27: Analyst Scenario (Part 2 - Detonation)
### **Execution & Telemetry Collection**
- **Detonation:** The worker picks up the task and executes the PDF in a Windows VM.
- **Behavior Logged:** The VM records that Adobe Acrobat spawned a hidden `cmd.exe` process, which executed a PowerShell script.
- **Kernel Tracing:** eBPF traces the PowerShell process initiating an outbound socket connection to an unknown IP.
- **Sigma Match:** The Sigma engine instantly flags this behavior with the rule "Suspicious Execution from PDF", mapping it to MITRE Tactic Execution.

---

## Slide 28: Analyst Scenario (Part 3 - Verdict & XAI)
### **Final Verdict and Intelligence Extraction**
- **ML Scoring:** The behavioral vector is passed to the XGBoost model, which returns a 94% Malicious probability.
- **SHAP Explanation:** The dashboard shows the analyst that the score was driven primarily by the high `process_tree_depth` and the presence of `network_beaconing`.
- **IOCs:** The external IP contacted by PowerShell is extracted and pushed to MISP, automatically updating the organization's firewalls.

---

## Slide 29: Deliverables & Technical Impact
### **Key System Deliverables**
- **Complete Orchestration:** Fully containerized Docker Compose setup ready for deployment.
- **Advanced Security:** True Remote Browser Isolation and Document Sanitization pipelines.
- **Actionable Forensics:** Combined reporting mechanism that outputs standard formats matching Sigma and MITRE standards.
- **Explainable AI:** A transparent machine learning classifier that empowers, rather than replaces, the analyst.

---

## Slide 30: Summary, Future Vision & Q&A
### **Summary of Accomplishments**
- Built a highly modular, containerized, and secure analysis architecture.
- Bridged deep kernel monitoring with high-level AI classifications.
- Provided practical, air-gapped web tools for operational environments.

### **Future Work**
- Add support for macOS / Linux detonation targets.
- Integrate real-time YARA scanning inside the static analyzer.

### **Thank You! Questions?**
- **Platform URL:** `http://localhost:8080`
- **Documentation:** `Project_Properties.md` & `Project_Deep_Dive_AR.md`
