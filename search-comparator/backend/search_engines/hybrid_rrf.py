"""
Hybrid RRF (Reciprocal Rank Fusion) Search combining vector and keyword search.
"""
import time
from asyncpg import Pool

from ..config import EMBEDDING_MODEL_DEPLOYMENT, RRF_K
from ..models import ProductResult


def embedding_to_pgvector(embedding: list) -> str:
    """Convert embedding list to pgvector string format."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


async def hybrid_rrf_search(query: str, pool: Pool, limit: int = 5) -> tuple[list[ProductResult], float]:
    """
    Perform hybrid search using Reciprocal Rank Fusion.
    
    Combines vector search and keyword search results using RRF formula:
    RRF Score = 1/(k + vector_rank) + 1/(k + keyword_rank)
    
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
        # Set HNSW iterative scan for better results
        await conn.execute("SET hnsw.iterative_scan = strict_order")
        
        # Generate embedding
        embedding_row = await conn.fetchrow(
            "SELECT azure_openai.create_embeddings($1, $2)",
            EMBEDDING_MODEL_DEPLOYMENT, query
        )
        embedding = embedding_row[0]
        # Convert to pgvector string format
        embedding_str = embedding_to_pgvector(embedding)
        
        # Hybrid RRF SQL query
        rrf_sql = """
        WITH vector_search AS (
            SELECT 
                p.product_id,
                p.sku,
                p.product_name,
                p.product_description,
                RANK() OVER (ORDER BY pde.description_embedding <=> $1::vector) AS rank
            FROM retail.products p
            JOIN retail.product_description_embeddings pde ON p.product_id = pde.product_id
            WHERE pde.description_embedding IS NOT NULL
            ORDER BY pde.description_embedding <=> $1::vector
            LIMIT 20
        ),
        keyword_search AS (
            SELECT 
                p.product_id,
                p.sku,
                p.product_name,
                p.product_description,
                RANK() OVER (ORDER BY ts_rank_cd(
                    to_tsvector('english', p.product_name || ' ' || p.product_description),
                    to_tsquery('english', $2),
                    2
                ) DESC) AS rank
            FROM retail.products p
            WHERE to_tsvector('english', p.product_name || ' ' || p.product_description) 
                  @@ to_tsquery('english', $2)
            ORDER BY ts_rank_cd(
                to_tsvector('english', p.product_name || ' ' || p.product_description),
                to_tsquery('english', $2),
                2
            ) DESC
            LIMIT 20
        )
        SELECT
            COALESCE(vector_search.product_id, keyword_search.product_id) AS product_id,
            COALESCE(vector_search.sku, keyword_search.sku) AS sku,
            COALESCE(vector_search.product_name, keyword_search.product_name) AS product_name,
            COALESCE(vector_search.product_description, keyword_search.product_description) AS product_description,
            COALESCE(1.0 / ($3 + vector_search.rank), 0.0) +
            COALESCE(1.0 / ($3 + keyword_search.rank), 0.0) AS rrf_score,
            vector_search.rank AS vector_rank,
            keyword_search.rank AS keyword_rank
        FROM vector_search
        FULL OUTER JOIN keyword_search ON vector_search.product_id = keyword_search.product_id
        ORDER BY rrf_score DESC
        LIMIT $4;
        """
        
        rows = await conn.fetch(rrf_sql, embedding_str, tsquery, RRF_K, limit)
    
    execution_time = (time.perf_counter() - start_time) * 1000
    
    results = [
        ProductResult(
            product_id=row['product_id'],
            sku=row['sku'],
            product_name=row['product_name'],
            product_description=row['product_description'],
            score=float(row['rrf_score']),
            rank=idx + 1,
            vector_rank=row['vector_rank'],
            keyword_rank=row['keyword_rank']
        )
        for idx, row in enumerate(rows)
    ]
    
    return results, execution_time
