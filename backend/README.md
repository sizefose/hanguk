# Hanguk Market Backend

## Requirements
- Python 3.11+
- MySQL 8+

## Setup
1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a `.env` based on `.env.example`.

3. Run migrations and create a superuser:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. Start the server:
   ```bash
   python manage.py runserver
   ```

Admin is available at `http://localhost:8000/admin/`.

## Healthcheck
- API health endpoint: `GET /api/health/`
