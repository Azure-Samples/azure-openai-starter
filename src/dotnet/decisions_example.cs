#!/usr/bin/dotnet run

#:package Azure.Identity@1.*
#:property PublishAot=false

using System.Net.Http.Headers;
using System.Text.Json;

using Azure.Core;
using Azure.Identity;

var endpoint = Environment.GetEnvironmentVariable("AZURE_OPENAI_ENDPOINT");
if (string.IsNullOrWhiteSpace(endpoint))
    throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT environment variable is required");
var apiKey = Environment.GetEnvironmentVariable("AZURE_OPENAI_API_KEY");
var useKey = !string.IsNullOrEmpty(apiKey);
if (!Uri.TryCreate(endpoint, UriKind.Absolute, out var uri)
    || string.IsNullOrEmpty(uri.Host) || !string.IsNullOrEmpty(uri.UserInfo)
    || !string.IsNullOrEmpty(uri.Query) || !string.IsNullOrEmpty(uri.Fragment)
    || uri.AbsolutePath.Trim('/').Length != 0)
    throw new InvalidOperationException("AZURE_OPENAI_ENDPOINT must be the Azure resource root URL");
if (uri.Scheme != Uri.UriSchemeHttps && !(uri.Scheme == Uri.UriSchemeHttp && uri.IsLoopback && useKey))
    throw new InvalidOperationException(
        "AZURE_OPENAI_ENDPOINT must use HTTPS (HTTP loopback is allowed with an API key)");
var model = Environment.GetEnvironmentVariable("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME") ?? "gpt-6-luna";
if (string.IsNullOrWhiteSpace(model))
    throw new InvalidOperationException("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME must not be empty");

var bearerToken = apiKey;
if (!useKey)
{
    var credential = new DefaultAzureCredential();
    var token = await credential.GetTokenAsync(new TokenRequestContext(
        ["https://cognitiveservices.azure.com/.default"]));
    bearerToken = token.Token;
}
using var httpClient = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false });

// OpenAI .NET 2.14.0 has no typed Decisions client; use the same v1 REST contract.
// [START decisions_request]
var payload = new
{
    model,
    input = "I was charged twice for order 123. Please refund the duplicate charge.",
    questions = new object[]
    {
        new
        {
            type = "predicate",
            name = "refund_requested",
            instructions = "Does the customer request a refund?"
        },
        new
        {
            type = "choice",
            name = "department",
            instructions = "Which department should handle this request?",
            choices = new[]
            {
                new { value = "billing", description = "Payments and refunds." },
                new { value = "technical", description = "Product problems." },
                new { value = "other", description = "Other requests." }
            }
        },
        new
        {
            type = "score",
            name = "severity",
            instructions = "How severe is this issue?",
            levels = new[]
            {
                new { label = "Low", description = "Minor inconvenience." },
                new { label = "Medium", description = "Needs attention." },
                new { label = "High", description = "Urgent action needed." }
            }
        }
    }
};
using var request = new HttpRequestMessage(HttpMethod.Post, $"{endpoint.TrimEnd('/')}/openai/v1/decisions");
if (useKey)
    request.Headers.Add("api-key", apiKey);
else
    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", bearerToken);
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
RequiredInteger(usage, "input_tokens");
RequiredInteger(usage, "output_tokens");
RequiredInteger(usage, "total_tokens");

var lines = new List<string>();
foreach (var answer in answers.EnumerateArray())
{
    var name = JsonSerializer.Serialize(RequiredString(answer, "name"));
    var type = RequiredString(answer, "type");
    switch (type)
    {
        case "predicate":
            lines.Add($"{name} (predicate): probability={RequiredNumber(answer, "probability", unit: true)}");
            break;
        case "choice":
            var choice = RequiredChoice(answer, "choice");
            var confidence = RequiredNumber(answer, "confidence", unit: true);
            foreach (var item in Required(answer, "probabilities", JsonValueKind.Array).EnumerateArray())
            {
                RequiredChoice(item, "value");
                RequiredNumber(item, "probability", unit: true);
            }
            lines.Add($"{name} (choice): value={choice}; confidence={confidence}");
            break;
        case "score":
            var score = RequiredNumber(answer, "score");
            var scoreConfidence = RequiredNumber(answer, "confidence", unit: true);
            foreach (var item in Required(answer, "probabilities", JsonValueKind.Array).EnumerateArray())
            {
                RequiredString(item, "label");
                RequiredInteger(item, "value");
                RequiredNumber(item, "probability", unit: true);
            }
            lines.Add($"{name} (score): score={score}; confidence={scoreConfidence}");
            break;
        case "refusal":
            lines.Add($"{name} (refusal): refused");
            break;
        default:
            throw new InvalidDataException($"Unknown Decisions answer type: {JsonSerializer.Serialize(type)}");
    }
}
foreach (var line in lines)
    Console.WriteLine(line);

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
