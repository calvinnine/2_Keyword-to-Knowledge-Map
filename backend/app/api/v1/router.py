from fastapi import APIRouter

from app.api.v1.endpoints import jobs, papers, authors, keywords, graphs, ntis

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(papers.router, tags=["papers"])
api_router.include_router(authors.router, tags=["authors"])
api_router.include_router(keywords.router, tags=["keywords"])
api_router.include_router(graphs.router, tags=["graphs"])
api_router.include_router(ntis.router, tags=["ntis"])
