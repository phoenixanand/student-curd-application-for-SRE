# Student CRUD REST API — EC2 Deployment Guide

## Architecture
```
EC2 Instance (Ubuntu 22.04)
  └── Nginx (reverse proxy, port 80/443)
        └── Gunicorn (WSGI server, port 5000)
              └── Flask app
```

---

## 1. Launch EC2 Instance

| Setting        | Value                          |
|----------------|--------------------------------|
| AMI            | Ubuntu Server 22.04 LTS        |
| Instance type  | t3.micro (free tier eligible)  |
| Storage        | 8 GB gp3                       |
| Security Group | Allow SSH (22), HTTP (80), HTTPS (443) |

Add an inbound rule to the Security Group:
- **Type**: Custom TCP, **Port**: 5000, **Source**: My IP (for direct testing)

---

## 2. Connect & Bootstrap

```bash
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

# Update & install Python + Nginx
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx git
```

---

## 3. Deploy the App

```bash
# Clone / upload your code
git clone https://github.com/<you>/student-api.git
cd student-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Configure Gunicorn (systemd service)

```bash
sudo nano /etc/systemd/system/student-api.service
```

Paste:
```ini
[Unit]
Description=Student API (Gunicorn)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/student-api
Environment="PATH=/home/ubuntu/student-api/venv/bin"
ExecStart=/home/ubuntu/student-api/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:5000 \
    --access-logfile /var/log/student-api/access.log \
    --error-logfile  /var/log/student-api/error.log \
    run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo mkdir -p /var/log/student-api
sudo chown ubuntu:ubuntu /var/log/student-api

sudo systemctl daemon-reload
sudo systemctl enable student-api
sudo systemctl start student-api
sudo systemctl status student-api
```

---

## 5. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/student-api
```

Paste:
```nginx
server {
    listen 80;
    server_name <EC2_PUBLIC_IP>;   # or your domain

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/student-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 6. Run Tests

```bash
cd /home/ubuntu/student-api
source venv/bin/activate
pytest tests/ -v
```

---

## 7. Quick Smoke Test

```bash
BASE=http://<EC2_PUBLIC_IP>/api/v1

# Healthcheck
curl $BASE/healthcheck

# Create student
curl -X POST $BASE/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com","age":20,"grade":"A"}'

# Get all students
curl $BASE/students

# Get by ID
curl $BASE/students/1

# Update
curl -X PUT $BASE/students/1 \
  -H "Content-Type: application/json" \
  -d '{"grade":"A+"}'

# Delete
curl -X DELETE $BASE/students/1
```

---

## 8. Optional: HTTPS with Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## Production Tips

- Move the SQLite DB path to `/var/lib/student-api/students.db` (persistent across deploys)
- Add an Application Load Balancer (ALB) in front of multiple EC2s for HA
- Use RDS (PostgreSQL/MySQL) instead of SQLite for multi-instance setups
- Store logs in CloudWatch with the CloudWatch agent
- Use AWS Secrets Manager for any secrets/env vars
