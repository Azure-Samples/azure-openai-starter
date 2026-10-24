"""Classify a support request using the Azure OpenAI Decisions API."""

import argparse
import base64
import json
import os
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

from azure.identity import AzureDeveloperCliCredential, DefaultAzureCredential, get_bearer_token_provider
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
            print(f"  probabilities={json.dumps([item.model_dump() for item in answer.probabilities])}")
        elif answer.type == "score":
            print(f"{answer.name}: score value={answer.score} confidence={answer.confidence}")
            print(f"  probabilities={json.dumps([item.model_dump() for item in answer.probabilities])}")
        elif answer.type == "refusal":
            print(f"{answer.name}: refusal (send this question for human review)")
        else:
            raise RuntimeError(f"Unexpected decision answer type: {answer.type}")
    print(f"Usage: {decision.usage.model_dump_json()}")


def image_url(source: str | None) -> str | None:
    if source is None:
        return None
    if "://" in source:
        url = urlsplit(source)
        if url.scheme != "https" or not url.hostname or url.username is not None or url.fragment:
            raise ValueError("Image URLs must be publicly accessible HTTPS URLs without user information or fragments")
        return source
    path = Path(source)
    media_type = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif",
    }.get(path.suffix.lower())
    if media_type is None:
        raise ValueError("Image files must be PNG, JPEG, WebP, or GIF")
    if not 0 < path.stat().st_size <= 32 * 1024 * 1024:
        raise ValueError("Image files must be nonempty and no larger than 32 MB")
    return f"data:{media_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Real photo file or publicly accessible HTTPS photo URL")
    args = parser.parse_args(argv)
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].strip()
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT must not be empty")
    # This is your Azure deployment name; the deployment must host gpt-6-luna.
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-6-luna")
    if not deployment.strip():
        raise ValueError("AZURE_OPENAI_DEPLOYMENT must not be empty")

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

    photo = image_url(args.image)
    credential = None
    # Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
    if not api_key:
        # An explicitly selected azd credential needs its resource tenant forwarded.
        credential = (
            AzureDeveloperCliCredential(tenant_id=os.getenv("AZURE_TENANT_ID"))
            if os.getenv("AZURE_TOKEN_CREDENTIALS", "").lower() == "azuredeveloperclicredential"
            else DefaultAzureCredential()
        )
        api_key = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
    try:
        # Create once and reuse for more batches so connections stay warm.
        with OpenAI(
            base_url=f"{endpoint.rstrip('/')}/openai/v1/",
            api_key=api_key,
        ) as client:
            decision = client.decisions.create(
                model=deployment,
                input=(
                    [{"role": "user", "content": [
                        {"type": "input_text", "text": "Inspect the photo for visible damage and classify the main object."},
                        {"type": "input_image", "image_url": photo},
                    ]}]
                    if photo is not None else
                    "I was charged twice for order 123. Please refund the duplicate charge."
                ),
                # Batch related questions; the service accepts at most 400.
                questions=[
                    {
                        "type": "predicate",
                        "name": "visible_damage" if photo else "refund_requested",
                        "instructions": (
                            "Does the photo show visible damage to the main object?"
                            if photo else "Does the customer request a refund?"
                        ),
                    },
                    {
                        "type": "choice",
                        "name": "category" if photo else "department",
                        "instructions": (
                            "Which category best describes the main object?"
                            if photo else "Which department should handle this request?"
                        ),
                        "choices": [
                            {"value": "parcel", "description": "A package or parcel."},
                            {"value": "vehicle", "description": "A vehicle."},
                            {"value": "other", "description": "None of these categories."},
                        ] if photo else [
                            {"value": "billing", "description": "Payments and refunds."},
                            {"value": "technical", "description": "Product problems."},
                            {"value": "other", "description": "Other requests."},
                        ],
                    },
                    {
                        "type": "score",
                        "name": "severity",
                        "instructions": "How severe is the visible damage?" if photo else "How severe is this issue?",
                        "levels": [
                            {"label": "Low", "description": "No damage or minor cosmetic damage."},
                            {"label": "Medium", "description": "Visible damage that needs attention."},
                            {"label": "High", "description": "Severe damage or loss of function."},
                        ] if photo else [
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
