"""SmartMail AI+ — FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from app.config import settings
from app.routers import (
    track_router,
    users_router,
    analytics_router,
    predict_router,
    recommend_router,
    decide_router,
    generate_router,
    email_router,
    email_logs_router,
)
from app.workers.event_worker import start_event_worker
from app.workers.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    # Startup: Initialize Redis
    app.state.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    # Start event worker in the background
    app.state.worker_task = asyncio.create_task(start_event_worker(app.state.redis))

    # Start scheduler (DISABLED to prevent automated email sends)
    # app.state.scheduler = await start_scheduler()

    yield

    # Shutdown: Clean up background tasks
    # 1. Stop scheduler (DISABLED)
    # await shutdown_scheduler(app.state.scheduler)

    # 2. Cancel event worker task
    app.state.worker_task.cancel()
    try:
        await app.state.worker_task
    except asyncio.CancelledError:
        pass

    # 3. Close Redis
    await app.state.redis.close()

    # 4. Dispose SQL engine
    from app.database import engine
    await engine.dispose()


app = FastAPI(
    title="SmartMail AI+",
    description="Agentic AI-powered e-commerce email marketing platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(track_router)
app.include_router(users_router)
app.include_router(analytics_router)
app.include_router(predict_router)
app.include_router(recommend_router)
app.include_router(decide_router)
app.include_router(generate_router)
app.include_router(email_router)
app.include_router(email_logs_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint returning status: ok for frontend indicator."""
    return {"status": "ok"}

