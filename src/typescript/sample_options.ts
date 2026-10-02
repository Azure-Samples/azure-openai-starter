import type { Response } from "openai/resources/responses/responses";

export function loadOptions(): {
    model: string;
    reasoning: { effort: "low" | "medium" | "high" | "xhigh" | "max" };
    max_output_tokens: number;
} {
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

    return { model, reasoning: { effort }, max_output_tokens: maxOutputTokens };
}

export function printResponse(response: Response): void {
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
