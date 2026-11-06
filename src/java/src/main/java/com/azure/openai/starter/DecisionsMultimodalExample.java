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
import com.openai.models.decisions.DecisionInputImage;
import com.openai.models.decisions.DecisionInputItem;
import com.openai.models.decisions.DecisionInputMessage;
import com.openai.models.decisions.DecisionInputPart;
import com.openai.models.decisions.DecisionInputText;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.List;
import java.util.stream.Collectors;

public class DecisionsMultimodalExample {
    // A public-domain NASA photo. Azure fetches an HTTPS URL itself.
    private static final String DEFAULT_IMAGE =
            "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png";

    public static void main(String[] args) throws IOException {
        String endpoint = System.getenv("AZURE_OPENAI_ENDPOINT");
        if (endpoint == null) {
            System.err.println("Error: AZURE_OPENAI_ENDPOINT must be set");
            System.exit(1);
        }
        // This is your Azure deployment name; the deployment must host gpt-6-luna.
        String model = System.getenv().getOrDefault("AZURE_OPENAI_DEPLOYMENT", "gpt-6-luna");

        // Pass your own HTTPS image URL or the path to an image file.
        String image = args.length > 0 ? args[0] : DEFAULT_IMAGE;
        if (!image.startsWith("https://")) {
            // A local file is sent inline as a base64 data URL.
            Path path = Path.of(image);
            image = "data:" + Files.probeContentType(path) + ";base64,"
                    + Base64.getEncoder().encodeToString(Files.readAllBytes(path));
        }

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
                .inputOfDecisionInputItems(List.of(
                        DecisionInputItem.ofDecisionInputMessage(DecisionInputMessage.ofUser(
                                DecisionInputMessage.User.builder().contentOfParts(List.of(
                                        DecisionInputPart.ofInputText(DecisionInputText.builder()
                                                .text("Inspect the photo for visible damage and classify the main object.")
                                                .build()),
                                        DecisionInputPart.ofInputImage(DecisionInputImage.builder()
                                                .imageUrl(image).build())))
                                        .build()))))
                .addQuestion(DecisionCreateParams.Question.Predicate.builder()
                        .name("visible_damage")
                        .instructions("Does the photo show visible damage to the main object?")
                        .build())
                .addQuestion(DecisionCreateParams.Question.Choice.builder()
                        .name("category")
                        .instructions("Which category best describes the main object?")
                        .addChoice(DecisionChoiceOption.builder()
                                .value("parcel").description("A package or parcel.").build())
                        .addChoice(DecisionChoiceOption.builder()
                                .value("vehicle").description("A vehicle.").build())
                        .addChoice(DecisionChoiceOption.builder()
                                .value("other").description("None of these categories.").build())
                        .build())
                .addQuestion(DecisionCreateParams.Question.Score.builder()
                        .name("severity")
                        .instructions("How severe is the visible damage?")
                        .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                .label("Low").description("No damage or minor cosmetic damage.").build())
                        .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                .label("Medium").description("Visible damage that needs attention.").build())
                        .addLevel(DecisionCreateParams.Question.Score.Level.builder()
                                .label("High").description("Severe damage or loss of function.").build())
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
