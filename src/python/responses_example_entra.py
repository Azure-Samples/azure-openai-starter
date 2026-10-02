#!/usr/bin/env python3
"""
Azure OpenAI GPT-6.1 Sol - Responses API with EntraID Authentication
This demonstrates using Azure Identity (EntraID) instead of API keys.
"""

import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI
from sample_options import load_options, print_response

load_dotenv()


def main():
    """Run Responses API examples with EntraID authentication."""
    print("Azure OpenAI GPT-6.1 Sol - EntraID Authentication\n")
    
    # Get required environment variables - raises KeyError if missing
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    if not endpoint.strip():
        raise ValueError("AZURE_OPENAI_ENDPOINT must not be empty")
    options = load_options()
    print(f"Deployment: {options.model}; reasoning effort: {options.effort}\n")
    
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
        model=options.model,
        input="Explain quantum computing in simple terms in at most 150 words.",
        reasoning={"effort": options.effort},
        max_output_tokens=options.max_output_tokens
    )
    print_response(response)
    
    # Example 2: Conversation format with Responses API
    print("Example 2: Conversation format\n")
    response = client.responses.create(
        model=options.model,
        input=[
            {"role": "system", "content": "You are an Azure cloud architect."},
            {"role": "user", "content": "Design a scalable web application architecture in at most 150 words."}
        ],
        reasoning={"effort": options.effort},
        max_output_tokens=options.max_output_tokens
    )
    print_response(response)


if __name__ == "__main__":
    main()
