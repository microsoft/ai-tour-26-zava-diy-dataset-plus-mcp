"""
Configuration for the Search Comparator backend.
"""
import os
from azure.identity import DefaultAzureCredential

# PostgreSQL Configuration
POSTGRES_HOST = os.environ.get("POSTGRES_SERVER_FQDN", "localhost")
POSTGRES_USERNAME = os.environ.get("POSTGRES_SERVER_USERNAME", "store_manager")
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE", "zava")
POSTGRES_SSL = os.environ.get("POSTGRES_SSL")

# Azure OpenAI Configuration
EMBEDDING_MODEL_DEPLOYMENT = os.environ.get("EMBEDDING_MODEL_DEPLOYMENT_NAME", "text-embedding-3-small")

# Cohere Reranker Configuration (Azure AI Foundry)
COHERE_RERANK_ENDPOINT = os.environ.get("COHERE_RERANK_ENDPOINT_URI")
COHERE_RERANK_KEY = os.environ.get("COHERE_RERANK_ENDPOINT_KEY")
COHERE_MODEL = "Cohere-rerank-v4.0-fast"

# RRF Configuration
RRF_K = 60  # Standard RRF parameter value

# Server Configuration
API_PORT = int(os.environ.get("SEARCH_COMPARATOR_PORT", "8010"))


def get_postgres_password() -> str:
    """Get PostgreSQL password, using Azure AD token if on Azure."""
    if POSTGRES_HOST.endswith(".database.azure.com"):
        azure_credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
        token = azure_credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        return token.token
    return os.environ.get("POSTGRES_SERVER_PASSWORD", "StoreManager123!")


def get_connection_string() -> str:
    """Get asyncpg connection string."""
    password = get_postgres_password()
    ssl_param = f"?sslmode={POSTGRES_SSL}" if POSTGRES_SSL else ""
    return f"postgresql://{POSTGRES_USERNAME}:{password}@{POSTGRES_HOST}/{POSTGRES_DATABASE}{ssl_param}"
