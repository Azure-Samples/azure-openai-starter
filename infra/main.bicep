// Minimal Azure OpenAI resource deployment for Azure Developer CLI
targetScope = 'resourceGroup'

@description('Environment name for tagging')
@minLength(1)
@maxLength(64)
param environmentName string

@description('Primary location; defaults to East US. Check the current model/SKU region table before changing. Decisions is excluded in East US 2: https://aka.ms/foundrydecisionsapi')
@metadata({
  azd: {
    type: 'location'
  }
})
param location string = 'eastus'

@description('Unique token for resource naming')
param resourceToken string = toLower(uniqueString(subscription().id, environmentName, location))

@description('Principal ID of the deploying user. azd populates this automatically.')
param principalId string = ''

@description('GPT deployment capacity in thousands of tokens per minute. Subject to regional subscription quota.')
@minValue(1)
param gptCapacity int = 10

@description('Also deploy GPT-6 Luna for the Decisions API. Check regional rollout and subscription quota before enabling.')
param deployDecisionsModel bool = false

@description('GPT-6 Luna version. Check the current model catalog before overriding.')
param decisionsModelVersion string = '2026-09-22'

@description('Prefer DataZoneStandard where supported; choose GlobalStandard when required by availability or quota.')
@allowed(['DataZoneStandard', 'GlobalStandard'])
param decisionsDeploymentSku string = 'DataZoneStandard'

@description('Decisions deployment capacity in thousands of tokens per minute. Billed separately from the Responses deployment.')
@minValue(1)
param decisionsCapacity int = 10

// Deploy the Azure OpenAI resource
module openai 'resources.bicep' = {
  name: 'openai'
  params: {
    location: location
    resourceToken: resourceToken
    environmentName: environmentName
    deployGptModel: true
    gptModelName: 'gpt-6.1-sol'
    gptModelVersion: '2026-09-29'
    gptCapacity: gptCapacity
    deployDecisionsModel: deployDecisionsModel
    decisionsModelVersion: decisionsModelVersion
    decisionsDeploymentSku: decisionsDeploymentSku
    decisionsCapacity: decisionsCapacity
    principalId: principalId
  }
}

// Outputs that azd expects
output AZURE_LOCATION string = location
output AZURE_OPENAI_ENDPOINT string = openai.outputs.AZURE_OPENAI_ENDPOINT
output AZURE_OPENAI_NAME string = openai.outputs.AZURE_OPENAI_NAME
output AZURE_OPENAI_RESOURCE_ID string = openai.outputs.AZURE_OPENAI_RESOURCE_ID
output AZURE_OPENAI_GPT_DEPLOYMENT_NAME string = openai.outputs.AZURE_OPENAI_GPT_DEPLOYMENT_NAME
output AZURE_OPENAI_DEPLOYMENT string = openai.outputs.AZURE_OPENAI_DEPLOYMENT
