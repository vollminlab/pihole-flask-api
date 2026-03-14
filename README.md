# pihole-flask-api

A lightweight Flask REST API for managing Pi-hole DNS A records. Allows authorized clients to add and remove entries in Pi-hole's `pihole.toml` configuration via HTTP.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/add-a-record` | Add a DNS A record |
| `DELETE` | `/delete-a-record` | Remove a DNS A record by domain |

### Request bodies

**POST /add-a-record**
```json
{ "domain": "myhost.lan", "ip": "192.168.1.100" }
```

**DELETE /delete-a-record**
```json
{ "domain": "myhost.lan" }
```

All requests require a `Authorization: Bearer <API_KEY>` header.

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> `inotify-tools` is also required on the host for the permissions-watcher script:
> `sudo apt install inotify-tools`

### 2. Configure the API key

Copy `.env.example` to `/etc/pihole-flask-api/.env` and set a strong random key:

```bash
sudo mkdir -p /etc/pihole-flask-api
sudo cp .env.example /etc/pihole-flask-api/.env
sudo nano /etc/pihole-flask-api/.env
sudo chmod 600 /etc/pihole-flask-api/.env
```

### 3. Deploy

Use the provided deploy script, which handles cloning the repo, setting up the virtualenv, writing the env file, and installing the systemd services:

```bash
bash scripts/deploy.sh <host>
```

The script will prompt for the API key and requires SSH access with sudo on the target host.

## Security notes

- Run behind a reverse proxy (nginx, Caddy) with TLS — the API transmits the Bearer token in plain HTTP otherwise.
- Restrict access to trusted hosts/networks at the firewall level; the service binds to `0.0.0.0:5001`.
- Keep `/etc/pihole-flask-api/.env` readable only by the service user (`chmod 600`).
