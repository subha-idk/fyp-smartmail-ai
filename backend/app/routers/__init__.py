# FastAPI routers (one per domain)

from app.routers.track import router as track_router
from app.routers.users import router as users_router
from app.routers.analytics import router as analytics_router
from app.routers.predict import router as predict_router
from app.routers.recommend import router as recommend_router
from app.routers.decide import router as decide_router
from app.routers.generate import router as generate_router
from app.routers.email import router as email_router, router_logs as email_logs_router

__all__ = [
    "track_router",
    "users_router",
    "analytics_router",
    "predict_router",
    "recommend_router",
    "decide_router",
    "generate_router",
    "email_router",
    "email_logs_router",
]



