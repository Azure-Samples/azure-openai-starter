"""Assess a photo with the Azure OpenAI Decisions API (text and image input)."""

import base64
import json
import mimetypes
import os
import sys

from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.decision import Decision

load_dotenv()

# A public-domain NASA photo. Azure fetches an HTTPS URL itself.
DEFAULT_IMAGE = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"


def print_decision(decision: Decision) -> None:
    if not decision.answers:
        raise RuntimeError("The response contains no answers.")
    if decision.usage is None:
        raise RuntimeError("The response contains no usage.")
    for answer in decision.answers:
        match answer.type:
            case "predicate":
                print(f"{answer.name}: predicate probability={answer.probability}")
            case "choice":
                print(f"{answer.name}: choice value={json.dumps(answer.choice)} confidence={answer.confidence}")
                print(f"  probabilities={json.dumps([item.model_dump() for item in answer.probabilities])}")
            case "score":
                print(f"{answer.name}: score value={answer.score} confidence={answer.confidence}")
                print(f"  probabilities={json.dumps([item.model_dump() for item in answer.probabilities])}")
            case "refusal":
                print(f"{answer.name}: refusal (send this question for human review)")
            case _:
                raise RuntimeError(f"The response contains an unknown answer type: {answer.type}.")
    print(f"Usage: {decision.usage.model_dump_json()}")


def main() -> None:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    # This is your Azure deployment name; the deployment must host gpt-6-luna.
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-6-luna")

    # Pass your own HTTPS image URL or the path to an image file.
    image = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE
    if not image.startswith("https://"):
        # A local file is sent inline as a base64 data URL.
        media_type = mimetypes.guess_type(image)[0]
        with open(image, "rb") as file:
            image = f"data:{media_type};base64,{base64.b64encode(file.read()).decode()}"

    # Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        # Use your `azd auth login` session, and the resource's tenant when AZURE_TENANT_ID is set.
        tenant_id = os.getenv("AZURE_TENANT_ID")
        if tenant_id:
            credential = AzureDeveloperCliCredential(tenant_id=tenant_id)
        else:
            credential = AzureDeveloperCliCredential()
        api_key = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

    client = OpenAI(base_url=f"{endpoint.rstrip('/')}/openai/v1/", api_key=api_key)

    # Batch related questions in one request; the service accepts at most 400.
    decision = client.decisions.create(
        model=deployment,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Inspect the photo for visible damage and classify the main object."},
                    {"type": "input_image", "image_url": image},
                ],
            }
        ],
        questions=[
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
        ],
    )
    print_decision(decision)


if __name__ == "__main__":
    main()
