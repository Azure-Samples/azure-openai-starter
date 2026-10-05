package main

import (
	"context"
	"log"
	"os"
	"strconv"
	"strings"

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
	effort := shared.ReasoningEffort(envOrDefault("AZURE_OPENAI_REASONING_EFFORT", "medium"))
	switch effort {
	case shared.ReasoningEffortLow, shared.ReasoningEffortMedium, shared.ReasoningEffortHigh, shared.ReasoningEffortXhigh, shared.ReasoningEffortMax:
	default:
		log.Fatal("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max")
	}
	tokens := envOrDefault("AZURE_OPENAI_MAX_OUTPUT_TOKENS", "16384")
	maxOutputTokens, err := strconv.ParseInt(tokens, 10, 64)
	if err != nil || maxOutputTokens < 16 || maxOutputTokens > 128000 {
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

func newClientUsingAnAPIKey(endpoint string) openai.Client {
	apiKey := os.Getenv("AZURE_OPENAI_API_KEY")

	if apiKey == "" {
		log.Fatalf("Missing AZURE_OPENAI_API_KEY environment variable")
	}

	// Initialize OpenAI client with Azure endpoint, using an API Key
	// NOTE: for Entra authentication, see the [NewClientUsingEntraAuthentication] function.
	client := openai.NewClient(
		option.WithBaseURL(strings.TrimRight(endpoint, "/")+"/openai/v1/"),
		option.WithAPIKey(apiKey),
	)

	return client
}

func main() {
	log.Printf("Azure OpenAI GPT-6.1 Sol - API Key Authentication\n")

	endpoint := os.Getenv("AZURE_OPENAI_ENDPOINT")

	if endpoint == "" {
		log.Fatalf("Missing AZURE_OPENAI_ENDPOINT environment variable")
	}
	model, effort, maxOutputTokens := loadOptions()
	log.Printf("Deployment: %s; reasoning effort: %s", model, effort)

	client := newClientUsingAnAPIKey(endpoint)

	// Example 1: Simple text input with Responses API
	log.Printf("Example 1: Simple text input")

	resp, err := client.Responses.New(context.TODO(), responses.ResponseNewParams{
		Model: model,
		Input: responses.ResponseNewParamsInputUnion{
			OfString: openai.String("Explain quantum computing in simple terms"),
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
							OfString: openai.String("Design a scalable web application architecture."),
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
