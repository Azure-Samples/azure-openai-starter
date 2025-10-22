// Minimal Azure OpenAI resource deployment for Azure Developer CLI
targetScope = 'resourceGroup'

@description('Environment name for tagging')
@minLength(1)
@maxLength(64)
param environmentName string

@description('Primary location for all resources')
param location string = resourceGroup().location

@description('Unique token for resource naming')
param resourceToken string = toLower(uniqueString(subscription().id, environmentName, location))

// Deploy the Azure OpenAI resource
module openai 'resources.bicep' = {
  name: 'openai'
  params: {
    location: location
    resourceToken: resourceToken
    environmentName: environmentName
    deployGptModel: true
    gptModelName: 'gpt-5-mini'
    gptModelVersion: '2025-08-07'
    gptCapacity: 10
  }
}

// Outputs that azd expects
output AZURE_OPENAI_ENDPOINT string = openai.outputs.AZURE_OPENAI_ENDPOINT
output AZURE_OPENAI_NAME string = openai.outputs.AZURE_OPENAI_NAME
output AZURE_OPENAI_RESOURCE_ID string = openai.outputs.AZURE_OPENAI_RESOURCE_ID
output AZURE_OPENAI_GPT_DEPLOYMENT_NAME string = openai.outputs.AZURE_OPENAI_GPT_DEPLOYMENT_NAME
