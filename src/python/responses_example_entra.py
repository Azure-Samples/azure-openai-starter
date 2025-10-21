#!/usr/bin/env python3
"""
Azure OpenAI GPT-5-mini - Responses API with EntraID Authentication
This demonstrates using Azure Identity (EntraID) instead of API keys.
"""

import os
import sys
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def check_environment():
    """Verify required environment variables are set."""
    required_vars = ["AZURE_OPENAI_ENDPOINT"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\nRun this command to set it:")
        print("$endpoint = azd env get-values | Select-String 'AZURE_OPENAI_ENDPOINT' | ForEach-Object { $_ -replace 'AZURE_OPENAI_ENDPOINT=\"(.*)\"', '$1' }")
        print("$env:AZURE_OPENAI_ENDPOINT = $endpoint")
        sys.exit(1)
    
    print("✅ Environment variables configured")


def main():
    """Run Responses API examples with EntraID authentication."""
    print("=" * 60)
    print("Azure OpenAI GPT-5-mini - EntraID Authentication")
    print("=" * 60)
    
    check_environment()
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    
    # Use DefaultAzureCredential for EntraID authentication
    # This automatically uses your Azure CLI login, Managed Identity, or other credential sources
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
    
    # Initialize OpenAI client with Azure endpoint and EntraID authentication
    client = OpenAI(
        base_url=f"{endpoint}openai/v1/",
        api_key=token_provider
    )
    
    print("✅ Authenticated using EntraID (Azure Identity)")
    
    # Example 1: Simple text input with Responses API
    print("\n📝 Example 1: Simple text input")
    print("-" * 60)
    response = client.responses.create(
        model="gpt-5-mini",
        input="Explain quantum computing in simple terms",
        max_output_tokens=1000
    )
    print(f"Response: {response.output_text}")
    print(f"Status: {response.status}")
    print(f"Reasoning tokens: {response.usage.output_tokens_details.reasoning_tokens}")
    print(f"Output tokens: {response.usage.output_tokens}")
    
    # Example 2: Conversation format with Responses API
    print("\n📝 Example 2: Conversation format")
    print("-" * 60)
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
    
    print("\n" + "=" * 60)
    print("✅ All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
