package main

import (
	"context"
	"encoding/base64"
	"errors"
	"fmt"
	"io"
	"math"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
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
	image, err := imageInput(os.Args[1:])
	if err != nil {
		return err
	}
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
	// Azure deployment name; it must point to GPT-6 Luna.
	model, configured := os.LookupEnv("AZURE_OPENAI_DEPLOYMENT")
	if !configured {
		model = "gpt-6-luna"
	}
	if strings.TrimSpace(model) == "" {
		return fmt.Errorf("AZURE_OPENAI_DEPLOYMENT must not be empty")
	}

	options := []option.RequestOption{
		option.WithBaseURL(strings.TrimRight(endpoint, "/") + "/openai/v1/"),
		option.WithAPIKey(apiKey),
	}
	if apiKey == "" {
		credential, err := azidentity.NewDefaultAzureCredential(&azidentity.DefaultAzureCredentialOptions{
			TenantID: os.Getenv("AZURE_TENANT_ID"),
		})
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
	// Create one client and reuse its connections for subsequent requests.
	client := openai.NewClient(options...)
	input := openai.DecisionNewParamsInputUnion{
		OfString: openai.String("I was charged twice for order 123. Please refund the duplicate charge."),
	}
	expectedNames := []string{"refund_requested", "department", "severity"}
	if image != "" {
		input = openai.DecisionNewParamsInputUnion{
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
		}
		expectedNames = []string{"visible_damage", "category", "severity"}
	}

	// Batch all three questions in one call.
	// [START decisions_request]
	result, err := client.Decisions.New(ctx, openai.DecisionNewParams{
		Model:     model,
		Input:     input,
		Questions: decisionQuestions(image != ""),
	})
	// [END decisions_request]
	if err != nil {
		var apiError *openai.Error
		if errors.As(err, &apiError) {
			return fmt.Errorf("Decisions HTTP %d: %s", apiError.StatusCode, apiError.RawJSON())
		}
		return fmt.Errorf("Decisions request failed: %w", err)
	}
	lines, err := answerLines(result, expectedNames...)
	if err != nil {
		return err
	}
	for _, line := range lines {
		fmt.Println(line)
	}
	return nil
}

func imageInput(args []string) (string, error) {
	if len(args) == 0 {
		return "", nil
	}
	if len(args) != 2 || args[0] != "--image" || strings.TrimSpace(args[1]) == "" {
		return "", fmt.Errorf("usage: go run . [--image PATH_OR_HTTPS_URL]")
	}
	source := args[1]
	if strings.Contains(source, "://") {
		image, err := url.Parse(source)
		if err != nil || !strings.EqualFold(image.Scheme, "https") || image.Hostname() == "" ||
			image.User != nil || strings.Contains(source, "#") {
			return "", fmt.Errorf("image URL must use HTTPS with a host, no credentials, and no fragment")
		}
		return source, nil
	}
	var mime string
	switch strings.ToLower(filepath.Ext(source)) {
	case ".png":
		mime = "image/png"
	case ".jpg", ".jpeg":
		mime = "image/jpeg"
	case ".webp":
		mime = "image/webp"
	case ".gif":
		mime = "image/gif"
	default:
		return "", fmt.Errorf("image file must be PNG, JPEG, WebP, or GIF")
	}
	file, err := os.Open(source)
	if err != nil {
		return "", fmt.Errorf("image file must exist and be readable: %w", err)
	}
	defer file.Close()
	const maxBytes = 32 * 1024 * 1024
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() {
		return "", fmt.Errorf("image file must be a readable regular file")
	}
	if info.Size() <= 0 || info.Size() > maxBytes {
		return "", fmt.Errorf("image file must be nonempty and at most 32 MiB (33554432 bytes)")
	}
	data, err := io.ReadAll(io.LimitReader(file, maxBytes+1))
	if err != nil {
		return "", fmt.Errorf("read image file: %w", err)
	}
	if len(data) == 0 || len(data) > maxBytes {
		return "", fmt.Errorf("image file must be nonempty and at most 32 MiB")
	}
	return "data:" + mime + ";base64," + base64.StdEncoding.EncodeToString(data), nil
}

func decisionQuestions(withImage bool) []openai.DecisionNewParamsQuestionUnion {
	predicateName, predicateInstructions := "refund_requested", "Does the customer request a refund?"
	choiceName, choiceInstructions := "department", "Which department should handle this request?"
	scoreInstructions := "How severe is this issue?"
	values := []string{"billing", "technical", "other"}
	descriptions := []string{"Payments and refunds.", "Product problems.", "Other requests."}
	levelDescriptions := []string{"Minor inconvenience.", "Needs attention.", "Urgent action needed."}
	if withImage {
		predicateName, predicateInstructions = "visible_damage", "Does the photo show visible damage to the main object?"
		choiceName, choiceInstructions = "category", "Which category best describes the main object?"
		scoreInstructions = "How severe is the visible damage?"
		values = []string{"parcel", "vehicle", "other"}
		descriptions = []string{"A package or parcel.", "A vehicle.", "None of these categories."}
		levelDescriptions = []string{
			"No damage or minor cosmetic damage.",
			"Visible damage that needs attention.",
			"Severe damage or loss of function.",
		}
	}
	choices := make([]openai.DecisionNewParamsQuestionChoiceChoice, len(values))
	for i, value := range values {
		choices[i] = openai.DecisionNewParamsQuestionChoiceChoice{
			Value:       openai.DecisionNewParamsQuestionChoiceChoiceValueUnion{OfString: openai.String(value)},
			Description: openai.String(descriptions[i]),
		}
	}
	levels := make([]openai.DecisionNewParamsQuestionScoreLevel, len(levelDescriptions))
	for i, label := range []string{"Low", "Medium", "High"} {
		levels[i] = openai.DecisionNewParamsQuestionScoreLevel{
			Label: label, Description: openai.String(levelDescriptions[i]),
		}
	}
	return []openai.DecisionNewParamsQuestionUnion{
		{OfPredicate: &openai.DecisionNewParamsQuestionPredicate{
			Name: openai.String(predicateName),
			Instructions: openai.DecisionNewParamsQuestionPredicateInstructionsUnion{
				OfString: openai.String(predicateInstructions),
			},
		}},
		{OfChoice: &openai.DecisionNewParamsQuestionChoice{
			Name: openai.String(choiceName),
			Instructions: openai.DecisionNewParamsQuestionChoiceInstructionsUnion{
				OfString: openai.String(choiceInstructions),
			},
			Choices: choices,
		}},
		{OfScore: &openai.DecisionNewParamsQuestionScore{
			Name: openai.String("severity"),
			Instructions: openai.DecisionNewParamsQuestionScoreInstructionsUnion{
				OfString: openai.String(scoreInstructions),
			},
			Levels: levels,
		}},
	}
}

func probability(value float64) bool {
	return !math.IsNaN(value) && !math.IsInf(value, 0) && value >= 0 && value <= 1
}

func answerLines(result *openai.Decision, expectedNames ...string) ([]string, error) {
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

	lines := make([]string, 0, len(result.Answers)+7)
	seen := make(map[string]bool)
	for _, answer := range result.Answers {
		if !answer.JSON.Name.Valid() || strings.TrimSpace(answer.Name) == "" || !answer.JSON.Type.Valid() {
			return nil, fmt.Errorf("Decisions response has an invalid answer name or type")
		}
		if seen[answer.Name] {
			return nil, fmt.Errorf("Decisions response has duplicate answer %q", answer.Name)
		}
		seen[answer.Name] = true
		switch answer.Type {
		case "predicate":
			if !answer.JSON.Probability.Valid() || !probability(answer.Probability) {
				return nil, fmt.Errorf("predicate answer %q has invalid probability", answer.Name)
			}
			lines = append(lines, fmt.Sprintf("%q (predicate): probability=%g", answer.Name, answer.Probability))
		case "choice":
			choice := answer.AsChoice()
			if !choice.JSON.Choice.Valid() || !choice.JSON.Confidence.Valid() || !probability(choice.Confidence) ||
				!choice.JSON.Probabilities.Valid() || len(choice.Probabilities) == 0 {
				return nil, fmt.Errorf("choice answer %q is malformed", answer.Name)
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
			chosen := value
			probabilities := make([]string, 0, len(choice.Probabilities))
			for _, item := range choice.Probabilities {
				if !item.JSON.Probability.Valid() || !probability(item.Probability) || !item.JSON.Value.Valid() {
					return nil, fmt.Errorf("choice answer %q has invalid probabilities", answer.Name)
				}
				switch {
				case item.Value.JSON.OfString.Valid():
					value = fmt.Sprintf("%q", item.Value.OfString)
				case item.Value.JSON.OfBool.Valid():
					value = fmt.Sprintf("%t", item.Value.OfBool)
				default:
					return nil, fmt.Errorf("choice answer %q has invalid option value", answer.Name)
				}
				probabilities = append(probabilities, fmt.Sprintf("{value=%s; probability=%g}", value, item.Probability))
			}
			lines = append(lines, fmt.Sprintf("%q (choice): value=%s; confidence=%g; probabilities=[%s]",
				answer.Name, chosen, choice.Confidence, strings.Join(probabilities, ", ")))
		case "score":
			score := answer.AsScore()
			if !score.JSON.Score.Valid() || math.IsNaN(score.Score) || math.IsInf(score.Score, 0) ||
				!score.JSON.Confidence.Valid() || !probability(score.Confidence) ||
				!score.JSON.Probabilities.Valid() || len(score.Probabilities) == 0 {
				return nil, fmt.Errorf("score answer %q is malformed", answer.Name)
			}
			probabilities := make([]string, 0, len(score.Probabilities))
			for _, item := range score.Probabilities {
				if !item.JSON.Label.Valid() || !item.JSON.Value.Valid() || !item.JSON.Probability.Valid() ||
					strings.TrimSpace(item.Label) == "" || item.Value < 0 || !probability(item.Probability) {
					return nil, fmt.Errorf("score answer %q has invalid probabilities", answer.Name)
				}
				probabilities = append(probabilities, fmt.Sprintf("{label=%q; value=%d; probability=%g}",
					item.Label, item.Value, item.Probability))
			}
			lines = append(lines, fmt.Sprintf("%q (score): score=%g; confidence=%g; probabilities=[%s]",
				answer.Name, score.Score, score.Confidence, strings.Join(probabilities, ", ")))
		case "refusal":
			lines = append(lines, fmt.Sprintf("%q (refusal): refused", answer.Name))
		default:
			return nil, fmt.Errorf("unknown Decisions answer type %q", answer.Type)
		}
	}
	if len(expectedNames) > 0 {
		for _, name := range expectedNames {
			if !seen[name] {
				return nil, fmt.Errorf("Decisions response is missing answer %q", name)
			}
		}
		if len(seen) != len(expectedNames) {
			return nil, fmt.Errorf("Decisions response contains an unknown answer name")
		}
	}
	usageLine := fmt.Sprintf("Usage: input_tokens=%d; output_tokens=%d; total_tokens=%d",
		usage.InputTokens, usage.OutputTokens, usage.TotalTokens)
	if usage.JSON.InputTokensDetails.Raw() != "" {
		if !usage.JSON.InputTokensDetails.Valid() {
			return nil, fmt.Errorf("Decisions response has invalid input_tokens_details")
		}
		details := usage.InputTokensDetails
		if details.JSON.CachedTokens.Raw() != "" {
			if !details.JSON.CachedTokens.Valid() || details.CachedTokens < 0 {
				return nil, fmt.Errorf("Decisions response has invalid cached_tokens")
			}
			usageLine += fmt.Sprintf("; cached_tokens=%d", details.CachedTokens)
		}
		if details.JSON.CacheWriteTokens.Raw() != "" {
			if !details.JSON.CacheWriteTokens.Valid() || details.CacheWriteTokens < 0 {
				return nil, fmt.Errorf("Decisions response has invalid cache_write_tokens")
			}
			usageLine += fmt.Sprintf("; cache_write_tokens=%d", details.CacheWriteTokens)
		}
	}
	if usage.JSON.OutputTokensDetails.Raw() != "" {
		if !usage.JSON.OutputTokensDetails.Valid() {
			return nil, fmt.Errorf("Decisions response has invalid output_tokens_details")
		}
		details := usage.OutputTokensDetails
		if details.JSON.ReasoningTokens.Raw() != "" {
			if !details.JSON.ReasoningTokens.Valid() || details.ReasoningTokens < 0 {
				return nil, fmt.Errorf("Decisions response has invalid reasoning_tokens")
			}
			usageLine += fmt.Sprintf("; reasoning_tokens=%d", details.ReasoningTokens)
		}
	}
	lines = append(lines, usageLine)
	return lines, nil
}
