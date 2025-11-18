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

// Deploy the Azure OpenAI resource
module openai 'br/public:avm/res/cognitive-services/account:0.13.2' = {
  name: 'openai'
  params: {
    name: 'openai-${resourceToken}'
    location: location
    tags: {
      'azd-env-name': environmentName
    }
    kind: 'OpenAI'
    sku: sku
    customSubDomainName: 'openai-${resourceToken}'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
    // Allow key-based authentication
    // Should be disabled in production environments in favor of managed identities
    disableLocalAuth: false
    deployments: [
      {
        name: gptModelName
        model: {
          format: 'OpenAI'
          name: gptModelName
          version: gptModelVersion
        }
        sku: {
          name: 'GlobalStandard'
          capacity: gptCapacity
        }
      }
    ]
  }
}

// Outputs
output AZURE_OPENAI_ENDPOINT string = openai.outputs.endpoint
output AZURE_OPENAI_NAME string = openai.outputs.name
output AZURE_OPENAI_RESOURCE_ID string = openai.outputs.resourceId
output AZURE_OPENAI_GPT_DEPLOYMENT_NAME string = deployGptModel ? gptModelName : ''
