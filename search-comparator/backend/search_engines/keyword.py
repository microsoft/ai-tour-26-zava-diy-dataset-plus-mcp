"""
Keyword (Full-Text) Search using PostgreSQL ts_rank.
"""
import time
from asyncpg import Pool

from ..models import ProductResult


async def keyword_search(query: str, pool: Pool, limit: int = 5) -> tuple[list[ProductResult], float]:
    """
    Perform keyword search using PostgreSQL full-text search.
    
    Args:
        query: Search query text
        pool: asyncpg connection pool
        limit: Maximum number of results
        
    Returns:
        Tuple of (results list, execution time in ms)
    """
    start_time = time.perf_counter()
    
    # Convert query to OR-based tsquery for broader matching
    tsquery = " | ".join(query.split())
    
    sql = """
    SELECT 
        p.product_id,
        p.sku,
        p.product_name,
        p.product_description,
        ts_rank(
            to_tsvector('english', p.product_name || ' ' || p.product_description),
            to_tsquery('english', $1)
        ) as relevance_score
    FROM retail.products p
    WHERE to_tsvector('english', p.product_name || ' ' || p.product_description) 
          @@ to_tsquery('english', $1)
    ORDER BY relevance_score DESC, p.product_name
    LIMIT $2;
    """
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, tsquery, limit)
    
    execution_time = (time.perf_counter() - start_time) * 1000
    
    results = [
        ProductResult(
            product_id=row['product_id'],
            sku=row['sku'],
            product_name=row['product_name'],
            product_description=row['product_description'],
            score=float(row['relevance_score']),
            rank=idx + 1
        )
        for idx, row in enumerate(rows)
    ]
    
    return results, execution_time
