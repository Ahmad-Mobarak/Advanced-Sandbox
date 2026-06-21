import asyncio
import asyncpg
import os
import uuid
import json

async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://sandbox:sandbox_dev_password_change_me@localhost:5432/sandbox_db")
    print(f"Connecting to {db_url}")
    conn = await asyncpg.connect(db_url)
    
    # Check if we already have a demo sample
    sample_id = await conn.fetchval("SELECT id FROM samples LIMIT 1")
    
    if not sample_id:
        sample_id = uuid.uuid4()
        await conn.execute("""
            INSERT INTO samples (id, sha256_hash, sha1_hash, md5_hash, file_name, file_size, status, verdict, confidence_score)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, sample_id, "42514072b0fe44b8f66e0395bcd23a0b1d1642c28ed00831f1527b2f41b14670", "e5c46b55a80e1ec0e7646cd62660f607142bd017", "9e107d9d372bb6826bd81d3542a419d6", "invoice_overdue.exe", 102400, "completed", "malicious", 0.95)
        print("Inserted demo sample.")

    # Seed IOCs
    iocs_count = await conn.fetchval("SELECT COUNT(*) FROM iocs")
    if iocs_count == 0:
        await conn.execute("""
            INSERT INTO iocs (sample_id, ioc_type, value, confidence, tlp, ti_tags) VALUES 
            ($1, 'ip', '185.158.248.42', 'high', 'red', '{"cobalt strike", "c2"}'),
            ($1, 'domain', 'update-windows-service.com', 'high', 'amber', '{"phishing", "malware"}'),
            ($1, 'file_hash', '1234567890abcdef1234567890abcdef', 'medium', 'green', '{"dropper"}'),
            ($1, 'registry_key', 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\Updater', 'low', 'white', '{}')
        """, sample_id)
        print("Inserted demo IOCs.")

    # Seed Behaviors (MITRE ATT&CK)
    behaviors_count = await conn.fetchval("SELECT COUNT(*) FROM behaviors")
    if behaviors_count == 0:
        await conn.execute("""
            INSERT INTO behaviors (sample_id, behavior_type, severity, description, mitre_attack_id, mitre_attack_tactic, mitre_attack_technique, sigma_rule_name) VALUES 
            ($1, 'persistence', 'high', 'Adds Run key to start automatically', 'T1060', 'Persistence', 'Registry Run Keys / Startup Folder', 'Suspicious Run Key Creation'),
            ($1, 'exfiltration', 'critical', 'Sends data over an encrypted channel', 'T1041', 'Exfiltration', 'Exfiltration Over C2 Channel', 'C2 Traffic Detected'),
            ($1, 'evasion', 'medium', 'Sleeps for 60 seconds to evade sandboxes', 'T1497', 'Defense Evasion', 'Virtualization/Sandbox Evasion', 'Sandbox Evasion Timeout')
        """, sample_id)
        print("Inserted demo behaviors.")

    # Seed ML Feedback
    ml_count = await conn.fetchval("SELECT COUNT(*) FROM ml_feedback")
    if ml_count == 0:
        await conn.execute("""
            INSERT INTO ml_feedback (sample_id, predicted_verdict, actual_verdict, predicted_confidence, analyst_notes, incorporated) VALUES 
            ($1, 'malicious', 'benign', 0.85, 'This is a legitimate internal updater falsely flagged by the model.', FALSE),
            ($1, 'benign', 'malicious', 0.45, 'Missed ransomware dropper.', TRUE)
        """, sample_id)
        print("Inserted demo ML Feedback.")

    await conn.close()
    print("Database seeding complete.")

if __name__ == "__main__":
    asyncio.run(main())
