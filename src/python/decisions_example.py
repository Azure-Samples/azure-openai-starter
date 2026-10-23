"""Classify a support request using the Azure OpenAI Decisions API."""

import json
import os
from ipaddress import ip_address
from urllib.parse import urlsplit

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.decision import Decision

load_dotenv()


def print_decision(decision: Decision) -> None:
    if not decision.answers:
        raise RuntimeError("Decision returned no answers")
    if decision.usage is None:
        raise RuntimeError("Decision returned no token usage")
    for answer in decision.answers:
        if answer.type == "predicate":
            print(f"{answer.name}: predicate probability={answer.probability}")
        elif answer.type == "choice":
            print(
                f"{answer.name}: choice value={json.dumps(answer.choice)} "
                f"confidence={answer.confidence}"
            )
        elif answer.type == "score":
            print(f"{answer.name}: score value={answer.score} confidence={answer.confidence}")
        elif answer.type == "refusal":
            print(f"{answer.name}: refusal (send this question for human review)")
        else:
            raise RuntimeError(f"Unexpected decision answer type: {answer.type}")
    print(f"Input tokens: {decision.usage.input_tokens}")


def main() -> None:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].strip()
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT must not be empty")
    deployment = os.getenv("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME", "gpt-6-luna")
    if not deployment.strip():
        raise ValueError("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME must not be empty")

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    try:
        url = urlsplit(endpoint)
        hostname = url.hostname
        port = url.port
    except ValueError as error:
        raise ValueError("AZURE_OPENAI_ENDPOINT must be the Azure resource root URL") from error
    if (not hostname or url.username is not None or url.password is not None
            or url.path.strip("/") or "?" in endpoint or "#" in endpoint
            or "\\" in endpoint or any(character.isspace() for character in endpoint)
            or port == 0):
        raise ValueError("AZURE_OPENAI_ENDPOINT must be the Azure resource root URL")
    try:
        loopback = ip_address(hostname).is_loopback
    except ValueError:
        loopback = hostname == "localhost"
    if url.scheme != "https" and not (url.scheme == "http" and loopback and api_key):
        raise ValueError(
            "AZURE_OPENAI_ENDPOINT must use HTTPS (HTTP loopback is allowed with an API key)"
        )

    credential = None
    if not api_key:
        credential = DefaultAzureCredential()
        api_key = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
    try:
        with OpenAI(
            base_url=f"{endpoint.rstrip('/')}/openai/v1/",
            api_key=api_key,
        ) as client:
            decision = client.decisions.create(
                model=deployment,
                input="I was charged twice for order 123. Please refund the duplicate charge.",
                questions=[
                    {
                        "type": "predicate",
                        "name": "refund_requested",
                        "instructions": "Does the customer request a refund?",
                    },
                    {
                        "type": "choice",
                        "name": "department",
                        "instructions": "Which department should handle this request?",
                        "choices": [
                            {"value": "billing", "description": "Payments and refunds."},
                            {"value": "technical", "description": "Product problems."},
                            {"value": "other", "description": "Other requests."},
                        ],
                    },
                    {
                        "type": "score",
                        "name": "severity",
                        "instructions": "How severe is this issue?",
                        "levels": [
                            {"label": "Low", "description": "Minor inconvenience."},
                            {"label": "Medium", "description": "Needs attention."},
                            {"label": "High", "description": "Urgent action needed."},
                        ],
                    },
                ],
            )
            print_decision(decision)
    finally:
        if credential is not None:
            credential.close()


if __name__ == "__main__":
    main()
