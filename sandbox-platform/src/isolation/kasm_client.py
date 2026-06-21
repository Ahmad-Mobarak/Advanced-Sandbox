import uuid
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from .schemas import RBISessionRequest, RBISessionResponse

logger = logging.getLogger(__name__)

class KasmClient:
    """Interface for managing Kasm Workspaces Remote Browser Isolation sessions."""
    async def create_session(self, request: RBISessionRequest) -> RBISessionResponse:
        raise NotImplementedError

class RealKasmClient(KasmClient):
    """Implementation using the official Kasm Workspaces API."""
    def __init__(self, api_url: str, api_key: str, api_secret: str):
        self.api_url = api_url
        self.api_key = api_key
        self.api_secret = api_secret

    async def create_session(self, request: RBISessionRequest) -> RBISessionResponse:
        import httpx
        import os
        
        # We use the Chrome image ID from the Kasm database
        image_id = "54ffa417-dc10-485b-9929-0c047908ac8b" 
        user_id = os.getenv("KASM_USER_ID")
        
        url = f"{self.api_url.rstrip('/')}/api/public/request_kasm"
        data = {
            "api_key": self.api_key,
            "api_key_secret": self.api_secret,
            "user_id": user_id,
            "image_id": image_id,
            "kasm_url": request.url
        }
        
        try:
            # Add X-Forwarded-For header to match the user's browser IP, 
            # so Kasm doesn't reject the session_token due to an IP mismatch.
            headers = {
                "X-Forwarded-For": "127.0.0.1",
                "X-Real-IP": "127.0.0.1"
            }
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.post(url, json=data, headers=headers)
            
            if resp.status_code == 200 and "kasm_url" in resp.json():
                result = resp.json()
                
                # The kasm_url returned is relative (e.g., /#/connect/kasm/...). 
                # We need to prepend the public URL (127.0.0.1:8443) so the user's browser can reach it.
                # NOTE: The user MUST access the dashboard via http://127.0.0.1:8000 to prevent third-party cookie drops.
                public_base_url = self.api_url.replace("host.docker.internal", "127.0.0.1")
                full_cast_url = f"{public_base_url.rstrip('/')}{result.get('kasm_url')}"
                
                return RBISessionResponse(
                    session_id=result.get("kasm_id", str(uuid.uuid4())),
                    cast_url=full_cast_url,
                    status="active",
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
                )
            else:
                logger.error(f"Kasm API error: {resp.status_code} {resp.text}")
                return RBISessionResponse(
                    session_id=str(uuid.uuid4()),
                    cast_url="about:blank",
                    status="error",
                    expires_at=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.error(f"Failed to call Kasm API: {e}")
            return RBISessionResponse(
                session_id=str(uuid.uuid4()),
                cast_url="about:blank",
                status="error",
                expires_at=datetime.now(timezone.utc)
            )

class SimulatedKasmClient(KasmClient):
    """Simulated Kasm Client for local development and UI testing."""
    async def create_session(self, request: RBISessionRequest) -> RBISessionResponse:
        # Simulate API delay
        time.sleep(0.5)
        
        session_id = str(uuid.uuid4())
        # For simulation, we'll return a cast URL that just echoes the requested URL safely 
        # or points to a safe placeholder. Since we want to show it in an iframe, 
        # we'll use a data URI or a safe public site like example.com wrapped securely.
        # Note: In a real Kasm setup, this URL points to a WebSocket stream of the container GUI.
        
        import urllib.parse
        safe_html = f"<html><body style='font-family:sans-serif; text-align:center; padding: 50px; background: #000; color: #4ade80;'><h2>Simulated Remote Browser</h2><p>In a live environment, you would be securely browsing:</p><p style='font-size: 1.2rem; color: #fff;'>{request.url}</p></body></html>"
        safe_url = f"data:text/html;charset=utf-8,{urllib.parse.quote(safe_html)}"
        
        return RBISessionResponse(
            session_id=session_id,
            cast_url=safe_url,
            status="active",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

def get_kasm_client(mode: str = "simulated", api_url: Optional[str] = None, api_key: Optional[str] = None, api_secret: Optional[str] = None) -> KasmClient:
    """Factory function to get the appropriate Kasm Client."""
    if mode == "live" and api_url and api_key and api_secret:
        return RealKasmClient(api_url, api_key, api_secret)
    return SimulatedKasmClient()
