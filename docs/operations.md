# pihole-flask-api — Operations

## Deploying / updating

**Initial deploy to a new Pi-hole host:**
```bash
cd ~/repos/vollminlab/pihole-flask-api
bash scripts/deploy.sh pihole1
bash scripts/deploy.sh pihole2
```

The deploy script is idempotent — safe to re-run. It installs dependencies, sets up the virtualenv, writes the `.env` file, and enables/starts both systemd services.

**Updating after a code change:**
```bash
ssh pihole1 "cd /opt/pihole-flask-api && sudo git pull && sudo systemctl restart pihole-flask-api"
ssh pihole2 "cd /opt/pihole-flask-api && sudo git pull && sudo systemctl restart pihole-flask-api"
```

Always update both hosts. Update one at a time to maintain DNS availability.

## Checking service health

```bash
# Service status
ssh pihole1 "systemctl status pihole-flask-api fix-pihole-perms"

# Live logs
ssh pihole1 "sudo journalctl -u pihole-flask-api -f"
ssh pihole1 "sudo tail -f /opt/pihole-api.log"

# Quick health test (replace with actual API key)
API_KEY=$(op read "op://Homelab/recordimporter-api-token/password")
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $API_KEY" \
  http://192.168.100.2:5001/add-a-record \
  -d '{"domain":"health-check.vollminlab.com","ip":"127.0.0.1"}'
# Then clean up: DELETE the health-check record
```

## Restarting services

```bash
ssh pihole1 "sudo systemctl restart pihole-flask-api"
ssh pihole1 "sudo systemctl restart fix-pihole-perms"
```

If `fix-pihole-perms` is not running, the API will fail on writes after any Pi-hole config rewrite. Check this first when troubleshooting 500 errors.

## Log locations

| Log | Content |
|-----|---------|
| `/opt/pihole-api.log` | All API requests, auth failures, TOML read/write operations |
| `journalctl -u pihole-flask-api` | Service lifecycle, startup errors, Gunicorn output |
| `journalctl -u fix-pihole-perms` | Permission reset events |

## Rotating the API key

1. Generate a new key: `openssl rand -hex 32`
2. Store in 1Password: update `op://Homelab/recordimporter-api-token/password`
3. Update on both hosts:
   ```bash
   NEW_KEY="<new-key>"
   ssh pihole1 "echo 'PIHOLE_API_KEY=${NEW_KEY}' | sudo tee /etc/pihole-flask-api/.env && sudo systemctl restart pihole-flask-api"
   ssh pihole2 "echo 'PIHOLE_API_KEY=${NEW_KEY}' | sudo tee /etc/pihole-flask-api/.env && sudo systemctl restart pihole-flask-api"
   ```
4. Update any callers (external-dns, scripts) with the new key

## Troubleshooting

**500 on all write operations:**
- Check if `fix-pihole-perms` is running: `systemctl status fix-pihole-perms`
- Check permissions on pihole.toml: `ls -la /etc/pihole/pihole.toml` — should be `664 pihole:pihole`
- Manually fix: `sudo chmod 664 /etc/pihole/pihole.toml`

**401 Unauthorized:**
- Verify `Authorization: Bearer <key>` header (note the space after `Bearer`)
- Confirm the key matches `/etc/pihole-flask-api/.env` on that host
- Check `/opt/pihole-api.log` for `Authorization failed` entries

**Record not persisting after Pi-hole restart:**
- Pi-hole v6 reads from `pihole.toml` on start — records written via this API should persist
- If records disappear, check if pihole.toml is being replaced wholesale by an update

**API only updated one Pi-hole:**
- Manually replay the API call against the other host
- Check both hosts' `pihole.toml` to confirm parity
