#!/usr/bin/dotnet run

#:package OpenAI@2.*

// Azure OpenAI GPT-5-mini - Responses API Example
// This demonstrates the new Responses API with GPT-5-mini reasoning model.

using System.ClientModel;

using OpenAI;
using OpenAI.Responses;

#pragma warning disable OPENAI001

// Run Responses API examples.
Console.WriteLine("Azure OpenAI GPT-5-mini - Responses API");
Console.WriteLine();

// Get required environment variables - throws InvalidOperationException if missing
var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT")
               ?? throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT environment variable is required");
var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY")
             ?? throw new InvalidOperationException("AZURE_OPENAI_API_KEY environment variable is required");

// Use ApiKeyCredential for API key authentication
var credential = new ApiKeyCredential(apiKey);
var clientOptions = new OpenAIClientOptions
{
    Endpoint = new Uri($"{endpoint.TrimEnd('/')}/openai/v1/")
};

// Initialize OpenAI Response client with Azure endpoint
var responseClient = new OpenAIResponseClient("gpt-5-mini", credential, clientOptions);
var responseCreationOptions = new ResponseCreationOptions
{
    MaxOutputTokenCount = 1000
};

// Example 1: Simple text input
Console.WriteLine("Example 1: Simple text input");
Console.WriteLine();

OpenAIResponse response1 = await responseClient.CreateResponseAsync(
    userInputText: "Explain quantum computing in simple terms",
    options: responseCreationOptions);

Console.WriteLine($"Response: {response1.GetOutputText()}");
Console.WriteLine($"Status: {response1.Status}");
Console.WriteLine($"Reasoning tokens: {response1.Usage.OutputTokenDetails.ReasoningTokenCount}");
Console.WriteLine($"Output tokens: {response1.Usage.OutputTokenCount}");
Console.WriteLine();

// Example 2: Conversation format
Console.WriteLine("Example 2: Conversation format");
Console.WriteLine();

var messages = new List<ResponseItem>
{
    ResponseItem.CreateSystemMessageItem("You are an Azure cloud architect."),
    ResponseItem.CreateUserMessageItem("Design a scalable web application architecture.")
};

OpenAIResponse response2 = await responseClient.CreateResponseAsync(
    inputItems: messages,
    options: responseCreationOptions);

Console.WriteLine($"Response: {response2.GetOutputText()}");
Console.WriteLine($"Status: {response2.Status}");
Console.WriteLine($"Reasoning tokens: {response2.Usage.OutputTokenDetails.ReasoningTokenCount}");
Console.WriteLine($"Output tokens: {response2.Usage.OutputTokenCount}");
Console.WriteLine();
