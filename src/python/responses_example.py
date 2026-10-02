#!/usr/bin/env python3
"""
Azure OpenAI GPT-6.1 Sol - Responses API Example
This demonstrates the Responses API with the GPT-6.1 Sol reasoning model.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from sample_options import load_options, print_response

load_dotenv()


def main():
    """Run Responses API examples."""
    print("Azure OpenAI GPT-6.1 Sol - Responses API\n")
    
    # Get required environment variables - raises KeyError if missing
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    if not endpoint.strip() or not api_key.strip():
        raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must not be empty")
    options = load_options()
    print(f"Deployment: {options.model}; reasoning effort: {options.effort}\n")
    
    # Initialize OpenAI client with Azure endpoint (v1 API path)
    client = OpenAI(
        api_key=api_key,
        base_url=f"{endpoint.rstrip('/')}/openai/v1/"
    )
    
    # Example 1: Simple text input
    print("Example 1: Simple text input\n")
    response = client.responses.create(
        model=options.model,
        input="Explain quantum computing in simple terms in at most 150 words.",
        reasoning={"effort": options.effort},
        max_output_tokens=options.max_output_tokens
    )
    print_response(response)
    
    # Example 2: Conversation format
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
