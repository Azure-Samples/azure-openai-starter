package com.azure.openai.starter;

import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.models.Reasoning;
import com.openai.models.ReasoningEffort;
import com.openai.models.responses.Response;
import com.openai.models.responses.ResponseCreateParams;
import com.openai.models.responses.ResponseInputItem;
import com.openai.models.responses.ResponseOutputText;
import com.openai.models.responses.ResponseStatus;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Azure OpenAI - Responses API Example
 * This demonstrates the Responses API with the GPT-6.1 Sol reasoning model.
 */
public class ResponsesExample {

    public static void main(String[] args) {
        System.out.println("Azure OpenAI GPT-6.1 Sol - Responses API");

        // Get required environment variables - throws if missing
        String endpoint = System.getenv("AZURE_OPENAI_ENDPOINT");
        String apiKey = System.getenv("AZURE_OPENAI_API_KEY");

        if (endpoint == null || apiKey == null) {
            System.err.println("Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set");
            System.exit(1);
        }

        // Optional settings. GPT-6.1 Sol supports low, medium, high, xhigh and max reasoning effort.
        String model = System.getenv().getOrDefault("AZURE_OPENAI_GPT_DEPLOYMENT_NAME", "gpt-6.1-sol");
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
        if (maxOutputTokens < 16 || maxOutputTokens > 128000) {
            throw new IllegalArgumentException("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000");
        }
        Reasoning reasoning = Reasoning.builder().effort(ReasoningEffort.of(effort)).build();
        System.out.println("Deployment: " + model + "; reasoning effort: " + effort);

        // Initialize OpenAI client with Azure endpoint (v1 API path)
        String baseUrl = endpoint.replaceAll("/+$", "") + "/openai/v1/";
        OpenAIClient client = OpenAIOkHttpClient.builder()
                .apiKey(apiKey)
                .baseUrl(baseUrl)
                .build();

        // Example 1: Simple text input with Responses API
        System.out.println("Example 1: Simple text input");
        Response response1 = client.responses().create(
                ResponseCreateParams.builder()
                        .model(model)
                        .input(ResponseCreateParams.Input.ofText("Explain quantum computing in simple terms"))
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
                        .addInputTextContent("Design a scalable web application architecture.")
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
