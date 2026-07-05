#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$HOME/opensource_st_4/amhs}"

sudo apt-get update
sudo apt-get install -y nginx

sudo tee /etc/nginx/sites-available/amhs-streamlit >/dev/null <<EOF
server {
    listen 80 default_server;
    server_name _;

    location /oht3d/ {
        alias ${ROOT_DIR}/oht_3d/;
        try_files \$uri \$uri/ =404;
    }

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/amhs-streamlit /etc/nginx/sites-enabled/amhs-streamlit
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

echo "Nginx is proxying http://EC2_PUBLIC_IP/ to Streamlit and /oht3d/."
