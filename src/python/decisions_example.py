"""Route a support ticket with the Azure OpenAI Decisions API."""

import json
import os

from azure.identity import AzureDeveloperCliCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.decision import Decision

load_dotenv()


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


if __name__ == "__main__":
    main()
