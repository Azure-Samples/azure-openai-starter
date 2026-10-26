#!/usr/bin/dotnet run

#:package Azure.Core@1.62.0
#:package Microsoft.Extensions.Hosting@10.0.10
#:package Microsoft.Extensions.Http@10.0.10
#:property PublishAot=false

using System.Net.Http.Headers;
using System.ClientModel.Primitives;
using System.Text.Json;

using Azure.Core;
using Azure.Identity;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

#pragma warning disable SCME0002

var imageUrl = ImageInput(args);
var withImage = imageUrl is not null;
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
var predicateName = withImage ? "visible_damage" : "refund_requested";
var choiceName = withImage ? "category" : "department";

builder.AddAzureCredentialResolver();
builder.Services.AddSingleton(services => builder.Configuration.GetAzureCredentialSettings(
    "Clients:Decisions:Credential", services.GetServices<CredentialResolver>().ToArray())
    ?? throw new InvalidOperationException("Clients:Decisions:Credential is required"));
builder.Services.AddHttpClient("Decisions", client =>
{
    client.BaseAddress = new Uri($"{uri.AbsoluteUri.TrimEnd('/')}/");
    client.Timeout = TimeSpan.Parse(settings["Options:NetworkTimeout"] ?? "00:01:40");
}).ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler { AllowAutoRedirect = false });
using var host = builder.Build();
var credentials = host.Services.GetRequiredService<CredentialSettings>();
using var httpClient = host.Services.GetRequiredService<IHttpClientFactory>().CreateClient("Decisions");

// Interim REST sample: OpenAI .NET 2.14.0 has no typed Decisions client.
// TODO: Switch to the typed client when a stable SDK exposes Decisions.
object input = "I was charged twice for order 123. Please refund the duplicate charge.";
if (withImage)
{
    input = new[]
    {
        new
        {
            role = "user",
            content = new object[]
            {
                new { type = "input_text", text = "Inspect the photo for visible damage and classify the main object." },
                new { type = "input_image", image_url = imageUrl }
            }
        }
    };
}
// Batch all three questions in one call.
// [START decisions_request]
var payload = new
{
    model,
    input,
    questions = new object[]
    {
        new
        {
            type = "predicate",
            name = predicateName,
            instructions = withImage
                ? "Does the photo show visible damage to the main object?"
                : "Does the customer request a refund?"
        },
        new
        {
            type = "choice",
            name = choiceName,
            instructions = withImage
                ? "Which category best describes the main object?"
                : "Which department should handle this request?",
            choices = new[]
            {
                new { value = withImage ? "parcel" : "billing",
                    description = withImage ? "A package or parcel." : "Payments and refunds." },
                new { value = withImage ? "vehicle" : "technical",
                    description = withImage ? "A vehicle." : "Product problems." },
                new { value = "other",
                    description = withImage ? "None of these categories." : "Other requests." }
            }
        },
        new
        {
            type = "score",
            name = "severity",
            instructions = withImage ? "How severe is the visible damage?" : "How severe is this issue?",
            levels = new[]
            {
                new { label = "Low",
                    description = withImage ? "No damage or minor cosmetic damage." : "Minor inconvenience." },
                new { label = "Medium",
                    description = withImage ? "Visible damage that needs attention." : "Needs attention." },
                new { label = "High",
                    description = withImage ? "Severe damage or loss of function." : "Urgent action needed." }
            }
        }
    }
};
using var request = new HttpRequestMessage(HttpMethod.Post, "decisions");
if (useKey)
    request.Headers.Add("api-key", credentials.Key);
else
{
    if (credentials.TokenProvider is not TokenCredential credential)
        throw new InvalidOperationException("Configured credential source did not resolve to an Azure token credential");
    var scope = settings["Credential:Scope"]
        ?? throw new InvalidOperationException("Clients:Decisions:Credential:Scope is required");
    var token = await credential.GetTokenAsync(new TokenRequestContext([scope]), CancellationToken.None);
    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token.Token);
}
request.Content = new StringContent(JsonSerializer.Serialize(payload), System.Text.Encoding.UTF8, "application/json");
using var response = await httpClient.SendAsync(request);
// [END decisions_request]

var responseBody = await response.Content.ReadAsStringAsync();
if (!response.IsSuccessStatusCode)
    throw new HttpRequestException(
        $"Decisions HTTP {(int)response.StatusCode} {response.ReasonPhrase}: {responseBody}",
        null, response.StatusCode);
using var document = JsonDocument.Parse(responseBody);
var root = document.RootElement;
RequiredString(root, "model");
var answers = Required(root, "answers", JsonValueKind.Array);
if (answers.GetArrayLength() == 0)
    throw new InvalidDataException("Decisions response has empty answers");
var usage = Required(root, "usage", JsonValueKind.Object);
var inputTokens = RequiredInteger(usage, "input_tokens");
var outputTokens = RequiredInteger(usage, "output_tokens");
var totalTokens = RequiredInteger(usage, "total_tokens");

var lines = new List<string>();
var expectedNames = new HashSet<string>([predicateName, choiceName, "severity"], StringComparer.Ordinal);
var seen = new HashSet<string>(StringComparer.Ordinal);
foreach (var answer in answers.EnumerateArray())
{
    var rawName = RequiredString(answer, "name");
    var name = JsonSerializer.Serialize(rawName);
    if (!expectedNames.Contains(rawName))
        throw new InvalidDataException($"Decisions response has an unknown answer name: {name}");
    if (!seen.Add(rawName))
        throw new InvalidDataException($"Decisions response has a duplicate answer: {name}");
    var type = RequiredString(answer, "type");
    switch (type)
    {
        case "predicate":
            lines.Add($"{name} (predicate): probability={RequiredNumber(answer, "probability", unit: true)}");
            break;
        case "choice":
            var choice = RequiredChoice(answer, "choice");
            var confidence = RequiredNumber(answer, "confidence", unit: true);
            var choiceProbabilities = Required(answer, "probabilities", JsonValueKind.Array);
            if (choiceProbabilities.GetArrayLength() == 0)
                throw new InvalidDataException($"Choice answer {name} is missing probabilities");
            var choiceOptions = new List<string>();
            foreach (var item in choiceProbabilities.EnumerateArray())
            {
                var value = RequiredChoice(item, "value");
                var chance = RequiredNumber(item, "probability", unit: true);
                choiceOptions.Add($"{{value={value}; probability={chance}}}");
            }
            lines.Add($"{name} (choice): value={choice}; confidence={confidence}; "
                + $"probabilities=[{string.Join(", ", choiceOptions)}]");
            break;
        case "score":
            var score = RequiredNumber(answer, "score");
            var scoreConfidence = RequiredNumber(answer, "confidence", unit: true);
            var scoreProbabilities = Required(answer, "probabilities", JsonValueKind.Array);
            if (scoreProbabilities.GetArrayLength() == 0)
                throw new InvalidDataException($"Score answer {name} is missing probabilities");
            var scoreOptions = new List<string>();
            foreach (var item in scoreProbabilities.EnumerateArray())
            {
                var label = JsonSerializer.Serialize(RequiredString(item, "label"));
                var value = RequiredInteger(item, "value");
                var chance = RequiredNumber(item, "probability", unit: true);
                scoreOptions.Add($"{{label={label}; value={value}; probability={chance}}}");
            }
            lines.Add($"{name} (score): score={score}; confidence={scoreConfidence}; "
                + $"probabilities=[{string.Join(", ", scoreOptions)}]");
            break;
        case "refusal":
            lines.Add($"{name} (refusal): refused");
            break;
        default:
            throw new InvalidDataException($"Unknown Decisions answer type: {JsonSerializer.Serialize(type)}");
    }
}
foreach (var expected in expectedNames)
    if (!seen.Contains(expected))
        throw new InvalidDataException($"Decisions response is missing answer: {expected}");
var usageLine = $"Usage: input_tokens={inputTokens}; output_tokens={outputTokens}; total_tokens={totalTokens}";
if (usage.TryGetProperty("input_tokens_details", out var inputDetails))
{
    if (inputDetails.ValueKind != JsonValueKind.Object)
        throw new InvalidDataException("Decisions response has invalid input_tokens_details");
    foreach (var field in new[] { "cached_tokens", "cache_write_tokens" })
        if (inputDetails.TryGetProperty(field, out _))
            usageLine += $"; {field}={RequiredInteger(inputDetails, field)}";
}
if (usage.TryGetProperty("output_tokens_details", out var outputDetails))
{
    if (outputDetails.ValueKind != JsonValueKind.Object)
        throw new InvalidDataException("Decisions response has invalid output_tokens_details");
    if (outputDetails.TryGetProperty("reasoning_tokens", out _))
        usageLine += $"; reasoning_tokens={RequiredInteger(outputDetails, "reasoning_tokens")}";
}
lines.Add(usageLine);
foreach (var line in lines)
    Console.WriteLine(line);

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

static JsonElement Required(JsonElement parent, string name, JsonValueKind kind)
{
    if (parent.ValueKind != JsonValueKind.Object || !parent.TryGetProperty(name, out var value)
        || value.ValueKind != kind)
        throw new InvalidDataException($"Malformed Decisions response: missing or invalid {name}");
    return value;
}

static string RequiredString(JsonElement parent, string name)
{
    var value = Required(parent, name, JsonValueKind.String).GetString()!;
    if (string.IsNullOrWhiteSpace(value))
        throw new InvalidDataException($"Malformed Decisions response: empty {name}");
    return value;
}

static long RequiredInteger(JsonElement parent, string name)
{
    if (!Required(parent, name, JsonValueKind.Number).TryGetInt64(out var value) || value < 0)
        throw new InvalidDataException($"Malformed Decisions response: invalid {name}");
    return value;
}

static double RequiredNumber(JsonElement parent, string name, bool unit = false)
{
    if (!Required(parent, name, JsonValueKind.Number).TryGetDouble(out var value) || !double.IsFinite(value)
        || (unit && (value < 0 || value > 1)))
        throw new InvalidDataException($"Malformed Decisions response: invalid {name}");
    return value;
}

static string RequiredChoice(JsonElement parent, string name)
{
    if (parent.ValueKind != JsonValueKind.Object || !parent.TryGetProperty(name, out var value)
        || value.ValueKind is not (JsonValueKind.String or JsonValueKind.True or JsonValueKind.False))
        throw new InvalidDataException($"Malformed Decisions response: invalid {name}");
    return value.GetRawText();
}
