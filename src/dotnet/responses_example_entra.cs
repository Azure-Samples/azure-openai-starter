#!/usr/bin/dotnet run

#:package OpenAI@2.14.0
#:package Azure.Core@1.62.0
#:package Microsoft.Extensions.Hosting@10.0.10
#:property PublishAot=false

// Azure OpenAI GPT-6.1 Sol - Responses API with Entra Authentication
// This demonstrates using keyless authentication with Entra instead of API keys.

using Azure.Identity;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using OpenAI.Responses;

#pragma warning disable OPENAI001
#pragma warning disable SCME0002

// Run Responses API examples with Entra authentication.
Console.WriteLine("Azure OpenAI GPT-6.1 Sol - Entra Authentication");
Console.WriteLine();

var builder = Host.CreateApplicationBuilder(args);
var settings = builder.Configuration.GetSection("Clients:Responses");
if (settings["Options:Endpoint"] is null)
{
    var endpoint = builder.Configuration["AZURE_OPENAI_ENDPOINT"]
        ?? throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT environment variable is required");
    settings["Options:Endpoint"] = $"{endpoint.TrimEnd('/')}/openai/v1/";
}
settings["Credential:TenantId"] ??= builder.Configuration["AZURE_TENANT_ID"];
if (settings["Credential:CredentialSource"] is null)
{
    var selected = builder.Configuration["AZURE_TOKEN_CREDENTIALS"];
    if (!string.IsNullOrWhiteSpace(selected)
        && !string.Equals(selected, "dev", StringComparison.OrdinalIgnoreCase)
        && !string.Equals(selected, "prod", StringComparison.OrdinalIgnoreCase))
    {
        settings["Credential:CredentialSource"] = selected;
    }
    else
    {
        settings["Credential:CredentialSource"] = "ChainedTokenCredential";
        string[] sources = selected?.ToLowerInvariant() switch
        {
            "prod" => ["EnvironmentCredential", "WorkloadIdentityCredential", "ManagedIdentityCredential"],
            "dev" => ["AzureCliCredential", "AzureDeveloperCliCredential"],
            _ => ["EnvironmentCredential", "WorkloadIdentityCredential", "ManagedIdentityCredential",
                  "AzureCliCredential", "AzureDeveloperCliCredential"]
        };
        for (var index = 0; index < sources.Length; index++)
        {
            settings[$"Credential:Sources:{index}:CredentialSource"] = sources[index];
            settings[$"Credential:Sources:{index}:TenantId"] = settings["Credential:TenantId"];
        }
    }
}
if (string.Equals(settings["Credential:CredentialSource"], "ApiKeyCredential", StringComparison.OrdinalIgnoreCase)
    || string.Equals(settings["Credential:CredentialSource"], "ApiKey", StringComparison.OrdinalIgnoreCase))
{
    settings["Credential:Key"] ??= builder.Configuration["AZURE_OPENAI_API_KEY"]
        ?? throw new InvalidOperationException("AZURE_OPENAI_API_KEY environment variable is required");
}
settings["Credential:Scope"] ??= "https://cognitiveservices.azure.com/.default";

// Optional settings. GPT-6.1 Sol supports low, medium, high, xhigh and max reasoning effort.
var model = settings["Model"] ?? builder.Configuration["AZURE_OPENAI_GPT_DEPLOYMENT_NAME"] ?? "gpt-6.1-sol";
var effort = settings["ReasoningEffort"] ?? builder.Configuration["AZURE_OPENAI_REASONING_EFFORT"] ?? "medium";
if (effort is not ("low" or "medium" or "high" or "xhigh" or "max"))
    throw new InvalidOperationException("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max");
var tokens = settings["MaxOutputTokens"] ?? builder.Configuration["AZURE_OPENAI_MAX_OUTPUT_TOKENS"] ?? "16384";
if (!int.TryParse(tokens, out var maxOutputTokens)
    || maxOutputTokens < 16 || maxOutputTokens > 128000)
    throw new InvalidOperationException("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000");
Console.WriteLine($"Deployment: {model}; reasoning effort: {effort}");

CreateResponseOptions CreateOptions(IEnumerable<ResponseItem> input) => new(model, input)
{
    MaxOutputTokenCount = maxOutputTokens,
    ReasoningOptions = new ResponseReasoningOptions
    {
        ReasoningEffortLevel = new ResponseReasoningEffortLevel(effort)
    }
};

// Credential sources and their options are bound by the registered Azure resolver.
builder.AddAzureCredentialResolver();
builder.AddAzureClient<ResponsesClient, ResponsesClientSettings>("Clients:Responses");
using var host = builder.Build();
var responsesClient = host.Services.GetRequiredService<ResponsesClient>();

// Example 1: Simple text input with Responses API
Console.WriteLine("Example 1: Simple text input");
Console.WriteLine();

ResponseResult response1 = await responsesClient.CreateResponseAsync(CreateOptions(
    [ResponseItem.CreateUserMessageItem("Explain quantum computing in simple terms")]));
PrintResponse(response1);

// Example 2: Conversation format with Responses API
Console.WriteLine("Example 2: Conversation format");
Console.WriteLine();

var messages = new List<ResponseItem>
{
    ResponseItem.CreateSystemMessageItem("You are an Azure cloud architect."),
    ResponseItem.CreateUserMessageItem("Design a scalable web application architecture.")
};
ResponseResult response2 = await responsesClient.CreateResponseAsync(CreateOptions(messages));
PrintResponse(response2);

static void PrintResponse(ResponseResult response)
{
    if (response.Status != ResponseStatus.Completed)
        throw new InvalidOperationException($"Response did not complete: {response.Status}");
    var text = response.GetOutputText();
    if (string.IsNullOrWhiteSpace(text))
        throw new InvalidOperationException("Response completed without output text");
    if (response.Usage is null)
        throw new InvalidOperationException("Response completed without token usage");

    Console.WriteLine($"Response: {text}");
    Console.WriteLine($"Status: {response.Status}");
    Console.WriteLine($"Reasoning tokens: {response.Usage.OutputTokenDetails.ReasoningTokenCount}");
    Console.WriteLine($"Output tokens: {response.Usage.OutputTokenCount}");
    Console.WriteLine();
}
