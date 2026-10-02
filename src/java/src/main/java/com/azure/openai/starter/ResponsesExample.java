package com.azure.openai.starter;

import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.models.responses.Response;
import com.openai.models.responses.ResponseCreateParams;
import com.openai.models.responses.ResponseInputItem;

import java.util.List;

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

        if (endpoint == null || endpoint.isBlank() || apiKey == null || apiKey.isBlank()) {
            System.err.println("Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set");
            System.exit(1);
        }
        SampleOptions options = SampleOptions.fromEnvironment();
        System.out.println("Deployment: " + options.model() + "; reasoning effort: " + options.reasoning().effort().orElseThrow());

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
                        .model(options.model())
                        .input(ResponseCreateParams.Input.ofText("Explain quantum computing in simple terms in at most 150 words."))
                        .reasoning(options.reasoning())
                        .maxOutputTokens(options.maxOutputTokens())
                        .build()
        );

        SampleOptions.printResponse(response1);

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
                        .model(options.model())
                        .input(ResponseCreateParams.Input.ofResponse(responseInputItems))
                        .reasoning(options.reasoning())
                        .maxOutputTokens(options.maxOutputTokens())
                        .build()
        );

        SampleOptions.printResponse(response2);
    }
}
