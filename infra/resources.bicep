// Resources for Azure OpenAI template

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Unique token for resource naming')
param resourceToken string

@description('Environment name for tagging')
param environmentName string

@description('The SKU for the Azure OpenAI resource')
@allowed(['S0'])
param sku string = 'S0'

@description('Deploy GPT model automatically')
param deployGptModel bool = true

@description('GPT model to deploy')
param gptModelName string = 'gpt-5-mini'

@description('GPT model version')
param gptModelVersion string = '2025-08-07'

@description('GPT deployment capacity')
param gptCapacity int = 10

// Azure OpenAI resource
resource openAiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: 'openai-${resourceToken}'
  location: location
  kind: 'OpenAI'
  properties: {
    customSubDomainName: 'openai-${resourceToken}'
    publicNetworkAccess: 'Enabled'
  }
  sku: {
    name: sku
  }
  tags: {
    'azd-env-name': environmentName
  }
}

// GPT Model Deployment
resource gptModelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = if (deployGptModel) {
  name: 'gpt-5-mini'
  parent: openAiAccount
  properties: {
    model: {
      format: 'OpenAI'
      name: gptModelName
      version: gptModelVersion
    }
  }
  sku: {
    name: 'GlobalStandard'
    capacity: gptCapacity
  }
}

// Outputs
output AZURE_OPENAI_ENDPOINT string = openAiAccount.properties.endpoint
output AZURE_OPENAI_NAME string = openAiAccount.name
output AZURE_OPENAI_RESOURCE_ID string = openAiAccount.id
output AZURE_OPENAI_GPT_DEPLOYMENT_NAME string = deployGptModel ? gptModelDeployment.name : ''
