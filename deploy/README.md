# VPS Deploy

## 1. Prepare the server

Install Docker, Docker Compose plugin, Nginx and Git.

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg nginx git
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker compose version
```

## 2. Upload the project

```bash
git clone <your-repo-url> /srv/hanguk2
cd /srv/hanguk2
cp .env.deploy.example .env.deploy
mkdir -p deploy/data/media deploy/data/static
```

Fill in `.env.deploy` with your real domain, secrets and database passwords.

If HTTPS is not configured yet, temporarily set:

```env
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
```

## 3. Start containers

```bash
docker compose --env-file .env.deploy -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.deploy -f docker-compose.prod.yml ps
```

## 4. Configure Nginx

Copy `deploy/nginx/default.conf.example` to `/etc/nginx/sites-available/hanguk2`, replace the domain and project path (`/srv/hanguk2`), then enable the site:

```bash
sudo cp deploy/nginx/default.conf.example /etc/nginx/sites-available/hanguk2
sudo ln -s /etc/nginx/sites-available/hanguk2 /etc/nginx/sites-enabled/hanguk2
sudo nginx -t
sudo systemctl reload nginx
```

## 5. Create Django admin user

```bash
docker compose --env-file .env.deploy -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## 6. Enable HTTPS

Issue a certificate, update `.env.deploy` back to secure cookies / redirect, then restart the stack:

```bash
docker compose --env-file .env.deploy -f docker-compose.prod.yml up -d
```
