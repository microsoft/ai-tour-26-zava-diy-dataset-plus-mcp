#!/bin/bash

echo "Deploying the Azure resources..."

# Define resource group parameters
RG_LOCATION="westus"
AI_PROJECT_FRIENDLY_NAME="Zava Agent Service Workshop"
RESOURCE_PREFIX="zava-agent-wks"
UNIQUE_SUFFIX=$(openssl rand -hex 2 | tr '[:upper:]' '[:lower:]')

# Deploy the Azure resources and save output to JSON
echo -e "\033[1;37;41m Creating agent workshop resources in resource group: rg-$RESOURCE_PREFIX-$UNIQUE_SUFFIX \033[0m"
echo "Starting Azure deployment..."
DEPLOYMENT_NAME="azure-ai-agent-service-lab-$(date +%Y%m%d%H%M%S)"
az deployment sub create \
  --name "$DEPLOYMENT_NAME" \
  --location "$RG_LOCATION" \
  --template-file main.bicep \
  --parameters @main.parameters.json \
  --parameters location="$RG_LOCATION" \
  --parameters resourcePrefix="$RESOURCE_PREFIX" \
  --parameters uniqueSuffix="$UNIQUE_SUFFIX" \
  --output json > output.json 2> deploy.err

if [ $? -ne 0 ]; then
  echo "❌ Deployment failed. Check deploy.err for details."
  exit 1
fi

# Parse the JSON file
if [ ! -f output.json ]; then
  echo "Error: output.json not found."
  exit 1
fi

PROJECTS_ENDPOINT=$(jq -r '.properties.outputs.projectsEndpoint.value' output.json)
RESOURCE_GROUP_NAME=$(jq -r '.properties.outputs.resourceGroupName.value' output.json)
SUBSCRIPTION_ID=$(jq -r '.properties.outputs.subscriptionId.value' output.json)
AI_FOUNDRY_NAME=$(jq -r '.properties.outputs.aiFoundryName.value' output.json)
AI_PROJECT_NAME=$(jq -r '.properties.outputs.aiProjectName.value' output.json)
AZURE_OPENAI_ENDPOINT=$(jq -r '.properties.outputs.azureOpenAIEndpoint.value' output.json)
APPLICATIONINSIGHTS_CONNECTION_STRING=$(jq -r '.properties.outputs.applicationInsightsConnectionString.value' output.json)
APPLICATION_INSIGHTS_NAME=$(jq -r '.properties.outputs.applicationInsightsName.value' output.json)
POSTGRES_SERVER_FQDN=$(jq -r '.properties.outputs.postgresServerFqdn.value' output.json)
POSTGRES_SERVER_USERNAME=$(jq -r '.properties.outputs.postgresServerUsername.value' output.json)
COHERE_RERANK_ENDPOINT_URI=$(jq -r '.properties.outputs.cohereRerankEndpointUri.value // empty' output.json)
COHERE_RERANK_ENDPOINT_NAME=$(jq -r '.properties.outputs.cohereRerankEndpointName.value // empty' output.json)
COHERE_WORKSPACE_PROJECT_NAME=$(jq -r '.properties.outputs.cohereWorkspaceProjectName.value // empty' output.json)
COHERE_RERANK_ENDPOINT_KEY=""

if [ -z "$PROJECTS_ENDPOINT" ] || [ "$PROJECTS_ENDPOINT" = "null" ]; then
  echo "Error: projectsEndpoint not found. Possible deployment failure."
  exit 1
fi

AZURE_OPENAI_KEY=""

ENV_FILE_PATH="../src/python/workshop/.env"

# Delete the file if it exists
[ -f "$ENV_FILE_PATH" ] && rm "$ENV_FILE_PATH"

# Create workshop directory if it doesn't exist
mkdir -p "$(dirname "$ENV_FILE_PATH")"

# If a Cohere rerank endpoint was deployed, attempt to retrieve its primary key
if [ -n "$COHERE_RERANK_ENDPOINT_URI" ]; then
  KEYS_RESPONSE=$(az rest \
    --method post \
    --url "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_NAME}/providers/Microsoft.MachineLearningServices/workspaces/${COHERE_WORKSPACE_PROJECT_NAME}/serverlessEndpoints/${COHERE_RERANK_ENDPOINT_NAME}/listKeys?api-version=2024-04-01-preview" 2>/dev/null || true)
  if [ -n "$KEYS_RESPONSE" ]; then
    COHERE_RERANK_ENDPOINT_KEY=$(echo "$KEYS_RESPONSE" | jq -r '.primaryKey // empty')
  fi
fi

# Retrieve Azure OpenAI (Cognitive Services) account key (moved earlier so it's written to .env)
if [ -n "$AI_FOUNDRY_NAME" ] && [ -n "$RESOURCE_GROUP_NAME" ]; then
  OPENAI_KEYS_RESPONSE=$(az rest \
    --method post \
    --url "https://management.azure.com/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_NAME}/providers/Microsoft.CognitiveServices/accounts/${AI_FOUNDRY_NAME}/listKeys?api-version=2025-04-01-preview" 2>/dev/null || true)
  if [ -n "$OPENAI_KEYS_RESPONSE" ]; then
    # Prefer primaryKey; fall back to secondaryKey if primary absent
    AZURE_OPENAI_KEY=$(echo "$OPENAI_KEYS_RESPONSE" | jq -r '.key1 // .primaryKey // .key2 // .secondaryKey // empty')
  fi
fi

# Write to the workshop .env file
{
  echo "PROJECT_ENDPOINT=$PROJECTS_ENDPOINT"
  echo "GPT_MODEL_DEPLOYMENT_NAME=\"gpt-4o-mini\""
  echo "EMBEDDING_MODEL_DEPLOYMENT_NAME=\"text-embedding-3-small\""
  echo "APPLICATIONINSIGHTS_CONNECTION_STRING=\"$APPLICATIONINSIGHTS_CONNECTION_STRING\""
  echo "POSTGRES_SERVER_FQDN=\"$POSTGRES_SERVER_FQDN\""
  echo "POSTGRES_SERVER_USERNAME=\"$POSTGRES_SERVER_USERNAME\""
  if [ -n "$COHERE_RERANK_ENDPOINT_URI" ]; then
    echo "COHERE_RERANK_ENDPOINT_URI=\"$COHERE_RERANK_ENDPOINT_URI\""
    if [ -n "$COHERE_RERANK_ENDPOINT_KEY" ]; then
      echo "COHERE_RERANK_ENDPOINT_KEY=\"$COHERE_RERANK_ENDPOINT_KEY\""
    fi
  fi
  if [ -n "$AZURE_OPENAI_KEY" ]; then
    echo "AZURE_OPENAI_KEY=\"$AZURE_OPENAI_KEY\""
  fi
} > "$ENV_FILE_PATH"

# Create fresh root .env file (always overwrite)
ROOT_ENV_FILE_PATH="../.env"
{
  echo "AZURE_OPENAI_ENDPOINT=\"$AZURE_OPENAI_ENDPOINT\""
  echo "PROJECT_ENDPOINT=\"$PROJECTS_ENDPOINT\""
  echo "GPT_MODEL_DEPLOYMENT_NAME=\"gpt-4o-mini\""
  echo "EMBEDDING_MODEL_DEPLOYMENT_NAME=\"text-embedding-3-small\""
  echo "APPLICATIONINSIGHTS_CONNECTION_STRING=\"$APPLICATIONINSIGHTS_CONNECTION_STRING\""
  echo "POSTGRES_SERVER_FQDN=\"$POSTGRES_SERVER_FQDN\""
  echo "POSTGRES_SERVER_USERNAME=\"$POSTGRES_SERVER_USERNAME\""
  if [ -n "$COHERE_RERANK_ENDPOINT_URI" ]; then
    echo "COHERE_RERANK_ENDPOINT_URI=\"$COHERE_RERANK_ENDPOINT_URI\""
    if [ -n "$COHERE_RERANK_ENDPOINT_KEY" ]; then
      echo "COHERE_RERANK_ENDPOINT_KEY=\"$COHERE_RERANK_ENDPOINT_KEY\""
    fi
  fi
  if [ -n "$AZURE_OPENAI_KEY" ]; then
    echo "AZURE_OPENAI_KEY=\"$AZURE_OPENAI_KEY\""
  fi
} > "$ROOT_ENV_FILE_PATH"

CSHARP_PROJECT_PATH="../src/csharp/workshop/AgentWorkshop.Client/AgentWorkshop.Client.csproj"

# Set the user secrets for the C# project (if the project exists)
if [ -f "$CSHARP_PROJECT_PATH" ]; then
  dotnet user-secrets set "ConnectionStrings:AiAgentService" "$PROJECTS_ENDPOINT" --project "$CSHARP_PROJECT_PATH"
  dotnet user-secrets set "Azure:ModelName" "gpt-4o-mini" --project "$CSHARP_PROJECT_PATH"
fi

# (Keeping output.json for reference; delete manually if not needed)

echo "Adding Azure AI Developer user role"

# Set Variables (reuse subscription ID from deployment outputs)
subId="$SUBSCRIPTION_ID"
objectId=$(az ad signed-in-user show --query id -o tsv)

echo "Ensuring Azure AI Developer role assignment..."

# Try to create the role assignment and capture both stdout and stderr
roleResult=$(az role assignment create --role "f6c7c914-8db3-469d-8ca1-694a8f32e121" \
                                       --assignee-object-id "$objectId" \
                                       --scope "subscriptions/$subId/resourceGroups/$RESOURCE_GROUP_NAME" \
                                       --assignee-principal-type 'User' 2>&1)

exitCode=$?

# Check if it succeeded or if the role assignment already exists
if [ $exitCode -eq 0 ]; then
    echo "✅ Azure AI Developer role assignment created successfully."
elif echo "$roleResult" | grep -q "RoleAssignmentExists\|already exists"; then
    echo "✅ Azure AI Developer role assignment already exists."
else
    echo "❌ User role assignment failed with unexpected error:"
    echo "$roleResult"
    exit 1
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Resource Information:"
echo "  Resource Group: $RESOURCE_GROUP_NAME"
echo "  AI Project: $AI_PROJECT_NAME"
echo "  Foundry Resource: $AI_FOUNDRY_NAME"
echo "  Application Insights: $APPLICATION_INSIGHTS_NAME"
echo "  PostgreSQL Server: $POSTGRES_SERVER_FQDN"
echo "  PostgreSQL Username: $POSTGRES_SERVER_USERNAME"
if [ -n "$COHERE_RERANK_ENDPOINT_URI" ]; then
  echo "  Cohere Rerank Endpoint: $COHERE_RERANK_ENDPOINT_URI"
  if [ -n "$COHERE_RERANK_ENDPOINT_KEY" ]; then
    echo "  Cohere Rerank Endpoint Key: (stored in .env)"
  else
    echo "  Cohere Rerank Endpoint Key: (not retrieved)"
  fi
fi
if [ -n "$AZURE_OPENAI_KEY" ]; then
  echo "  Azure OpenAI Key: (stored in .env)"
else
  echo "  Azure OpenAI Key: (not retrieved)"
fi
echo ""