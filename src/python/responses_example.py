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
    missing = []
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        missing.append("AZURE_OPENAI_API_KEY")
    
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)


def main():
    """Run Responses API examples."""
    print("Azure OpenAI GPT-5-mini - Responses API\n")
    
    check_environment()
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    # Initialize OpenAI client with Azure endpoint
    client = OpenAI(
        api_key=api_key,
        base_url=f"{endpoint}openai/v1/"
    )
    
    # Example 1: Simple text input
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
    
    # Example 2: Conversation format
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
