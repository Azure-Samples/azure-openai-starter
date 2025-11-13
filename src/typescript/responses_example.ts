/**
 * Azure OpenAI GPT-5-mini - Responses API Example
 * This demonstrates the new Responses API with GPT-5-mini reasoning model.
 */

import "dotenv/config";
import OpenAI from "openai";

function checkEnvironment(): void {
    const missing = [];
    if (!process.env.AZURE_OPENAI_ENDPOINT) missing.push("AZURE_OPENAI_ENDPOINT");
    if (!process.env.AZURE_OPENAI_API_KEY) missing.push("AZURE_OPENAI_API_KEY");
    
    if (missing.length > 0) {
        console.error(`Missing environment variables: ${missing.join(", ")}`);
        process.exit(1);
    }
}

async function main(): Promise<void> {
    console.log("Azure OpenAI GPT-5-mini - Responses API\n");
    
    checkEnvironment();
    
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT!;
    const apiKey = process.env.AZURE_OPENAI_API_KEY!;
    
    // Initialize OpenAI client with Azure endpoint
    const client = new OpenAI({
        apiKey: apiKey,
        baseURL: `${endpoint}/openai/v1/`
    });
    
    // Example 1: Simple text input
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
    
    // Example 2: Conversation format
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
