#!/usr/bin/env python3
"""
Azure OpenAI GPT-5-mini - Responses API with EntraID Authentication
This demonstrates using Azure Identity (EntraID) instead of API keys.
"""

import os
import sys

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)


def main():
    """Run Responses API examples with EntraID authentication."""
    print("Azure OpenAI GPT-5-mini - EntraID Authentication\n")
    
    # Get required environment variables - raises KeyError if missing
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    
    # Use DefaultAzureCredential for EntraID authentication
    # This automatically uses your Azure CLI login, Managed Identity, or other credential sources
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
        model="gpt-5-mini",
        input="Explain quantum computing in simple terms",
        max_output_tokens=1000
    )
    print(f"Response: {response.output_text}")
    print(f"Status: {response.status}")
    print(f"Reasoning tokens: {response.usage.output_tokens_details.reasoning_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}\n")
    
    # Example 2: Conversation format with Responses API
    print("Example 2: Conversation format\n")
    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": "You are an Azure cloud architect."},
            {"role": "user", "content": "Design a scalable web application architecture."}
        ],
        max_output_tokens=1000
    )
    print(f"Response: {response.output_text}")
    print(f"Status: {response.status}")
    print(f"Reasoning tokens: {response.usage.output_tokens_details.reasoning_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}")


if __name__ == "__main__":
    main()
