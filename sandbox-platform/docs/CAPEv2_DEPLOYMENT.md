# CAPEv2 Deployment & Integration Guide

## Overview
CAPEv2 is the primary malware detonation sandbox for the Advanced Sandbox Platform. Due to its requirement for dedicated hardware (KVM/nested virtualization) and precise networking, it is deployed independently of the Dockerized microservices stack.

## Hardware Requirements
- **OS**: Ubuntu 22.04 LTS (Bare Metal or Cloud VM with nested virtualization enabled)
- **CPU**: Minimum 8 cores (vt-x / AMD-V enabled)
- **RAM**: 32GB+ recommended
- **Disk**: 500GB+ SSD

## Step 1: Base Installation
1. Install KVM and QEMU:
   ```bash
   sudo apt update
   sudo apt install -y qemu-kvm libvirt-clients libvirt-daemon-system bridge-utils virtinst libvirt-daemon virt-manager
   ```
2. Clone the CAPEv2 installer:
   ```bash
   git clone https://github.com/kevoreilly/CAPEv2.git /opt/CAPEv2
   cd /opt/CAPEv2/installer
   sudo ./cape2.sh all cape
   ```

## Step 2: Virtual Machine Configuration
You must configure your Windows 10/Linux guest VMs according to the official CAPEv2 guidelines:
1. Disable Windows Defender, Firewall, and Auto Updates.
2. Install the Python agent (`agent.py`) and set it to run on startup.
3. Take a clean snapshot (e.g., `clean_win10`).

## Step 3: Network Wiring
CAPEv2 uses a host-only bridge (usually `virbr0`) to route traffic:
- Set up iptables rules to allow Internet access for the VMs while logging PCAP data.
- Ensure the Sandbox Platform backend can reach the CAPE API (`http://<cape-ip>:8000`).

## Step 4: Platform Integration
Update the `.env` file on the Sandbox Platform server:
```env
CAPEV2_MODE=live
CAPEV2_API_URL=http://<cape-ip>:8000
```

## Step 5: Health Check
Run the following from the Sandbox Platform server to verify connectivity:
```bash
curl -H "Authorization: Bearer <api_token>" http://<cape-ip>:8000/apiv2/cuckoo/status/
```
