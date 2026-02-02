"""
Streamlit frontend for Zava Search Comparator.
Compare different search types side by side.
"""
import os
import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

# Configuration
API_URL = os.environ.get("SEARCH_COMPARATOR_API_URL", "http://localhost:8010")

# Page configuration
st.set_page_config(
    page_title="Zava Search Comparator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .search-result-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        border-left: 4px solid #0066cc;
    }
    .result-rank {
        font-size: 24px;
        font-weight: bold;
        color: #0066cc;
    }
    .result-sku {
        font-size: 12px;
        color: #666;
    }
    .result-name {
        font-size: 16px;
        font-weight: 600;
        color: #333;
    }
    .result-score {
        font-size: 14px;
        color: #28a745;
    }
    .metric-box {
        background-color: #e9ecef;
        border-radius: 6px;
        padding: 8px;
        text-align: center;
    }
    .highlight-unique {
        background-color: #fff3cd !important;
        border-left-color: #ffc107 !important;
    }
    .header-card {
        background: linear-gradient(135deg, #0066cc 0%, #004080 100%);
        color: white;
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Search type configurations
SEARCH_TYPES = {
    "keyword": {
        "name": "Keyword (Full-Text)",
        "icon": "📝",
        "description": "PostgreSQL ts_rank",
        "color": "#17a2b8"
    },
    "vector": {
        "name": "Vector (Semantic)",
        "icon": "🧠",
        "description": "pgvector cosine similarity",
        "color": "#28a745"
    },
    "hybrid_rrf": {
        "name": "Hybrid RRF",
        "icon": "🔀",
        "description": "Reciprocal Rank Fusion",
        "color": "#6f42c1"
    },
    "hybrid_ranker": {
        "name": "Hybrid + Ranker",
        "icon": "🎯",
        "description": "RRF + Cohere Rerank v4",
        "color": "#fd7e14"
    }
}


def check_api_health():
    """Check if the backend API is available."""
    try:
        response = httpx.get(f"{API_URL}/health", timeout=5)
        data = response.json()
        return data.get("status") == "healthy", data.get("database_connected", False)
    except Exception:
        return False, False


def perform_search(query: str, search_types: list[str], limit: int):
    """Call the backend API to perform searches."""
    try:
        response = httpx.post(
            f"{API_URL}/api/search",
            json={
                "query": query,
                "search_types": search_types,
                "limit": limit
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        st.error(f"API Error: {e}")
        return None


def render_result_card(result: dict, rank: int, is_unique: bool = False):
    """Render a single search result as a card."""
    unique_class = "highlight-unique" if is_unique else ""
    
    st.markdown(f"""
    <div class="search-result-card {unique_class}">
        <div style="display: flex; align-items: flex-start; gap: 12px;">
            <div class="result-rank">#{rank}</div>
            <div style="flex: 1;">
                <div class="result-sku">{result['sku']}</div>
                <div class="result-name">{result['product_name']}</div>
                <div class="result-score">Score: {result['score']:.4f}</div>
                <div style="font-size: 13px; color: #555; margin-top: 4px;">
                    {result['product_description'][:150]}...
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def get_product_ids(results: list) -> set:
    """Extract product IDs from results list."""
    return {r['product_id'] for r in results}


def main():
    # Header
    st.title("🔍 Zava Search Comparator")
    st.markdown("Compare different search strategies side by side to understand their effectiveness.")
    
    # Check API health
    api_healthy, db_connected = check_api_health()
    
    # Status indicators in sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Status
        col1, col2 = st.columns(2)
        with col1:
            if api_healthy:
                st.success("API: ✓")
            else:
                st.error("API: ✗")
        with col2:
            if db_connected:
                st.success("DB: ✓")
            else:
                st.warning("DB: ✗")
        
        st.divider()
        
        # Search type selection
        st.subheader("📋 Search Types")
        st.caption("Select which search methods to compare:")
        
        selected_types = []
        for type_id, type_info in SEARCH_TYPES.items():
            if st.checkbox(
                f"{type_info['icon']} {type_info['name']}", 
                value=True,
                help=type_info['description'],
                key=f"cb_{type_id}"
            ):
                selected_types.append(type_id)
        
        st.divider()
        
        # Result limit
        limit = st.slider(
            "Results per search",
            min_value=1,
            max_value=20,
            value=5,
            help="Number of results to return for each search type"
        )
        
        st.divider()
        
        # API URL configuration
        with st.expander("🔧 Advanced"):
            st.text_input(
                "API URL",
                value=API_URL,
                disabled=True,
                help="Configure via SEARCH_COMPARATOR_API_URL env var"
            )
    
    # Main search area
    col_query, col_button = st.columns([4, 1])
    
    with col_query:
        query = st.text_input(
            "Search query",
            placeholder="e.g., 25 foot drip hose, garden watering supplies",
            label_visibility="collapsed"
        )
    
    with col_button:
        search_button = st.button("🔍 Compare", type="primary", use_container_width=True)
    
    # Validation
    if not api_healthy:
        st.warning("⚠️ Backend API is not available. Please start the API server first.")
        st.code("cd search-comparator && uvicorn backend.main:app --reload --port 8010", language="bash")
        return
    
    if not selected_types:
        st.info("👈 Please select at least one search type from the sidebar.")
        return
    
    # Perform search
    if search_button and query:
        with st.spinner("Searching..."):
            results = perform_search(query, selected_types, limit)
        
        if results:
            # Summary metrics
            st.divider()
            
            metric_cols = st.columns(len(selected_types) + 1)
            
            with metric_cols[0]:
                st.metric(
                    "Total Time",
                    f"{results['total_execution_time_ms']:.0f}ms"
                )
            
            for idx, type_id in enumerate(selected_types):
                if type_id in results['search_results']:
                    type_result = results['search_results'][type_id]
                    with metric_cols[idx + 1]:
                        st.metric(
                            SEARCH_TYPES[type_id]['icon'] + " " + SEARCH_TYPES[type_id]['name'],
                            f"{type_result['execution_time_ms']:.0f}ms",
                            f"{type_result['result_count']} results"
                        )
            
            st.divider()
            
            # Collect all product IDs per search type
            type_product_ids = {}
            for type_id in selected_types:
                if type_id in results['search_results']:
                    type_product_ids[type_id] = get_product_ids(
                        results['search_results'][type_id]['results']
                    )
            
            # Find products unique to each search type
            all_product_ids = set()
            for ids in type_product_ids.values():
                all_product_ids.update(ids)
            
            # Create columns for each search type
            cols = st.columns(len(selected_types))
            
            for col_idx, type_id in enumerate(selected_types):
                with cols[col_idx]:
                    type_info = SEARCH_TYPES[type_id]
                    
                    # Header for this search type
                    st.markdown(f"""
                    <div class="header-card" style="background: {type_info['color']};">
                        <div style="font-size: 18px; font-weight: bold;">
                            {type_info['icon']} {type_info['name']}
                        </div>
                        <div style="font-size: 12px; opacity: 0.9;">
                            {type_info['description']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if type_id in results['search_results']:
                        type_result = results['search_results'][type_id]
                        
                        if type_result['results']:
                            # Get IDs from other search types
                            other_type_ids = set()
                            for other_type, ids in type_product_ids.items():
                                if other_type != type_id:
                                    other_type_ids.update(ids)
                            
                            for result in type_result['results']:
                                # Check if this product is unique to this search type
                                is_unique = result['product_id'] not in other_type_ids
                                render_result_card(result, result['rank'], is_unique)
                        else:
                            st.info("No results found")
                    else:
                        st.error("Search failed")
            
            # Legend
            st.divider()
            st.caption("💡 **Yellow highlighted** results are unique to that search type and don't appear in other selected searches.")
    
    elif search_button and not query:
        st.warning("Please enter a search query.")


if __name__ == "__main__":
    main()
