package com.azure.openai.starter;

import com.azure.identity.AuthenticationUtil;
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.credential.BearerTokenCredential;
import com.openai.models.Reasoning;
import com.openai.models.ReasoningEffort;
import com.openai.models.responses.Response;
import com.openai.models.responses.ResponseCreateParams;
import com.openai.models.responses.ResponseInputItem;
import com.openai.models.responses.ResponseOutputText;
import com.openai.models.responses.ResponseStatus;

import java.util.List;
import java.util.Set;
import java.util.function.Supplier;
import java.util.stream.Collectors;

/**
 * Azure OpenAI GPT-6.1 Sol - Responses API with EntraID Authentication
 * This demonstrates using Azure Identity (EntraID) instead of API keys.
 */
public class ResponsesExampleEntra {

    public static void main(String[] args) {
        System.out.println("Azure OpenAI GPT-6.1 Sol - EntraID Authentication");

        // Get required environment variables - throws if missing
        String endpoint = System.getenv("AZURE_OPENAI_ENDPOINT");

        if (endpoint == null || endpoint.isBlank()) {
            System.err.println("Error: AZURE_OPENAI_ENDPOINT must be set");
            System.exit(1);
        }
        String model = System.getenv().getOrDefault("AZURE_OPENAI_GPT_DEPLOYMENT_NAME", "gpt-6.1-sol");
        if (model.isBlank()) {
            throw new IllegalArgumentException("AZURE_OPENAI_GPT_DEPLOYMENT_NAME must not be empty");
        }
        String effort = System.getenv().getOrDefault("AZURE_OPENAI_REASONING_EFFORT", "medium");
        if (!Set.of("low", "medium", "high", "xhigh", "max").contains(effort)) {
            throw new IllegalArgumentException("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max");
        }
        String tokens = System.getenv().getOrDefault("AZURE_OPENAI_MAX_OUTPUT_TOKENS", "16384");
        long maxOutputTokens;
        try {
            maxOutputTokens = Long.parseLong(tokens);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000", e);
        }
        if (!tokens.matches("[0-9]+") || maxOutputTokens < 16 || maxOutputTokens > 128000) {
            throw new IllegalArgumentException("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000");
        }
        Reasoning reasoning = Reasoning.builder().effort(ReasoningEffort.of(effort)).build();
        System.out.println("Deployment: " + model + "; reasoning effort: " + effort);

        // Use DefaultAzureCredential for EntraID authentication
        // For production, use a specific credential (e.g. ManagedIdentityCredential) or set
        // AZURE_TOKEN_CREDENTIALS to control which credential is used. See:
        // https://aka.ms/azsdk/java/identity/credential-chains#defaultazurecredential-overview
        Supplier<String> bearerTokenSupplier = AuthenticationUtil.getBearerTokenSupplier(
                new DefaultAzureCredentialBuilder().build(), "https://cognitiveservices.azure.com/.default");

        // Initialize OpenAI client with Azure endpoint and Entra ID (v1 API path)
        String baseUrl = endpoint.replaceAll("/+$", "") + "/openai/v1/";
        OpenAIClient client = OpenAIOkHttpClient.builder()
                .baseUrl(baseUrl)
                // Set the Azure Entra ID
                .credential(BearerTokenCredential.create(bearerTokenSupplier))
                .build();

        // Example 1: Simple text input with Responses API
        System.out.println("Example 1: Simple text input");
        Response response1 = client.responses().create(
                ResponseCreateParams.builder()
                        .model(model)
                        .input(ResponseCreateParams.Input.ofText("Explain quantum computing in simple terms in at most 150 words."))
                        .reasoning(reasoning)
                        .maxOutputTokens(maxOutputTokens)
                        .build()
        );

        printResponse(response1);

        // Example 2: Conversation format with Responses API
        System.out.println("Example 2: Conversation format");
        List<ResponseInputItem> responseInputItems = List.of(
                ResponseInputItem.ofMessage(ResponseInputItem.Message.builder()
                        .role(ResponseInputItem.Message.Role.SYSTEM)
                        .addInputTextContent("You are an Azure cloud architect.")
                        .build()),
                ResponseInputItem.ofMessage(ResponseInputItem.Message.builder()
                        .role(ResponseInputItem.Message.Role.USER)
                        .addInputTextContent("Design a scalable web application architecture in at most 150 words.")
                        .build())
        );

        Response response2 = client.responses().create(
                ResponseCreateParams.builder()
                        .model(model)
                        .input(ResponseCreateParams.Input.ofResponse(responseInputItems))
                        .reasoning(reasoning)
                        .maxOutputTokens(maxOutputTokens)
                        .build()
        );

        printResponse(response2);
    }

    private static void printResponse(Response response) {
        if (!ResponseStatus.COMPLETED.equals(response.status().orElse(null))) {
            throw new IllegalStateException("Response did not complete: " + response.status()
                    + "; details=" + response.incompleteDetails() + "; error=" + response.error());
        }
        String text = response.output().stream()
                .flatMap(item -> item.message().stream())
                .flatMap(message -> message.content().stream())
                .flatMap(content -> content.outputText().stream())
                .map(ResponseOutputText::text)
                .collect(Collectors.joining());
        if (text.isBlank()) {
            throw new IllegalStateException("Response completed without output text");
        }
        var usage = response.usage().orElseThrow(
                () -> new IllegalStateException("Response completed without token usage"));

        System.out.println("Response: " + text);
        System.out.println("Status: " + response.status().orElseThrow());
        System.out.println("Reasoning tokens: " + usage.outputTokensDetails().reasoningTokens());
        System.out.println("Output tokens: " + usage.outputTokens());
        System.out.println();
    }
}
