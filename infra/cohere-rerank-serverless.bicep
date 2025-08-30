@description('Name of the hub-based project (workspace) where the serverless endpoint will be created')
param projectName string

@description('Azure location for the serverless endpoint (should match the project / supported regions)')
param location string = resourceGroup().location

param tags object = {}

@description('Model ID for Cohere Rerank v3.5. Validate in the Azure AI Foundry model catalog.')
param modelId string = 'azureml://registries/azureml-cohere/models/Cohere-rerank-v3.5'

var modelName = substring(modelId, (lastIndexOf(modelId, '/') + 1))
var sanitizedModelName = replace(modelName, '.', '')
// Subscription name can only contain alphanumeric characters, dashes, and underscores, with a limit of 255 characters.
var subscriptionName = '${sanitizedModelName}-subscription'

// Endpoint Resource name is invalid. Resource name can only contain alphanumeric characters, dashes, with a limit of 52 characters.
var endpointName = '${sanitizedModelName}-endpoint'

// Existing project (workspace)
resource project 'Microsoft.MachineLearningServices/workspaces@2024-01-01-preview' existing = {
  name: projectName
}

// Subscribe the project to the marketplace/partner model offer
resource modelSubscription 'Microsoft.MachineLearningServices/workspaces/marketplaceSubscriptions@2024-04-01-preview' = {
  name: subscriptionName
  parent: project
  properties: {
    modelId: modelId
  }
}

// Create the serverless endpoint (consumption based)
resource rerankEndpoint 'Microsoft.MachineLearningServices/workspaces/serverlessEndpoints@2024-04-01-preview' = {
  name: endpointName
  parent: project
  location: location
  tags: tags
  sku: {
    name: 'Consumption'
  }
  properties: {
    modelSettings: {
      modelId: modelId
    }
  }
  dependsOn: [
    modelSubscription
  ]
}

output endpointName string = rerankEndpoint.name
output endpointUri string = rerankEndpoint.properties.inferenceEndpoint.uri
output modelSubscriptionName string = modelSubscription.name
