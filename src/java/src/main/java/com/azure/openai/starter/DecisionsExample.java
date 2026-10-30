package com.azure.openai.starter;

import com.azure.identity.AuthenticationUtil;
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.credential.BearerTokenCredential;
import com.openai.errors.OpenAIServiceException;
import com.openai.models.decisions.Decision;
import com.openai.models.decisions.DecisionChoiceOption;
import com.openai.models.decisions.DecisionChoiceValue;
import com.openai.models.decisions.DecisionCreateParams;
import com.openai.models.decisions.DecisionInputImage;
import com.openai.models.decisions.DecisionInputItem;
import com.openai.models.decisions.DecisionInputMessage;
import com.openai.models.decisions.DecisionInputPart;
import com.openai.models.decisions.DecisionInputText;

import java.io.IOException;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;

public class DecisionsExample {
    public static void main(String[] args) {
        String imageUrl = imageInput(args);
        boolean withImage = imageUrl != null;
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
        // Azure deployment name; it must point to GPT-6 Luna.
        String model = System.getenv("AZURE_OPENAI_DEPLOYMENT");
        if (model == null) {
            model = "gpt-6-luna";
        }
        if (model.isBlank()) {
            throw new IllegalArgumentException("AZURE_OPENAI_DEPLOYMENT must not be empty");
        }
        String predicateName = withImage ? "visible_damage" : "refund_requested";
        String choiceName = withImage ? "category" : "department";

        var builder = OpenAIOkHttpClient.builder()
                .baseUrl(endpoint.replaceAll("/+$", "") + "/openai/v1/");
        // Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
        if (useKey) {
            builder.apiKey(apiKey);
        } else {
            builder.credential(BearerTokenCredential.create(AuthenticationUtil.getBearerTokenSupplier(
                    new DefaultAzureCredentialBuilder().build(),
                    "https://cognitiveservices.azure.com/.default")));
        }
        // Create one client and reuse its connections for subsequent requests.
        OpenAIClient client = builder.build();
        try {
            // [START decisions_request]
            var params = DecisionCreateParams.builder().model(model);
            if (withImage) {
                params.inputOfDecisionInputItems(List.of(
                        DecisionInputItem.ofDecisionInputMessage(DecisionInputMessage.ofUser(
                                DecisionInputMessage.User.builder().contentOfParts(List.of(
                                        DecisionInputPart.ofInputText(DecisionInputText.builder()
                                                .text("Inspect the photo for visible damage and classify the main object.")
                                                .build()),
                                        DecisionInputPart.ofInputImage(DecisionInputImage.builder()
                                                .imageUrl(imageUrl).build())))
                                        .build()))));
            } else {
                params.input("I was charged twice for order 123. Please refund the duplicate charge.");
            }
            // Batch all three questions in one call.
            Decision result = client.decisions().create(params
                    .addQuestion(DecisionCreateParams.Question.Predicate.builder()
                            .name(predicateName)
                            .instructions(withImage
                                    ? "Does the photo show visible damage to the main object?"
                                    : "Does the customer request a refund?")
                            .build())
                    .addQuestion(DecisionCreateParams.Question.Choice.builder()
                            .name(choiceName)
                            .instructions(withImage
                                    ? "Which category best describes the main object?"
                                    : "Which department should handle this request?")
                            .addChoice(DecisionChoiceOption.builder()
                                    .value(withImage ? "parcel" : "billing")
                                    .description(withImage ? "A package or parcel." : "Payments and refunds.").build())
                            .addChoice(DecisionChoiceOption.builder()
                                    .value(withImage ? "vehicle" : "technical")
                                    .description(withImage ? "A vehicle." : "Product problems.").build())
                            .addChoice(DecisionChoiceOption.builder()
                                    .value("other")
                                    .description(withImage ? "None of these categories." : "Other requests.").build())
                            .build())
                    .addQuestion(DecisionCreateParams.Question.Score.builder()
                            .name("severity")
                            .instructions(withImage ? "How severe is the visible damage?" : "How severe is this issue?")
                            .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                    .label("Low").description(withImage
                                            ? "No damage or minor cosmetic damage." : "Minor inconvenience.").build())
                            .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                    .label("Medium").description(withImage
                                            ? "Visible damage that needs attention." : "Needs attention.").build())
                            .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                    .label("High").description(withImage
                                            ? "Severe damage or loss of function." : "Urgent action needed.").build())
                            .build())
                    .build());
            // [END decisions_request]
            for (String line : answerLines(result, List.of(predicateName, choiceName, "severity"))) {
                System.out.println(line);
            }
        } catch (OpenAIServiceException error) {
            throw new IllegalStateException("Decisions HTTP " + error.statusCode() + ": " + error.body());
        } finally {
            client.close();
        }
    }

    private static String imageInput(String[] args) {
        if (args.length == 0) {
            return null;
        }
        if (args.length != 2 || !"--image".equals(args[0]) || args[1].isBlank()) {
            throw new IllegalArgumentException("Usage: DecisionsExample [--image PATH_OR_HTTPS_URL]");
        }
        String source = args[1];
        if (source.contains("://")) {
            URI image;
            try {
                image = URI.create(source);
            } catch (IllegalArgumentException error) {
                throw new IllegalArgumentException("Image URL must be a valid HTTPS URL");
            }
            if (!"https".equalsIgnoreCase(image.getScheme()) || image.getHost() == null
                    || image.getHost().isBlank() || image.getUserInfo() != null || image.getRawFragment() != null) {
                throw new IllegalArgumentException(
                        "Image URL must use HTTPS with a host, no credentials, and no fragment");
            }
            return source;
        }
        String lower = source.toLowerCase(Locale.ROOT);
        String extension = lower.substring(lower.lastIndexOf('.') + 1);
        String mime = switch (extension) {
            case "png" -> "image/png";
            case "jpg", "jpeg" -> "image/jpeg";
            case "webp" -> "image/webp";
            case "gif" -> "image/gif";
            default -> throw new IllegalArgumentException("Image file must be PNG, JPEG, WebP, or GIF");
        };
        final int maxBytes = 32 * 1024 * 1024;
        try {
            Path path = Path.of(source);
            if (!Files.isRegularFile(path) || !Files.isReadable(path)) {
                throw new IllegalArgumentException("Image file must exist and be a readable regular file");
            }
            long size = Files.size(path);
            if (size <= 0 || size > maxBytes) {
                throw new IllegalArgumentException("Image file must be nonempty and at most 32 MiB");
            }
            byte[] data;
            try (var file = Files.newInputStream(path)) {
                data = file.readNBytes(maxBytes + 1);
            }
            if (data.length == 0 || data.length > maxBytes) {
                throw new IllegalArgumentException("Image file must be nonempty and at most 32 MiB");
            }
            return "data:" + mime + ";base64," + Base64.getEncoder().encodeToString(data);
        } catch (IOException error) {
            throw new IllegalArgumentException("Image file must exist and be readable");
        }
    }

    private static List<String> answerLines(Decision result, List<String> expectedNames) {
        if (result == null || result.answers().isEmpty()) {
            throw new IllegalStateException("Decisions response has empty answers");
        }
        if (result.model().isBlank()) {
            throw new IllegalStateException("Decisions response is missing model");
        }
        var usage = result.usage();
        long inputTokens = nonnegative(usage.inputTokens(), "input_tokens");
        long outputTokens = nonnegative(usage.outputTokens(), "output_tokens");
        long totalTokens = nonnegative(usage.totalTokens(), "total_tokens");
        List<String> lines = new ArrayList<>();
        var seen = new HashSet<String>();
        for (var answer : result.answers()) {
            String answerName;
            if (answer.isPredicate()) {
                var predicate = answer.asPredicate();
                answerName = name(predicate.name().orElseThrow(
                        () -> new IllegalStateException("Decisions response is missing an answer name")));
                lines.add(answerName + " (predicate): probability="
                        + probability(predicate.probability()));
            } else if (answer.isChoice()) {
                var choice = answer.asChoice();
                answerName = name(choice.name().orElseThrow(
                        () -> new IllegalStateException("Decisions response is missing an answer name")));
                if (choice.probabilities().isEmpty()) {
                    throw new IllegalStateException("Decisions choice answer is missing probabilities");
                }
                var probabilities = new ArrayList<String>();
                for (var item : choice.probabilities()) {
                    probabilities.add("{value=" + choiceText(item.value())
                            + "; probability=" + probability(item.probability()) + "}");
                }
                lines.add(answerName + " (choice): value=" + choiceText(choice.choice())
                        + "; confidence=" + probability(choice.confidence())
                        + "; probabilities=[" + String.join(", ", probabilities) + "]");
            } else if (answer.isScore()) {
                var score = answer.asScore();
                if (!Double.isFinite(score.score())) {
                    throw new IllegalStateException("Decisions score answer has an invalid score");
                }
                answerName = name(score.name().orElseThrow(
                        () -> new IllegalStateException("Decisions response is missing an answer name")));
                if (score.probabilities().isEmpty()) {
                    throw new IllegalStateException("Decisions score answer is missing probabilities");
                }
                var probabilities = new ArrayList<String>();
                for (var item : score.probabilities()) {
                    probabilities.add("{label=" + name(item.label())
                            + "; value=" + nonnegative(item.value(), "score level")
                            + "; probability=" + probability(item.probability()) + "}");
                }
                lines.add(answerName + " (score): score=" + score.score()
                        + "; confidence=" + probability(score.confidence())
                        + "; probabilities=[" + String.join(", ", probabilities) + "]");
            } else if (answer.isRefusal()) {
                answerName = name(answer.asRefusal().name().orElseThrow(
                        () -> new IllegalStateException("Decisions response is missing an answer name")));
                lines.add(answerName + " (refusal): refused");
            } else {
                throw new IllegalStateException("Unknown Decisions answer type");
            }
            if (!expectedNames.contains(answerName)) {
                throw new IllegalStateException("Decisions response has an unknown answer name: " + answerName);
            }
            if (!seen.add(answerName)) {
                throw new IllegalStateException("Decisions response has a duplicate answer: " + answerName);
            }
        }
        for (String expected : expectedNames) {
            if (!seen.contains(expected)) {
                throw new IllegalStateException("Decisions response is missing answer: " + expected);
            }
        }
        var usageLine = new StringBuilder("Usage: input_tokens=" + inputTokens
                + "; output_tokens=" + outputTokens + "; total_tokens=" + totalTokens);
        if (!usage._inputTokensDetails().isMissing()) {
            var details = usage.inputTokensDetails();
            if (!details._cachedTokens().isMissing()) {
                usageLine.append("; cached_tokens=").append(nonnegative(details.cachedTokens(), "cached_tokens"));
            }
            if (!details._cacheWriteTokens().isMissing()) {
                usageLine.append("; cache_write_tokens=")
                        .append(nonnegative(details.cacheWriteTokens(), "cache_write_tokens"));
            }
        }
        if (!usage._outputTokensDetails().isMissing()) {
            var details = usage.outputTokensDetails();
            if (!details._reasoningTokens().isMissing()) {
                usageLine.append("; reasoning_tokens=")
                        .append(nonnegative(details.reasoningTokens(), "reasoning_tokens"));
            }
        }
        lines.add(usageLine.toString());
        return lines;
    }

    private static String choiceText(DecisionChoiceValue value) {
        if (value.isString()) {
            return name(value.asString());
        }
        if (value.isBool()) {
            return Boolean.toString(value.asBool());
        }
        throw new IllegalStateException("Decisions choice answer has an invalid value");
    }

    private static long nonnegative(long value, String field) {
        if (value < 0) {
            throw new IllegalStateException("Decisions response has invalid " + field);
        }
        return value;
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
