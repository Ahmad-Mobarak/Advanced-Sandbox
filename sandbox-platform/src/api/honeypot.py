"""
Advanced Cybersecurity Sandbox Platform
Cowrie Honeypot Webhook API

Receives real-time events from Cowrie SSH/Telnet honeypots,
parses them into actionable intelligence, and stores them
in the database. Auto-extracts IOCs and malware sample hashes.
"""

import os
import hashlib
import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header
import asyncpg

from src.advanced.schemas import CowrieEvent, ParsedHoneypotEvent
from src.advanced.cowrie_parser import CowrieParser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/honeypot", tags=["Honeypot"])

COWRIE_WEBHOOK_TOKEN = os.getenv("COWRIE_WEBHOOK_TOKEN", "")

# Shared database pool (set by the parent app on startup)
_db_pool: Optional[asyncpg.Pool] = None
_parser = CowrieParser()


def set_db_pool(pool: asyncpg.Pool):
    """Called by the parent app to inject the database connection pool."""
    global _db_pool
    _db_pool = pool


async def get_db():
    """Dependency that provides a database connection."""
    if _db_pool is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    async with _db_pool.acquire() as conn:
        yield conn


async def verify_webhook_token(x_cowrie_token: str = Header(None, alias="X-Cowrie-Token")):
    """Verify the webhook authentication token."""
    if not COWRIE_WEBHOOK_TOKEN:
        raise HTTPException(status_code=500, detail="COWRIE_WEBHOOK_TOKEN not configured")
    if x_cowrie_token != COWRIE_WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid webhook token")
    return True


@router.post("/cowrie/webhook", summary="Receive Cowrie Honeypot Events")
async def receive_cowrie_event(
    event: CowrieEvent,
    conn: asyncpg.Connection = Depends(get_db),
    _auth: bool = Depends(verify_webhook_token),
):
    """
    Webhook endpoint for Cowrie SSH/Telnet honeypot events.

    Automatically:
    - Parses the event to extract attacker IP, commands, credentials
    - Stores the raw event in the honeypot_events table
    - Creates IOC entries for attacker IPs
    - If a file download is detected, creates a sample entry for auto-analysis
    """
    # Parse the event
    parsed = _parser.parse_event(event)

    # Store in honeypot_events table
    event_id = await conn.fetchval("""
        INSERT INTO honeypot_events (
            cowrie_session_id, attacker_ip, event_type, raw_event
        ) VALUES ($1, $2, $3, $4)
        RETURNING id
    """,
        event.session,
        event.src_ip,
        event.eventid,
        parsed.raw_event,
    )

    logger.info(
        "Honeypot event stored: %s from %s (session=%s)",
        event.eventid, event.src_ip, event.session,
    )

    # Auto-create IOC for attacker IP
    if parsed.created_ioc_value:
        await conn.execute("""
            INSERT INTO iocs (sample_id, ioc_type, value, confidence, description)
            VALUES (
                (SELECT id FROM samples LIMIT 1),
                'ip', $1, 'high',
                'Attacker IP captured by Cowrie honeypot'
            )
            ON CONFLICT (ioc_type, value) DO UPDATE
            SET last_seen = NOW(), confidence = 'high'
        """, parsed.created_ioc_value)

    # If Cowrie captured a malware download, create a sample entry for auto-analysis
    correlated_sample_id = None
    if parsed.created_sample_hash:
        # Check if sample already exists
        existing = await conn.fetchrow(
            "SELECT id FROM samples WHERE sha256_hash = $1",
            parsed.created_sample_hash,
        )
        if existing:
            correlated_sample_id = existing["id"]
        else:
            # Create a new sample entry for the honeypot-captured malware
            correlated_sample_id = await conn.fetchval("""
                INSERT INTO samples (
                    sha256_hash, sha1_hash, md5_hash,
                    file_name, file_size, file_type,
                    source_type, priority, status
                ) VALUES ($1, $2, $3, $4, 0, 'unknown', 'honeypot', 8, 'pending')
                RETURNING id
            """,
                parsed.created_sample_hash,
                parsed.created_sample_hash[:40],  # placeholder
                parsed.created_sample_hash[:32],  # placeholder
                f"honeypot-download-{parsed.created_sample_hash[:16]}",
            )

            # Queue it for analysis
            await conn.execute("""
                INSERT INTO submission_queue (sample_id, priority)
                VALUES ($1, 8)
            """, correlated_sample_id)

            logger.info(
                "Auto-queued honeypot-captured malware %s for analysis",
                parsed.created_sample_hash[:16],
            )

        # Link the honeypot event to the sample
        await conn.execute("""
            UPDATE honeypot_events
            SET correlated_sample_id = $1
            WHERE id = $2
        """, correlated_sample_id, event_id)

    return {
        "status": "received",
        "event_id": str(event_id),
        "event_type": event.eventid,
        "attacker_ip": event.src_ip,
        "ioc_created": parsed.created_ioc_value is not None,
        "sample_queued": parsed.created_sample_hash is not None,
    }


@router.get("/events", summary="List Honeypot Events")
async def list_honeypot_events(
    limit: int = 50,
    conn: asyncpg.Connection = Depends(get_db),
):
    """Retrieve recent honeypot events."""
    rows = await conn.fetch("""
        SELECT id, cowrie_session_id, attacker_ip, event_type,
               raw_event, correlated_sample_id, created_at
        FROM honeypot_events
        ORDER BY created_at DESC
        LIMIT $1
    """, limit)

    return {
        "total": len(rows),
        "events": [dict(r) for r in rows],
    }


@router.get("/stats", summary="Honeypot Statistics")
async def honeypot_stats(conn: asyncpg.Connection = Depends(get_db)):
    """Get aggregated honeypot statistics."""
    total = await conn.fetchval("SELECT COUNT(*) FROM honeypot_events")
    unique_ips = await conn.fetchval(
        "SELECT COUNT(DISTINCT attacker_ip) FROM honeypot_events"
    )
    top_attackers = await conn.fetch("""
        SELECT attacker_ip, COUNT(*) as event_count
        FROM honeypot_events
        GROUP BY attacker_ip
        ORDER BY event_count DESC
        LIMIT 10
    """)
    event_types = await conn.fetch("""
        SELECT event_type, COUNT(*) as count
        FROM honeypot_events
        GROUP BY event_type
        ORDER BY count DESC
    """)

    return {
        "total_events": total,
        "unique_attacker_ips": unique_ips,
        "top_attackers": [dict(r) for r in top_attackers],
        "event_type_distribution": [dict(r) for r in event_types],
    }
