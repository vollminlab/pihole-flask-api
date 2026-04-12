# CLAUDE.md — pihole-flask-api

Lightweight Flask/Gunicorn REST API for managing Pi-hole DNS records. Runs on both Pi-hole hosts (pihole1 and pihole2) at port 5001.

## What it does

Reads and writes `/etc/pihole/pihole.toml` directly. Two record types:

| Type | TOML key | Entry format |
|------|----------|-------------|
| A record | `dns.hosts` | `"192.168.1.x hostname.vollminlab.com"` |
| CNAME record | `dns.cnameRecords` | `"cname.vollminlab.com,target.vollminlab.com"` |

## Endpoints

| Method | Path | Body |
|--------|------|------|
| `POST` | `/add-a-record` | `{"domain": "...", "ip": "..."}` |
| `DELETE` | `/delete-a-record` | `{"domain": "..."}` |
| `POST` | `/add-cname-record` | `{"domain": "...", "target": "..."}` |
| `DELETE` | `/delete-cname-record` | `{"domain": "..."}` |

All requests require `Authorization: Bearer <API_KEY>`.

## Auth

API key stored in `/etc/pihole-flask-api/.env` on each host. Retrieve from 1Password:

```bash
op read "op://Homelab/Recordimporter/credential"
```

## DNS architecture

Three categories of DNS record:

| Category | Type | Target | Examples |
|----------|------|--------|---------|
| Machine hostnames | A | Own IP | pihole1/2, esxi01-03, k8scp01-03, haproxy01/02 |
| Cluster app subdomains | A | `192.168.152.244` (ingress-nginx MetalLB) | homepage, radarr, shlink, go |
| NPM-proxied infra | A | `192.168.152.2` (Nginx Proxy Manager) | pihole, plex, truenas, udm, vcenter, haproxy (stats) |
| Externally-accessible DMZ | CNAME | `dynamic.vollminlab.com` → public WAN IP | bluemap |

- `haproxyvip.vollminlab.com` → `192.168.152.7` is the k8s **API** VIP (port 6443 only), not for app traffic
- CNAME records are used for Pi-hole-internal aliases (e.g. `pihole1.vollminlab.com` → `pihole1.mgmt.vollminlab.com`)

## Deployment

Uses `scripts/deploy.sh <host>`. Idempotent — safe to re-run for updates.

After pushing code changes, deploy to both hosts:

```bash
export PATH="/c/Windows/System32/OpenSSH:$PATH"
ssh pihole1 "cd /opt/pihole-flask-api && sudo git pull && sudo systemctl restart pihole-flask-api"
ssh pihole2 "cd /opt/pihole-flask-api && sudo git pull && sudo systemctl restart pihole-flask-api"
```

DNS record changes via the API must be made against **both** pihole1 (`192.168.100.2:5001`) and pihole2 (`192.168.100.3:5001`) directly. Do not rely on nebula-sync to replicate API-driven changes — it syncs on its own schedule and the timing is unpredictable.

## Key files

| File | Purpose |
|------|---------|
| `src/recordimporter.py` | Flask app — all route handlers |
| `scripts/deploy.sh` | Idempotent deploy script |
| `/etc/pihole-flask-api/.env` | API key (on the remote host, not in repo) |
| `/opt/pihole-api.log` | Application log (on the remote host) |
