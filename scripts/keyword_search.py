import os

import dotenv
import psycopg2
from azure.identity import DefaultAzureCredential

dotenv.load_dotenv(override=True)

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

search_query = "25 foot drip hose"

print(f"Full-text Search for: '{search_query}'\n")

# turn query into tsquery by using | operator between words
tsquery = " | ".join(search_query.split())

cur.execute(
    """
SELECT 
    p.product_id,
    p.sku,
    p.product_name,
    p.product_description,
    ts_rank(
        to_tsvector('english', p.product_name || ' ' || p.product_description),
        to_tsquery('english', %s)
    ) as relevance_score
FROM retail.products p
WHERE to_tsvector('english', p.product_name || ' ' || p.product_description) 
@@ to_tsquery('english', %s)
ORDER BY relevance_score DESC, p.product_name
LIMIT 5;""",
    (tsquery, tsquery),
)
closest_items = cur.fetchall()

for i, (_, sku, name, description, relevance_score) in enumerate(closest_items, 1):
    print(f"{i}. {sku} - {name}")
    print(f"   Relevance Score: {relevance_score:.4f}")
    print(f"   Description: {description}")
    print()
