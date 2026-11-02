import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend root directory is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Configure Windows SelectorEventLoop for psycopg async compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Ensure database schema is created on startup (or via Alembic)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="MemoryProject Enterprise API",
    version="1.0.0",
    description="Enterprise FastAPI backend with Auth, Authorization, S3 Avatar Uploads, and Neon PostgreSQL",
    lifespan=lifespan,
)

# CORS configurations for Next.js frontend
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    settings.frontend_url,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount local static files (for fallback default avatar)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount API Routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "MemoryProject API"}

