"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import auth, coffee, users, payments, invoices, account, mietzahlungen


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    yield
    # Cleanup if needed


app = FastAPI(
    title="LSB Kaffeeabrechnung API",
    description="Authenticated API for coffee logging and billing",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lsbkaffee.streamlit.app",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_origin_regex=r"https://.*\.streamlit\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(coffee.router, prefix="/coffee", tags=["coffee"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
app.include_router(account.router, prefix="/account", tags=["account"])
app.include_router(mietzahlungen.router, prefix="/mietzahlungen", tags=["mietzahlungen"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
