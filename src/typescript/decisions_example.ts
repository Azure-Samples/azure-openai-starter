import "dotenv/config";
import OpenAI from "openai";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";

async function main(): Promise<void> {
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT;
    if (!endpoint) {
        throw new Error("Missing AZURE_OPENAI_ENDPOINT environment variable");
    }
    // This is your Azure deployment name; the deployment must host gpt-6-luna.
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT ?? "gpt-6-luna";

    const client = new OpenAI({
        baseURL: `${endpoint.replace(/\/+$/, "")}/openai/v1/`,
        // Entra ID is the default; an explicitly set API key is the fallback.
        apiKey: process.env.AZURE_OPENAI_API_KEY || getBearerTokenProvider(
            new DefaultAzureCredential({ tenantId: process.env.AZURE_TENANT_ID }),
            "https://cognitiveservices.azure.com/.default",
        ),
    });

    // Batch related questions in one request; the service accepts at most 400.
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

    if (!decision.answers?.length || !decision.usage) {
        throw new Error("Decisions response is missing answers or usage");
    }
    for (const answer of decision.answers) {
        switch (answer.type) {
            case "predicate":
                console.log(`${answer.name}: predicate probability=${answer.probability}`);
                break;
            case "choice":
                console.log(`${answer.name}: choice value=${JSON.stringify(answer.choice)} confidence=${answer.confidence}`);
                console.log(`  probabilities=${JSON.stringify(answer.probabilities)}`);
                break;
            case "score":
                console.log(`${answer.name}: score value=${answer.score} confidence=${answer.confidence}`);
                console.log(`  probabilities=${JSON.stringify(answer.probabilities)}`);
                break;
            case "refusal":
                console.log(`${answer.name}: refusal (send this question for human review)`);
                break;
            default:
                throw new Error("Unexpected Decisions answer type");
        }
    }
    console.log(`Usage: ${JSON.stringify(decision.usage)}`);
}

main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
});
