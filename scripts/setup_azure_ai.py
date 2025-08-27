import os
import sys

import dotenv
import psycopg2
from azure.identity import AzureCliCredential, DefaultAzureCredential
from dotenv import load_dotenv

dotenv.load_dotenv(override=True)

POSTGRES_HOST = os.environ["POSTGRES_SERVER_FQDN"]
POSTGRES_USERNAME = os.environ["POSTGRES_SERVER_USERNAME"]
POSTGRES_DATABASE = "zava"

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
EMBEDDING_MODEL_DEPLOYMENT = os.environ.get("EMBEDDING_MODEL_DEPLOYMENT_NAME")

# Azure ML Cohere Reranker configuration
AZURE_ML_RANKING_ENDPOINT = os.environ.get("AZURE_ML_SERVERLESS_RANKING_ENDPOINT")
AZURE_ML_RANKING_KEY = os.environ.get("AZURE_ML_SERVERLESS_RANKING_ENDPOINT_KEY")

# Environment variable examples:
# AZURE_ML_SERVERLESS_RANKING_ENDPOINT=https://<deployment-name>.<region>.models.ai.azure.com/v1/rerank
# AZURE_ML_SERVERLESS_RANKING_ENDPOINT_KEY=<your-api-key>

# Determine authentication method
USE_MANAGED_IDENTITY = not AZURE_OPENAI_KEY  # Use managed identity if no key is provided
USE_RANKING_MANAGED_IDENTITY = not AZURE_ML_RANKING_KEY  # Use managed identity for ranking if no key is provided

if not AZURE_OPENAI_ENDPOINT:
    print("Error: AZURE_OPENAI_ENDPOINT environment variable is required")
    sys.exit(1)

if not EMBEDDING_MODEL_DEPLOYMENT:
    print("Error: EMBEDDING_MODEL_DEPLOYMENT_NAME environment variable is required")
    sys.exit(1)

if not USE_MANAGED_IDENTITY and not AZURE_OPENAI_KEY:
    print("Error: Either use managed identity (don't set AZURE_OPENAI_KEY) or provide AZURE_OPENAI_KEY")
    sys.exit(1)

print(f"Authentication method: {'Managed Identity' if USE_MANAGED_IDENTITY else 'Subscription Key'}")
print(f"Ranking authentication method: {'Managed Identity' if USE_RANKING_MANAGED_IDENTITY else 'Subscription Key'}")

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

try:
    conn = psycopg2.connect(
        database=POSTGRES_DATABASE,
        user=POSTGRES_USERNAME,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        **extra_params,
    )
    
    conn.autocommit = True
    cur = conn.cursor()
    
    print("Connected to PostgreSQL successfully!")
    
    # 1. Create azure_ai extension if it doesn't exist
    print("\n1. Creating azure_ai extension...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS azure_ai")
    print("✓ azure_ai extension created/verified")
    
    # 2. Configure Azure OpenAI authentication
    print(f"\n2. Configuring Azure OpenAI with {('managed identity' if USE_MANAGED_IDENTITY else 'subscription key')}...")
    
    if USE_MANAGED_IDENTITY:
        # Set authentication type to managed identity
        cur.execute("SELECT azure_ai.set_setting('azure_openai.auth_type', 'managed-identity')")
        print("✓ Set authentication type to managed-identity")
    else:
        # Set authentication type to subscription key
        cur.execute("SELECT azure_ai.set_setting('azure_openai.auth_type', 'subscription-key')")
        print("✓ Set authentication type to subscription-key")
        
        # Set the subscription key
        cur.execute("SELECT azure_ai.set_setting('azure_openai.subscription_key', %s)", (AZURE_OPENAI_KEY,))
        print("✓ Set Azure OpenAI subscription key")
    
    # Set Azure OpenAI endpoint (required for both auth methods)
    cur.execute("SELECT azure_ai.set_setting('azure_openai.endpoint', %s)", (AZURE_OPENAI_ENDPOINT,))
    print(f"✓ Set Azure OpenAI endpoint to: {AZURE_OPENAI_ENDPOINT}")
    
    # 2b. Configure Azure ML Cohere Reranker (if available)
    if AZURE_ML_RANKING_ENDPOINT:
        print(f"\n2b. Configuring Azure ML Cohere Reranker with {('managed identity' if USE_RANKING_MANAGED_IDENTITY else 'subscription key')}...")
        
        if USE_RANKING_MANAGED_IDENTITY:
            # Set authentication type to managed identity for ranking
            cur.execute("SELECT azure_ai.set_setting('azure_ml.auth_type', 'managed-identity')")
            print("✓ Set ranking authentication type to managed-identity")
        else:
            # Set the subscription key for ranking
            cur.execute("SELECT azure_ai.set_setting('azure_ml.serverless_ranking_endpoint_key', %s)", (AZURE_ML_RANKING_KEY,))
            print("✓ Set Azure ML ranking endpoint key")
        
        # Set Azure ML ranking endpoint (required for both auth methods)
        cur.execute("SELECT azure_ai.set_setting('azure_ml.serverless_ranking_endpoint', %s)", (AZURE_ML_RANKING_ENDPOINT,))
        print(f"✓ Set Azure ML ranking endpoint to: {AZURE_ML_RANKING_ENDPOINT}")
    else:
        print("\n2b. Azure ML Cohere Reranker configuration skipped (AZURE_ML_SERVERLESS_RANKING_ENDPOINT not provided)")
        print("   Note: To use azure_ai.rank() with Cohere reranker, set AZURE_ML_SERVERLESS_RANKING_ENDPOINT environment variable")
    
    # 3. Verify settings
    print("\n3. Verifying azure_ai configuration...")
    
    cur.execute("SELECT azure_ai.get_setting('azure_openai.auth_type')")
    auth_type = cur.fetchone()[0]
    print(f"✓ Authentication type: {auth_type}")
    
    cur.execute("SELECT azure_ai.get_setting('azure_openai.endpoint')")
    endpoint = cur.fetchone()[0]
    print(f"✓ OpenAI endpoint: {endpoint}")
    
    if not USE_MANAGED_IDENTITY:
        print("✓ Subscription key configured (not displayed for security)")
    
    # Verify Cohere reranker settings if configured
    if AZURE_ML_RANKING_ENDPOINT:
        try:
            cur.execute("SELECT azure_ai.get_setting('azure_ml.serverless_ranking_endpoint')")
            ranking_endpoint = cur.fetchone()[0]
            print(f"✓ Ranking endpoint: {ranking_endpoint}")
            
            if USE_RANKING_MANAGED_IDENTITY:
                cur.execute("SELECT azure_ai.get_setting('azure_ml.auth_type')")
                ranking_auth_type = cur.fetchone()[0]
                print(f"✓ Ranking authentication type: {ranking_auth_type}")
            else:
                print("✓ Ranking subscription key configured (not displayed for security)")
                
        except Exception as e:
            print(f"⚠ Warning: Could not verify ranking configuration: {e}")
    
    # 4. Test the configuration with a simple embedding call
    print("\n4. Testing Azure OpenAI integration...")
    
    try:
        test_text = "This is a test to verify Azure OpenAI connectivity"
        
        # Use the correct function name from the documentation
        print(f"  Testing azure_openai.create_embeddings with deployment: {EMBEDDING_MODEL_DEPLOYMENT}")
        cur.execute("SELECT azure_openai.create_embeddings(%s, %s)", (EMBEDDING_MODEL_DEPLOYMENT, test_text))
        result = cur.fetchone()
        
        if result and result[0]:
            embedding_vector = result[0]
            vector_length = len(embedding_vector) if isinstance(embedding_vector, (list, tuple)) else 'Unknown'
            print(f"✓ Successfully created embedding! Vector length: {vector_length}")
            print("✓ Azure OpenAI integration is working correctly!")
            
            # Also test the data type
            cur.execute("SELECT pg_typeof(azure_openai.create_embeddings(%s, %s))", (EMBEDDING_MODEL_DEPLOYMENT, test_text))
            type_result = cur.fetchone()
            if type_result:
                print(f"✓ Embedding data type: {type_result[0]}")
        else:
            print("⚠ Warning: Embedding creation returned empty result")
            
    except psycopg2.Error as e:
        print(f"✗ Error testing Azure OpenAI integration: {e}")
        
    except Exception as e:
        print(f"✗ Unexpected error during testing: {e}")
    
    # 4b. Test Cohere reranker if configured
    if AZURE_ML_RANKING_ENDPOINT:
        print("\n4b. Testing Azure ML Cohere Reranker integration...")
        
        try:
            test_query = "Best headphones for travel"
            test_documents = [
                "The headphones are lightweight and foldable, making them easy to carry.",
                "Bad battery life, not so great for long trips.",
                "The sound quality is excellent, with good noise isolation."
            ]
            
            print(f"  Testing azure_ai.rank() with query: '{test_query}'")
            cur.execute("SELECT * FROM azure_ai.rank(%s, %s)", (test_query, test_documents))
            results = cur.fetchall()
            
            if results:
                print(f"✓ Successfully ranked {len(results)} documents!")
                for doc_id, rank, score in results[:3]:  # Show first 3 results
                    print(f"  Rank {rank}: Document {doc_id}, Score: {score:.4f}")
                print("✓ Azure ML Cohere Reranker integration is working correctly!")
            else:
                print("⚠ Warning: Ranking returned empty result")
                
        except psycopg2.Error as e:
            print(f"✗ Error testing Azure ML Cohere Reranker: {e}")
            print("  Note: Make sure the Cohere rerank model is deployed and accessible")
            
        except Exception as e:
            print(f"✗ Unexpected error during reranker testing: {e}")
    else:
        print("\n4b. Cohere reranker testing skipped (endpoint not configured)")
    
    # 5. Show available azure_ai functions
    print("\n5. Available azure_ai functions:")
    try:
        cur.execute("""
            SELECT routine_name, routine_type 
            FROM information_schema.routines 
            WHERE routine_schema = 'azure_ai' 
            ORDER BY routine_name
        """)
        
        functions = cur.fetchall()
        if functions:
            for func_name, func_type in functions:
                print(f"  - {func_name} ({func_type})")
        else:
            print("  No azure_ai functions found in information_schema")
            
        # Also try to check for azure_openai schema
        cur.execute("""
            SELECT routine_name, routine_type 
            FROM information_schema.routines 
            WHERE routine_schema = 'azure_openai' 
            ORDER BY routine_name
        """)
        
        openai_functions = cur.fetchall()
        if openai_functions:
            print("\n  Available azure_openai functions:")
            for func_name, func_type in openai_functions:
                print(f"  - azure_openai.{func_name} ({func_type})")
                
    except Exception as e:
        print(f"  Error listing functions: {e}")
        
        # Try alternative approach
        try:
            cur.execute("SELECT extname FROM pg_extension WHERE extname LIKE '%azure%'")
            extensions = cur.fetchall()
            print(f"  Installed Azure extensions: {[ext[0] for ext in extensions]}")
        except:
            pass
    
    print("\n" + "="*60)
    print("CONFIGURATION SUMMARY")
    print("="*60)
    
    print(f"✓ Azure AI extension: Enabled")
    print(f"✓ Azure OpenAI: Configured with {('managed identity' if USE_MANAGED_IDENTITY else 'subscription key')}")
    if AZURE_ML_RANKING_ENDPOINT:
        print(f"✓ Cohere Reranker: Configured with {('managed identity' if USE_RANKING_MANAGED_IDENTITY else 'subscription key')}")
        print("  Available functions: azure_ai.rank() with Cohere-rerank-v3.5 (default)")
    else:
        print("⚠ Cohere Reranker: Not configured")
        print("  To enable azure_ai.rank(), set these environment variables:")
        print("  - AZURE_ML_SERVERLESS_RANKING_ENDPOINT")
        print("  - AZURE_ML_SERVERLESS_RANKING_ENDPOINT_KEY (or use managed identity)")
    
    print("\nAvailable semantic operators:")
    print("  - azure_ai.generate() - Text generation using LLMs")
    print("  - azure_ai.extract() - Extract structured data from text") 
    print("  - azure_ai.is_true() - Evaluate if statements are true")
    if AZURE_ML_RANKING_ENDPOINT:
        print("  - azure_ai.rank() - Rerank documents by relevance")
    else:
        print("  - azure_ai.rank() - Available after Cohere reranker setup")
    print("="*60)
    
except psycopg2.Error as e:
    print(f"Error connecting to PostgreSQL: {e}")
    sys.exit(1)
    
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
    
finally:
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()
    print("\nConnection closed.")
