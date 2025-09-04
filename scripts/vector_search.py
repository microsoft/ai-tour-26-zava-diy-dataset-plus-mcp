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
cur.execute("CREATE INDEX IF NOT EXISTS idx_product_embeddings_hnsw ON retail.product_description_embeddings USING hnsw (description_embedding vector_cosine_ops)")
cur.execute("SET hnsw.iterative_scan = strict_order")

search_query = "25 foot garden hose"

print(f"Vector search for: '{search_query}'\n")

cur.execute("SELECT azure_openai.create_embeddings(%s, %s)", (EMBEDDING_MODEL_DEPLOYMENT, search_query))
embedding_result = cur.fetchone()
embedding = embedding_result[0]

cur.execute("""
SELECT 
    p.product_id,
    p.sku,
    p.product_name,
    p.product_description,
    (1 - (pde.description_embedding <=> %s::vector)) as cosine_similarity,
    (pde.description_embedding <=> %s::vector) as cosine_distance
FROM retail.products p
JOIN retail.product_description_embeddings pde ON p.product_id = pde.product_id
WHERE pde.description_embedding IS NOT NULL
ORDER BY pde.description_embedding <=> %s::vector
LIMIT 5;""", (embedding, embedding, embedding))
closest_items = cur.fetchall()

for i, item in enumerate(closest_items, 1):
    product_id, sku, name, description, similarity, distance = item
    print(f"{i}. {sku} - {name}")
    print(f"   Cosine Similarity: {similarity:.2f} | Cosine Distance: {distance:.2f}")
    print(f"   Description: {description}...")
    print()
