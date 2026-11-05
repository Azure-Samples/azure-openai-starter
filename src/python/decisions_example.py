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
        match answer.type:
            case "predicate":
                print(f"{answer.name}: predicate probability={answer.probability}")
            case "choice":
                print(
                    f"{answer.name}: choice value={json.dumps(answer.choice)} "
                    f"confidence={answer.confidence}"
                )
                print(f"  probabilities={json.dumps([item.model_dump() for item in answer.probabilities])}")
            case "score":
                print(f"{answer.name}: score value={answer.score} confidence={answer.confidence}")
                print(f"  probabilities={json.dumps([item.model_dump() for item in answer.probabilities])}")
            case "refusal":
                print(f"{answer.name}: refusal (send this question for human review)")
            case _:
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


def text_request() -> tuple[str, list[dict]]:
    """Scenario 1: route a billing ticket (text input)."""
    text = "I was charged twice for order 123. Please refund the duplicate charge."
    questions = [
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
    ]
    return text, questions


def photo_request(photo: str) -> tuple[list[dict], list[dict]]:
    """Scenario 2: assess a photo (an HTTPS URL or an inline base64 data URL)."""
    messages = [{"role": "user", "content": [
        {"type": "input_text", "text": "Inspect the photo for visible damage and classify the main object."},
        {"type": "input_image", "image_url": photo},
    ]}]
    questions = [
        {
            "type": "predicate",
            "name": "visible_damage",
            "instructions": "Does the photo show visible damage to the main object?",
        },
        {
            "type": "choice",
            "name": "category",
            "instructions": "Which category best describes the main object?",
            "choices": [
                {"value": "parcel", "description": "A package or parcel."},
                {"value": "vehicle", "description": "A vehicle."},
                {"value": "other", "description": "None of these categories."},
            ],
        },
        {
            "type": "score",
            "name": "severity",
            "instructions": "How severe is the visible damage?",
            "levels": [
                {"label": "Low", "description": "No damage or minor cosmetic damage."},
                {"label": "Medium", "description": "Visible damage that needs attention."},
                {"label": "High", "description": "Severe damage or loss of function."},
            ],
        },
    ]
    return messages, questions


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
    decision_input, questions = text_request() if photo is None else photo_request(photo)
    credential = None
    # Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
    if not api_key:
        # DefaultAzureCredential builds the Azure Developer CLI credential without a tenant,
        # so when AZURE_TOKEN_CREDENTIALS selects that credential, create it directly with
        # the resource tenant. Otherwise a login that spans tenants may get a token for the
        # wrong one.
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
            # Batch related questions; the service accepts at most 400.
            decision = client.decisions.create(
                model=deployment,
                input=decision_input,
                questions=questions,
            )
            print_decision(decision)
    finally:
        if credential is not None:
            credential.close()


if __name__ == "__main__":
    main()
