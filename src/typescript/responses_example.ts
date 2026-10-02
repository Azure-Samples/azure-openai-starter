/**
 * Azure OpenAI GPT-6.1 Sol - Responses API Example
 * This demonstrates the Responses API with the GPT-6.1 Sol reasoning model.
 */

import "dotenv/config";
import OpenAI from "openai";
import { loadOptions, printResponse } from "./sample_options";

function checkEnvironment(): void {
    const missing = [];
    if (!process.env.AZURE_OPENAI_ENDPOINT?.trim()) missing.push("AZURE_OPENAI_ENDPOINT");
    if (!process.env.AZURE_OPENAI_API_KEY?.trim()) missing.push("AZURE_OPENAI_API_KEY");
    
    if (missing.length > 0) {
        console.error(`Missing environment variables: ${missing.join(", ")}`);
        process.exit(1);
    }
}

async function main(): Promise<void> {
    console.log("Azure OpenAI GPT-6.1 Sol - Responses API\n");
    
    checkEnvironment();
    
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT!;
    const apiKey = process.env.AZURE_OPENAI_API_KEY!;
    const options = loadOptions();
    console.log(`Deployment: ${options.model}; reasoning effort: ${options.reasoning.effort}\n`);
    
    // Initialize OpenAI client with Azure endpoint (v1 API path)
    const client = new OpenAI({
        apiKey: apiKey,
        baseURL: `${endpoint.replace(/\/+$/, '')}/openai/v1/`
    });
    
    // Example 1: Simple text input
    console.log("Example 1: Simple text input\n");
    const response1 = await client.responses.create({
        ...options,
        input: "Explain quantum computing in simple terms in at most 150 words."
    });
    printResponse(response1);
    
    // Example 2: Conversation format
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
