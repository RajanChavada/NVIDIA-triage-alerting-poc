"""
FastAPI application entry point.

Starts the triage worker background task and registers all routes.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import alerts, health, observability, experiments
from app.services.triage import triage_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start/stop background workers."""
    # Startup: launch triage worker
    worker_task = asyncio.create_task(triage_worker())
    print("🚀 Triage worker started")
    
    yield
    
    # Shutdown: cancel worker
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    print("🛑 Triage worker stopped")


app = FastAPI(
    title="NVIDIA Triage Alerting MVP",
    description="AI-powered triage alerting system using multi-agent workflows with NVIDIA GPU monitoring",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware for Streamlit dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to Streamlit host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router, tags=["Health"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(observability.router, tags=["Observability"])
app.include_router(experiments.router, tags=["Experiments"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "NVIDIA Triage Alerting MVP",
        "version": "0.1.0",
        "docs": "/docs",
        "llm_provider": settings.llm_provider,
    }
