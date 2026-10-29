
import logging
from contextlib import asynccontextmanager

import mysql.connector
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from database import DATABASE_NAME, get_connection, init_db
from routes.ai import router as ai_router
from routes.assignments import router as assignments_router
from routes.complaints import router as complaints_router
from routes.dashboard import router as dashboard_router
from routes.evidence import router as evidence_router
from services.local_auth import init_demo_accounts, router as auth_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_demo_accounts()
    yield

app = FastAPI(
    title="CityWatch AI API",
    description="Citizen complaint management, review, routing, and AI-assisted triage",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints_router)
app.include_router(evidence_router)
app.include_router(assignments_router)
app.include_router(ai_router)
app.include_router(dashboard_router)
app.include_router(auth_router)


@app.get("/")
def home():
    return {
        "message": "CityWatch AI API is running",
        "status": "success",
        "features": [
            "complaints",
            "evidence",
            "assignments",
            "ai_analysis",
            "dashboards",
        ],
    }


@app.get("/api/health")
def health():
    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            finally:
                cursor.close()
    except (mysql.connector.Error, RuntimeError) as exc:
        logger.exception("MySQL health check failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MySQL database is unavailable.",
        ) from exc

    return {
        "status": "healthy",
        "service": "citywatch-ai",
        "database": "ready",
        "database_name": DATABASE_NAME,
    }
