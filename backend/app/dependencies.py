"""FastAPI shared dependencies for authentication, rate limiting, and database/Redis connections."""

import time
from fastapi import Header, HTTPException, status, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import AsyncGenerator

from app.config import settings
from app.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_redis(request: Request):
    """Retrieves the async Redis client from FastAPI app state."""
    return request.app.state.redis


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key")
) -> str:
    """Verifies that the request contains a valid X-API-Key header."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
        )
    if x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return x_api_key


async def check_rate_limit(
    api_key: str = Depends(verify_api_key),
    redis = Depends(get_redis),
) -> None:
    """Enforces a rate limit of 1000 requests per minute per API key."""
    current_minute = int(time.time()) // 60
    key = f"rate_limit:{api_key}:{current_minute}"

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)

    if count > 1000:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 1000 requests per minute.",
        )


async def verify_presenter_passcode(
    x_presenter_passcode: str | None = Header(None, alias="X-Presenter-Passcode")
) -> str:
    """Verifies that the request contains a valid presenter passcode header."""
    if not x_presenter_passcode:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Presenter Passcode",
        )
    if x_presenter_passcode != settings.PRESENTER_PASSCODE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Presenter Passcode",
        )
    return x_presenter_passcode
