#!/usr/bin/env python3
"""
Azure OpenAI GPT-6.1 Sol - Responses API Example
This demonstrates the Responses API with the GPT-6.1 Sol reasoning model.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import Response

load_dotenv()


def main() -> None:
    """Run Responses API examples."""
    print("Azure OpenAI GPT-6.1 Sol - Responses API\n")
    
    # Get required environment variables - raises KeyError if missing
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    if not endpoint.strip() or not api_key.strip():
        raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must not be empty")
    model = os.getenv("AZURE_OPENAI_GPT_DEPLOYMENT_NAME", "gpt-6.1-sol")
    if not model.strip():
        raise ValueError("AZURE_OPENAI_GPT_DEPLOYMENT_NAME must not be empty")
    effort = os.getenv("AZURE_OPENAI_REASONING_EFFORT", "medium")
    if effort != "low" and effort != "medium" and effort != "high" and effort != "xhigh" and effort != "max":
        raise ValueError("AZURE_OPENAI_REASONING_EFFORT must be low, medium, high, xhigh, or max")
    tokens = os.getenv("AZURE_OPENAI_MAX_OUTPUT_TOKENS", "16384")
    if not tokens.isascii() or not tokens.isdecimal() or not 16 <= int(tokens) <= 128000:
        raise ValueError("AZURE_OPENAI_MAX_OUTPUT_TOKENS must be an integer from 16 to 128000")
    max_output_tokens = int(tokens)
    print(f"Deployment: {model}; reasoning effort: {effort}\n")
    
    # Initialize OpenAI client with Azure endpoint (v1 API path)
    client = OpenAI(
        api_key=api_key,
        base_url=f"{endpoint.rstrip('/')}/openai/v1/"
    )
    
    # Example 1: Simple text input
    print("Example 1: Simple text input\n")
    response = client.responses.create(
        model=model,
        input="Explain quantum computing in simple terms in at most 150 words.",
        reasoning={"effort": effort},
        max_output_tokens=max_output_tokens
    )
    print_response(response)
    
    # Example 2: Conversation format
    print("Example 2: Conversation format\n")
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": "You are an Azure cloud architect."},
            {"role": "user", "content": "Design a scalable web application architecture in at most 150 words."}
        ],
        reasoning={"effort": effort},
        max_output_tokens=max_output_tokens
    )
    print_response(response)


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


if __name__ == "__main__":
    main()
