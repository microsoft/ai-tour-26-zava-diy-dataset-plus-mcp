"""
Hybrid RRF Search with Cohere Reranker using Azure AI Foundry endpoint.
"""
import time
import httpx
from asyncpg import Pool

from ..config import (
    EMBEDDING_MODEL_DEPLOYMENT, 
    RRF_K, 
    COHERE_RERANK_ENDPOINT, 
    COHERE_RERANK_KEY,
    COHERE_MODEL
)
from ..models import ProductResult


async def cohere_rerank(query: str, documents: list[dict], top_n: int = 10) -> list[dict]:
    """
    Call Cohere Rerank API via Azure AI Foundry.
    
    Args:
        query: The search query
        documents: List of dicts with 'id' and 'text' keys
        top_n: Number of top results to return
    
    Returns:
        List of dicts with 'id', 'index', 'relevance_score', and 'rank'
    """
    if not COHERE_RERANK_ENDPOINT or not COHERE_RERANK_KEY:
        raise ValueError("COHERE_RERANK_ENDPOINT_URI and COHERE_RERANK_ENDPOINT_KEY must be set")
    
    headers = {
        "api-key": COHERE_RERANK_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": COHERE_MODEL,
        "query": query,
        "documents": [doc["text"] for doc in documents],
        "top_n": top_n
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(COHERE_RERANK_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
    
    result = response.json()
    
    # Map back to original document IDs
    reranked = []
    for item in result.get("results", []):
        original_idx = item["index"]
        reranked.append({
            "id": documents[original_idx]["id"],
            "index": original_idx,
            "relevance_score": item["relevance_score"],
            "rank": len(reranked) + 1
        })
    
    return reranked


async def hybrid_ranker_search(query: str, pool: Pool, limit: int = 5) -> tuple[list[ProductResult], float]:
    """
    Perform hybrid search with RRF + Cohere Reranker.
    
    First combines vector and keyword search using RRF, then reranks
    the top candidates using Cohere Rerank v4.0 via Azure AI Foundry.
    
    Args:
        query: Search query text
        pool: asyncpg connection pool
        limit: Maximum number of results
        
    Returns:
        Tuple of (results list, execution time in ms)
    """
    start_time = time.perf_counter()
    
    # Convert query to OR-based tsquery
    tsquery = " | ".join(query.split())
    
    async with pool.acquire() as conn:
        # Set HNSW iterative scan
        await conn.execute("SET hnsw.iterative_scan = strict_order")
        
        # Generate embedding
        embedding_row = await conn.fetchrow(
            "SELECT azure_openai.create_embeddings($1, $2)",
            EMBEDDING_MODEL_DEPLOYMENT, query
        )
        embedding = embedding_row[0]
        
        # RRF SQL query to get candidates for reranking
        rrf_sql = """
        WITH base_candidates AS (
            (
                SELECT 
                    p.product_id,
                    p.sku,
                    p.product_name,
                    p.product_description
                FROM retail.products p
                JOIN retail.product_description_embeddings pde ON p.product_id = pde.product_id
                WHERE pde.description_embedding IS NOT NULL
                ORDER BY pde.description_embedding <=> $1::vector
                LIMIT 15
            )
            UNION
            (
                SELECT 
                    p.product_id,
                    p.sku,
                    p.product_name,
                    p.product_description
                FROM retail.products p
                WHERE to_tsvector('english', p.product_name || ' ' || p.product_description) 
                      @@ to_tsquery('english', $2)
                ORDER BY ts_rank_cd(
                    to_tsvector('english', p.product_name || ' ' || p.product_description),
                    to_tsquery('english', $2),
                    2
                ) DESC
                LIMIT 15
            )
        ),
        vector_search AS (
            SELECT 
                bc.product_id,
                bc.sku,
                bc.product_name,
                bc.product_description,
                RANK() OVER (ORDER BY pde.description_embedding <=> $1::vector) AS rank
            FROM base_candidates bc
            JOIN retail.product_description_embeddings pde ON bc.product_id = pde.product_id
            WHERE pde.description_embedding IS NOT NULL
            ORDER BY pde.description_embedding <=> $1::vector
            LIMIT 20
        ),
        keyword_search AS (
            SELECT 
                bc.product_id,
                bc.sku,
                bc.product_name,
                bc.product_description,
                RANK() OVER (ORDER BY ts_rank_cd(
                    to_tsvector('english', bc.product_name || ' ' || bc.product_description),
                    to_tsquery('english', $2),
                    2
                ) DESC) AS rank
            FROM base_candidates bc
            WHERE to_tsvector('english', bc.product_name || ' ' || bc.product_description) 
                  @@ to_tsquery('english', $2)
            ORDER BY ts_rank_cd(
                to_tsvector('english', bc.product_name || ' ' || bc.product_description),
                to_tsquery('english', $2),
                2
            ) DESC
            LIMIT 20
        ),
        rrf_combined AS (
            SELECT 
                COALESCE(vs.product_id, ks.product_id) AS product_id,
                COALESCE(vs.sku, ks.sku) AS sku,
                COALESCE(vs.product_name, ks.product_name) AS product_name,
                COALESCE(vs.product_description, ks.product_description) AS product_description,
                COALESCE(1.0 / ($3 + vs.rank), 0.0) +
                COALESCE(1.0 / ($3 + ks.rank), 0.0) AS rrf_score,
                vs.rank AS vector_rank,
                ks.rank AS keyword_rank,
                ROW_NUMBER() OVER (ORDER BY 
                    COALESCE(1.0 / ($3 + vs.rank), 0.0) +
                    COALESCE(1.0 / ($3 + ks.rank), 0.0) DESC
                ) AS rrf_rank
            FROM vector_search vs
            FULL OUTER JOIN keyword_search ks ON vs.product_id = ks.product_id
            ORDER BY rrf_score DESC
            LIMIT 50
        )
        SELECT
            product_id,
            sku,
            product_name,
            product_description,
            rrf_score,
            vector_rank,
            keyword_rank,
            rrf_rank
        FROM rrf_combined
        ORDER BY rrf_score DESC;
        """
        
        rows = await conn.fetch(rrf_sql, embedding, tsquery, RRF_K)
    
    # Prepare documents for Cohere reranking
    documents = []
    results_dict = {}
    for row in rows:
        doc_id = str(row['product_id'])
        documents.append({
            "id": doc_id,
            "text": f"{row['product_name']}: {row['product_description']}"
        })
        results_dict[doc_id] = {
            "product_id": row['product_id'],
            "sku": row['sku'],
            "product_name": row['product_name'],
            "product_description": row['product_description'],
            "rrf_score": float(row['rrf_score']),
            "vector_rank": row['vector_rank'],
            "keyword_rank": row['keyword_rank'],
            "rrf_rank": row['rrf_rank']
        }
    
    # Call Cohere Rerank API
    reranked = await cohere_rerank(query, documents, top_n=limit)
    
    execution_time = (time.perf_counter() - start_time) * 1000
    
    results = []
    for item in reranked:
        doc_id = item["id"]
        result_data = results_dict[doc_id]
        results.append(ProductResult(
            product_id=result_data['product_id'],
            sku=result_data['sku'],
            product_name=result_data['product_name'],
            product_description=result_data['product_description'],
            score=float(result_data['rrf_score']),
            rank=item['rank'],
            vector_rank=result_data['vector_rank'],
            keyword_rank=result_data['keyword_rank'],
            ranker_score=item['relevance_score']
        ))
    
    return results, execution_time
