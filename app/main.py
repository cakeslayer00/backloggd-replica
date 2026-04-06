from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

import app.models  # noqa
from app.core.config import settings
from app.core.elasticsearch import close_es_client
from app.middleware.logging import LoggingMiddleware
from app.middleware.profiling import ProfilingMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.routers import auth, games, platforms, reviews, tags, backlogs, screenshots


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_es_client()


app = FastAPI()

app.add_middleware(ProfilingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)


app.include_router(auth.router)
app.include_router(games.router)
app.include_router(platforms.router)
app.include_router(backlogs.router)
app.include_router(reviews.router)
app.include_router(tags.router)
app.include_router(screenshots.router)