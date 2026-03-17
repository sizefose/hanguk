# Hanguk 2.0

Hanguk 2.0 is a catalog storefront built with Next.js on the frontend and Django + MySQL on the backend.

## Stack

- Next.js 16
- React 19
- Django 5
- MySQL 8
- Docker Compose for production deployment

## Local Development

Frontend:

```bash
npm install
npm run dev
```

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Frontend expects the backend API at `http://localhost:8000/api` during local development.

## Production

- Frontend production image uses a standalone Next.js build.
- Backend production container runs migrations, collects static files and starts `gunicorn`.
- Production Compose stack: [`docker-compose.prod.yml`](docker-compose.prod.yml)
- Deployment guide: [`deploy/README.md`](deploy/README.md)
- Nginx example config: [`deploy/nginx/default.conf.example`](deploy/nginx/default.conf.example)
- Production env template: [`.env.deploy.example`](.env.deploy.example)

## Notes

- Do not commit `.env` files with real secrets.
- Uploaded media and local backups are intentionally excluded from Git.
- A fresh production environment still needs real content data and media restoration if you want to reproduce the current catalog state.
