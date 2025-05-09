[Unit]
Description=Pi-hole Flask API Service
After=network.target
Wants=pihole-FTL.service

[Service]
EnvironmentFile=/etc/pihole-flask-api/.env

ExecStart={{VENV}}/bin/python {{APP}}/src/recordimporter.py
WorkingDirectory={{APP}}
Environment="PATH={{VENV}}/bin"
User=www-data
Group=pihole-api
Restart=always

[Install]
WantedBy=multi-user.target
