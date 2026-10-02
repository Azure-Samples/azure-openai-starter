package com.azure.openai.starter;

import com.openai.models.Reasoning;
import com.openai.models.ReasoningEffort;
import com.openai.models.responses.Response;
import com.openai.models.responses.ResponseOutputText;
import com.openai.models.responses.ResponseStatus;

import java.util.Set;
import java.util.stream.Collectors;

record SampleOptions(String model, Reasoning reasoning, long maxOutputTokens) {
    static SampleOptions fromEnvironment() {
        String model = System.getenv().getOrDefault("AZURE_OPENAI_GPT_DEPLOYMENT_NAME", "gpt-6.1-sol");
        if (model.isBlank()) {
            throw new IllegalArgumentException("AZURE_OPENAI_GPT_DEPLOYMENT_NAME must not be empty");
        }

        String effort = System.getenv().getOrDefault("AZURE_OPENAI_REASONING_EFFORT", "medium");
        if (!Set.of("low", "medium", "high", "xhigh", "max").contains(effort)) {
            throw new IllegalArgumentException("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max");
        }

        String tokens = System.getenv().getOrDefault("AZURE_OPENAI_MAX_OUTPUT_TOKENS", "16384");
        long maxOutputTokens;
        try {
            maxOutputTokens = Long.parseLong(tokens);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000", e);
        }
        if (!tokens.matches("[0-9]+") || maxOutputTokens < 16 || maxOutputTokens > 128000) {
            throw new IllegalArgumentException("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000");
        }

        return new SampleOptions(model, Reasoning.builder().effort(ReasoningEffort.of(effort)).build(), maxOutputTokens);
    }

    static void printResponse(Response response) {
        if (!ResponseStatus.COMPLETED.equals(response.status().orElse(null))) {
            throw new IllegalStateException("Response did not complete: " + response.status()
                    + "; details=" + response.incompleteDetails() + "; error=" + response.error());
        }
        String text = response.output().stream()
                .flatMap(item -> item.message().stream())
                .flatMap(message -> message.content().stream())
                .flatMap(content -> content.outputText().stream())
                .map(ResponseOutputText::text)
                .collect(Collectors.joining());
        if (text.isBlank()) {
            throw new IllegalStateException("Response completed without output text");
        }
        var usage = response.usage().orElseThrow(
                () -> new IllegalStateException("Response completed without token usage"));

        System.out.println("Response: " + text);
        System.out.println("Status: " + response.status().orElseThrow());
        System.out.println("Reasoning tokens: " + usage.outputTokensDetails().reasoningTokens());
        System.out.println("Output tokens: " + usage.outputTokens());
        System.out.println();
    }
}
