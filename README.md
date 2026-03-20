# pihole-flask-api

A lightweight REST API for managing Pi-hole DNS records. Exposes HTTP endpoints that allow authorized clients to add and remove A records and CNAME records in Pi-hole's `pihole.toml` configuration file. Useful for automating DNS record management from scripts, Ansible, or other tooling without SSH access to the Pi-hole host.

## How it works

The API runs as a Gunicorn/Flask service on the Pi-hole host itself, running as `www-data` with group access to `pihole.toml`. A companion `fix-pihole-perms` service watches `/etc/pihole` with `inotifywait` and resets `pihole.toml` ownership after Pi-hole rewrites it — keeping the API able to write DNS records even across Pi-hole updates and restarts.

## Requirements

- Debian-based Linux host (Raspberry Pi OS, Ubuntu, etc.)
- Pi-hole v6+ (uses `pihole.toml`)
- SSH access with `sudo` to the target host
- Git Bash or any bash shell on your local machine for running the deploy script

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/add-a-record` | Add a DNS A record |
| `DELETE` | `/delete-a-record` | Remove a DNS A record by domain |
| `POST` | `/add-cname-record` | Add a DNS CNAME record |
| `DELETE` | `/delete-cname-record` | Remove a DNS CNAME record by domain |

All requests require an `Authorization: Bearer <API_KEY>` header.

### POST /add-a-record

Adds a DNS A record to `dns.hosts` in `pihole.toml`. Returns `409` if the record already exists.

```bash
curl -X POST http://<host>:5001/add-a-record \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_KEY>' \
  -d '{"domain": "myhost.lan", "ip": "192.168.1.100"}'
```

```json
{"message": "Record added successfully"}
```

### DELETE /delete-a-record

Removes all A records for the given domain. Returns `404` if no matching record exists.

```bash
curl -X DELETE http://<host>:5001/delete-a-record \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_KEY>' \
  -d '{"domain": "myhost.lan"}'
```

```json
{"message": "Deleted 1 record(s) for myhost.lan"}
```

### POST /add-cname-record

Adds a CNAME record to `dns.cnameRecords` in `pihole.toml`. Returns `409` if a CNAME for that domain already exists.

```bash
curl -X POST http://<host>:5001/add-cname-record \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_KEY>' \
  -d '{"domain": "go.vollminlab.com", "target": "haproxyvip.vollminlab.com"}'
```

```json
{"message": "Record added successfully"}
```

### DELETE /delete-cname-record

Removes the CNAME record for the given domain. Returns `404` if no matching record exists.

```bash
curl -X DELETE http://<host>:5001/delete-cname-record \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_KEY>' \
  -d '{"domain": "go.vollminlab.com"}'
```

```json
{"message": "Deleted 1 record(s) for go.vollminlab.com"}
```

## Deployment

### 1. Fork and configure

Fork this repo, then update `REPO_URL` in `scripts/deploy.sh` to point to your fork:

```bash
REPO_URL="https://github.com/<your-username>/pihole-flask-api.git"
```

### 2. Generate an API key

Use any method to generate a strong random key, for example:

```bash
openssl rand -base64 32
```

### 3. Run the deploy script

The deploy script handles everything on the target host: installing dependencies, cloning the repo, setting up the virtualenv, writing the env file, and installing the systemd services.

```bash
bash scripts/deploy.sh <host>
```

The script will prompt for the API key and requires SSH access with `sudo` on the target host. It is idempotent — safe to re-run for updates.

### What gets deployed

| Path | Description |
|------|-------------|
| `/opt/pihole-flask-api/` | Application code (git clone) |
| `/opt/pihole-flask-api-venv/` | Python virtualenv |
| `/etc/pihole-flask-api/.env` | API key (root:www-data, mode 640) |
| `/opt/pihole-api.log` | Application log |
| `/usr/local/bin/fix-pihole-perms.sh` | Permissions watcher script |
| `/etc/systemd/system/pihole-flask-api.service` | Main service |
| `/etc/systemd/system/fix-pihole-perms.service` | Permissions watcher service |

## Configuration

The only required configuration is the API key, set in `/etc/pihole-flask-api/.env`:

```
PIHOLE_API_KEY=your-secret-api-key-here
```

See `.env.example` for the template. The following paths are hardcoded in `src/recordimporter.py` and can be changed there if needed:

| Variable | Default |
|----------|---------|
| `TOML_PATH` | `/etc/pihole/pihole.toml` |
| `LOG_FILE` | `/opt/pihole-api.log` |

## Security notes

- **Use a reverse proxy with TLS** (nginx, Caddy) — the Bearer token is transmitted in plain HTTP otherwise.
- **Restrict network access** — the service binds to `0.0.0.0:5001`; limit access to trusted hosts at the firewall level.
- **Protect the env file** — `/etc/pihole-flask-api/.env` is `root:www-data 640`; only the service user can read it.
- **Rotate the API key** by updating `/etc/pihole-flask-api/.env` and restarting the service: `sudo systemctl restart pihole-flask-api`.

## Troubleshooting

**Service fails to start**
```bash
sudo journalctl -u pihole-flask-api --no-pager -n 30
```

**API returns 401**
Verify the `Authorization: Bearer <key>` header matches the key in `/etc/pihole-flask-api/.env`.

**Records not persisting across Pi-hole restarts**
Check that the `fix-pihole-perms` service is running:
```bash
sudo systemctl status fix-pihole-perms
```

**Permission denied on `pihole.toml`**
The `www-data` user needs read/write access. The `fix-pihole-perms` service handles this automatically, but you can also fix it manually:
```bash
sudo chown pihole:pihole /etc/pihole/pihole.toml
sudo chmod 664 /etc/pihole/pihole.toml
sudo setfacl -m u:www-data:rw /etc/pihole/pihole.toml
```

## License

MIT — see [LICENSE](LICENSE).
