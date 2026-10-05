/**
 * Azure OpenAI GPT-6.1 Sol - Responses API Example
 * This demonstrates the Responses API with the GPT-6.1 Sol reasoning model.
 */

import "dotenv/config";
import OpenAI from "openai";
import type { Response } from "openai/resources/responses/responses";

async function main(): Promise<void> {
    console.log("Azure OpenAI GPT-6.1 Sol - Responses API\n");
    
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT;
    const apiKey = process.env.AZURE_OPENAI_API_KEY;
    if (!endpoint?.trim() || !apiKey?.trim()) {
        throw new Error("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must not be empty");
    }
    const model = process.env.AZURE_OPENAI_GPT_DEPLOYMENT_NAME ?? "gpt-6.1-sol";
    if (!model.trim()) {
        throw new Error("AZURE_OPENAI_GPT_DEPLOYMENT_NAME must not be empty");
    }
    const effort = process.env.AZURE_OPENAI_REASONING_EFFORT ?? "medium";
    if (effort !== "low" && effort !== "medium" && effort !== "high" && effort !== "xhigh" && effort !== "max") {
        throw new Error("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max");
    }
    const tokens = process.env.AZURE_OPENAI_MAX_OUTPUT_TOKENS ?? "16384";
    const maxOutputTokens = Number(tokens);
    if (!/^[0-9]+$/.test(tokens) || !Number.isSafeInteger(maxOutputTokens) || maxOutputTokens < 16 || maxOutputTokens > 128000) {
        throw new Error("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000");
    }
    console.log(`Deployment: ${model}; reasoning effort: ${effort}\n`);
    
    // Initialize OpenAI client with Azure endpoint (v1 API path)
    const client = new OpenAI({
        apiKey: apiKey,
        baseURL: `${endpoint.replace(/\/+$/, '')}/openai/v1/`
    });
    
    // Example 1: Simple text input
    console.log("Example 1: Simple text input\n");
    const response1 = await client.responses.create({
        model,
        reasoning: { effort },
        max_output_tokens: maxOutputTokens,
        input: "Explain quantum computing in simple terms in at most 150 words."
    });
    printResponse(response1);
    
    // Example 2: Conversation format
    console.log("Example 2: Conversation format\n");
    const response2 = await client.responses.create({
        model,
        reasoning: { effort },
        max_output_tokens: maxOutputTokens,
        input: [
            { role: "system", content: "You are an Azure cloud architect." },
            { role: "user", content: "Design a scalable web application architecture in at most 150 words." }
        ]
    });
    printResponse(response2);
}

function printResponse(response: Response): void {
    if (response.status !== "completed") {
        throw new Error(
            `Response did not complete: ${response.status}; ` +
            `details=${JSON.stringify(response.incomplete_details)}; error=${JSON.stringify(response.error)}`
        );
    }
    if (!response.output_text.trim()) {
        throw new Error("Response completed without output text");
    }
    if (!response.usage) {
        throw new Error("Response completed without token usage");
    }

    console.log(`Response: ${response.output_text}`);
    console.log(`Status: ${response.status}`);
    console.log(`Reasoning tokens: ${response.usage.output_tokens_details.reasoning_tokens}`);
    console.log(`Output tokens: ${response.usage.output_tokens}\n`);
}

main().catch((error) => {
    console.error("Error:", error.message);
    process.exit(1);
});
