"""Shared configuration and response checks for the two authentication examples."""

import os
from dataclasses import dataclass
from typing import Literal

from openai.types.responses import Response


@dataclass(frozen=True)
class SampleOptions:
    model: str
    effort: Literal["low", "medium", "high", "xhigh", "max"]
    max_output_tokens: int


def load_options() -> SampleOptions:
    model = os.getenv("AZURE_OPENAI_GPT_DEPLOYMENT_NAME", "gpt-6.1-sol")
    if not model.strip():
        raise ValueError("AZURE_OPENAI_GPT_DEPLOYMENT_NAME must not be empty")

    effort = os.getenv("AZURE_OPENAI_REASONING_EFFORT", "medium")
    if effort != "low" and effort != "medium" and effort != "high" and effort != "xhigh" and effort != "max":
        raise ValueError("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max")

    tokens = os.getenv("AZURE_OPENAI_MAX_OUTPUT_TOKENS", "16384")
    if not tokens.isascii() or not tokens.isdecimal() or not 16 <= int(tokens) <= 128000:
        raise ValueError("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000")

    return SampleOptions(model, effort, int(tokens))


def print_response(response: Response) -> None:
    if response.status != "completed":
        raise RuntimeError(
            f"Response did not complete: {response.status}; "
            f"details={response.incomplete_details}; error={response.error}"
        )
    if not response.output_text.strip():
        raise RuntimeError("Response completed without output text")
    if response.usage is None:
        raise RuntimeError("Response completed without token usage")

    print(f"Response: {response.output_text}")
    print(f"Status: {response.status}")
    print(f"Reasoning tokens: {response.usage.output_tokens_details.reasoning_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}\n")
