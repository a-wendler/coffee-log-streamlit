# LSB Kaffeeabrechnung

Coffee logging and billing app for the LSB.

## Architecture

- **FastAPI backend** – runs on your server, connects to MySQL (localhost only), handles all computations
- **Streamlit frontend** – runs on Streamlit Cloud, fetches data from the API only (no direct DB access)

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment instructions.

## Local development

```bash
# Install
poetry install

# Run API (Terminal 1)
uvicorn api.main:app --reload --port 8000

# Run Streamlit (Terminal 2)
# Set .streamlit/secrets.toml with api.base_url = "http://127.0.0.1:8000"
streamlit run coffee_log/app.py
```

## Dependencies

- Python 3.12+
- MySQL, Streamlit, FastAPI, SQLAlchemy, etc. (see pyproject.toml)
