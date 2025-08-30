import os

import dotenv
import psycopg2
from azure.identity import DefaultAzureCredential
from pgvector.psycopg2 import register_vector

dotenv.load_dotenv(override=True)

EMBEDDING_MODEL_DEPLOYMENT = os.environ["EMBEDDING_MODEL_DEPLOYMENT_NAME"]

POSTGRES_HOST = os.environ["POSTGRES_SERVER_FQDN"]
POSTGRES_USERNAME = os.environ["POSTGRES_SERVER_USERNAME"]
POSTGRES_DATABASE = "zava"

if POSTGRES_HOST.endswith(".database.azure.com"):
    azure_credential = DefaultAzureCredential()
    token = azure_credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
    POSTGRES_PASSWORD = token.token
else:
    POSTGRES_PASSWORD = os.environ["POSTGRES_SERVER_PASSWORD"]

extra_params = {}
if POSTGRES_SSL := os.environ.get("POSTGRES_SSL"):
    extra_params["sslmode"] = POSTGRES_SSL

conn = psycopg2.connect(
    database=POSTGRES_DATABASE,
    user=POSTGRES_USERNAME,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    **extra_params,
)

conn.autocommit = True
cur = conn.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
register_vector(conn)
cur.execute("SET hnsw.iterative_scan = strict_order")

# Search query
search_query = "garden watering supplies"

print(f"Hybrid RRF Search for: '{search_query}'\n")

cur.execute("SELECT azure_openai.create_embeddings(%s, %s)", (EMBEDDING_MODEL_DEPLOYMENT, search_query))
embedding_result = cur.fetchone()
embedding = embedding_result[0]

# Convert to OR-based search for broader matching (like TF-IDF/BM25)
tsquery = ' | '.join(search_query.split())  # Use | operator, not OR word

# RRF (Reciprocal Rank Fusion) parameter - controls the weighting
k = 60  # Standard RRF parameter value

# Hybrid RRF SQL query combining vector search and keyword search
rrf_sql = """
WITH vector_search AS (
    SELECT 
        p.product_id,
        p.sku,
        p.product_name,
        p.product_description,
        RANK() OVER (ORDER BY pde.description_embedding <=> %(embedding)s::vector) AS rank
    FROM retail.products p
    JOIN retail.product_description_embeddings pde ON p.product_id = pde.product_id
    WHERE pde.description_embedding IS NOT NULL
    ORDER BY pde.description_embedding <=> %(embedding)s::vector
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
            to_tsquery('english', %(tsquery)s),
            2  -- Normalize by document length (TF-IDF/BM25-like)
        ) DESC) AS rank
    FROM retail.products p
    WHERE to_tsvector('english', p.product_name || ' ' || p.product_description) 
          @@ to_tsquery('english', %(tsquery)s)
    ORDER BY ts_rank_cd(
        to_tsvector('english', p.product_name || ' ' || p.product_description),
        to_tsquery('english', %(tsquery)s),
        2  -- Normalize by document length (TF-IDF/BM25-like)
    ) DESC
    LIMIT 20
)
SELECT
    COALESCE(vector_search.product_id, keyword_search.product_id) AS product_id,
    COALESCE(vector_search.sku, keyword_search.sku) AS sku,
    COALESCE(vector_search.product_name, keyword_search.product_name) AS product_name,
    COALESCE(vector_search.product_description, keyword_search.product_description) AS product_description,
    COALESCE(1.0 / (%(k)s + vector_search.rank), 0.0) +
    COALESCE(1.0 / (%(k)s + keyword_search.rank), 0.0) AS rrf_score,
    vector_search.rank AS vector_rank,
    keyword_search.rank AS keyword_rank
FROM vector_search
FULL OUTER JOIN keyword_search ON vector_search.product_id = keyword_search.product_id
ORDER BY rrf_score DESC
LIMIT 10;
"""

cur.execute(rrf_sql, {
    'embedding': embedding,
    'tsquery': tsquery,  # Use the OR-based tsquery
    'k': k
})

results = cur.fetchall()
for i, result in enumerate(results, 1):
    product_id, sku, name, description, rrf_score, vector_rank, keyword_rank = result
    
    print(f"{i}. {sku} - {name}")
    print(f"   RRF Score: {rrf_score:.4f}")
    
    # Show which search methods contributed
    contributions = []
    if vector_rank is not None:
        contributions.append(f"Vector: #{vector_rank}")
    if keyword_rank is not None:
        contributions.append(f"Keyword: #{keyword_rank}")
    
    print(f"   Rankings: {' | '.join(contributions) if contributions else 'No rankings'}")
    print(f"   Description: {description}...")
    print()
