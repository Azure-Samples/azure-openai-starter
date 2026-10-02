#!/usr/bin/dotnet run

#:package OpenAI@2.13.0

// Azure OpenAI GPT-6.1 Sol - Responses API Example
// This demonstrates the Responses API with the GPT-6.1 Sol reasoning model.

using System.ClientModel;
using System.Globalization;

using OpenAI;
using OpenAI.Responses;

#pragma warning disable OPENAI001

// Run Responses API examples.
Console.WriteLine("Azure OpenAI GPT-6.1 Sol - Responses API");
Console.WriteLine();

// Get required environment variables - throws InvalidOperationException if missing
var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT")
               ?? throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT environment variable is required");
var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY")
             ?? throw new InvalidOperationException("AZURE_OPENAI_API_KEY environment variable is required");
if (string.IsNullOrWhiteSpace(endpoint) || string.IsNullOrWhiteSpace(apiKey))
    throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must not be empty");

var model = Environment.GetEnvironmentVariable("AZURE_OPENAI_GPT_DEPLOYMENT_NAME") ?? "gpt-6.1-sol";
if (string.IsNullOrWhiteSpace(model))
    throw new InvalidOperationException("AZURE_OPENAI_GPT_DEPLOYMENT_NAME must not be empty");
var effort = Environment.GetEnvironmentVariable("AZURE_OPENAI_REASONING_EFFORT") ?? "medium";
if (effort is not ("low" or "medium" or "high" or "xhigh" or "max"))
    throw new InvalidOperationException("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max");
var tokens = Environment.GetEnvironmentVariable("AZURE_OPENAI_MAX_OUTPUT_TOKENS") ?? "16384";
if (!int.TryParse(tokens, NumberStyles.None, CultureInfo.InvariantCulture, out var maxOutputTokens)
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

// Use ApiKeyCredential for API key authentication
var credential = new ApiKeyCredential(apiKey);
var clientOptions = new ResponsesClientOptions
{
    Endpoint = new Uri($"{endpoint.TrimEnd('/')}/openai/v1/")
};

// Initialize OpenAI Response client with Azure endpoint
var responsesClient = new ResponsesClient(credential, clientOptions);

// Example 1: Simple text input
Console.WriteLine("Example 1: Simple text input");
Console.WriteLine();

ResponseResult response1 = await responsesClient.CreateResponseAsync(CreateOptions(
    [ResponseItem.CreateUserMessageItem("Explain quantum computing in simple terms in at most 150 words.")]));
PrintResponse(response1);

// Example 2: Conversation format
Console.WriteLine("Example 2: Conversation format");
Console.WriteLine();

var messages = new List<ResponseItem>
{
    ResponseItem.CreateSystemMessageItem("You are an Azure cloud architect."),
    ResponseItem.CreateUserMessageItem("Design a scalable web application architecture in at most 150 words.")
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
