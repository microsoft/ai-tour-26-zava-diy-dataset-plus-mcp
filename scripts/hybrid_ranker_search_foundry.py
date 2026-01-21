"""
Hybrid RRF Search with Cohere Reranker using Azure AI Foundry endpoint.

This script performs Reciprocal Rank Fusion (RRF) combining vector search and
keyword search, then uses Cohere Rerank v4 via Azure AI Foundry to rerank results.

Unlike hybrid_ranker_search.py which uses azure_ai.rank() in PostgreSQL,
this version calls the Cohere API directly from Python, which allows using
Azure AI Foundry endpoints (services.ai.azure.com) that are not compatible
with the azure_ai extension's serverless_rank function.
"""

import os

import dotenv
import psycopg2
import requests
from azure.identity import AzureCliCredential
from pgvector.psycopg2 import register_vector

dotenv.load_dotenv(override=True)

EMBEDDING_MODEL_DEPLOYMENT = os.environ["EMBEDDING_MODEL_DEPLOYMENT_NAME"]

# Cohere Reranker configuration (Azure AI Foundry endpoint)
COHERE_RERANK_ENDPOINT = os.environ.get("COHERE_RERANK_ENDPOINT_URI")
COHERE_RERANK_KEY = os.environ.get("COHERE_RERANK_ENDPOINT_KEY")
COHERE_MODEL = "Cohere-rerank-v4.0-fast"

POSTGRES_HOST = os.environ["POSTGRES_SERVER_FQDN"]
POSTGRES_USERNAME = os.environ["POSTGRES_SERVER_USERNAME"]
POSTGRES_DATABASE = "zava"

if POSTGRES_HOST.endswith(".database.azure.com"):
    print("Authenticating to Azure Database for PostgreSQL using Azure CLI...")
    azure_credential = AzureCliCredential()
    token = azure_credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
    POSTGRES_PASSWORD = token.token
else:
    POSTGRES_PASSWORD = os.environ["POSTGRES_SERVER_PASSWORD"]

extra_params = {}
if POSTGRES_SSL := os.environ.get("POSTGRES_SSL"):
    extra_params["sslmode"] = POSTGRES_SSL


def cohere_rerank(query: str, documents: list[dict], top_n: int = 10) -> list[dict]:
    """
    Call Cohere Rerank API via Azure AI Foundry.
    
    Args:
        query: The search query
        documents: List of dicts with 'id' and 'text' keys
        top_n: Number of top results to return
    
    Returns:
        List of dicts with 'id', 'index', and 'relevance_score'
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
    
    response = requests.post(COHERE_RERANK_ENDPOINT, headers=headers, json=payload)
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
print(f"RRF Search with Cohere Reranker (Foundry) for: '{search_query}'")

# Create embedding using PostgreSQL azure_openai extension
cur.execute("SELECT azure_openai.create_embeddings(%s, %s)", (EMBEDDING_MODEL_DEPLOYMENT, search_query))
embedding_result = cur.fetchone()
embedding = embedding_result[0]

# Convert to OR-based search for broader matching (like TF-IDF/BM25)
tsquery = ' | '.join(search_query.split())
print(f"✓ Using OR-based query for broader matching: '{tsquery}'")

# RRF (Reciprocal Rank Fusion) parameter - controls the weighting
k = 60  # Standard RRF parameter value

# RRF SQL query combining vector search and keyword search (without azure_ai.rank)
rrf_sql = """
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
    -- RRF combination of vector and keyword search
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

cur.execute(rrf_sql, {
    'embedding': embedding,
    'tsquery': tsquery,
    'k': k
})

rrf_results = cur.fetchall()
print(f"✓ Got {len(rrf_results)} candidates from RRF search")

# Prepare documents for Cohere reranking
documents = []
results_dict = {}
for result in rrf_results:
    product_id, sku, name, description, rrf_score, vector_rank, keyword_rank, rrf_rank = result
    doc_id = str(product_id)
    documents.append({
        "id": doc_id,
        "text": f"{name}: {description}"
    })
    results_dict[doc_id] = {
        "product_id": product_id,
        "sku": sku,
        "name": name,
        "description": description,
        "rrf_score": rrf_score,
        "vector_rank": vector_rank,
        "keyword_rank": keyword_rank,
        "rrf_rank": rrf_rank
    }

# Call Cohere Rerank API
print(f"✓ Calling Cohere Rerank v4.0 Fast via Azure AI Foundry...")
reranked = cohere_rerank(search_query, documents, top_n=5)

print(f"\n{'='*80}")
print(f"Top 5 Results (Reranked by Cohere)")
print(f"{'='*80}\n")

for i, item in enumerate(reranked, 1):
    doc_id = item["id"]
    result = results_dict[doc_id]
    ranker_score = item["relevance_score"]
    ranker_rank = item["rank"]
    
    print(f"{i}. {result['sku']} - {result['name']}")
    print(f"   RRF Score: {result['rrf_score']:.4f} | Ranker Score: {ranker_score:.4f}")
    
    # Show ranking progression
    rankings = []
    if result['vector_rank'] is not None:
        rankings.append(f"Vector: #{result['vector_rank']}")
    if result['keyword_rank'] is not None:
        rankings.append(f"Keyword: #{result['keyword_rank']}")
    rankings.append(f"RRF: #{result['rrf_rank']}")
    rankings.append(f"Ranker: #{ranker_rank}")
    
    print(f"   Ranking Flow: {' → '.join(rankings)}")
    print(f"   Description: {result['description']}")
    print()

cur.close()
conn.close()
