import "dotenv/config";
import { readFileSync, statSync } from "node:fs";
import { isIP } from "node:net";
import { extname } from "node:path";
import OpenAI from "openai";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";

function imageUrl(source: string | undefined): string | undefined {
    if (source === undefined) {
        return undefined;
    }
    if (source.includes("://")) {
        const url = new URL(source);
        if (url.protocol !== "https:" || !url.hostname || url.username || url.password || url.hash) {
            throw new Error("Image URLs must be publicly accessible HTTPS URLs without user information or fragments");
        }
        return source;
    }
    const mediaTypes: Record<string, string> = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif",
    };
    const mediaType = mediaTypes[extname(source).toLowerCase()];
    if (!mediaType) {
        throw new Error("Image files must be PNG, JPEG, WebP, or GIF");
    }
    const size = statSync(source).size;
    if (size === 0 || size > 32 * 1024 * 1024) {
        throw new Error("Image files must be nonempty and no larger than 32 MB");
    }
    return `data:${mediaType};base64,${readFileSync(source).toString("base64")}`;
}

async function main(): Promise<void> {
    const args = process.argv.slice(2);
    if (args.length !== 0 && (args.length !== 2 || args[0] !== "--image")) {
        throw new Error("Usage: decisions_example [--image PATH_OR_HTTPS_URL]");
    }
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT?.trim();
    if (!endpoint) {
        throw new Error("AZURE_OPENAI_ENDPOINT must not be empty");
    }
    // This is your Azure deployment name; the deployment must host gpt-6-luna.
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT ?? "gpt-6-luna";
    if (!deployment.trim()) {
        throw new Error("AZURE_OPENAI_DEPLOYMENT must not be empty");
    }
    const apiKey = process.env.AZURE_OPENAI_API_KEY;
    let url: URL;
    try {
        url = new URL(endpoint);
    } catch {
        throw new Error("AZURE_OPENAI_ENDPOINT must be the Azure resource root URL");
    }
    if (url.username || url.password || endpoint.includes("@") || url.pathname.replace(/\/+$/, "")
        || endpoint.includes("?") || endpoint.includes("#") || endpoint.includes("\\")
        || /\s/.test(endpoint) || url.port === "0") {
        throw new Error("AZURE_OPENAI_ENDPOINT must be the Azure resource root URL");
    }
    const hostname = url.hostname.replace(/^\[|\]$/g, "");
    const loopback = hostname === "localhost"
        || (isIP(hostname) === 4 && hostname.startsWith("127."))
        || hostname === "::1";
    if (url.protocol !== "https:" && !(url.protocol === "http:" && loopback && apiKey)) {
        throw new Error("AZURE_OPENAI_ENDPOINT must use HTTPS (HTTP loopback is allowed with an API key)");
    }
    const photo = imageUrl(args[1]);
    // Create once and reuse for more batches so connections stay warm.
    const client = new OpenAI({
        baseURL: `${endpoint.replace(/\/+$/, "")}/openai/v1/`,
        // Entra ID is the default; an explicitly set API key is the fallback.
        apiKey: apiKey || getBearerTokenProvider(
            new DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        ),
    });
    const decision = await client.decisions.create({
        model: deployment,
        input: photo ? [{ role: "user", content: [
            { type: "input_text", text: "Inspect the photo for visible damage and classify the main object." },
            { type: "input_image", image_url: photo },
        ] }] : "I was charged twice for order 123. Please refund the duplicate charge.",
        // Batch related questions; the service accepts at most 400.
        questions: [
            {
                type: "predicate",
                name: photo ? "visible_damage" : "refund_requested",
                instructions: photo ? "Does the photo show visible damage to the main object?" : "Does the customer request a refund?",
            },
            {
                type: "choice",
                name: photo ? "category" : "department",
                instructions: photo ? "Which category best describes the main object?" : "Which department should handle this request?",
                choices: photo ? [
                    { value: "parcel", description: "A package or parcel." },
                    { value: "vehicle", description: "A vehicle." },
                    { value: "other", description: "None of these categories." },
                ] : [
                    { value: "billing", description: "Payments and refunds." },
                    { value: "technical", description: "Product problems." },
                    { value: "other", description: "Other requests." },
                ],
            },
            {
                type: "score",
                name: "severity",
                instructions: photo ? "How severe is the visible damage?" : "How severe is this issue?",
                levels: photo ? [
                    { label: "Low", description: "No damage or minor cosmetic damage." },
                    { label: "Medium", description: "Visible damage that needs attention." },
                    { label: "High", description: "Severe damage or loss of function." },
                ] : [
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
                throw new Error("Unexpected decision answer type");
        }
    }
    console.log(`Usage: ${JSON.stringify(decision.usage)}`);
}

main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
});
