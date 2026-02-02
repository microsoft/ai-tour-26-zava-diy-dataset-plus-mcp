"""
FastAPI backend for Search Comparator.
Provides endpoints to compare different search types.
"""
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_connection_string, API_PORT
from .models import (
    SearchRequest, 
    SearchType, 
    SearchTypeResult, 
    CompareResponse,
    HealthResponse
)
from .search_engines import (
    keyword_search,
    vector_search,
    hybrid_rrf_search,
    hybrid_ranker_search
)

load_dotenv(override=True)

# Global connection pool
db_pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    global db_pool
    
    # Startup: create connection pool
    try:
        connection_string = get_connection_string()
        db_pool = await asyncpg.create_pool(
            connection_string,
            min_size=1,
            max_size=5,
            command_timeout=30,
            server_settings={
                "jit": "off",
                "work_mem": "4MB",
                "statement_timeout": "30s"
            }
        )
        print(f"✓ Database connection pool created")
    except Exception as e:
        print(f"✗ Failed to create database pool: {e}")
        db_pool = None
    
    yield
    
    # Shutdown: close connection pool
    if db_pool:
        await db_pool.close()
        print("✓ Database connection pool closed")


app = FastAPI(
    title="Zava Search Comparator",
    description="Compare different search types: keyword, vector, hybrid RRF, and hybrid with ranker",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Map search types to their functions
SEARCH_FUNCTIONS = {
    SearchType.KEYWORD: keyword_search,
    SearchType.VECTOR: vector_search,
    SearchType.HYBRID_RRF: hybrid_rrf_search,
    SearchType.HYBRID_RANKER: hybrid_ranker_search,
}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db_connected = False
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_connected = True
        except Exception:
            pass
    
    return HealthResponse(status="healthy", database_connected=db_connected)


@app.post("/api/search", response_model=CompareResponse)
async def compare_searches(request: SearchRequest):
    """
    Execute multiple search types in parallel and return comparative results.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    if not request.search_types:
        raise HTTPException(status_code=400, detail="At least one search type must be selected")
    
    start_time = time.perf_counter()
    
    # Create tasks for each search type
    async def run_search(search_type: SearchType):
        try:
            search_func = SEARCH_FUNCTIONS[search_type]
            results, exec_time = await search_func(request.query, db_pool, request.limit)
            return search_type, SearchTypeResult(
                search_type=search_type,
                results=results,
                execution_time_ms=exec_time,
                result_count=len(results)
            )
        except Exception as e:
            print(f"Error in {search_type} search: {e}")
            return search_type, SearchTypeResult(
                search_type=search_type,
                results=[],
                execution_time_ms=0,
                result_count=0
            )
    
    # Execute all searches in parallel
    tasks = [run_search(st) for st in request.search_types]
    completed = await asyncio.gather(*tasks)
    
    # Build response
    search_results = {st.value: result for st, result in completed}
    
    total_time = (time.perf_counter() - start_time) * 1000
    
    return CompareResponse(
        query=request.query,
        timestamp=datetime.utcnow(),
        search_results=search_results,
        total_execution_time_ms=total_time
    )


@app.get("/api/search-types")
async def list_search_types():
    """List available search types with descriptions."""
    return {
        "search_types": [
            {
                "id": "keyword",
                "name": "Keyword (Full-Text)",
                "description": "PostgreSQL ts_rank with OR-based tsquery matching"
            },
            {
                "id": "vector",
                "name": "Vector (Semantic)",
                "description": "pgvector cosine similarity with Azure OpenAI embeddings"
            },
            {
                "id": "hybrid_rrf",
                "name": "Hybrid RRF",
                "description": "Reciprocal Rank Fusion combining vector and keyword search"
            },
            {
                "id": "hybrid_ranker",
                "name": "Hybrid + Ranker",
                "description": "RRF with Cohere Rerank v4 via Azure AI Foundry"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
