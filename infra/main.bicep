targetScope = 'subscription'

// Parameters
@description('Prefix for the resource group and resources')
param resourcePrefix string

@description('Location of the resource group to create or use for the deployment')
param location string

@description('Friendly name for your Azure AI resource')
param aiProjectFriendlyName string = 'Agents standard project resource'

@description('Description of your Azure AI resource displayed in Azure AI Foundry')
param aiProjectDescription string

@description('Set of tags to apply to all resources.')
param tags object = {}

@description('Array of models to deploy')
param models array = [
  {
    name: 'gpt-4o-mini'
    format: 'OpenAI'
    version: '2024-07-18'
    skuName: 'GlobalStandard'
    capacity: 120
  }
  {
    name: 'text-embedding-3-small'
    format: 'OpenAI'
    version: '1'
    skuName: 'GlobalStandard'
    capacity: 120
  }
]

@description('Unique suffix for the resources. Must be 4 characters long.')
@maxLength(4)
@minLength(4)
param uniqueSuffix string

@description('Whether to deploy the Cohere Rerank v3.5 serverless endpoint (preview)')
param deployCohereRerank bool = false

var resourceGroupName = toLower('rg-${resourcePrefix}-${uniqueSuffix}')

var defaultTags = {
  source: 'Azure AI Foundry Agents Service lab'
}

var rootTags = union(defaultTags, tags)

// Create resource group
resource rg 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
}

// Calculate the unique suffix
var aiProjectName = toLower('prj-${resourcePrefix}-${uniqueSuffix}')
var foundryResourceName = toLower('fdy-${resourcePrefix}-${uniqueSuffix}')
var applicationInsightsName = toLower('appi-${resourcePrefix}-${uniqueSuffix}')

module applicationInsights 'application-insights.bicep' = {
  name: 'application-insights-deployment'
  scope: rg
  params: {
    applicationInsightsName: applicationInsightsName
    location: location
    tags: rootTags
  }
}

module foundry 'foundry.bicep' = {
  name: 'foundry-account-deployment'
  scope: rg
  params: {
    aiProjectName: aiProjectName
    location: location
    tags: rootTags
    foundryResourceName: foundryResourceName
  }
}

module foundryProject 'foundry-project.bicep' = {
  name: 'foundry-project-deployment'
  scope: rg
  params: {
    foundryResourceName: foundry.outputs.accountName
    aiProjectName: aiProjectName
    aiProjectFriendlyName: aiProjectFriendlyName
    aiProjectDescription: aiProjectDescription
    location: location
    tags: rootTags
  }
}

@batchSize(1)
module foundryModelDeployments 'foundry-model-deployment.bicep' = [for (model, index) in models: {
  name: 'foundry-model-deployment-${model.name}-${index}'
  scope: rg
  dependsOn: [
    foundryProject
  ]
  params: {
    foundryResourceName: foundry.outputs.accountName
    modelName: model.name
    modelFormat: model.format
    modelVersion: model.version
    modelSkuName: model.skuName
    modelCapacity: model.capacity
    tags: rootTags
  }
}]


module storage 'br/public:avm/res/storage/storage-account:0.9.1' = {
  name: 'storage'
  scope: rg
  params: {
    name: toLower('aist${replace(resourcePrefix, '-', '')}${uniqueSuffix}')
    location: location
    tags: tags
    kind: 'StorageV2'
    skuName: 'Standard_LRS'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    roleAssignments: [
      {
        principalId: deployer().objectId
        principalType: 'User'
        roleDefinitionIdOrName: 'Storage Blob Data Contributor'
      }
    ]
    blobServices: {
      containers: [
        {
          name: 'default'
          publicAccess: 'None'
        }
      ]
      cors: {
        corsRules: [
          {
          allowedOrigins: [
            'https://mlworkspace.azure.ai'
            'https://ml.azure.com'
            'https://*.ml.azure.com'
            'https://ai.azure.com'
            'https://*.ai.azure.com'
            'https://mlworkspacecanary.azure.ai'
            'https://mlworkspace.azureml-test.net'
          ]
          allowedMethods: [
            'GET'
            'HEAD'
            'POST'
            'PUT'
            'DELETE'
            'OPTIONS'
            'PATCH'
          ]
          maxAgeInSeconds: 1800
          exposedHeaders: [
            '*'
          ]
          allowedHeaders: [
            '*'
          ]
        }
      ]
    }
  }
  }
}


module hubBasedProject 'ai/ai-environment.bicep' = {
  name: 'ai'
  scope: rg
  params: {
    location: location
    tags: tags
    hubName: toLower('aihub-${resourcePrefix}-${uniqueSuffix}')
    projectName: toLower('aiproj-${resourcePrefix}-${uniqueSuffix}')
    applicationInsightsId: applicationInsights.outputs.applicationInsightsId
    storageAccountId: storage.outputs.resourceId
  }
}

module cohereRerank 'cohere-rerank-serverless.bicep' = if (deployCohereRerank) {
  name: 'cohere-rerank'
  scope: rg
  params: {
    projectName: hubBasedProject.outputs.projectName
    location: location
    tags: rootTags
  }
}

module postgresServer 'postgres.bicep' = {
  name: 'postgresql'
  scope: rg
  params: {
    name: '${resourcePrefix}-${uniqueSuffix}-postgresql'
    location: location
    tags: tags
    sku: {
      name: 'Standard_B1ms'
      tier: 'Burstable'
    }
    storage: {
      storageSizeGB: 32
    }
    version: '17'
    authType: 'EntraOnly'
    allowAzureIPsFirewall: true
    allowAllIPsFirewall: true // Necessary for post-provision script, can be disabled after
  }
}

// Grant PostgreSQL managed identity access to Azure OpenAI
module postgresOpenAIRole 'role.bicep' = {
  name: 'postgres-openai-role'
  scope: rg
  params: {
    principalId: postgresServer.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
  }
}

// Outputs
output subscriptionId string = subscription().subscriptionId
output resourceGroupName string = rg.name
output aiFoundryName string = foundry.outputs.accountName
output aiProjectName string = foundryProject.outputs.aiProjectName
output projectsEndpoint string = '${foundry.outputs.endpoint}api/projects/${foundryProject.outputs.aiProjectName}'
output azureOpenAIEndpoint string = foundry.outputs.openaiEndpoint
output deployedModels array = [for (model, index) in models: {
  name: model.name
  deploymentName: foundryModelDeployments[index].outputs.modelDeploymentName
}]
output applicationInsightsName string = applicationInsights.outputs.applicationInsightsName
output applicationInsightsConnectionString string = applicationInsights.outputs.connectionString
output applicationInsightsInstrumentationKey string = applicationInsights.outputs.instrumentationKey
output postgresServerFqdn string = postgresServer.outputs.domain
output postgresServerUsername string = postgresServer.outputs.username
output cohereRerankEndpointUri string = deployCohereRerank ? cohereRerank!.outputs.endpointUri : ''
output cohereRerankEndpointName string = deployCohereRerank ? cohereRerank!.outputs.endpointName : ''
output cohereWorkspaceProjectName string = hubBasedProject.outputs.projectName
