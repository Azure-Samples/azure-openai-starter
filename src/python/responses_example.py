#!/usr/bin/env python3
"""
Azure OpenAI GPT-5-mini - Responses API Example
This demonstrates the new Responses API with GPT-5-mini reasoning model.
"""

import os
import sys
from openai import OpenAI


def check_environment():
    """Verify required environment variables are set."""
    required_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("\nRun these commands to set them:")
        print("$endpoint = azd env get-values | Select-String 'AZURE_OPENAI_ENDPOINT' | ForEach-Object { $_ -replace 'AZURE_OPENAI_ENDPOINT=\"(.*)\"', '$1' }")
        print("$apiKey = az cognitiveservices account keys list --name RESOURCE_NAME --resource-group RESOURCE_GROUP --query key1 -o tsv")
        print("$env:AZURE_OPENAI_ENDPOINT = $endpoint")
        print("$env:AZURE_OPENAI_API_KEY = $apiKey")
        sys.exit(1)
    
    print("✅ Environment variables configured")


def main():
    """Run Responses API examples."""
    print("=" * 60)
    print("Azure OpenAI GPT-5-mini - Responses API Examples")
    print("=" * 60)
    
    check_environment()
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    # Initialize OpenAI client with Azure endpoint
    client = OpenAI(
        api_key=api_key,
        base_url=f"{endpoint}openai/v1/"
    )
    
    # Example 1: Simple text input
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
    
    # Example 2: Conversation format
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
