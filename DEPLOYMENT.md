# Deployment Guide: FastAPI Backend + Streamlit Frontend

This app has two components:

1. **FastAPI backend** – runs on your server (same host as MySQL), handles all DB access and computations
2. **Streamlit frontend** – runs on Streamlit Community Cloud (or elsewhere), calls the API only

## Architecture

```
Streamlit Cloud  -->  HTTPS  -->  FastAPI (your server)  -->  MySQL (localhost)
                                      |
                                      +-> SMTP (email)
```

- MySQL is only reachable from the FastAPI process (localhost).
- Streamlit never touches the database; it only talks to the API.

## 1. FastAPI backend (on your server)

### Requirements

- Python 3.12+
- MySQL accessible on localhost
- SMTP server for activation and password-reset emails

### Environment variables

Create a `.env` file (or set these in your environment):

```env
# Database (use same DB as before)
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/coffee

# JWT (use a strong random secret)
JWT_SECRET=your-random-secret-at-least-32-chars

# Coffee prices
KAFFEE_PREIS_MITGLIED=0.25
KAFFEE_PREIS_GAST=1.0

# SMTP
SMTP_PORT=587
SMTP_SERVER=smtp.example.com
SMTP_LOGIN=your-smtp-user
SMTP_PASSWORD=your-smtp-password
SMTP_SENDER=noreply@example.com
SMTP_REPLY=reply@example.com

# App URL (for activation/reset links)
STREAMLIT_APP_URL=https://lsbkaffee.streamlit.app
ADMIN_RECHNUNG=Name für Abrechnungsfragen
ADMIN_TECHNIK=Name für technische Fragen
ZAHLUNGSOPTIONEN=Ihr Überweisungstext...
```

### Run

```bash
poetry install
uvicorn api.main:app --host 0.0.0.0 --port 8000
# Or with auto-reload for development:
python run_api.py
```

### Production

- Run behind nginx or Caddy for HTTPS.
- Use systemd or Docker to keep the process running.
- CORS is set for `*.streamlit.app` and localhost.

## 2. Streamlit frontend (Streamlit Cloud)

### Secrets

In Streamlit Cloud → App → Settings → Secrets, add:

```toml
[api]
base_url = "https://your-api-server.example.com"
timeout = 30

[admins]
rechnung = "Name für Abrechnungsfragen"
technik = "Name für technische Fragen"
```

Or copy from `.streamlit/secrets.toml.example` and fill in.

### Deploy

1. Push repo to GitHub.
2. Connect to Streamlit Cloud.
3. Set secrets as above.
4. Deploy. The app will call `base_url` for all data.

**Important:** Remove any old `connections.coffee_counter` secrets; the DB is no longer used by Streamlit.

## 3. Run locally for development

### Terminal 1 – API

```bash
poetry install
# Set DATABASE_URL etc. in .env
uvicorn api.main:app --reload --port 8000
```

### Terminal 2 – Streamlit

```bash
# In .streamlit/secrets.toml:
# [api]
# base_url = "http://127.0.0.1:8000"
streamlit run coffee_log/app.py
# Or from project root: streamlit run coffee_log/app.py
```

## Migrations

Run Alembic migrations on the server (where the DB is):

```bash
cd coffee_log
alembic upgrade head
```

Uses `sqlalchemy.url` from `alembic.ini` or `DATABASE_URL` from env.
