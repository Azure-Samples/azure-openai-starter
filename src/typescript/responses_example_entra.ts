import "dotenv/config";
import OpenAI from "openai";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";

/**
 * Azure OpenAI GPT-5-mini - Responses API with EntraID Authentication
 * This demonstrates using Azure Identity (EntraID) instead of API keys.
 */

function checkEnvironment(): void {
    if (!process.env.AZURE_OPENAI_ENDPOINT) {
        console.error("Missing AZURE_OPENAI_ENDPOINT environment variable");
        process.exit(1);
    }
}

async function main(): Promise<void> {
    console.log("Azure OpenAI GPT-5-mini - EntraID Authentication\n");
    
    checkEnvironment();
    
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT!;
    
    // Use DefaultAzureCredential for EntraID authentication
    // This automatically uses your Azure CLI login, Managed Identity, or other credential sources
    const credential = new DefaultAzureCredential();
    const scope = "https://cognitiveservices.azure.com/.default";
    const tokenProvider = getBearerTokenProvider(credential, scope);

    // Get a fresh token directly
    const tokenResponse = await credential.getToken(scope);
    
    // Initialize OpenAI client with Azure endpoint and the token
    const client = new OpenAI({
        baseURL: `${endpoint}/openai/v1/`,
        apiKey: await tokenProvider()
    });
    
    // Example 1: Simple text input with Responses API
    console.log("Example 1: Simple text input\n");
    const response1 = await client.responses.create({
        model: "gpt-5-mini",
        input: "Explain quantum computing in simple terms",
        max_output_tokens: 1000
    });
    console.log(`Response: ${response1.output_text}`);
    console.log(`Status: ${response1.status}`);
    console.log(`Reasoning tokens: ${response1.usage?.output_tokens_details?.reasoning_tokens}`);
    console.log(`Output tokens: ${response1.usage?.output_tokens}\n`);
    
    // Example 2: Conversation format with Responses API
    console.log("Example 2: Conversation format\n");
    const response2 = await client.responses.create({
        model: "gpt-5-mini",
        input: [
            { role: "system", content: "You are an Azure cloud architect." },
            { role: "user", content: "Design a scalable web application architecture." }
        ],
        max_output_tokens: 1000
    });
    console.log(`Response: ${response2.output_text}`);
    console.log(`Status: ${response2.status}`);
    console.log(`Reasoning tokens: ${response2.usage?.output_tokens_details?.reasoning_tokens}`);
    console.log(`Output tokens: ${response2.usage?.output_tokens}`);
}

main().catch((error) => {
    console.error("Error:", error.message);
    process.exit(1);
});
