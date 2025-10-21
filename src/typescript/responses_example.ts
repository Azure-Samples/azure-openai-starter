/**
 * Azure OpenAI GPT-5-mini - Responses API Example
 * This demonstrates the new Responses API with GPT-5-mini reasoning model.
 */

import OpenAI from "openai";

function checkEnvironment(): void {
    const requiredVars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"];
    const missing = requiredVars.filter(varName => !process.env[varName]);
    
    if (missing.length > 0) {
        console.error(`❌ Missing environment variables: ${missing.join(", ")}`);
        console.error("\nRun these commands to set them:");
        console.error("$endpoint = azd env get-values | Select-String 'AZURE_OPENAI_ENDPOINT' | ForEach-Object { $_ -replace 'AZURE_OPENAI_ENDPOINT=\"(.*)\"', '$1' }");
        console.error("$apiKey = az cognitiveservices account keys list --name RESOURCE_NAME --resource-group RESOURCE_GROUP --query key1 -o tsv");
        console.error("$env:AZURE_OPENAI_ENDPOINT = $endpoint");
        console.error("$env:AZURE_OPENAI_API_KEY = $apiKey");
        process.exit(1);
    }
    
    console.log("✅ Environment variables configured");
}

async function main(): Promise<void> {
    console.log("=".repeat(60));
    console.log("Azure OpenAI GPT-5-mini - Responses API Examples");
    console.log("=".repeat(60));
    
    checkEnvironment();
    
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT!;
    const apiKey = process.env.AZURE_OPENAI_API_KEY!;
    
    // Initialize OpenAI client with Azure endpoint
    const client = new OpenAI({
        apiKey: apiKey,
        baseURL: `${endpoint}openai/v1/`
    });
    
    // Example 1: Simple text input
    console.log("\n📝 Example 1: Simple text input");
    console.log("-".repeat(60));
    const response1 = await client.responses.create({
        model: "gpt-5-mini",
        input: "Explain quantum computing in simple terms",
        max_output_tokens: 1000
    });
    console.log(`Response: ${response1.output_text}`);
    console.log(`Status: ${response1.status}`);
    console.log(`Reasoning tokens: ${response1.usage?.output_tokens_details?.reasoning_tokens}`);
    console.log(`Output tokens: ${response1.usage?.output_tokens}`);
    
    // Example 2: Conversation format
    console.log("\n📝 Example 2: Conversation format");
    console.log("-".repeat(60));
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
    
    console.log("\n" + "=".repeat(60));
    console.log("✅ All examples completed successfully!");
    console.log("=".repeat(60));
}

main().catch((error) => {
    console.error("❌ Error:", error.message);
    process.exit(1);
});
