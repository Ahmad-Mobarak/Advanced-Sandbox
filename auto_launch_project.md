# Auto Launch Project Guide

**Purpose**: This document provides exact instructions for future AI agents to automatically launch the Advanced Cybersecurity Sandbox Platform without needing to debug common environment issues from scratch.

## 1. Start the Remote Browser Isolation (Kasm) Dependency
Kasm Workspaces is installed on this machine via the `Ubuntu` WSL instance, but its services (`kasm_proxy`, `kasm_db`, etc.) often do not start automatically after a system reboot. If Kasm is down, the Sandbox platform will throw a **403 API Error** or **Provisioning Failed** error when trying to launch isolated browsers.

**Command to start Kasm (Run in PowerShell):**
```powershell
wsl -d Ubuntu -u root /opt/kasm/bin/start
```
*Wait a few seconds after running this to ensure the containers spin up.*

## 2. Clean Up Orphaned Containers
Sometimes old container networks or orphaned containers from previous sessions hold onto port `8080` (or `8000`), causing a `port is already allocated` or `failed to set up container networking` error during launch.

**Command to clean the Docker environment:**
```powershell
cd "d:\My\Projects\graduation project2\sandbox-platform"
docker compose -f docker-compose.dev.yml down --remove-orphans
```

## 3. Fix Docker DNS / TLS Handshake Timeout (If Needed)
**Symptom**: `docker compose up --build` fails with:
```
failed to do request: Head "https://registry-1.docker.io/v2/...": net/http: TLS handshake timeout
```
or
```
failed to fetch oauth token: Post "https://auth.docker.io/token": EOF
```
This happens because **Docker Desktop's internal DNS resolver** fails to reach Docker Hub's auth endpoint, even though the machine itself has internet access. This is a known Docker Desktop bug triggered after certain system states (e.g., after Kasm starts its own Docker network).

**Diagnosis**: Verify the machine can reach Docker Hub but Docker cannot:
```powershell
# This should succeed (TcpTestSucceeded: True) — confirms internet is fine
Test-NetConnection -ComputerName registry-1.docker.io -Port 443

# This will fail if the DNS bug is present
docker pull python:3.11-slim-bookworm
```

**Fix**: Add explicit public DNS servers to Docker's daemon config so its internal resolver doesn't rely on the broken auto-detected DNS.

1. Open (or create) the file: `C:\Users\FreeComp\.docker\daemon.json`
2. Add the `"dns"` key so the file looks like this:
```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
```
3. Restart Docker Desktop (installed on **D: drive** on this machine):
```powershell
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Start-Process "d:\Program Files\Docker\Docker\frontend\Docker Desktop.exe"
```
4. Wait ~30 seconds, then verify Docker is back up:
```powershell
docker info --format "Server Version: {{.ServerVersion}}"
```
5. Retry the image pull — it should now succeed:
```powershell
docker pull python:3.11-slim-bookworm
```

> **Note**: This fix is **persistent** — once `daemon.json` is updated you will not need to repeat it after future reboots. Only redo this if `daemon.json` gets reset.

---

## 4. Launch the Platform
Once Kasm is running, the ports are clear, and Docker can reach Docker Hub, launch the main application.

**Command to start the Sandbox Platform:**
```powershell
cd "d:\My\Projects\graduation project2\sandbox-platform"
docker compose -f docker-compose.dev.yml up --build -d
```

## 5. Verification
After the containers are built and started, verify everything is working:

**Expected running containers:**
| Container | Status | Port |
|---|---|---|
| `sandbox-platform` | Up | `8080` |
| `sandbox-postgres` | Healthy | `5432` |
| `sandbox-redis` | Healthy | `6379` |
| `sandbox-worker` | Up | — |

```powershell
docker compose -f docker-compose.dev.yml ps
```

**Open in browser:**
- **Dashboard**: `http://localhost:8080`
- **Default credentials**: `admin` / `123123123123`
- If you need to test isolation, ensure `KASM_MODE=live` in the `.env` file and use the dashboard UI to request a safe browser session.
