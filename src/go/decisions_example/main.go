package main

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strings"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/option"
)

func main() {
	if err := run(context.Background()); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(ctx context.Context) error {
	endpoint := os.Getenv("AZURE_OPENAI_ENDPOINT")
	if endpoint == "" {
		return fmt.Errorf("missing AZURE_OPENAI_ENDPOINT environment variable")
	}
	// This is your Azure deployment name; the deployment must host gpt-6-luna.
	model := os.Getenv("AZURE_OPENAI_DEPLOYMENT")
	if model == "" {
		model = "gpt-6-luna"
	}

	apiKey := os.Getenv("AZURE_OPENAI_API_KEY")
	options := []option.RequestOption{
		option.WithBaseURL(strings.TrimRight(endpoint, "/") + "/openai/v1/"),
		option.WithAPIKey(apiKey),
	}
	// Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
	if apiKey == "" {
		credential, err := azidentity.NewDefaultAzureCredential(&azidentity.DefaultAzureCredentialOptions{
			TenantID: os.Getenv("AZURE_TENANT_ID"),
		})
		if err != nil {
			return err
		}
		options = append(options, option.WithMiddleware(func(req *http.Request, next option.MiddlewareNext) (*http.Response, error) {
			token, err := credential.GetToken(req.Context(), policy.TokenRequestOptions{
				Scopes: []string{"https://cognitiveservices.azure.com/.default"},
			})
			if err != nil {
				return nil, err
			}
			req.Header.Set("Authorization", "Bearer "+token.Token)
			return next(req)
		}))
	}
	client := openai.NewClient(options...)

	// Batch related questions in one request.
	// [START decisions_request]
	decision, err := client.Decisions.New(ctx, openai.DecisionNewParams{
		Model: model,
		Input: openai.DecisionNewParamsInputUnion{
			OfString: openai.String("I was charged twice for order 123. Please refund the duplicate charge."),
		},
		Questions: []openai.DecisionNewParamsQuestionUnion{
			{OfPredicate: &openai.DecisionNewParamsQuestionPredicate{
				Name: openai.String("refund_requested"),
				Instructions: openai.DecisionNewParamsQuestionPredicateInstructionsUnion{
					OfString: openai.String("Does the customer request a refund?"),
				},
			}},
			{OfChoice: &openai.DecisionNewParamsQuestionChoice{
				Name: openai.String("department"),
				Instructions: openai.DecisionNewParamsQuestionChoiceInstructionsUnion{
					OfString: openai.String("Which department should handle this request?"),
				},
				Choices: []openai.DecisionNewParamsQuestionChoiceChoice{
					{
						Value:       openai.DecisionNewParamsQuestionChoiceChoiceValueUnion{OfString: openai.String("billing")},
						Description: openai.String("Payments and refunds."),
					},
					{
						Value:       openai.DecisionNewParamsQuestionChoiceChoiceValueUnion{OfString: openai.String("technical")},
						Description: openai.String("Product problems."),
					},
					{
						Value:       openai.DecisionNewParamsQuestionChoiceChoiceValueUnion{OfString: openai.String("other")},
						Description: openai.String("Other requests."),
					},
				},
			}},
			{OfScore: &openai.DecisionNewParamsQuestionScore{
				Name: openai.String("severity"),
				Instructions: openai.DecisionNewParamsQuestionScoreInstructionsUnion{
					OfString: openai.String("How severe is this issue?"),
				},
				Levels: []openai.DecisionNewParamsQuestionScoreLevel{
					{Label: "Low", Description: openai.String("Minor inconvenience.")},
					{Label: "Medium", Description: openai.String("Needs attention.")},
					{Label: "High", Description: openai.String("Urgent action needed.")},
				},
			}},
		},
	})
	// [END decisions_request]
	if err != nil {
		// The SDK's error string leaves out the service's message, so add it.
		var apiError *openai.Error
		if errors.As(err, &apiError) {
			return fmt.Errorf("%w: %s", err, apiError.Message)
		}
		return err
	}

	return printDecision(decision)
}

func printDecision(decision *openai.Decision) error {
	if decision == nil || len(decision.Answers) == 0 || !decision.JSON.Usage.Valid() {
		return fmt.Errorf("Decisions response is missing answers or usage")
	}
	for _, answer := range decision.Answers {
		switch answer := answer.AsAny().(type) {
		case openai.DecisionAnswerPredicate:
			fmt.Printf("%s (predicate): probability=%g\n", answer.Name, answer.Probability)
		case openai.DecisionAnswerChoice:
			fmt.Printf("%s (choice): value=%s; confidence=%g\n  probabilities=%s\n",
				answer.Name, answer.Choice.RawJSON(), answer.Confidence, rawJSON(answer.Probabilities))
		case openai.DecisionAnswerScore:
			fmt.Printf("%s (score): score=%g; confidence=%g\n  probabilities=%s\n",
				answer.Name, answer.Score, answer.Confidence, rawJSON(answer.Probabilities))
		case openai.DecisionAnswerRefusal:
			fmt.Printf("%s (refusal): send this question for human review\n", answer.Name)
		default:
			return fmt.Errorf("unexpected Decisions answer type")
		}
	}
	fmt.Println("Usage:", decision.Usage.RawJSON())
	return nil
}

// rawJSON lists each item as the JSON the service returned.
func rawJSON[T interface{ RawJSON() string }](items []T) string {
	parts := make([]string, len(items))
	for i, item := range items {
		parts[i] = item.RawJSON()
	}
	return "[" + strings.Join(parts, ", ") + "]"
}
