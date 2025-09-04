import os

import dotenv
import psycopg2
from azure.identity import DefaultAzureCredential
from pgvector.psycopg2 import register_vector

dotenv.load_dotenv(override=True)

EMBEDDING_MODEL_DEPLOYMENT = os.environ["EMBEDDING_MODEL_DEPLOYMENT_NAME"]
# Note: Using Cohere-rerank-v3.5 as default reranker (configured via azure_ml settings)

POSTGRES_HOST = os.environ["POSTGRES_SERVER_FQDN"]
POSTGRES_USERNAME = os.environ["POSTGRES_SERVER_USERNAME"]
POSTGRES_DATABASE = "zava"

if POSTGRES_HOST.endswith(".database.azure.com"):
    print("Authenticating to Azure Database for PostgreSQL using Azure Identity...")
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

# Create pgvector extension
cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
register_vector(conn)

# Enable iterative index scans to ensure we get the full LIMIT count
cur.execute("SET hnsw.iterative_scan = strict_order")

# Search query
search_query = "garden watering supplies"
print(f"RRF Search with Cohere Reranker for: '{search_query}'")

# Create embedding using PostgreSQL azure_openai extension
cur.execute("SELECT azure_openai.create_embeddings(%s, %s)", (EMBEDDING_MODEL_DEPLOYMENT, search_query))
embedding_result = cur.fetchone()
embedding = embedding_result[0]

# Convert to OR-based search for broader matching (like TF-IDF/BM25)
tsquery = ' | '.join(search_query.split())
print(f"✓ Using OR-based query for broader matching: '{tsquery}'")

# RRF (Reciprocal Rank Fusion) parameter - controls the weighting
k = 60  # Standard RRF parameter value

# Triple RRF SQL query combining vector search, keyword search, and azure_ai.rank
triple_rrf_sql = """
WITH base_candidates AS (
    -- Get a broader set of candidates using proper ranking from both searches
    (
        SELECT 
            p.product_id,
            p.sku,
            p.product_name,
            p.product_description
        FROM retail.products p
        JOIN retail.product_description_embeddings pde ON p.product_id = pde.product_id
        WHERE pde.description_embedding IS NOT NULL
        ORDER BY pde.description_embedding <=> %(embedding)s::vector
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
              @@ to_tsquery('english', %(tsquery)s)
        ORDER BY ts_rank_cd(
            to_tsvector('english', p.product_name || ' ' || p.product_description),
            to_tsquery('english', %(tsquery)s),
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
        RANK() OVER (ORDER BY pde.description_embedding <=> %(embedding)s::vector) AS rank
    FROM base_candidates bc
    JOIN retail.product_description_embeddings pde ON bc.product_id = pde.product_id
    WHERE pde.description_embedding IS NOT NULL
    ORDER BY pde.description_embedding <=> %(embedding)s::vector
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
            to_tsquery('english', %(tsquery)s),
            2  -- Normalize by document length (TF-IDF/BM25-like)
        ) DESC) AS rank
    FROM base_candidates bc
    WHERE to_tsvector('english', bc.product_name || ' ' || bc.product_description) 
          @@ to_tsquery('english', %(tsquery)s)
    ORDER BY ts_rank_cd(
        to_tsvector('english', bc.product_name || ' ' || bc.product_description),
        to_tsquery('english', %(tsquery)s),
        2
    ) DESC
    LIMIT 20
),
rrf_combined AS (
    -- Step 1: RRF combination of vector and keyword search
    SELECT 
        COALESCE(vs.product_id, ks.product_id) AS product_id,
        COALESCE(vs.sku, ks.sku) AS sku,
        COALESCE(vs.product_name, ks.product_name) AS product_name,
        COALESCE(vs.product_description, ks.product_description) AS product_description,
        COALESCE(1.0 / (%(k)s + vs.rank), 0.0) +
        COALESCE(1.0 / (%(k)s + ks.rank), 0.0) AS rrf_score,
        vs.rank AS vector_rank,
        ks.rank AS keyword_rank,
        ROW_NUMBER() OVER (ORDER BY 
            COALESCE(1.0 / (%(k)s + vs.rank), 0.0) +
            COALESCE(1.0 / (%(k)s + ks.rank), 0.0) DESC
        ) AS rrf_rank
    FROM vector_search vs
    FULL OUTER JOIN keyword_search ks ON vs.product_id = ks.product_id
    ORDER BY rrf_score DESC
    LIMIT 50  -- Get top 50 for reranking
),
reranked AS (
    -- Step 2: Get ranker ranking for all RRF results, then join back
    WITH ranker_results AS (
        SELECT id, rank, score
        FROM azure_ai.rank(
            query => %(query)s,
            document_contents => ARRAY(
                SELECT rrf2.product_name || ': ' || rrf2.product_description
                FROM rrf_combined rrf2
                ORDER BY rrf2.rrf_score DESC
            ),
            document_ids => ARRAY(
                SELECT rrf2.product_id::text
                FROM rrf_combined rrf2
                ORDER BY rrf2.rrf_score DESC
            )
            -- Using default Cohere-rerank-v3.5 model (no model parameter needed)
        )
    )
    SELECT 
        rrf.*,
        rr.rank AS ranker_rank,
        rr.score AS ranker_score
    FROM rrf_combined rrf
    JOIN ranker_results rr ON rr.id = rrf.product_id::text
)
SELECT
    r.product_id,
    r.sku,
    r.product_name,
    r.product_description,
    r.rrf_score,
    r.ranker_score,
    r.vector_rank,
    r.keyword_rank,
    r.rrf_rank,
    r.ranker_rank
FROM reranked r
ORDER BY r.ranker_rank ASC  -- Let reranker determine the final order
LIMIT 5;
"""

cur.execute(triple_rrf_sql, {
    'embedding': embedding,
    'tsquery': tsquery,
    'query': search_query,
    'k': k
})

results = cur.fetchall()
for i, result in enumerate(results, 1):
    product_id, sku, name, description, rrf_score, ranker_score, vector_rank, keyword_rank, rrf_rank, ranker_rank = result
    
    print(f"{i}. {sku} - {name}")
    print(f"   RRF Score: {rrf_score:.4f} | Ranker Score: {ranker_score:.4f}")
    
    # Show ranking progression
    rankings = []
    if vector_rank is not None:
        rankings.append(f"Vector: #{vector_rank}")
    if keyword_rank is not None:
        rankings.append(f"Keyword: #{keyword_rank}")
    rankings.append(f"RRF: #{rrf_rank}")
    rankings.append(f"Ranker: #{ranker_rank}")
    
    print(f"   Ranking Flow: {' → '.join(rankings)}")
    print(f"   Description: {description}")
    print()

