package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/runtime"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/option"
	"github.com/openai/openai-go/v3/responses"
	"github.com/openai/openai-go/v3/shared"
)

func envOrDefault(name, fallback string) string {
	if value, exists := os.LookupEnv(name); exists {
		return value
	}
	return fallback
}

func loadOptions() (string, shared.ReasoningEffort, int64) {
	model := envOrDefault("AZURE_OPENAI_GPT_DEPLOYMENT_NAME", "gpt-6.1-sol")
	if strings.TrimSpace(model) == "" {
		log.Fatal("AZURE_OPENAI_GPT_DEPLOYMENT_NAME must not be empty")
	}
	effort := shared.ReasoningEffort(envOrDefault("AZURE_OPENAI_REASONING_EFFORT", "medium"))
	switch effort {
	case shared.ReasoningEffortLow, shared.ReasoningEffortMedium, shared.ReasoningEffortHigh, shared.ReasoningEffortXhigh, shared.ReasoningEffortMax:
	default:
		log.Fatal("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max")
	}
	tokens := envOrDefault("AZURE_OPENAI_MAX_OUTPUT_TOKENS", "16384")
	maxOutputTokens, err := strconv.ParseInt(tokens, 10, 64)
	if err != nil || strings.Trim(tokens, "0123456789") != "" || maxOutputTokens < 16 || maxOutputTokens > 128000 {
		log.Fatal("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000")
	}
	return model, effort, maxOutputTokens
}

func printResponse(response *responses.Response) {
	if response.Status != responses.ResponseStatusCompleted {
		log.Fatalf("Response did not complete: %s; details=%+v; error=%+v", response.Status, response.IncompleteDetails, response.Error)
	}
	if strings.TrimSpace(response.OutputText()) == "" {
		log.Fatal("Response completed without output text")
	}
	if !response.JSON.Usage.Valid() {
		log.Fatal("Response completed without token usage")
	}
	log.Printf("Response: %s", response.OutputText())
	log.Printf("Status: %s", response.Status)
	log.Printf("Reasoning tokens: %d", response.Usage.OutputTokensDetails.ReasoningTokens)
	log.Printf("Output tokens: %d", response.Usage.OutputTokens)
	log.Println()
}

type policyAdapter option.MiddlewareNext

func (mp policyAdapter) Do(req *policy.Request) (*http.Response, error) {
	return (option.MiddlewareNext)(mp)(req.Raw())
}

func newClientUsingEntraAuthentication(endpoint string) openai.Client {
	const scope = "https://cognitiveservices.azure.com/.default"

	// Use DefaultAzureCredential for EntraID authentication
	// This automatically uses your Azure CLI login, Managed Identity, or other credential sources
	// For production, use a specific credential (e.g. azidentity.NewManagedIdentityCredential)
	// or set AZURE_TOKEN_CREDENTIALS to control which credential is used. See:
	// https://aka.ms/azsdk/go/identity/credential-chains#defaultazurecredential-overview
	tokenCredential, err := azidentity.NewDefaultAzureCredential(nil)

	if err != nil {
		log.Fatalf("Failed to create DefaultAzureCredential: %s", err)
	}

	bearerTokenPolicy := runtime.NewBearerTokenPolicy(tokenCredential, []string{scope}, nil)

	// Initialize OpenAI client with Azure endpoint and the token
	client := openai.NewClient(
		option.WithBaseURL(strings.TrimRight(endpoint, "/")+"/openai/v1/"),
		option.WithMiddleware(func(req *http.Request, next option.MiddlewareNext) (*http.Response, error) {
			pipeline := runtime.NewPipeline("azopenai-starter-kit", "", runtime.PipelineOptions{}, &policy.ClientOptions{
				InsecureAllowCredentialWithHTTP: true, // allow for plain HTTP proxies, etc..
				PerRetryPolicies: []policy.Policy{
					bearerTokenPolicy,
					policyAdapter(next),
				},
			})

			req2, err := runtime.NewRequestFromRequest(req)

			if err != nil {
				return nil, err
			}

			return pipeline.Do(req2)
		}),
	)

	return client
}

func main() {
	log.Printf("Azure OpenAI GPT-6.1 Sol - EntraID Authentication\n")

	endpoint := os.Getenv("AZURE_OPENAI_ENDPOINT")

	if strings.TrimSpace(endpoint) == "" {
		log.Fatalf("Missing AZURE_OPENAI_ENDPOINT environment variable")
	}
	model, effort, maxOutputTokens := loadOptions()
	log.Printf("Deployment: %s; reasoning effort: %s", model, effort)

	client := newClientUsingEntraAuthentication(endpoint)

	// Example 1: Simple text input with Responses API
	log.Printf("Example 1: Simple text input")

	resp, err := client.Responses.New(context.TODO(), responses.ResponseNewParams{
		Model: model,
		Input: responses.ResponseNewParamsInputUnion{
			OfString: openai.String("Explain quantum computing in simple terms in at most 150 words."),
		},
		Reasoning:       shared.ReasoningParam{Effort: effort},
		MaxOutputTokens: openai.Int(maxOutputTokens),
	})

	if err != nil {
		log.Fatalf("Failed to create responses: %s", err)
	}

	printResponse(resp)

	// Example 2: Conversation format with Responses API
	log.Printf("Example 2: Conversation format")
	resp2, err := client.Responses.New(context.TODO(), responses.ResponseNewParams{
		Model: model,
		Input: responses.ResponseNewParamsInputUnion{
			OfInputItemList: responses.ResponseInputParam{
				{
					OfMessage: &responses.EasyInputMessageParam{
						Role: responses.EasyInputMessageRoleSystem,
						Content: responses.EasyInputMessageContentUnionParam{
							OfString: openai.String("You are an Azure cloud architect."),
						},
					},
				},
				{
					OfMessage: &responses.EasyInputMessageParam{
						Role: responses.EasyInputMessageRoleUser,
						Content: responses.EasyInputMessageContentUnionParam{
							OfString: openai.String("Design a scalable web application architecture in at most 150 words."),
						},
					},
				},
			},
		},
		Reasoning:       shared.ReasoningParam{Effort: effort},
		MaxOutputTokens: openai.Int(maxOutputTokens),
	})

	if err != nil {
		log.Fatalf("Failed to create responses: %s", err)
	}

	printResponse(resp2)
}
