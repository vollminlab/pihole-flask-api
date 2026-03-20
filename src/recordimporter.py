from flask import Flask, request, jsonify
import tomlkit
import logging
import os

env_path = "/etc/pihole-flask-api/.env"
if os.path.isfile(env_path):
    for line in open(env_path, 'r'):
        key,_,value = line.strip().partition("=")
        os.environ[key] = value

TOML_PATH = "/etc/pihole/pihole.toml"
API_KEY = os.environ.get("PIHOLE_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing PIHOLE_API_KEY in environment")
LOG_FILE  = "/opt/pihole-api.log"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

app = Flask(__name__)

def _authorize():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth.split(" ", 1)[1] != API_KEY:
        logger.error("Unauthorized access attempt.")
        return False
    return True

def _load_toml():
    with open(TOML_PATH, "r", encoding="utf-8") as f:
        return tomlkit.parse(f.read())

def _save_toml(data):
    with open(TOML_PATH, "w", encoding="utf-8") as f:
        f.write(tomlkit.dumps(data))

@app.route("/add-a-record", methods=["POST"])
def add_a_record():
    logger.debug("Received POST /add-a-record: %s", request.json)
    if not _authorize():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    domain = data.get("domain")
    ip     = data.get("ip")
    if not domain or not ip:
        logger.error("Missing domain or IP in POST")
        return jsonify({"error": "Missing domain or IP"}), 400

    try:
        toml_data = _load_toml()
        hosts = toml_data.setdefault("dns", {}).setdefault("hosts", [])
    except Exception as e:
        logger.error("Failed to read TOML: %s", e)
        return jsonify({"error": f"Failed to read TOML: {e}"}), 500

    entry = f"{ip} {domain}"
    if entry in hosts:
        logger.error("Record %s already exists", entry)
        return jsonify({"error": "Record already exists"}), 409

    hosts.append(entry)
    try:
        _save_toml(toml_data)
        logger.debug("Appended and saved new record: %s", entry)
    except Exception as e:
        logger.error("Failed to write TOML: %s", e)
        return jsonify({"error": f"Failed to write TOML: {e}"}), 500

    return jsonify({"message": "Record added successfully"}), 200

@app.route("/delete-a-record", methods=["DELETE"])
def delete_a_record():
    logger.debug("Received DELETE /delete-a-record: %s", request.json)
    if not _authorize():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    domain = data.get("domain")
    if not domain:
        logger.error("Missing domain in DELETE")
        return jsonify({"error": "Missing domain"}), 400

    try:
        toml_data = _load_toml()
        hosts = toml_data.setdefault("dns", {}).setdefault("hosts", [])
    except Exception as e:
        logger.error("Failed to read TOML: %s", e)
        return jsonify({"error": f"Failed to read TOML: {e}"}), 500

    # Remove any entries ending in the given domain
    before = len(hosts)
    hosts = [h for h in hosts if not h.split() or h.split()[1] != domain]
    removed_count = before - len(hosts)

    if removed_count == 0:
        logger.error("No record found for domain %s", domain)
        return jsonify({"error": "Record not found"}), 404

    toml_data["dns"]["hosts"] = hosts
    try:
        _save_toml(toml_data)
        logger.debug("Removed %d entries for domain %s", removed_count, domain)
    except Exception as e:
        logger.error("Failed to write TOML: %s", e)
        return jsonify({"error": f"Failed to write TOML: {e}"}), 500

    return jsonify({"message": f"Deleted {removed_count} record(s) for {domain}"}), 200


@app.route("/add-cname-record", methods=["POST"])
def add_cname_record():
    logger.debug("Received POST /add-cname-record: %s", request.json)
    if not _authorize():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    domain = data.get("domain")
    target = data.get("target")
    if not domain or not target:
        logger.error("Missing domain or target in POST")
        return jsonify({"error": "Missing domain or target"}), 400

    try:
        toml_data = _load_toml()
        cnames = toml_data.setdefault("dns", {}).setdefault("cnameRecords", [])
    except Exception as e:
        logger.error("Failed to read TOML: %s", e)
        return jsonify({"error": f"Failed to read TOML: {e}"}), 500

    entry = f"{domain},{target}"
    if any(r.split(",")[0] == domain for r in cnames):
        logger.error("CNAME record for %s already exists", domain)
        return jsonify({"error": "Record already exists"}), 409

    cnames.append(entry)
    try:
        _save_toml(toml_data)
        logger.debug("Appended and saved new CNAME record: %s", entry)
    except Exception as e:
        logger.error("Failed to write TOML: %s", e)
        return jsonify({"error": f"Failed to write TOML: {e}"}), 500

    return jsonify({"message": "Record added successfully"}), 200


@app.route("/delete-cname-record", methods=["DELETE"])
def delete_cname_record():
    logger.debug("Received DELETE /delete-cname-record: %s", request.json)
    if not _authorize():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json() or {}
    domain = data.get("domain")
    if not domain:
        logger.error("Missing domain in DELETE")
        return jsonify({"error": "Missing domain"}), 400

    try:
        toml_data = _load_toml()
        cnames = toml_data.setdefault("dns", {}).setdefault("cnameRecords", [])
    except Exception as e:
        logger.error("Failed to read TOML: %s", e)
        return jsonify({"error": f"Failed to read TOML: {e}"}), 500

    before = len(cnames)
    cnames = [r for r in cnames if r.split(",")[0] != domain]
    removed_count = before - len(cnames)

    if removed_count == 0:
        logger.error("No CNAME record found for domain %s", domain)
        return jsonify({"error": "Record not found"}), 404

    toml_data["dns"]["cnameRecords"] = cnames
    try:
        _save_toml(toml_data)
        logger.debug("Removed %d CNAME entries for domain %s", removed_count, domain)
    except Exception as e:
        logger.error("Failed to write TOML: %s", e)
        return jsonify({"error": f"Failed to write TOML: {e}"}), 500

    return jsonify({"message": f"Deleted {removed_count} record(s) for {domain}"}), 200

