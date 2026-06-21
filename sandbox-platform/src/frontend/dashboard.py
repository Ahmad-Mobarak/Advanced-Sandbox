"""
Advanced Cybersecurity Sandbox Platform
Analyst Dashboard - FastAPI-based Web Interface
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncpg
import os
import json
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv
from jose import jwt, JWTError

from src.config.auth import LocalIdentityProvider, SECRET_KEY, ALGORITHM

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sandbox:sandbox@localhost:5432/sandbox_db")

app = FastAPI(
    title="Sandbox Platform Dashboard",
    description="Analyst dashboard for malware analysis",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")

templates = Jinja2Templates(directory="src/frontend/templates")
templates.env.filters["fromjson"] = lambda s: json.loads(s) if isinstance(s, str) else s

db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    return db_pool


async def get_current_user(request: Request):
    """Get current authenticated user from cookie. Redirects to login if missing."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        roles: list = payload.get("roles", [])
        if username is None:
            raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
            
        return {"username": username, "roles": roles, "role": roles[0] if roles else "user"}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    pool = await get_db_pool()
    auth_provider = LocalIdentityProvider(pool)
    
    user = await auth_provider.authenticate({"username": username, "password": password})
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
        
    token = auth_provider.create_access_token(user)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=1800)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, current_user: dict = Depends(get_current_user)):
    """Dashboard home page."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Get statistics
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as pending_samples,
                COUNT(*) FILTER (WHERE status = 'analyzing') as analyzing_samples,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_samples,
                COUNT(*) FILTER (WHERE verdict = 'malicious') as malicious_samples,
                COUNT(*) FILTER (WHERE verdict = 'benign') as benign_samples
            FROM samples
        """)

        # Recent samples
        recent_samples = await conn.fetch("""
            SELECT id, sha256_hash, file_name, status, verdict, submitted_at
            FROM samples
            ORDER BY submitted_at DESC
            LIMIT 10
        """)

        # Recent IOCs
        recent_iocs = await conn.fetch("""
            SELECT ioc_type, value, confidence, first_seen
            FROM iocs
            ORDER BY first_seen DESC
            LIMIT 10
        """)

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "request": request,
        "stats": dict(stats),
        "recent_samples": [dict(s) for s in recent_samples],
        "recent_iocs": [dict(i) for i in recent_iocs],
        "current_user": current_user
    })


@app.get("/api/stats")
async def get_dashboard_stats():
    """Get dashboard statistics."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_samples,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'analyzing') as analyzing,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE verdict = 'malicious') as malicious,
                COUNT(*) FILTER (WHERE verdict = 'benign') as benign,
                COUNT(*) FILTER (WHERE verdict = 'suspicious') as suspicious,
                AVG(confidence_score) FILTER (WHERE verdict IS NOT NULL) as avg_confidence
            FROM samples
        """)

        # Queue status
        queue_stats = await conn.fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as queue_pending,
                COUNT(*) FILTER (WHERE status = 'processing') as queue_processing
            FROM submission_queue
        """)

        # Sandbox status
        sandbox_stats = await conn.fetch("""
            SELECT sandbox_type, status, COUNT(*) as count
            FROM sandboxes
            GROUP BY sandbox_type, status
        """)

        return {
            "samples": dict(stats),
            "queue": dict(queue_stats),
            "sandboxes": [dict(s) for s in sandbox_stats],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@app.get("/samples")
async def samples_list(
    request: Request,
    current_user: dict = Depends(get_current_user),
    status_filter: Optional[str] = None,
    verdict_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """Samples list page."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT id, sha256_hash, file_name, status, verdict,
                   confidence_score, submitted_at, analysis_completed_at
            FROM samples
            WHERE 1=1
        """
        params = []

        if status_filter:
            query += " AND status = $" + str(len(params) + 1)
            params.append(status_filter)

        if verdict_filter:
            query += " AND verdict = $" + str(len(params) + 1)
            params.append(verdict_filter)

        query += " ORDER BY submitted_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)

        samples = await conn.fetch(query, *params)

    return templates.TemplateResponse(request=request, name="samples.html", context={
        "request": request,
        "samples": [dict(s) for s in samples],
        "status_filter": status_filter,
        "verdict_filter": verdict_filter,
        "current_user": current_user
    })


@app.get("/sample/{sample_id}")
async def sample_detail(request: Request, sample_id: str, current_user: dict = Depends(get_current_user)):
    """Sample detail page."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        sample = await conn.fetchrow("""
            SELECT * FROM samples WHERE id = $1
        """, sample_id)

        if not sample:
            raise HTTPException(status_code=404, detail="Sample not found")

        behaviors = await conn.fetch("""
            SELECT * FROM behaviors
            WHERE sample_id = $1
            ORDER BY timestamp
        """, sample_id)

        iocs = await conn.fetch("""
            SELECT * FROM iocs
            WHERE sample_id = $1
        """, sample_id)

        # Phase 2: Fetch eBPF events
        ebpf_events = await conn.fetch("""
            SELECT * FROM ebpf_events
            WHERE sample_id = $1
            ORDER BY timestamp DESC
            LIMIT 100
        """, sample_id)

        # Phase 2: Fetch Falco alerts
        falco_alerts = await conn.fetch("""
            SELECT * FROM falco_alerts
            WHERE sample_id = $1
            ORDER BY timestamp DESC
        """, sample_id)

    return templates.TemplateResponse(request=request, name="sample_detail.html", context={
        "request": request,
        "sample": dict(sample),
        "behaviors": [dict(b) for b in behaviors],
        "iocs": [dict(i) for i in iocs],
        "ebpf_events": [dict(e) for e in ebpf_events],
        "falco_alerts": [dict(a) for a in falco_alerts],
        "current_user": current_user
    })


@app.get("/iocs")
async def iocs_list(request: Request, ioc_type: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """IOCs list page."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT ioc_type, value, confidence, tlp, ti_tags,
                   first_seen, last_seen, sample_count
            FROM v_active_iocs
        """
        if ioc_type:
            query += " WHERE ioc_type = $1"
            iocs = await conn.fetch(query, ioc_type)
        else:
            iocs = await conn.fetch(query)

    return templates.TemplateResponse(request=request, name="iocs.html", context={
        "request": request,
        "iocs": [dict(i) for i in iocs],
        "ioc_type_filter": ioc_type,
        "current_user": current_user
    })


@app.get("/mitre-attack")
async def mitre_attack_view(request: Request, current_user: dict = Depends(get_current_user)):
    """MITRE ATT&CK coverage view."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        coverage = await conn.fetch("SELECT * FROM v_mitre_attack_coverage")

    return templates.TemplateResponse(request=request, name="mitre_attack.html", context={
        "request": request,
        "coverage": [dict(c) for c in coverage],
        "current_user": current_user
    })


@app.get("/ai-sandbox")
async def ai_sandbox_view(request: Request, current_user: dict = Depends(get_current_user)):
    """Phase 3: AI Agent Sandboxing View."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Fetch execution logs from audit_log
        executions = await conn.fetch("""
            SELECT id, user_id, action, details, status, timestamp
            FROM audit_log
            WHERE action = 'ai_sandbox_execution' AND archived = FALSE
            ORDER BY timestamp DESC
            LIMIT 50
        """)

    return templates.TemplateResponse(request=request, name="ai_sandbox.html", context={
        "request": request,
        "executions": [dict(e) for e in executions],
        "current_user": current_user
    })


@app.get("/isolation")
async def isolation_view(request: Request, current_user: dict = Depends(get_current_user)):
    """Phase 4: Remote Browser Isolation & Sanitization View."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # Fetch rbi sessions
        rbi_logs = await conn.fetch("""
            SELECT id, action, details, status, timestamp
            FROM audit_log
            WHERE action = 'rbi_session_created' AND archived = FALSE
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        # Fetch sanitization logs
        sanitization_logs = await conn.fetch("""
            SELECT id, action, details, status, timestamp
            FROM audit_log
            WHERE action = 'document_sanitized' AND archived = FALSE
            ORDER BY timestamp DESC
            LIMIT 20
        """)

    return templates.TemplateResponse(request=request, name="isolation.html", context={
        "request": request,
        "rbi_logs": [dict(r) for r in rbi_logs],
        "sanitization_logs": [dict(s) for s in sanitization_logs],
        "current_user": current_user
    })


@app.get("/advanced")
async def advanced_view(request: Request, current_user: dict = Depends(get_current_user)):
    """Phase 5: Advanced Features View (DRAKVUF, Cowrie, MITRE)."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        # We simulate fetching the map data and drakvuf jobs
        pass

    return templates.TemplateResponse(request=request, name="advanced.html", context={
        "request": request,
        "current_user": current_user
    })

@app.get("/admin")
async def admin_view(request: Request, current_user: dict = Depends(get_current_user)):
    """Admin Panel View."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch("SELECT id, username, email, role, active, created_at FROM users")
        queue_stats = await conn.fetchrow("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE status='pending') as pending FROM submission_queue")
    
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "request": request,
        "current_user": current_user,
        "users": [dict(u) for u in users],
        "queue_stats": dict(queue_stats) if queue_stats else {}
    })

@app.get("/ml-feedback")
async def ml_feedback_view(request: Request, current_user: dict = Depends(get_current_user)):
    """ML Feedback UI View."""
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        feedbacks = await conn.fetch("SELECT * FROM ml_feedback ORDER BY created_at DESC LIMIT 50")
    
    return templates.TemplateResponse(request=request, name="ml_feedback.html", context={
        "request": request,
        "current_user": current_user,
        "feedbacks": [dict(f) for f in feedbacks]
    })

@app.post("/api/v1/admin/retrain-ml")
async def trigger_ml_retrain(current_user: dict = Depends(get_current_user)):
    """Trigger ML Retraining script in background."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    import subprocess
    script_path = os.path.join(os.getcwd(), "scripts", "train_model.py")
    try:
        subprocess.Popen(["python3", script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"status": "success", "message": "ML Retraining started in background"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start retraining: {str(e)}")

@app.post("/api/v1/admin/audit/{audit_id}/archive")
async def archive_audit_log(audit_id: str, current_user: dict = Depends(get_current_user)):
    """Archive an audit log entry (Hide from history)."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        res = await conn.execute("UPDATE audit_log SET archived = TRUE WHERE id = $1::uuid", audit_id)
        if res == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Audit log not found")
            
        await conn.execute(
            """INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, status)
               VALUES ($1, 'audit_archived', 'audit_log', $2::uuid, '{}'::jsonb, 'success')""",
            current_user["username"], audit_id
        )
    return {"status": "success", "message": "Record archived successfully"}

@app.post("/api/v1/admin/users/{user_id}")
async def update_user(user_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Update user role and active status."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    data = await request.json()
    role = data.get("role")
    active = data.get("active")
    
    if role not in ("admin", "analyst", "readonly"):
        raise HTTPException(status_code=400, detail="Invalid role")
        
    # Map roles to basic permissions
    perms_map = {
        "admin": '["samples:read", "samples:write", "samples:delete", "analysis:read", "analysis:write", "users:read", "users:write", "config:read", "config:write", "audit:read"]',
        "analyst": '["samples:read", "samples:write", "analysis:read", "analysis:write", "audit:read"]',
        "readonly": '["samples:read", "analysis:read"]'
    }
    permissions = perms_map[role]
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        res = await conn.execute(
            "UPDATE users SET role = $1, permissions = $2::jsonb, active = $3 WHERE id = $4::uuid",
            role, permissions, active, user_id
        )
        if res == "UPDATE 0":
            raise HTTPException(status_code=404, detail="User not found")
            
        await conn.execute(
            """INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, status)
               VALUES ($1, 'user_updated', 'user', $2::uuid, $3::jsonb, 'success')""",
            current_user["username"], user_id, json.dumps({"role": role, "active": active})
        )
    return {"status": "success", "message": "User updated successfully"}
@app.get("/api/v1/admin/kasm/sessions")
async def get_kasm_sessions(current_user: dict = Depends(get_current_user)):
    """Fetch live Kasm sessions via Docker socket."""
    if current_user.get("role") not in ("admin", "senior_analyst"):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    kasm_mode = os.getenv("KASM_MODE", "simulated")
    if kasm_mode != "live":
        return [{
            "id": "sim-9999",
            "name": "simulated_kasm_session",
            "owner": "test_user",
            "status": "running",
            "cpu": "0%",
            "memory": "0MB",
            "duration": "0m",
            "start_time": datetime.now(timezone.utc).isoformat()
        }]
        
    import httpx
    import time
    
    sessions = []
    try:
        async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds="/var/run/docker.sock")) as client:
            res = await client.get("http://localhost/containers/json")
            if res.status_code != 200:
                raise Exception(f"Docker API error: {res.status_code}")
                
            containers = res.json()
            for c in containers:
                labels = c.get("Labels", {})
                names = c.get("Names", [])
                image = c.get("Image", "")
                
                is_kasm = "kasm.kasm_id" in labels or "userkasm" in str(names) or "kasmweb" in image
                is_core = any(core in str(names) for core in ["kasm_manager", "kasm_share", "kasm_agent", "kasm_proxy", "kasm_db", "kasm_redis"])
                
                if is_kasm and not is_core:
                    cpu_usage = "N/A"
                    mem_usage = "N/A"
                    try:
                        stats_res = await client.get(f"http://localhost/containers/{c['Id']}/stats?stream=false", timeout=1.0)
                        if stats_res.status_code == 200:
                            stats = stats_res.json()
                            mem_bytes = stats.get("memory_stats", {}).get("usage", 0)
                            mem_usage = f"{mem_bytes / (1024*1024):.1f}MB"
                            cpu_delta = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0) - stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
                            sys_delta = stats.get("cpu_stats", {}).get("system_cpu_usage", 0) - stats.get("precpu_stats", {}).get("system_cpu_usage", 0)
                            if sys_delta > 0 and cpu_delta > 0:
                                cpus = stats.get("cpu_stats", {}).get("online_cpus", 1)
                                cpu_percent = (cpu_delta / sys_delta) * cpus * 100.0
                                cpu_usage = f"{cpu_percent:.1f}%"
                    except Exception:
                        pass

                    created = c.get("Created", 0)
                    duration_min = int((time.time() - created) / 60)
                    
                    sessions.append({
                        "id": c["Id"][:12],
                        "name": names[0].strip("/") if names else "Unknown",
                        "owner": labels.get("kasm.user_name", "Unknown"),
                        "status": c.get("State", "unknown"),
                        "cpu": cpu_usage,
                        "memory": mem_usage,
                        "duration": f"{duration_min}m",
                        "start_time": datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
                    })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sessions: {str(e)}")
        
    return sessions

@app.delete("/api/v1/admin/kasm/sessions/{container_id}")
async def terminate_kasm_session(container_id: str, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ("admin", "senior_analyst"):
        raise HTTPException(status_code=403, detail="Admin access required")
        
    import httpx
    try:
        async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds="/var/run/docker.sock")) as client:
            info_res = await client.get(f"http://localhost/containers/{container_id}/json")
            owner = "Unknown"
            if info_res.status_code == 200:
                info = info_res.json()
                owner = info.get("Config", {}).get("Labels", {}).get("kasm.user_name", "Unknown")

            # Graceful stop
            await client.post(f"http://localhost/containers/{container_id}/stop?t=10")
            # Remove
            res = await client.delete(f"http://localhost/containers/{container_id}?v=true&force=true")
            if res.status_code not in (204, 200, 404):
                raise Exception(f"Delete returned {res.status_code}: {res.text}")
                
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, status)
                       VALUES ($1, 'kasm_session_terminated', 'container', NULL, $2::jsonb, 'success')""",
                    current_user["username"], 
                    json.dumps({
                        "container_id": container_id,
                        "session_owner": owner,
                        "reason": "Admin manually terminated session"
                    })
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to terminate session: {str(e)}")
        
    return {"status": "success", "message": "Session terminated successfully"}

@app.on_event("startup")
async def startup():
    await get_db_pool()


@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
