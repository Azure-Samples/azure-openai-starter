#!/usr/bin/dotnet run

#:package OpenAI@2.15.0
#:package Azure.Core@1.62.0
#:package Microsoft.Extensions.Hosting@10.0.10
#:property PublishAot=false

// Azure OpenAI GPT-6 Luna - Decisions API Example
// Assesses a photo (text and image input) with the typed OpenAI DecisionsClient.

using Azure.Identity;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using OpenAI;
using OpenAI.Decisions;

#pragma warning disable OPENAI001 // The OpenAI Decisions API is experimental.
#pragma warning disable SCME0002 // System.ClientModel configuration/DI APIs (AddDecisionsClient, the Azure credential resolver) are experimental; the opt-in is intentional.

// A public-domain NASA photo. Azure fetches an HTTPS URL itself.
const string DefaultImage = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png";

var builder = Host.CreateApplicationBuilder();

// Map the starter's environment variables onto the Clients:Decisions settings.
// Anything already configured there (appsettings.json or Clients__Decisions__* variables) wins.
var settings = builder.Configuration.GetSection("Clients:Decisions");
if (settings["Options:Endpoint"] is null)
{
    var endpoint = builder.Configuration["AZURE_OPENAI_ENDPOINT"]
        ?? throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT environment variable is required");
    settings["Options:Endpoint"] = $"{endpoint.TrimEnd('/')}/openai/v1/";
}
// The SDK ignores an endpoint that is not an absolute URL and falls back to api.openai.com.
if (!Uri.TryCreate(settings["Options:Endpoint"], UriKind.Absolute, out var endpointUri)
    || endpointUri.Scheme is not ("http" or "https"))
    throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT must be an absolute URL using HTTP or HTTPS.");
settings["Credential:TenantId"] ??= builder.Configuration["AZURE_TENANT_ID"];
settings["Credential:Scope"] ??= "https://cognitiveservices.azure.com/.default";
if (settings["Credential:CredentialSource"] is null)
{
    // Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
    if (builder.Configuration["AZURE_OPENAI_API_KEY"] is { Length: > 0 } apiKey)
    {
        settings["Credential:CredentialSource"] = "ApiKeyCredential";
        settings["Credential:Key"] = apiKey;
    }
    else
    {
        // Use your `azd auth login` session.
        settings["Credential:CredentialSource"] = "AzureDeveloperCliCredential";
    }
}
// This is your Azure deployment name; the deployment must host gpt-6-luna.
var model = settings["Model"] ?? builder.Configuration["AZURE_OPENAI_DEPLOYMENT"] ?? "gpt-6-luna";

// Bind endpoint, pipeline options, and credentials from configuration; reuse the DI singleton.
builder.AddAzureCredentialResolver();
builder.AddDecisionsClient("Clients:Decisions");
using var host = builder.Build();
var decisionsClient = host.Services.GetRequiredService<DecisionsClient>();

// Pass your own HTTPS image URL or the path to an image file.
var image = args.Length > 0 ? args[0] : DefaultImage;
if (!image.StartsWith("https://", StringComparison.Ordinal))
{
    // A local file is sent inline as a base64 data URL.
    var mediaType = Path.GetExtension(image).ToLowerInvariant() switch
    {
        ".png" => "image/png",
        ".jpg" or ".jpeg" => "image/jpeg",
        ".webp" => "image/webp",
        ".gif" => "image/gif",
        _ => throw new ArgumentException("Use a PNG, JPEG, WebP or GIF image file.")
    };
    image = $"data:{mediaType};base64,{Convert.ToBase64String(File.ReadAllBytes(image))}";
}

List<DecisionsItem> inputItems =
[
    new DecisionsUserMessageItem(
    [
        new DecisionsInputTextContentPart("Inspect the photo for visible damage and classify the main object."),
        new DecisionsInputImageContentPart(image)
    ])
];

// Batch related questions in one request; the service accepts at most 400.
List<DecisionsQuestion> questions =
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
];

// [START decisions_request]
DecisionCreationOptions options = new(inputItems, model, questions);
DecisionResource decision = await decisionsClient.CreateDecisionAsync(options);
// [END decisions_request]

if (decision.Answers.Count == 0)
    throw new InvalidDataException("The response contains no answers.");
var usage = decision.Usage ?? throw new InvalidDataException("The response contains no usage.");

// Any question can return a refusal instead of an answer, so match on the answer type.
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
            throw new InvalidDataException($"The response contains an unknown answer type: {answer.Kind}.");
    }
}
Console.WriteLine($"Usage: input_tokens={usage.InputTokenCount}; output_tokens={usage.OutputTokenCount}; "
    + $"total_tokens={usage.TotalTokenCount}; cached_tokens={usage.InputTokenDetails?.CachedTokenCount}; "
    + $"cache_write_tokens={usage.InputTokenDetails?.CacheWriteTokenCount}; "
    + $"reasoning_tokens={usage.OutputTokenDetails?.ReasoningTokenCount}");

// A choice is a string or a boolean, and DecisionsChoiceValue has no ToString() or equality.
// Read the active component; quotes tell a string from a boolean.
static string ChoiceText(DecisionsChoiceValue? value) =>
    value?.StringValue is { } text ? $"\"{text}\""
    : value?.BooleanValue is { } flag ? (flag ? "true" : "false")
    : throw new InvalidDataException("A choice must be a string or a boolean.");
