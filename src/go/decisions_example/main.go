package main

import (
	"context"
	"errors"
	"fmt"
	"math"
	"net"
	"net/http"
	"net/url"
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
	apiKey := os.Getenv("AZURE_OPENAI_API_KEY")
	parsed, err := url.Parse(endpoint)
	if err != nil || parsed.Host == "" || parsed.User != nil || parsed.RawQuery != "" ||
		parsed.Fragment != "" || strings.Trim(parsed.Path, "/") != "" {
		return fmt.Errorf("AZURE_OPENAI_ENDPOINT must be the Azure resource root URL")
	}
	ip := net.ParseIP(parsed.Hostname())
	loopback := strings.EqualFold(parsed.Hostname(), "localhost") || (ip != nil && ip.IsLoopback())
	if parsed.Scheme != "https" && !(parsed.Scheme == "http" && loopback && apiKey != "") {
		return fmt.Errorf("AZURE_OPENAI_ENDPOINT must use HTTPS (HTTP loopback is allowed with an API key)")
	}
	model, configured := os.LookupEnv("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME")
	if !configured {
		model = "gpt-6-luna"
	}
	if strings.TrimSpace(model) == "" {
		return fmt.Errorf("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME must not be empty")
	}

	options := []option.RequestOption{
		option.WithBaseURL(strings.TrimRight(endpoint, "/") + "/openai/v1/"),
		option.WithAPIKey(apiKey),
	}
	if apiKey == "" {
		credential, err := azidentity.NewDefaultAzureCredential(nil)
		if err != nil {
			return fmt.Errorf("create DefaultAzureCredential: %w", err)
		}
		options = append(options, option.WithMiddleware(func(req *http.Request, next option.MiddlewareNext) (*http.Response, error) {
			token, err := credential.GetToken(req.Context(), policy.TokenRequestOptions{
				Scopes: []string{"https://cognitiveservices.azure.com/.default"},
			})
			if err != nil {
				return nil, fmt.Errorf("get Azure OpenAI access token: %w", err)
			}
			req.Header.Set("Authorization", "Bearer "+token.Token)
			return next(req)
		}))
	}
	client := openai.NewClient(options...)

	// [START decisions_request]
	result, err := client.Decisions.New(ctx, openai.DecisionNewParams{
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
		var apiError *openai.Error
		if errors.As(err, &apiError) {
			return fmt.Errorf("Decisions HTTP %d: %s", apiError.StatusCode, apiError.RawJSON())
		}
		return fmt.Errorf("Decisions request failed: %w", err)
	}
	lines, err := answerLines(result)
	if err != nil {
		return err
	}
	for _, line := range lines {
		fmt.Println(line)
	}
	return nil
}

func probability(value float64) bool {
	return !math.IsNaN(value) && !math.IsInf(value, 0) && value >= 0 && value <= 1
}

func answerLines(result *openai.Decision) ([]string, error) {
	if result == nil || !result.JSON.Answers.Valid() || len(result.Answers) == 0 {
		return nil, fmt.Errorf("Decisions response has empty or invalid answers")
	}
	if !result.JSON.Usage.Valid() {
		return nil, fmt.Errorf("Decisions response is missing usage")
	}
	usage := result.Usage
	if !usage.JSON.InputTokens.Valid() || !usage.JSON.OutputTokens.Valid() || !usage.JSON.TotalTokens.Valid() ||
		usage.InputTokens < 0 || usage.OutputTokens < 0 || usage.TotalTokens < 0 {
		return nil, fmt.Errorf("Decisions response has invalid token usage")
	}
	if !result.JSON.Model.Valid() || result.Model == "" {
		return nil, fmt.Errorf("Decisions response is missing model")
	}

	lines := make([]string, 0, len(result.Answers))
	for _, answer := range result.Answers {
		if !answer.JSON.Name.Valid() || strings.TrimSpace(answer.Name) == "" || !answer.JSON.Type.Valid() {
			return nil, fmt.Errorf("Decisions response has an invalid answer name or type")
		}
		switch answer.Type {
		case "predicate":
			if !answer.JSON.Probability.Valid() || !probability(answer.Probability) {
				return nil, fmt.Errorf("predicate answer %q has invalid probability", answer.Name)
			}
			lines = append(lines, fmt.Sprintf("%q (predicate): probability=%g", answer.Name, answer.Probability))
		case "choice":
			choice := answer.AsChoice()
			if !choice.JSON.Choice.Valid() || !choice.JSON.Confidence.Valid() || !probability(choice.Confidence) ||
				!choice.JSON.Probabilities.Valid() {
				return nil, fmt.Errorf("choice answer %q is malformed", answer.Name)
			}
			for _, item := range choice.Probabilities {
				if !item.JSON.Probability.Valid() || !probability(item.Probability) || !item.JSON.Value.Valid() ||
					(!item.Value.JSON.OfString.Valid() && !item.Value.JSON.OfBool.Valid()) {
					return nil, fmt.Errorf("choice answer %q has invalid probabilities", answer.Name)
				}
			}
			var value string
			switch {
			case choice.Choice.JSON.OfString.Valid():
				value = fmt.Sprintf("%q", choice.Choice.OfString)
			case choice.Choice.JSON.OfBool.Valid():
				value = fmt.Sprintf("%t", choice.Choice.OfBool)
			default:
				return nil, fmt.Errorf("choice answer %q has invalid value", answer.Name)
			}
			lines = append(lines, fmt.Sprintf("%q (choice): value=%s; confidence=%g", answer.Name, value, choice.Confidence))
		case "score":
			score := answer.AsScore()
			if !score.JSON.Score.Valid() || math.IsNaN(score.Score) || math.IsInf(score.Score, 0) ||
				!score.JSON.Confidence.Valid() || !probability(score.Confidence) || !score.JSON.Probabilities.Valid() {
				return nil, fmt.Errorf("score answer %q is malformed", answer.Name)
			}
			for _, item := range score.Probabilities {
				if !item.JSON.Label.Valid() || !item.JSON.Value.Valid() || !item.JSON.Probability.Valid() ||
					!probability(item.Probability) {
					return nil, fmt.Errorf("score answer %q has invalid probabilities", answer.Name)
				}
			}
			lines = append(lines, fmt.Sprintf("%q (score): score=%g; confidence=%g", answer.Name, score.Score, score.Confidence))
		case "refusal":
			lines = append(lines, fmt.Sprintf("%q (refusal): refused", answer.Name))
		default:
			return nil, fmt.Errorf("unknown Decisions answer type %q", answer.Type)
		}
	}
	return lines, nil
}
