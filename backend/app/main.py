import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="K2KM API",
    description="Keyword-to-Knowledge Map: scholarly graph analysis backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/v1/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
