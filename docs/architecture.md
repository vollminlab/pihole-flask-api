# pihole-flask-api — Architecture

## Overview

A lightweight Flask/Gunicorn REST API that provides programmatic management of Pi-hole v6+ DNS records. It reads and writes directly to  on the Pi-hole host.

The API runs identically on **both pihole1 and pihole2**. There is no automatic replication between them — callers must write to both hosts independently.

## Deployment topology

```
External caller (external-dns, scripts, Claude Code)
        │
        ├──► pihole1 (192.168.100.2:5001) ──► /etc/pihole/pihole.toml
        │
        └──► pihole2 (192.168.100.3:5001) ──► /etc/pihole/pihole.toml
```

Pi-hole itself uses VRRP to present a single VIP to DNS clients, but the management API must be called against both hosts directly. Do not rely on nebula-sync for replication — it has unpredictable timing.

## TOML record format

Pi-hole v6 stores DNS records in `/etc/pihole/pihole.toml` under `[dns]`:

```toml
[dns]
  hosts = [
    "192.168.100.2 pihole1.vollminlab.com",
    "192.168.152.244 homepage.vollminlab.com"
  ]
  cnameRecords = [
    "go.vollminlab.com,shlink.vollminlab.com"
  ]
```

**A record format:** `"<IP> <hostname>"` (space-separated, single string per entry)
**CNAME format:** `"<alias>,<target>"` (comma-separated, single string per entry)

## Permissions problem and solution

Pi-hole frequently rewrites `pihole.toml` (on restarts, FTL updates, gravity runs), resetting ownership to `pihole:pihole 644`. The API runs as `www-data`, which cannot write a 644 file owned by `pihole`.

**Solution:** A companion `fix-pihole-perms` systemd service watches `/etc/pihole` with `inotifywait` and immediately resets `pihole.toml` to `664 pihole:pihole` on any write event, restoring `www-data` write access within milliseconds.

```
Pi-hole rewrites pihole.toml (resets perms to 644)
        │
        └──► inotifywait detects close_write/move/create
                    │
                    └──► chmod 664 + chown pihole:pihole
                                │
                                └──► www-data can write again
```

## Authentication

All endpoints require a `Authorization: Bearer <token>` header. The token is compared against the `PIHOLE_API_KEY` environment variable loaded from `/etc/pihole-flask-api/.env`. No JWT — simple string equality.

The API key is stored in 1Password:
```bash
op read "op://Homelab/recordimporter-api-token/password"
```

## Idempotency behaviour

Add operations (`POST`) are idempotent:
- If the exact record already exists → returns `200` with `"Record already exists"` (not `409` — the README is wrong on this)
- CNAME deduplication checks domain only, not target — adding `alias → target2` when `alias → target1` exists returns `200` without updating

Delete operations (`DELETE`) remove **all** entries matching the domain, not just the first match.

## File locations on Pi-hole hosts

| Path | Purpose |
|------|---------|
| `/opt/pihole-flask-api/` | Application (git clone) |
| `/opt/pihole-flask-api-venv/` | Python virtualenv |
| `/etc/pihole-flask-api/.env` | API key (root:www-data 640) |
| `/opt/pihole-api.log` | Application log |
| `/usr/local/bin/fix-pihole-perms.sh` | Permissions watcher script |
| `/etc/systemd/system/pihole-flask-api.service` | Main service |
| `/etc/systemd/system/fix-pihole-perms.service` | Permissions watcher service |

## DNS record categories in this homelab

Three categories of A records are managed via this API:

1. **Infrastructure hosts** — pihole1, pihole2, k8s nodes, GLaDOS
2. **Kubernetes services** — one A record per ingress (pointing to MetalLB VIP)
3. **CNAME aliases** — DMZ services mapped to their internal ingress names

CNAMEs are used for DMZ services where the external hostname differs from the internal Kubernetes service name.
