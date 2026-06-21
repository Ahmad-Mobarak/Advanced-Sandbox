#!/bin/bash
echo "=== Kasm Server/Agent Status ==="
docker exec kasm_db psql -U kasmapp -d kasm -c "SELECT server_id, hostname, enabled, operational_status, cores, memory, cores_override, memory_override, container_limit FROM servers;"

echo ""
echo "=== Kasm Images Available ==="
docker exec kasm_db psql -U kasmapp -d kasm -c "SELECT image_id, name, enabled, available FROM images LIMIT 10;"

echo ""
echo "=== Active Kasm Sessions ==="
docker exec kasm_db psql -U kasmapp -d kasm -c "SELECT kasm_id, operational_status, server_id FROM kasms LIMIT 10;"
