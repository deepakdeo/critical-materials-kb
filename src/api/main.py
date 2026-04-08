"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.health import router as health_router
from src.api.routes.query import router as query_router

app = FastAPI(
    title="Critical Materials Knowledge Base",
    description=(
        "Hybrid RAG and GraphRAG-powered knowledge base for querying "
        "U.S. critical materials supply chain data."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(query_router, prefix="/api")
