"""Pydantic request/response models for the API."""

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request body for the /query endpoint."""

    question: str
    filters: dict[str, Any] = Field(default_factory=dict)
    include_sources: bool = True


class SourceResponse(BaseModel):
    """A source reference in the query response."""

    name: str = ""
    page: str = ""
    section: str = ""
    relevance_score: float = 0.0


class VerificationResponse(BaseModel):
    """Verification result in the query response."""

    verdict: str = "PASS"
    issues: list[str] = Field(default_factory=list)
    severity: str = "none"


class QueryResponseModel(BaseModel):
    """Response body for the /query endpoint."""

    answer: str = ""
    sources: list[SourceResponse] = Field(default_factory=list)
    verification: VerificationResponse = Field(
        default_factory=VerificationResponse
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Response body for the /health endpoint."""

    status: str = "ok"
    document_count: int = 0
    chunk_count: int = 0
