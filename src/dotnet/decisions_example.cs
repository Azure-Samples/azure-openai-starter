#!/usr/bin/dotnet run

#:package OpenAI@2.15.0
#:package Azure.Core@1.62.0
#:package Microsoft.Extensions.Hosting@10.0.10
#:property PublishAot=false

// Azure OpenAI GPT-6 Luna - Decisions API Example
// Classifies a support request, or a photo, with the typed OpenAI DecisionsClient.

using Azure.Identity;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using OpenAI;
using OpenAI.Decisions;

#pragma warning disable OPENAI001 // The OpenAI Decisions API is experimental.
#pragma warning disable SCME0002 // System.ClientModel configuration/DI APIs (AddDecisionsClient, the Azure credential resolver) are experimental; the opt-in is intentional.

var imageUrl = ImageInput(args);
var builder = Host.CreateApplicationBuilder();
var settings = builder.Configuration.GetSection("Clients:Decisions");
if (settings["Options:Endpoint"] is null)
{
    var resourceEndpoint = builder.Configuration["AZURE_OPENAI_ENDPOINT"];
    if (string.IsNullOrWhiteSpace(resourceEndpoint))
        throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT environment variable is required");
    settings["Options:Endpoint"] = $"{resourceEndpoint.TrimEnd('/')}/openai/v1/";
}
settings["Credential:TenantId"] ??= builder.Configuration["AZURE_TENANT_ID"];
// Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
if (settings["Credential:CredentialSource"] is null)
{
    var apiKey = builder.Configuration["AZURE_OPENAI_API_KEY"];
    if (!string.IsNullOrEmpty(apiKey))
    {
        settings["Credential:CredentialSource"] = "ApiKeyCredential";
        settings["Credential:Key"] = apiKey;
    }
    else
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
}
settings["Credential:Scope"] ??= "https://cognitiveservices.azure.com/.default";
var endpoint = settings["Options:Endpoint"];
var useKey = string.Equals(settings["Credential:CredentialSource"], "ApiKeyCredential", StringComparison.OrdinalIgnoreCase)
    || string.Equals(settings["Credential:CredentialSource"], "ApiKey", StringComparison.OrdinalIgnoreCase);
if (useKey)
    settings["Credential:Key"] ??= builder.Configuration["AZURE_OPENAI_API_KEY"];
if (useKey && string.IsNullOrEmpty(settings["Credential:Key"]))
    throw new InvalidOperationException("Clients:Decisions:Credential:Key is required for ApiKeyCredential");
if (!Uri.TryCreate(endpoint, UriKind.Absolute, out var uri)
    || string.IsNullOrEmpty(uri.Host) || !string.IsNullOrEmpty(uri.UserInfo)
    || !string.IsNullOrEmpty(uri.Query) || !string.IsNullOrEmpty(uri.Fragment)
    || uri.AbsolutePath.Trim('/') != "openai/v1")
    throw new InvalidOperationException("Configure an Azure resource root URL or Clients:Decisions:Options:Endpoint ending in /openai/v1/");
if (uri.Scheme != Uri.UriSchemeHttps && !(uri.Scheme == Uri.UriSchemeHttp && uri.IsLoopback && useKey))
    throw new InvalidOperationException(
        "AZURE_OPENAI_ENDPOINT must use HTTPS (HTTP loopback is allowed with an API key)");
// Azure deployment name; it must point to GPT-6 Luna.
var model = settings["Model"] ?? builder.Configuration["AZURE_OPENAI_DEPLOYMENT"] ?? "gpt-6-luna";
if (string.IsNullOrWhiteSpace(model))
    throw new InvalidOperationException("AZURE_OPENAI_DEPLOYMENT must not be empty");

// Bind endpoint, pipeline options, and credentials from configuration; reuse the DI singleton.
builder.AddAzureCredentialResolver();
builder.AddDecisionsClient("Clients:Decisions");
using var host = builder.Build();
var decisionsClient = host.Services.GetRequiredService<DecisionsClient>();

var (input, questions) = imageUrl is null ? TextScenario() : PhotoScenario(imageUrl);

// Batch all three questions in one call; the service accepts up to 400.
// [START decisions_request]
DecisionCreationOptions options = new(input, model, questions);
DecisionResource decision = await decisionsClient.CreateDecisionAsync(options);
// [END decisions_request]

PrintDecision(decision);

// Scenario 1: route a billing ticket (text input).
static (List<DecisionsItem> Input, List<DecisionsQuestion> Questions) TextScenario() => (
    [
        new DecisionsUserMessageItem(
        [
            new DecisionsInputTextContentPart("I was charged twice for order 123. Please refund the duplicate charge.")
        ])
    ],
    [
        new DecisionsPredicateQuestion(
            [new DecisionsInputTextInstructionsPart("Does the customer request a refund?")])
        {
            Name = "refund_requested"
        },
        new DecisionsChoiceQuestion(
            [
                new DecisionsChoice("billing") { Description = "Payments and refunds." },
                new DecisionsChoice("technical") { Description = "Product problems." },
                new DecisionsChoice("other") { Description = "Other requests." }
            ],
            [new DecisionsInputTextInstructionsPart("Which department should handle this request?")])
        {
            Name = "department"
        },
        new DecisionsScoreQuestion(
            [new DecisionsInputTextInstructionsPart("How severe is this issue?")],
            [
                new DecisionsScoreLevel("Low") { Description = "Minor inconvenience." },
                new DecisionsScoreLevel("Medium") { Description = "Needs attention." },
                new DecisionsScoreLevel("High") { Description = "Urgent action needed." }
            ])
        {
            Name = "severity"
        }
    ]);

// Scenario 2: assess a photo (an HTTPS URL or an inline base64 data URL).
static (List<DecisionsItem> Input, List<DecisionsQuestion> Questions) PhotoScenario(string imageUrl) => (
    [
        new DecisionsUserMessageItem(
        [
            new DecisionsInputTextContentPart("Inspect the photo for visible damage and classify the main object."),
            new DecisionsInputImageContentPart(imageUrl)
        ])
    ],
    [
        new DecisionsPredicateQuestion(
            [new DecisionsInputTextInstructionsPart("Does the photo show visible damage to the main object?")])
        {
            Name = "visible_damage"
        },
        new DecisionsChoiceQuestion(
            [
                new DecisionsChoice("parcel") { Description = "A package or parcel." },
                new DecisionsChoice("vehicle") { Description = "A vehicle." },
                new DecisionsChoice("other") { Description = "None of these categories." }
            ],
            [new DecisionsInputTextInstructionsPart("Which category best describes the main object?")])
        {
            Name = "category"
        },
        new DecisionsScoreQuestion(
            [new DecisionsInputTextInstructionsPart("How severe is the visible damage?")],
            [
                new DecisionsScoreLevel("Low") { Description = "No damage or minor cosmetic damage." },
                new DecisionsScoreLevel("Medium") { Description = "Visible damage that needs attention." },
                new DecisionsScoreLevel("High") { Description = "Severe damage or loss of function." }
            ])
        {
            Name = "severity"
        }
    ]);

static void PrintDecision(DecisionResource decision)
{
    if (decision.Answers.Count == 0)
        throw new InvalidDataException("Decision returned no answers");
    if (decision.Usage is not { } usage)
        throw new InvalidDataException("Decision returned no token usage");

    // Any question can return a refusal instead of an answer, so match on the answer type
    // rather than casting every answer to a predicate.
    foreach (var answer in decision.Answers)
    {
        switch (answer)
        {
            case DecisionsPredicateAnswer predicate:
                Console.WriteLine($"{predicate.Name} (predicate): probability={predicate.Probability}");
                break;
            case DecisionsChoiceAnswer choice:
                var choices = choice.Probabilities.Select(item =>
                    $"{{value={ChoiceText(item.Value)}; probability={item.Probability}}}");
                Console.WriteLine($"{choice.Name} (choice): value={ChoiceText(choice.Choice)}; "
                    + $"confidence={choice.Confidence}; probabilities=[{string.Join(", ", choices)}]");
                break;
            case DecisionsScoreAnswer score:
                var levels = score.Probabilities.Select(item =>
                    $"{{label={item.Label}; value={item.Value}; probability={item.Probability}}}");
                Console.WriteLine($"{score.Name} (score): score={score.Score}; "
                    + $"confidence={score.Confidence}; probabilities=[{string.Join(", ", levels)}]");
                break;
            case DecisionsRefusalAnswer refusal:
                Console.WriteLine($"{refusal.Name} (refusal): send this question for human review");
                break;
            default:
                throw new InvalidDataException($"Unexpected decision answer type: {answer.Kind}");
        }
    }

    var line = $"Usage: input_tokens={usage.InputTokenCount}; output_tokens={usage.OutputTokenCount}; "
        + $"total_tokens={usage.TotalTokenCount}";
    if (usage.InputTokenDetails is { } inputDetails)
        line += $"; cached_tokens={inputDetails.CachedTokenCount}; cache_write_tokens={inputDetails.CacheWriteTokenCount}";
    if (usage.OutputTokenDetails is { } outputDetails)
        line += $"; reasoning_tokens={outputDetails.ReasoningTokenCount}";
    Console.WriteLine(line);
}

// A choice is a string or a boolean, and DecisionsChoiceValue has no ToString() or equality.
// Read the active component instead of formatting or comparing the wrapper object. The typed
// client does not require a value, so reject a response without one instead of printing nothing.
static string ChoiceText(DecisionsChoiceValue? value) =>
    value is null
        ? throw new InvalidDataException("Choice answer has no value")
        : value.StringValue ?? value.BooleanValue?.ToString().ToLowerInvariant() ?? string.Empty;

static string? ImageInput(string[] args)
{
    if (args.Length == 0)
        return null;
    if (args.Length != 2 || args[0] != "--image" || string.IsNullOrWhiteSpace(args[1]))
        throw new ArgumentException("Usage: dotnet run decisions_example.cs -- [--image PATH_OR_HTTPS_URL]");
    var source = args[1];
    if (source.Contains("://", StringComparison.Ordinal))
    {
        if (!Uri.TryCreate(source, UriKind.Absolute, out var image) || image.Scheme != Uri.UriSchemeHttps
            || string.IsNullOrEmpty(image.Host) || !string.IsNullOrEmpty(image.UserInfo)
            || source.Contains('#'))
            throw new ArgumentException("Image URL must use HTTPS with a host, no credentials, and no fragment");
        return source;
    }
    var mime = Path.GetExtension(source).ToLowerInvariant() switch
    {
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".webp" => "image/webp",
        ".gif" => "image/gif",
        _ => throw new ArgumentException("Image file must be PNG, JPEG, WebP, or GIF")
    };
    const int maxBytes = 32 * 1024 * 1024;
    if (!File.Exists(source))
        throw new ArgumentException("Image file must exist and be a readable regular file");
    try
    {
        using var file = File.OpenRead(source);
        var size = file.Length;
        if (size <= 0 || size > maxBytes)
            throw new ArgumentException("Image file must be nonempty and at most 32 MiB");
        var data = new byte[(int)size];
        file.ReadExactly(data);
        if (file.ReadByte() != -1)
            throw new ArgumentException("Image file changed while reading; try again");
        return $"data:{mime};base64,{Convert.ToBase64String(data)}";
    }
    catch (IOException)
    {
        throw new ArgumentException("Image file must exist and be readable");
    }
    catch (UnauthorizedAccessException)
    {
        throw new ArgumentException("Image file must exist and be readable");
    }
}
