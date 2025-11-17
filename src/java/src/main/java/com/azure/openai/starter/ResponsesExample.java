package com.azure.openai.starter;

import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.models.ChatModel;
import com.openai.models.ResponsesModel;
import com.openai.models.responses.Response;
import com.openai.models.responses.ResponseCreateParams;
import com.openai.models.responses.ResponseInputItem;

import java.util.List;

/**
 * Azure OpenAI - Responses API Example
 * This demonstrates the new Responses API with GPT-5-mini reasoning model.
 */
public class ResponsesExample {

    public static void main(String[] args) {
        System.out.println("Azure OpenAI - Responses API");

        // Get required environment variables - throws if missing
        String endpoint = System.getenv("AZURE_OPENAI_ENDPOINT");
        String apiKey = System.getenv("AZURE_OPENAI_API_KEY");

        if (endpoint == null || apiKey == null) {
            System.err.println("Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set");
            System.exit(1);
        }

        // Initialize OpenAI client with Azure endpoint
        OpenAIClient client = OpenAIOkHttpClient.builder()
                .apiKey(apiKey)
                .baseUrl(endpoint)
                .build();

        // Example 1: Simple text input with Responses API
        System.out.println("Example 1: Simple text input");
        Response response1 = client.responses().create(
                ResponseCreateParams.builder()
                        .model(ResponsesModel.ofChat(ChatModel.GPT_5_MINI))
                        .input(ResponseCreateParams.Input.ofText("Explain quantum computing in simple terms"))
                        .maxOutputTokens(1000)
                        .build()
        );

        System.out.println("Response: " + response1.output());
        System.out.println("Status: " + response1.status());
        response1.usage().ifPresent(usage -> System.out.println("Reasoning tokens: " + usage.outputTokensDetails().reasoningTokens()));
        response1.usage().ifPresent(usage -> System.out.println("Output tokens: " + usage.outputTokens()));

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
                        .model("gpt-5-mini")
                        .input(ResponseCreateParams.Input.ofResponse(responseInputItems))
                        .maxOutputTokens(1000)
                        .build()
        );

        System.out.println("Response: " + response2.output());
        System.out.println("Status: " + response2.status());
        response2.usage().ifPresent(usage -> System.out.println("Reasoning tokens: " + usage.outputTokensDetails().reasoningTokens()));
        response2.usage().ifPresent(usage -> System.out.println("Output tokens: " + usage.outputTokens()));
    }
}
