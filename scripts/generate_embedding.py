import os
from pathlib import Path

import dotenv
import openai
from azure.identity import AzureCliCredential, get_bearer_token_provider

dotenv.load_dotenv()

azure_credential = AzureCliCredential()
token_provider = get_bearer_token_provider(azure_credential, "https://cognitiveservices.azure.com/.default")
openai_client = openai.AzureOpenAI(
    api_version="2024-10-21",
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_ad_token_provider=token_provider,
)
MODEL_NAME = os.environ["EMBEDDING_MODEL_DEPLOYMENT_NAME"]
MODEL_DIMENSIONS = 1536

embeddings_response = openai_client.embeddings.create(
    model=MODEL_NAME,
    dimensions=MODEL_DIMENSIONS,
    input="garden watering supplies"
)
embedding = embeddings_response.data[0].embedding

with Path("vector.txt").open("w") as f:
    f.write(str(embedding))