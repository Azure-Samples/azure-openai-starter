package main

import (
	"context"
	"log"
	"os"

	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/azure"
	"github.com/openai/openai-go/v3/option"
	"github.com/openai/openai-go/v3/responses"
)

func NewClientUsingEntraAuthentication(endpoint string) openai.Client {
	// Use DefaultAzureCredential for EntraID authentication
	// This automatically uses your Azure CLI login, Managed Identity, or other credential sources
	cred, err := azidentity.NewDefaultAzureCredential(nil)

	if err != nil {
		log.Fatalf("Failed to create DefaultAzureCredential: %s", err)
	}

	const scope = "https://cognitiveservices.azure.com/.default"

	// Initialize OpenAI client with Azure endpoint and the token
	client := openai.NewClient(
		option.WithBaseURL(endpoint+"/openai/v1/"),
		azure.WithTokenCredential(cred, azure.WithTokenCredentialScopes([]string{scope})),
	)

	return client
}

func NewClientUsingAnAPIKey(endpoint string) openai.Client {
	apiKey := os.Getenv("AZURE_OPENAI_API_KEY")

	if apiKey == "" {
		log.Fatalf("Missing AZURE_OPENAI_API_KEY environment variable")
	}

	// Initialize OpenAI client with Azure endpoint, using an API Key
	// NOTE: for Entra authentication, see the [NewClientUsingEntraAuthentication] function.
	client := openai.NewClient(
		option.WithBaseURL(endpoint+"/openai/v1/"),
		option.WithAPIKey(apiKey),
	)

	return client
}

func main() {
	log.Printf("Azure OpenAI GPT-5-mini - EntraID Authentication\n")

	endpoint := os.Getenv("AZURE_OPENAI_ENDPOINT")

	if endpoint == "" {
		log.Fatalf("Missing AZURE_OPENAI_ENDPOINT environment variable")
	}

	client := NewClientUsingEntraAuthentication(endpoint)
	// NOTE: If you want to use an API key to authenticate, instead of using Entra:
	// client := NewClientUsingAnAPIKey(endpoint)
	//

	// Example 1: Simple text input with Responses API
	log.Printf("Example 1: Simple text input")

	resp, err := client.Responses.New(context.TODO(), responses.ResponseNewParams{
		Model: "gpt-5-mini",
		Input: responses.ResponseNewParamsInputUnion{
			OfString: openai.String("Explain quantum computing in simple terms"),
		},
		MaxOutputTokens: openai.Int(1000),
	})

	if err != nil {
		log.Fatalf("Failed to create responses: %s", err)
	}

	log.Printf("Response: %s", resp.OutputText())
	log.Printf("Status: %s", resp.Status)
	log.Printf("Reasoning tokens: %d", resp.Usage.OutputTokensDetails.ReasoningTokens)
	log.Printf("Output tokens: %d", resp.Usage.OutputTokens)
	log.Println()

	// Example 2: Conversation format with Responses API
	log.Printf("Example 2: Conversation format")
	resp2, err := client.Responses.New(context.TODO(), responses.ResponseNewParams{
		Model: "gpt-5-mini",
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
		MaxOutputTokens: openai.Int(1000),
	})

	if err != nil {
		log.Fatalf("Failed to create responses: %s", err)
	}

	log.Printf("Response: %s", resp2.OutputText())
	log.Printf("Status: %s", resp2.Status)
	log.Printf("Reasoning tokens: %d", resp2.Usage.OutputTokensDetails.ReasoningTokens)
	log.Printf("Output tokens: %d", resp2.Usage.OutputTokens)
	log.Println()
}
