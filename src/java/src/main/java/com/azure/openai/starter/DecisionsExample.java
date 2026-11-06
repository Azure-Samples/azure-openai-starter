package com.azure.openai.starter;

import com.azure.identity.AuthenticationUtil;
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.credential.BearerTokenCredential;
import com.openai.models.decisions.Decision;
import com.openai.models.decisions.DecisionChoiceOption;
import com.openai.models.decisions.DecisionChoiceValue;
import com.openai.models.decisions.DecisionCreateParams;

import java.util.stream.Collectors;

public class DecisionsExample {
    public static void main(String[] args) {
        String endpoint = System.getenv("AZURE_OPENAI_ENDPOINT");
        if (endpoint == null) {
            System.err.println("Error: AZURE_OPENAI_ENDPOINT must be set");
            System.exit(1);
        }
        // This is your Azure deployment name; the deployment must host gpt-6-luna.
        String model = System.getenv().getOrDefault("AZURE_OPENAI_DEPLOYMENT", "gpt-6-luna");

        var builder = OpenAIOkHttpClient.builder()
                .baseUrl(endpoint.replaceAll("/+$", "") + "/openai/v1/");
        // Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
        String apiKey = System.getenv("AZURE_OPENAI_API_KEY");
        if (apiKey != null && !apiKey.isEmpty()) {
            builder.apiKey(apiKey);
        } else {
            builder.credential(BearerTokenCredential.create(AuthenticationUtil.getBearerTokenSupplier(
                    new DefaultAzureCredentialBuilder().build(),
                    "https://cognitiveservices.azure.com/.default")));
        }
        OpenAIClient client = builder.build();

        // Batch related questions in one request.
        // [START decisions_request]
        Decision decision = client.decisions().create(DecisionCreateParams.builder()
                .model(model)
                .input("I was charged twice for order 123. Please refund the duplicate charge.")
                .addQuestion(DecisionCreateParams.Question.Predicate.builder()
                        .name("refund_requested")
                        .instructions("Does the customer request a refund?")
                        .build())
                .addQuestion(DecisionCreateParams.Question.Choice.builder()
                        .name("department")
                        .instructions("Which department should handle this request?")
                        .addChoice(DecisionChoiceOption.builder()
                                .value("billing").description("Payments and refunds.").build())
                        .addChoice(DecisionChoiceOption.builder()
                                .value("technical").description("Product problems.").build())
                        .addChoice(DecisionChoiceOption.builder()
                                .value("other").description("Other requests.").build())
                        .build())
                .addQuestion(DecisionCreateParams.Question.Score.builder()
                        .name("severity")
                        .instructions("How severe is this issue?")
                        .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                .label("Low").description("Minor inconvenience.").build())
                        .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                .label("Medium").description("Needs attention.").build())
                        .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                .label("High").description("Urgent action needed.").build())
                        .build())
                .build());
        // [END decisions_request]

        printDecision(decision);
        client.close();
    }

    private static void printDecision(Decision decision) {
        if (decision.answers().isEmpty()) {
            throw new IllegalStateException("Decisions response is missing answers");
        }
        for (Decision.Answer answer : decision.answers()) {
            if (answer.isPredicate()) {
                var predicate = answer.asPredicate();
                System.out.println(predicate.name().orElse("") + " (predicate): probability="
                        + predicate.probability());
            } else if (answer.isChoice()) {
                var choice = answer.asChoice();
                var probabilities = choice.probabilities().stream()
                        .map(item -> "{value=" + choiceText(item.value()) + "; probability=" + item.probability() + "}")
                        .collect(Collectors.joining(", "));
                System.out.println(choice.name().orElse("") + " (choice): value=" + choiceText(choice.choice())
                        + "; confidence=" + choice.confidence() + "; probabilities=[" + probabilities + "]");
            } else if (answer.isScore()) {
                var score = answer.asScore();
                var probabilities = score.probabilities().stream()
                        .map(item -> "{label=" + item.label() + "; value=" + item.value()
                                + "; probability=" + item.probability() + "}")
                        .collect(Collectors.joining(", "));
                System.out.println(score.name().orElse("") + " (score): score=" + score.score()
                        + "; confidence=" + score.confidence() + "; probabilities=[" + probabilities + "]");
            } else if (answer.isRefusal()) {
                System.out.println(answer.asRefusal().name().orElse("")
                        + " (refusal): send this question for human review");
            } else {
                throw new IllegalStateException("Unexpected Decisions answer type");
            }
        }
        var usage = decision.usage();
        System.out.println("Usage: input_tokens=" + usage.inputTokens()
                + "; output_tokens=" + usage.outputTokens()
                + "; total_tokens=" + usage.totalTokens()
                + "; cached_tokens=" + usage.inputTokensDetails().cachedTokens()
                + "; cache_write_tokens=" + usage.inputTokensDetails().cacheWriteTokens()
                + "; reasoning_tokens=" + usage.outputTokensDetails().reasoningTokens());
    }

    // A choice is a string or a boolean; quotes tell them apart.
    private static String choiceText(DecisionChoiceValue value) {
        return value.isString() ? "\"" + value.asString() + "\"" : Boolean.toString(value.asBool());
    }
}
