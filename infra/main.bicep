// Minimal Azure OpenAI resource deployment for Azure Developer CLI
targetScope = 'resourceGroup'

@description('Environment name for tagging')
@minLength(1)
@maxLength(64)
param environmentName string

@description('Primary location for all resources')
@allowed([
  // Regions where gpt-5-mini is available,
  // see https://learn.microsoft.com/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure?pivots=azure-openai&tabs=global-standard-aoai%2Cstandard-chat-completions%2Cglobal-standard#global-standard-model-availability
  'australiaeast'
  'eastus'
  'eastus2'
  'japaneast'
  'koreacentral'
  'sounthindia'
  'swedencentral'
  'switzerlandnorth'
  'uksouth'
])
@metadata({
  azd: {
    type: 'location'
  }
})
param location string

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
output AZURE_LOCATION string = location
output AZURE_OPENAI_ENDPOINT string = openai.outputs.AZURE_OPENAI_ENDPOINT
output AZURE_OPENAI_NAME string = openai.outputs.AZURE_OPENAI_NAME
output AZURE_OPENAI_RESOURCE_ID string = openai.outputs.AZURE_OPENAI_RESOURCE_ID
output AZURE_OPENAI_GPT_DEPLOYMENT_NAME string = openai.outputs.AZURE_OPENAI_GPT_DEPLOYMENT_NAME
