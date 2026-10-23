package com.azure.openai.starter;

import com.azure.identity.AuthenticationUtil;
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.credential.BearerTokenCredential;
import com.openai.errors.OpenAIServiceException;
import com.openai.models.decisions.Decision;
import com.openai.models.decisions.DecisionChoiceOption;
import com.openai.models.decisions.DecisionCreateParams;

import java.net.URI;
import java.util.ArrayList;
import java.util.List;

public class DecisionsExample {
    public static void main(String[] args) {
        String endpoint = System.getenv("AZURE_OPENAI_ENDPOINT");
        if (endpoint == null || endpoint.isBlank()) {
            throw new IllegalArgumentException("AZURE_OPENAI_ENDPOINT is required");
        }
        String apiKey = System.getenv("AZURE_OPENAI_API_KEY");
        boolean useKey = apiKey != null && !apiKey.isEmpty();
        URI uri = URI.create(endpoint);
        boolean loopback = "localhost".equalsIgnoreCase(uri.getHost())
                || "127.0.0.1".equals(uri.getHost()) || "[::1]".equals(uri.getHost());
        if (uri.getHost() == null || uri.getUserInfo() != null || uri.getRawQuery() != null
                || uri.getRawFragment() != null || !uri.getPath().replace("/", "").isEmpty()) {
            throw new IllegalArgumentException("AZURE_OPENAI_ENDPOINT must be the Azure resource root URL");
        }
        if (!"https".equals(uri.getScheme())
                && !("http".equals(uri.getScheme()) && loopback && useKey)) {
            throw new IllegalArgumentException(
                    "AZURE_OPENAI_ENDPOINT must use HTTPS (HTTP loopback is allowed with an API key)");
        }
        String model = System.getenv("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME");
        if (model == null) {
            model = "gpt-6-luna";
        }
        if (model.isBlank()) {
            throw new IllegalArgumentException("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME must not be empty");
        }

        var builder = OpenAIOkHttpClient.builder()
                .baseUrl(endpoint.replaceAll("/+$", "") + "/openai/v1/");
        if (useKey) {
            builder.apiKey(apiKey);
        } else {
            builder.credential(BearerTokenCredential.create(AuthenticationUtil.getBearerTokenSupplier(
                    new DefaultAzureCredentialBuilder().build(),
                    "https://cognitiveservices.azure.com/.default")));
        }
        OpenAIClient client = builder.build();
        try {
            // [START decisions_request]
            Decision result = client.decisions().create(DecisionCreateParams.builder()
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
            for (String line : answerLines(result)) {
                System.out.println(line);
            }
        } catch (OpenAIServiceException error) {
            throw new IllegalStateException("Decisions HTTP " + error.statusCode() + ": " + error.body());
        } finally {
            client.close();
        }
    }

    private static List<String> answerLines(Decision result) {
        result.validate();
        if (result.answers().isEmpty()) {
            throw new IllegalStateException("Decisions response has empty answers");
        }
        var usage = result.usage();
        if (usage.inputTokens() < 0 || usage.outputTokens() < 0 || usage.totalTokens() < 0) {
            throw new IllegalStateException("Decisions response has invalid token usage");
        }
        List<String> lines = new ArrayList<>();
        for (var answer : result.answers()) {
            if (answer.isPredicate()) {
                var predicate = answer.asPredicate();
                lines.add(name(predicate.name().orElseThrow()) + " (predicate): probability="
                        + probability(predicate.probability()));
            } else if (answer.isChoice()) {
                var choice = answer.asChoice();
                var value = choice.choice();
                String text;
                if (value.isString()) {
                    text = name(value.asString());
                } else if (value.isBool()) {
                    text = Boolean.toString(value.asBool());
                } else {
                    throw new IllegalStateException("Decisions choice answer has an invalid value");
                }
                lines.add(name(choice.name().orElseThrow()) + " (choice): value=" + text
                        + "; confidence=" + probability(choice.confidence()));
            } else if (answer.isScore()) {
                var score = answer.asScore();
                if (!Double.isFinite(score.score())) {
                    throw new IllegalStateException("Decisions score answer has an invalid score");
                }
                lines.add(name(score.name().orElseThrow()) + " (score): score=" + score.score()
                        + "; confidence=" + probability(score.confidence()));
            } else if (answer.isRefusal()) {
                lines.add(name(answer.asRefusal().name().orElseThrow()) + " (refusal): refused");
            } else {
                throw new IllegalStateException("Unknown Decisions answer type");
            }
        }
        return lines;
    }

    private static double probability(double value) {
        if (!Double.isFinite(value) || value < 0 || value > 1) {
            throw new IllegalStateException("Decisions answer has an invalid probability");
        }
        return value;
    }

    private static String name(String value) {
        if (value.isBlank()) {
            throw new IllegalStateException("Decisions answer has an empty name or choice value");
        }
        return value.replace("\r", "\\r").replace("\n", "\\n");
    }
}
