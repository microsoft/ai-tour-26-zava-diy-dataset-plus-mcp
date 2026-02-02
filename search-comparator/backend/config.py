"""
Configuration for the Search Comparator backend.
"""
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

# Load .env file before reading configuration
load_dotenv(override=True)

# PostgreSQL Configuration
POSTGRES_HOST = os.environ.get("POSTGRES_SERVER_FQDN", "localhost")
POSTGRES_USERNAME = os.environ.get("POSTGRES_SERVER_USERNAME", "store_manager")
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE", "zava")
POSTGRES_SSL = os.environ.get("POSTGRES_SSL", "require" if "azure.com" in os.environ.get("POSTGRES_SERVER_FQDN", "") else None)

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

# Cached token for reuse
_cached_credential = None


def get_postgres_password() -> str:
    """Get PostgreSQL password, using Azure AD token if on Azure."""
    global _cached_credential
    if POSTGRES_HOST.endswith(".database.azure.com"):
        if _cached_credential is None:
            _cached_credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
        token = _cached_credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
        return token.token
    return os.environ.get("POSTGRES_SERVER_PASSWORD", "StoreManager123!")


def get_connection_string() -> str:
    """Get asyncpg connection string."""
    password = get_postgres_password()
    # URL encode username and password for special characters
    encoded_username = quote_plus(POSTGRES_USERNAME)
    encoded_password = quote_plus(password)
    ssl_param = f"?sslmode={POSTGRES_SSL}" if POSTGRES_SSL else ""
    return f"postgresql://{encoded_username}:{encoded_password}@{POSTGRES_HOST}/{POSTGRES_DATABASE}{ssl_param}"
