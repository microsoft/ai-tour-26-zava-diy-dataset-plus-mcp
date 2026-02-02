# Zava Search Comparator

A visual tool to compare different search strategies side by side for the Zava retail product catalog.

## Overview

This application allows you to execute and compare multiple search types simultaneously:

| Search Type | Description | Score Type |
|-------------|-------------|------------|
| **Keyword (Full-Text)** | PostgreSQL `ts_rank` with OR-based tsquery | Relevance Score |
| **Vector (Semantic)** | pgvector cosine similarity with Azure OpenAI embeddings | Cosine Similarity |
| **Hybrid RRF** | Reciprocal Rank Fusion combining vector + keyword | RRF Score |
| **Hybrid + Ranker** | RRF with Cohere Rerank v4 via Azure AI Foundry | Ranker Score |

## Architecture

```
search-comparator/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   └── search_engines/      # Search implementations
│       ├── keyword.py       # Full-text search
│       ├── vector.py        # Semantic search
│       ├── hybrid_rrf.py    # RRF fusion
│       └── hybrid_ranker.py # RRF + Cohere rerank
├── frontend/
│   └── app.py               # Streamlit UI
└── requirements.txt
```

## Prerequisites

- Python 3.11+
- PostgreSQL database with:
  - `retail.products` table with product data
  - `retail.product_description_embeddings` table with embeddings
  - `azure_openai` extension configured
  - `pgvector` extension installed
- Environment variables configured (see below)

## Environment Variables

Create a `.env` file or set these environment variables:

```bash
# PostgreSQL Connection
POSTGRES_SERVER_FQDN=localhost           # or *.database.azure.com for Azure
POSTGRES_SERVER_USERNAME=store_manager
POSTGRES_SERVER_PASSWORD=StoreManager123!
POSTGRES_DATABASE=zava
POSTGRES_SSL=require                     # Optional, for Azure

# Azure OpenAI (for embeddings)
EMBEDDING_MODEL_DEPLOYMENT_NAME=text-embedding-3-small

# Cohere Reranker (for Hybrid + Ranker search)
COHERE_RERANK_ENDPOINT_URI=https://your-endpoint.services.ai.azure.com/...
COHERE_RERANK_ENDPOINT_KEY=your-api-key

# Optional
SEARCH_COMPARATOR_PORT=8010              # Backend API port
SEARCH_COMPARATOR_API_URL=http://localhost:8010  # For frontend
```

## Installation

```bash
cd search-comparator
pip install -r requirements.txt
```

## Running

### 1. Start the Backend API

```bash
cd search-comparator
uvicorn backend.main:app --reload --port 8010
```

The API will be available at http://localhost:8010

### 2. Start the Frontend

In a new terminal:

```bash
cd search-comparator
streamlit run frontend/app.py --server.port 8501
```

The UI will open at http://localhost:8501

## Usage

1. **Select Search Types**: Use the checkboxes in the sidebar to choose which search methods to compare
2. **Enter Query**: Type your search query (e.g., "25 foot drip hose", "garden watering supplies")
3. **Adjust Limit**: Use the slider to set how many results per search type
4. **Click Compare**: Results appear side-by-side in columns

### Understanding Results

- **Yellow highlighted** results are unique to that search type
- **Execution time** shows how long each search took
- **Score** represents the relevance measure (varies by search type)
- Compare rankings to see how different methods prioritize results

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with DB connection status |
| `/api/search` | POST | Execute comparative search |
| `/api/search-types` | GET | List available search types |

### Example API Call

```bash
curl -X POST http://localhost:8010/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "garden hose",
    "search_types": ["keyword", "vector", "hybrid_rrf"],
    "limit": 5
  }'
```

## Development

The search engines are modular and can be extended. Each search module implements:

```python
async def search(query: str, pool: Pool, limit: int) -> tuple[list[ProductResult], float]:
    """
    Args:
        query: Search query text
        pool: asyncpg connection pool
        limit: Maximum results
        
    Returns:
        Tuple of (results list, execution time in ms)
    """
```

## License

MIT License
