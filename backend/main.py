"""
FastAPI application entry point for InvestIQ.

Startup:
  1. Create data/ directory if not exists
  2. Initialize SQLite schema
  3. Start APScheduler (jobs registered in Plan 04)
  4. Apply CORS middleware for localhost:3000
"""
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import settings
from backend.database import create_schema
from backend.api.health import router as health_router
from backend.api.portfolio import router as portfolio_router
from backend.api.indices import router as indices_router
from backend.api.fx import router as fx_router

# Global scheduler — jobs added in Plan 04
scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: startup → yield → shutdown."""
    # Startup
    data_dir = os.path.dirname(settings.DB_PATH)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

    create_schema(settings.DB_PATH)
    scheduler.start()

    yield

    # Shutdown
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="InvestIQ", version="0.1.0", lifespan=lifespan)

# CORS: allow only local frontend origins (T-01-05 mitigation)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(portfolio_router)
app.include_router(indices_router)
app.include_router(fx_router)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
