package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/Azure/azure-sdk-for-go/sdk/azcore/runtime"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/option"
	"github.com/openai/openai-go/v3/responses"
)

type policyAdapter option.MiddlewareNext

func (mp policyAdapter) Do(req *policy.Request) (*http.Response, error) {
	return (option.MiddlewareNext)(mp)(req.Raw())
}

func newClientUsingEntraAuthentication(endpoint string) openai.Client {
	const scope = "https://cognitiveservices.azure.com/.default"

	// Use DefaultAzureCredential for EntraID authentication
	// This automatically uses your Azure CLI login, Managed Identity, or other credential sources
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
	log.Printf("Azure OpenAI GPT-5-mini - EntraID Authentication\n")

	endpoint := os.Getenv("AZURE_OPENAI_ENDPOINT")

	if endpoint == "" {
		log.Fatalf("Missing AZURE_OPENAI_ENDPOINT environment variable")
	}

	client := newClientUsingEntraAuthentication(endpoint)

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


