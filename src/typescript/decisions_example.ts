import "dotenv/config";
import OpenAI from "openai";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";

async function main(): Promise<void> {
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT?.trim();
    if (!endpoint) {
        throw new Error("AZURE_OPENAI_ENDPOINT must not be empty");
    }
    const deployment = process.env.AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME ?? "gpt-6-luna";
    if (!deployment.trim()) {
        throw new Error("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME must not be empty");
    }
    const client = new OpenAI({
        baseURL: `${endpoint.replace(/\/+$/, "")}/openai/v1/`,
        apiKey: process.env.AZURE_OPENAI_API_KEY || getBearerTokenProvider(
            new DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        ),
    });
    const decision = await client.decisions.create({
        model: deployment,
        input: "I was charged twice for order 123. Please refund the duplicate charge.",
        questions: [
            {
                type: "predicate",
                name: "refund_requested",
                instructions: "Does the customer request a refund?",
            },
            {
                type: "choice",
                name: "department",
                instructions: "Which department should handle this request?",
                choices: [
                    { value: "billing", description: "Payments and refunds." },
                    { value: "technical", description: "Product problems." },
                    { value: "other", description: "Other requests." },
                ],
            },
            {
                type: "score",
                name: "severity",
                instructions: "How severe is this issue?",
                levels: [
                    { label: "Low", description: "Minor inconvenience." },
                    { label: "Medium", description: "Needs attention." },
                    { label: "High", description: "Urgent action needed." },
                ],
            },
        ],
    });
    if (!decision.answers?.length) {
        throw new Error("Decision returned no answers");
    }
    if (!decision.usage) {
        throw new Error("Decision returned no token usage");
    }
    for (const answer of decision.answers) {
        switch (answer.type) {
            case "predicate":
                console.log(`${answer.name}: predicate probability=${answer.probability}`);
                break;
            case "choice":
                console.log(`${answer.name}: choice value=${JSON.stringify(answer.choice)} confidence=${answer.confidence}`);
                break;
            case "score":
                console.log(`${answer.name}: score value=${answer.score} confidence=${answer.confidence}`);
                break;
            case "refusal":
                console.log(`${answer.name}: refusal (send this question for human review)`);
                break;
            default:
                throw new Error("Unexpected decision answer type");
        }
    }
    console.log(`Input tokens: ${decision.usage.input_tokens}`);
}

main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
});
