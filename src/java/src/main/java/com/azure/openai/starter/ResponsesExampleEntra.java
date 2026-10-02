package com.azure.openai.starter;

import com.azure.identity.AuthenticationUtil;
import com.azure.identity.DefaultAzureCredentialBuilder;
import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.credential.BearerTokenCredential;
import com.openai.models.responses.Response;
import com.openai.models.responses.ResponseInputItem;

import java.util.List;
import java.util.function.Supplier;

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
        SampleOptions options = SampleOptions.fromEnvironment();
        System.out.println("Deployment: " + options.model() + "; reasoning effort: " + options.reasoning().effort().orElseThrow());

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
                com.openai.models.responses.ResponseCreateParams.builder()
                        .model(options.model())
                        .input(com.openai.models.responses.ResponseCreateParams.Input.ofText("Explain quantum computing in simple terms in at most 150 words."))
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
                com.openai.models.responses.ResponseCreateParams.builder()
                        .model(options.model())
                        .input(com.openai.models.responses.ResponseCreateParams.Input.ofResponse(responseInputItems))
                        .reasoning(options.reasoning())
                        .maxOutputTokens(options.maxOutputTokens())
                        .build()
        );

        SampleOptions.printResponse(response2);
    }
}
