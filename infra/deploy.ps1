Write-Host "Deploying the Azure resources..."

# Define resource group parameters
$RG_LOCATION = "westus"
$AI_PROJECT_FRIENDLY_NAME = "Zava Agent Service Workshop"
$RESOURCE_PREFIX = "zava-agent-wks"
$UNIQUE_SUFFIX = -join ((65..90) + (97..122) | Get-Random -Count 4 | ForEach-Object { [char]$_ })

# Deploy the Azure resources and save output to JSON (capture errors to deploy.err like deploy.sh)
Write-Host " Creating agent workshop resources in resource group: rg-$RESOURCE_PREFIX-$UNIQUE_SUFFIX " -BackgroundColor Red -ForegroundColor White
$deploymentName = "azure-ai-agent-service-lab-$(Get-Date -Format 'yyyyMMddHHmmss')"

if (Test-Path deploy.err) { Remove-Item deploy.err -Force }
if (Test-Path output.json) { Remove-Item output.json -Force }

az deployment sub create `
    --name "$deploymentName" `
    --location "$RG_LOCATION" `
    --template-file main.bicep `
    --parameters "@main.parameters.json" `
    --parameters location="$RG_LOCATION" `
    --parameters resourcePrefix="$RESOURCE_PREFIX" `
    --parameters uniqueSuffix="$UNIQUE_SUFFIX" `
    --output json 1> output.json 2> deploy.err

if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Deployment failed. Check deploy.err for details." -ForegroundColor Red
        exit 1
}

# Parse the JSON file using native PowerShell cmdlets
if (-not (Test-Path -Path output.json)) {
    Write-Host "Error: output.json not found."
    exit -1
}

$jsonData = Get-Content output.json -Raw | ConvertFrom-Json
$outputs = $jsonData.properties.outputs

# Extract values from the JSON object
$projectsEndpoint = $outputs.projectsEndpoint.value
$resourceGroupName = $outputs.resourceGroupName.value
$subscriptionId = $outputs.subscriptionId.value
$aiFoundryName = $outputs.aiFoundryName.value
$aiProjectName = $outputs.aiProjectName.value
$azureOpenAIEndpoint = $outputs.azureOpenAIEndpoint.value
$applicationInsightsConnectionString = $outputs.applicationInsightsConnectionString.value
$applicationInsightsName = $outputs.applicationInsightsName.value
$postgresServerFqdn = $outputs.postgresServerFqdn.value
$postgresServerUsername = $outputs.postgresServerUsername.value
$cohereRerankEndpointUri = $outputs.cohereRerankEndpointUri.value
$cohereRerankEndpointName = $outputs.cohereRerankEndpointName.value
# Updated output name (bash script: cohereWorkspaceProjectName)
$cohereWorkspaceProjectName = $outputs.cohereWorkspaceProjectName.value

$cohereRerankEndpointKey = $null
$azureOpenAIKey = $null

if ([string]::IsNullOrEmpty($projectsEndpoint)) {
    Write-Host "Error: projectsEndpoint not found. Possible deployment failure."
    exit -1
}

# Set the path for the .env file
$ENV_FILE_PATH = "../src/python/workshop/.env"

# Create workshop directory if it doesn't exist
$workshopDir = Split-Path -Parent $ENV_FILE_PATH
if (-not (Test-Path $workshopDir)) {
    New-Item -ItemType Directory -Path $workshopDir -Force
}

# Delete the file if it exists
if (Test-Path $ENV_FILE_PATH) {
    Remove-Item -Path $ENV_FILE_PATH -Force
}

# Create a new workshop .env file and write to it
@"
PROJECT_ENDPOINT=$projectsEndpoint
GPT_MODEL_DEPLOYMENT_NAME="gpt-4o-mini"
EMBEDDING_MODEL_DEPLOYMENT_NAME="text-embedding-3-small"
APPLICATIONINSIGHTS_CONNECTION_STRING="$applicationInsightsConnectionString"
POSTGRES_SERVER_FQDN="$postgresServerFqdn"
POSTGRES_SERVER_USERNAME="$postgresServerUsername"
"@ | Set-Content -Path $ENV_FILE_PATH

# If a Cohere rerank endpoint was deployed, attempt to retrieve its primary key
if (-not [string]::IsNullOrWhiteSpace($cohereRerankEndpointUri)) {
    $workspaceName = $cohereWorkspaceProjectName
    # Use provided endpoint name output or derive from URI if absent
    if (-not [string]::IsNullOrWhiteSpace($cohereRerankEndpointName)) {
        $serverlessEndpointName = $cohereRerankEndpointName
    } elseif ($cohereRerankEndpointUri -match 'https?://([^/]+)') {
        $endpointHost = $Matches[1]
        $serverlessEndpointName = $endpointHost.Split('.')[0]
    }
    try {
        $subId = $subscriptionId
        if ($subId -and $serverlessEndpointName -and $workspaceName) {
            $keysJson = az rest --method post --url "https://management.azure.com/subscriptions/$subId/resourceGroups/$resourceGroupName/providers/Microsoft.MachineLearningServices/workspaces/$workspaceName/serverlessEndpoints/$serverlessEndpointName/listKeys?api-version=2024-04-01-preview" 2>$null
            if ($LASTEXITCODE -eq 0 -and $keysJson) {
                $keysObj = $keysJson | ConvertFrom-Json
                $cohereRerankEndpointKey = $keysObj.primaryKey
            }
        }
    }
    catch {
        Write-Host "Warning: Failed to retrieve Cohere rerank endpoint key: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Retrieve Azure OpenAI (Cognitive Services) account key (listKeys)
if (-not [string]::IsNullOrWhiteSpace($aiFoundryName) -and -not [string]::IsNullOrWhiteSpace($resourceGroupName)) {
    try {
        $openAIKeysJson = az rest --method post --url "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/$resourceGroupName/providers/Microsoft.CognitiveServices/accounts/$aiFoundryName/listKeys?api-version=2025-04-01-preview" 2>$null
        if ($LASTEXITCODE -eq 0 -and $openAIKeysJson) {
            $openAIKeys = $openAIKeysJson | ConvertFrom-Json
            # Prefer key1/primaryKey then key2/secondaryKey
            $azureOpenAIKey = $openAIKeys.key1
            if (-not $azureOpenAIKey) { $azureOpenAIKey = $openAIKeys.primaryKey }
            if (-not $azureOpenAIKey) { $azureOpenAIKey = $openAIKeys.key2 }
            if (-not $azureOpenAIKey) { $azureOpenAIKey = $openAIKeys.secondaryKey }
        }
    }
    catch {
        Write-Host "Warning: Failed to retrieve Azure OpenAI key: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Create fresh root .env file (always overwrite)
$ROOT_ENV_FILE_PATH = "../.env"
@"
AZURE_OPENAI_ENDPOINT="$azureOpenAIEndpoint"
PROJECT_ENDPOINT="$projectsEndpoint"
GPT_MODEL_DEPLOYMENT_NAME="gpt-4o-mini"
EMBEDDING_MODEL_DEPLOYMENT_NAME="text-embedding-3-small"
APPLICATIONINSIGHTS_CONNECTION_STRING="$applicationInsightsConnectionString"
POSTGRES_SERVER_FQDN="$postgresServerFqdn"
POSTGRES_SERVER_USERNAME="$postgresServerUsername"
"@ | Set-Content -Path $ROOT_ENV_FILE_PATH

# Append Cohere rerank endpoint details (only if deployed) to both env files
if (-not [string]::IsNullOrWhiteSpace($cohereRerankEndpointUri)) {
    Add-Content -Path $ENV_FILE_PATH -Value "COHERE_RERANK_ENDPOINT_URI=\"$cohereRerankEndpointUri\"" 
    Add-Content -Path $ROOT_ENV_FILE_PATH -Value "COHERE_RERANK_ENDPOINT_URI=\"$cohereRerankEndpointUri\"" 
    if (-not [string]::IsNullOrWhiteSpace($cohereRerankEndpointName)) {
        Add-Content -Path $ENV_FILE_PATH -Value "COHERE_RERANK_ENDPOINT_NAME=\"$cohereRerankEndpointName\""
        Add-Content -Path $ROOT_ENV_FILE_PATH -Value "COHERE_RERANK_ENDPOINT_NAME=\"$cohereRerankEndpointName\""
    }
    if (-not [string]::IsNullOrWhiteSpace($cohereRerankEndpointKey)) {
        Add-Content -Path $ENV_FILE_PATH -Value "COHERE_RERANK_ENDPOINT_KEY=\"$cohereRerankEndpointKey\""
        Add-Content -Path $ROOT_ENV_FILE_PATH -Value "COHERE_RERANK_ENDPOINT_KEY=\"$cohereRerankEndpointKey\""
    }
}

if (-not [string]::IsNullOrWhiteSpace($azureOpenAIKey)) {
    Add-Content -Path $ENV_FILE_PATH -Value "AZURE_OPENAI_KEY=\"$azureOpenAIKey\""
    Add-Content -Path $ROOT_ENV_FILE_PATH -Value "AZURE_OPENAI_KEY=\"$azureOpenAIKey\""
}

# Set the C# project path
$CSHARP_PROJECT_PATH = "../src/csharp/workshop/AgentWorkshop.Client/AgentWorkshop.Client.csproj"

# Set the user secrets for the C# project (if the project exists)
if (Test-Path $CSHARP_PROJECT_PATH) {
    dotnet user-secrets set "ConnectionStrings:AiAgentService" "$projectsEndpoint" --project "$CSHARP_PROJECT_PATH"
    dotnet user-secrets set "Azure:ModelName" "gpt-4o-mini" --project "$CSHARP_PROJECT_PATH"
}

# (Keeping output.json for reference; delete manually if not needed)

Write-Host "Adding Azure AI Developer user role"

# Set Variables (reuse subscriptionId from deployment outputs)
$subId = $subscriptionId
$objectId = az ad signed-in-user show --query id -o tsv

Write-Host "Ensuring Azure AI Developer role assignment..."

# Try to create the role assignment and capture the result
try {
    $roleResult = az role assignment create --role "f6c7c914-8db3-469d-8ca1-694a8f32e121" `
                            --assignee-object-id "$objectId" `
                            --scope "subscriptions/$subId/resourceGroups/$resourceGroupName" `
                            --assignee-principal-type 'User' 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Azure AI Developer role assignment created successfully." -ForegroundColor Green
    }
    else {
        # Check if the error is about existing role assignment
        $errorOutput = $roleResult -join " "
        if ($errorOutput -match "RoleAssignmentExists|already exists") {
            Write-Host "✅ Azure AI Developer role assignment already exists." -ForegroundColor Green
        }
        else {
            Write-Host "❌ User role assignment failed with unexpected error:" -ForegroundColor Red
            Write-Host $errorOutput -ForegroundColor Red
            exit 1
        }
    }
}
catch {
    # Handle any PowerShell exceptions
    $errorMessage = $_.Exception.Message
    if ($errorMessage -match "RoleAssignmentExists|already exists") {
        Write-Host "✅ Azure AI Developer role assignment already exists." -ForegroundColor Green
    }
    else {
        Write-Host "❌ User role assignment failed: $errorMessage" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "🎉 Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Resource Information:" -ForegroundColor Cyan
Write-Host "  Resource Group: $resourceGroupName"
Write-Host "  AI Project: $aiProjectName"
Write-Host "  Foundry Resource: $aiFoundryName"
Write-Host "  Application Insights: $applicationInsightsName"
Write-Host "  PostgreSQL Server: $postgresServerFqdn"
Write-Host "  PostgreSQL Username: $postgresServerUsername"
if (-not [string]::IsNullOrWhiteSpace($cohereRerankEndpointUri)) {
    Write-Host "  Cohere Rerank Endpoint: $cohereRerankEndpointUri"
    if (-not [string]::IsNullOrWhiteSpace($cohereRerankEndpointName)) { Write-Host "  Cohere Rerank Endpoint Name: $cohereRerankEndpointName" }
    if (-not [string]::IsNullOrWhiteSpace($cohereRerankEndpointKey)) {
        Write-Host "  Cohere Rerank Endpoint Key: (stored in .env)"
    } else {
        Write-Host "  Cohere Rerank Endpoint Key: (not retrieved)"
    }
}
if (-not [string]::IsNullOrWhiteSpace($azureOpenAIKey)) {
    Write-Host "  Azure OpenAI Key: (stored in .env)"
} else {
    Write-Host "  Azure OpenAI Key: (not retrieved)"
}
Write-Host ""
