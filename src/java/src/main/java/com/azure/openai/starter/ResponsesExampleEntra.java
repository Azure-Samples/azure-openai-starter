package com.azure.openai.starter;

import com.azure.identity.AuthenticationUtil;
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.credential.BearerTokenCredential;
import com.openai.models.ChatModel;
import com.openai.models.ResponsesModel;
import com.openai.models.responses.Response;
import com.openai.models.responses.ResponseInputItem;

import java.util.List;
import java.util.function.Supplier;

/**
 * Azure OpenAI GPT-5-mini - Responses API with EntraID Authentication
 * This demonstrates using Azure Identity (EntraID) instead of API keys.
 */
public class ResponsesExampleEntra {

    public static void main(String[] args) {
        System.out.println("Azure OpenAI - Responses API");

        // Get required environment variables - throws if missing
        String endpoint = System.getenv("AZURE_OPENAI_ENDPOINT");

        if (endpoint == null) {
            System.err.println("Error: AZURE_OPENAI_ENDPOINT must be set");
            System.exit(1);
        }

        Supplier<String> bearerTokenSupplier = AuthenticationUtil.getBearerTokenSupplier(
                new DefaultAzureCredentialBuilder().build(), "https://cognitiveservices.azure.com/.default");

        // Initialize OpenAI client with Azure endpoint and Entra ID
        OpenAIClient client = OpenAIOkHttpClient.builder()
                .baseUrl(endpoint)
                // Set the Azure Entra ID
                .credential(BearerTokenCredential.create(bearerTokenSupplier))
                .build();

        // Example 1: Simple text input with Responses API
        System.out.println("Example 1: Simple text input");
        Response response1 = client.responses().create(
                com.openai.models.responses.ResponseCreateParams.builder()
                        .model(ResponsesModel.ofChat(ChatModel.GPT_5_MINI))
                        .input(com.openai.models.responses.ResponseCreateParams.Input.ofText("Explain quantum computing in simple terms"))
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
                com.openai.models.responses.ResponseCreateParams.builder()
                        .model("gpt-5-mini")
                        .input(com.openai.models.responses.ResponseCreateParams.Input.ofResponse(responseInputItems))
                        .maxOutputTokens(1000)
                        .build()
        );

        System.out.println("Response: " + response2.output());
        System.out.println("Status: " + response2.status());
        response2.usage().ifPresent(usage -> System.out.println("Reasoning tokens: " + usage.outputTokensDetails().reasoningTokens()));
        response2.usage().ifPresent(usage -> System.out.println("Output tokens: " + usage.outputTokens()));
    }
}
