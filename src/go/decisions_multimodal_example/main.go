package main

import (
	"context"
	"encoding/base64"
	"errors"
	"fmt"
	"mime"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore/policy"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/option"
)

// A public-domain NASA photo. Azure fetches an HTTPS URL itself.
const defaultImage = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"

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

	// Pass your own HTTPS image URL or the path to an image file.
	image := defaultImage
	if len(os.Args) > 1 {
		image = os.Args[1]
	}
	if !strings.HasPrefix(image, "https://") {
		// A local file is sent inline as a base64 data URL.
		data, err := os.ReadFile(image)
		if err != nil {
			return err
		}
		image = "data:" + mime.TypeByExtension(filepath.Ext(image)) + ";base64," + base64.StdEncoding.EncodeToString(data)
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
			OfDecisionInputMessageArray: []openai.DecisionInputMessageParam{{
				Content: openai.DecisionInputMessageContentUnionParam{
					OfParts: []openai.DecisionInputPartUnionParam{
						{OfInputText: &openai.DecisionInputTextParam{
							Text: "Inspect the photo for visible damage and classify the main object.",
						}},
						{OfInputImage: &openai.DecisionInputImageParam{ImageURL: image}},
					},
				},
			}},
		},
		Questions: []openai.DecisionNewParamsQuestionUnion{
			{OfPredicate: &openai.DecisionNewParamsQuestionPredicate{
				Name: openai.String("visible_damage"),
				Instructions: openai.DecisionNewParamsQuestionPredicateInstructionsUnion{
					OfString: openai.String("Does the photo show visible damage to the main object?"),
				},
			}},
			{OfChoice: &openai.DecisionNewParamsQuestionChoice{
				Name: openai.String("category"),
				Instructions: openai.DecisionNewParamsQuestionChoiceInstructionsUnion{
					OfString: openai.String("Which category best describes the main object?"),
				},
				Choices: []openai.DecisionNewParamsQuestionChoiceChoice{
					{
						Value:       openai.DecisionNewParamsQuestionChoiceChoiceValueUnion{OfString: openai.String("parcel")},
						Description: openai.String("A package or parcel."),
					},
					{
						Value:       openai.DecisionNewParamsQuestionChoiceChoiceValueUnion{OfString: openai.String("vehicle")},
						Description: openai.String("A vehicle."),
					},
					{
						Value:       openai.DecisionNewParamsQuestionChoiceChoiceValueUnion{OfString: openai.String("other")},
						Description: openai.String("None of these categories."),
					},
				},
			}},
			{OfScore: &openai.DecisionNewParamsQuestionScore{
				Name: openai.String("severity"),
				Instructions: openai.DecisionNewParamsQuestionScoreInstructionsUnion{
					OfString: openai.String("How severe is the visible damage?"),
				},
				Levels: []openai.DecisionNewParamsQuestionScoreLevel{
					{Label: "Low", Description: openai.String("No damage or minor cosmetic damage.")},
					{Label: "Medium", Description: openai.String("Visible damage that needs attention.")},
					{Label: "High", Description: openai.String("Severe damage or loss of function.")},
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
