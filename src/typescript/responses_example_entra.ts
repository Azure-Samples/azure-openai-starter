import "dotenv/config";
import OpenAI from "openai";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";
import { loadOptions, printResponse } from "./sample_options";

/**
 * Azure OpenAI GPT-6.1 Sol - Responses API with EntraID Authentication
 * This demonstrates using Azure Identity (EntraID) instead of API keys.
 */

function checkEnvironment(): void {
    if (!process.env.AZURE_OPENAI_ENDPOINT?.trim()) {
        console.error("Missing AZURE_OPENAI_ENDPOINT environment variable");
        process.exit(1);
    }
}

async function main(): Promise<void> {
    console.log("Azure OpenAI GPT-6.1 Sol - EntraID Authentication\n");
    
    checkEnvironment();
    
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT!;
    const options = loadOptions();
    console.log(`Deployment: ${options.model}; reasoning effort: ${options.reasoning.effort}\n`);
    
    // Use DefaultAzureCredential for EntraID authentication
    // This automatically uses your Azure CLI login, Managed Identity, or other credential sources
    // For production, use a specific credential (e.g. ManagedIdentityCredential) or set
    // AZURE_TOKEN_CREDENTIALS to control which credential is used. See:
    // https://aka.ms/azsdk/js/identity/credential-chains#defaultazurecredential-overview
    const credential = new DefaultAzureCredential();
    const scope = "https://cognitiveservices.azure.com/.default";
    const tokenProvider = getBearerTokenProvider(credential, scope);
    
    // Initialize OpenAI client with Azure endpoint and the token (v1 API path)
    const client = new OpenAI({
        baseURL: `${endpoint.replace(/\/+$/, '')}/openai/v1/`,
        apiKey: tokenProvider
    });
    
    // Example 1: Simple text input with Responses API
    console.log("Example 1: Simple text input\n");
    const response1 = await client.responses.create({
        ...options,
        input: "Explain quantum computing in simple terms in at most 150 words."
    });
    printResponse(response1);
    
    // Example 2: Conversation format with Responses API
    console.log("Example 2: Conversation format\n");
    const response2 = await client.responses.create({
        ...options,
        input: [
            { role: "system", content: "You are an Azure cloud architect." },
            { role: "user", content: "Design a scalable web application architecture in at most 150 words." }
        ]
    });
    printResponse(response2);
}

main().catch((error) => {
    console.error("Error:", error.message);
    process.exit(1);
});
