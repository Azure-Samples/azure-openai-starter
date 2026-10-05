#!/usr/bin/env python3
"""
Azure OpenAI GPT-6.1 Sol - Responses API with EntraID Authentication
This demonstrates using Azure Identity (EntraID) instead of API keys.
"""

import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import Response

load_dotenv()


def main() -> None:
    """Run Responses API examples with EntraID authentication."""
    print("Azure OpenAI GPT-6.1 Sol - EntraID Authentication\n")
    
    # Get required environment variables - raises KeyError if missing
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    if not endpoint.strip():
        raise ValueError("AZURE_OPENAI_ENDPOINT must not be empty")
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
    
    # Use DefaultAzureCredential for EntraID authentication
    # This automatically uses your Azure CLI login, Managed Identity, or other credential sources
    # For production, use a specific credential (e.g. ManagedIdentityCredential) or set
    # AZURE_TOKEN_CREDENTIALS to control which credential is used. See:
    # https://aka.ms/azsdk/python/identity/credential-chains#defaultazurecredential-overview
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    
    # Initialize OpenAI client with Azure endpoint and EntraID authentication (v1 API path)
    client = OpenAI(
        base_url=f"{endpoint.rstrip('/')}/openai/v1/",
        api_key=token_provider
    )
    
    # Example 1: Simple text input with Responses API
    print("Example 1: Simple text input\n")
    response = client.responses.create(
        model=model,
        input="Explain quantum computing in simple terms in at most 150 words.",
        reasoning={"effort": effort},
        max_output_tokens=max_output_tokens
    )
    print_response(response)
    
    # Example 2: Conversation format with Responses API
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
