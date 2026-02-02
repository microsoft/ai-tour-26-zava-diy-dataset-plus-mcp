"""
Vector (Semantic) Search using pgvector cosine similarity.
"""
import time
from asyncpg import Pool

from ..config import EMBEDDING_MODEL_DEPLOYMENT
from ..models import ProductResult


async def vector_search(query: str, pool: Pool, limit: int = 5) -> tuple[list[ProductResult], float]:
    """
    Perform vector search using pgvector cosine similarity.
    
    Args:
        query: Search query text
        pool: asyncpg connection pool
        limit: Maximum number of results
        
    Returns:
        Tuple of (results list, execution time in ms)
    """
    start_time = time.perf_counter()
    
    async with pool.acquire() as conn:
        # Set HNSW iterative scan for better results
        await conn.execute("SET hnsw.iterative_scan = strict_order")
        
        # Generate embedding using azure_openai extension
        embedding_row = await conn.fetchrow(
            "SELECT azure_openai.create_embeddings($1, $2)",
            EMBEDDING_MODEL_DEPLOYMENT, query
        )
        embedding = embedding_row[0]
        
        # Vector search query
        sql = """
        SELECT 
            p.product_id,
            p.sku,
            p.product_name,
            p.product_description,
            (1 - (pde.description_embedding <=> $1::vector)) as cosine_similarity
        FROM retail.products p
        JOIN retail.product_description_embeddings pde ON p.product_id = pde.product_id
        WHERE pde.description_embedding IS NOT NULL
        ORDER BY pde.description_embedding <=> $1::vector
        LIMIT $2;
        """
        
        rows = await conn.fetch(sql, embedding, limit)
    
    execution_time = (time.perf_counter() - start_time) * 1000
    
    results = [
        ProductResult(
            product_id=row['product_id'],
            sku=row['sku'],
            product_name=row['product_name'],
            product_description=row['product_description'],
            score=float(row['cosine_similarity']),
            rank=idx + 1
        )
        for idx, row in enumerate(rows)
    ]
    
    return results, execution_time
