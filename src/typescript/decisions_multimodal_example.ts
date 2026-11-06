import "dotenv/config";
import { readFileSync } from "node:fs";
import { extname } from "node:path";
import OpenAI from "openai";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";

// A public-domain NASA photo. Azure fetches an HTTPS URL itself.
const defaultImage = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png";
const mediaTypes: Record<string, string> = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif",
};

async function main(): Promise<void> {
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT;
    if (!endpoint) {
        throw new Error("Missing AZURE_OPENAI_ENDPOINT environment variable");
    }
    // This is your Azure deployment name; the deployment must host gpt-6-luna.
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT ?? "gpt-6-luna";

    // Pass your own HTTPS image URL or the path to an image file.
    let image = process.argv[2] ?? defaultImage;
    if (!image.startsWith("https://")) {
        // A local file is sent inline as a base64 data URL.
        image = `data:${mediaTypes[extname(image).toLowerCase()]};base64,${readFileSync(image).toString("base64")}`;
    }

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
        input: [
            {
                role: "user",
                content: [
                    { type: "input_text", text: "Inspect the photo for visible damage and classify the main object." },
                    { type: "input_image", image_url: image },
                ],
            },
        ],
        questions: [
            {
                type: "predicate",
                name: "visible_damage",
                instructions: "Does the photo show visible damage to the main object?",
            },
            {
                type: "choice",
                name: "category",
                instructions: "Which category best describes the main object?",
                choices: [
                    { value: "parcel", description: "A package or parcel." },
                    { value: "vehicle", description: "A vehicle." },
                    { value: "other", description: "None of these categories." },
                ],
            },
            {
                type: "score",
                name: "severity",
                instructions: "How severe is the visible damage?",
                levels: [
                    { label: "Low", description: "No damage or minor cosmetic damage." },
                    { label: "Medium", description: "Visible damage that needs attention." },
                    { label: "High", description: "Severe damage or loss of function." },
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
