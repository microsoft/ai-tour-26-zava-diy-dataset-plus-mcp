"""
Pydantic models for the Search Comparator API.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SearchType(str, Enum):
    """Available search types."""
    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID_RRF = "hybrid_rrf"
    HYBRID_RANKER = "hybrid_ranker"


class SearchRequest(BaseModel):
    """Request model for comparative search."""
    query: str = Field(..., min_length=1, description="Search query text")
    search_types: list[SearchType] = Field(
        default=[SearchType.KEYWORD, SearchType.VECTOR],
        description="Types of search to perform"
    )
    limit: int = Field(default=5, ge=1, le=20, description="Maximum results per search type")


class ProductResult(BaseModel):
    """Individual product result."""
    product_id: int
    sku: str
    product_name: str
    product_description: str
    score: float = Field(description="Relevance/similarity score")
    rank: int = Field(description="Position in results")
    vector_rank: Optional[int] = Field(default=None, description="Rank in vector search (for hybrid)")
    keyword_rank: Optional[int] = Field(default=None, description="Rank in keyword search (for hybrid)")
    ranker_score: Optional[float] = Field(default=None, description="Cohere reranker score")


class SearchTypeResult(BaseModel):
    """Results for a single search type."""
    search_type: SearchType
    results: list[ProductResult]
    execution_time_ms: float = Field(description="Time taken to execute search in milliseconds")
    result_count: int = Field(description="Number of results returned")


class CompareResponse(BaseModel):
    """Complete response with all search results."""
    query: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    search_results: dict[str, SearchTypeResult]
    total_execution_time_ms: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    database_connected: bool = False
