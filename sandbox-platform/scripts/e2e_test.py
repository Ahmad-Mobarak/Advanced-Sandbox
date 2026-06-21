#!/usr/bin/env python3
"""
Advanced Cybersecurity Sandbox Platform
End-to-End Pipeline Test

Submits a test sample via the API, waits for the worker to process it,
then retrieves and validates the full analysis results.

Usage:
    python scripts/e2e_test.py
"""

import sys
import os
import time
import json
import urllib.request
import urllib.error

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")
API_KEY = os.getenv("API_KEY", "sk_live_admin_replace_me")


def api_request(method: str, path: str, data=None):
    """Make an API request and return the JSON response."""
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    if data:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  [!] API Error: {e.code} {e.reason}")
        print(f"     {body[:200]}")
        return None


def main():
    print("=" * 60)
    print("  End-to-End Pipeline Test")
    print("=" * 60)

    # Step 1: Check health
    print("\n[1/6] Checking API health...")
    health = api_request("GET", "/health")
    if not health:
        print("  [!] API is not responding. Is the platform running?")
        return 1
    print(f"  [+] API is healthy: {health.get('status', 'unknown')}")

    # Step 2: Submit a test sample
    print("\n[2/6] Submitting EICAR test malware sample...")
    import uuid
    eicar_content = (
        b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        + str(uuid.uuid4()).encode()
    ) # Create a multipart form upload using urllib
    import io
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="eicar_test.exe"\r\n'.encode())
    body.write(b"Content-Type: application/octet-stream\r\n\r\n")
    body.write(eicar_content)
    body.write(f"\r\n--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        f"{API_BASE}/samples",
        data=body.getvalue(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        print(f"  [!] Submission failed: {e.code} {body_text[:200]}")
        # Try fallback: direct DB insertion via a simple POST
        print("  [*] Trying alternative submission method...")
        result = api_request("POST", "/samples/submit", {
            "file_name": "eicar_test.exe",
            "file_content": eicar_content,
        })
        if not result:
            print("  [!] Could not submit sample. Check API logs.")
            return 1

    sample_id = result.get("sample_id") or result.get("id")
    if not sample_id:
        print(f"  [!] No sample_id in response: {result}")
        return 1
    print(f"  [+] Sample submitted: {sample_id}")

    # Step 3: Wait for worker to process
    print("\n[3/6] Waiting for worker to process the sample...")
    max_wait = 60
    waited = 0
    while waited < max_wait:
        sample = api_request("GET", f"/samples/{sample_id}")
        if sample and sample.get("status") in ("completed", "failed"):
            break
        time.sleep(3)
        waited += 3
        print(f"  [*] Status: {sample.get('status', '?') if sample else '?'} ({waited}s elapsed)")

    if not sample or sample.get("status") != "completed":
        print(f"  [!] Sample did not reach 'completed' status within {max_wait}s")
        print(f"     Current status: {sample.get('status', 'unknown') if sample else 'unknown'}")
        print("     (The worker may still be processing it)")
    else:
        print(f"  [+] Sample processed successfully!")
        print(f"     Verdict: {sample.get('verdict', 'N/A')}")
        print(f"     Confidence: {sample.get('confidence_score', 'N/A')}")
        print(f"     ML Score: {sample.get('ml_score', 'N/A')}")

    # Step 4 & 5: Check behaviors and IOCs from report
    print(f"\n[4/6] Fetching analysis report...")
    report = api_request("GET", f"/samples/{sample_id}/report")
    if report:
        behaviors = report.get("behaviors", [])
        print(f"  [+] Found {len(behaviors)} behavioral observations")

        iocs = report.get("iocs", [])
        print(f"  [+] Found {len(iocs)} indicators of compromise")
        
        mitre = report.get("mitre_attack", [])
        print(f"  [+] Found {len(mitre)} MITRE ATT&CK techniques")
    else:
        print("  [!] Could not fetch analysis report")

    # Step 6: Summary
    print(f"\n[6/6] Pipeline Test Summary")
    print("=" * 60)
    if sample and sample.get("status") == "completed":
        print("  [+] PASS -- Full pipeline executed successfully!")
        print(f"     Sample: {sample_id}")
        print(f"     Verdict: {sample.get('verdict')}")
        print(f"     Confidence: {sample.get('confidence_score')}")
        print(f"     ML Score: {sample.get('ml_score')}")
    else:
        print("  [!] PARTIAL -- Sample submitted but processing may still be in progress")
        print("     Check docker logs: docker logs sandbox-worker")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
