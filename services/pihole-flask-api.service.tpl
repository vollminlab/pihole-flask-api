[Unit]
Description=Pi-hole Flask API Service
After=network.target
Wants=pihole-FTL.service

[Service]
EnvironmentFile=/etc/pihole-flask-api/.env

ExecStart={{VENV}}/bin/gunicorn --workers 2 --bind 0.0.0.0:5001 --chdir {{APP}}/src recordimporter:app
WorkingDirectory={{APP}}
Environment="PATH={{VENV}}/bin"
User=www-data
Group=www-data
Restart=always

[Install]
WantedBy=multi-user.target
