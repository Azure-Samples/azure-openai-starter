# Azure OpenAI GPT-6.1 Sol Starter

This is a minimal Azure Developer CLI (azd) template deploying Azure OpenAI with
`gpt-6.1-sol`, model version `2026-09-29`, and the `GlobalStandard` SKU.

## Repository Layout

- `azure.yaml`: azd configuration; `azd up` must propagate provisioning failures.
- `infra/main.bicep`: resource-group-scoped deployment, allowed regions and capacity.
- `infra/resources.bicep`: Azure OpenAI account, optional model deployment and RBAC.
- `infra/main.parameters.json`: azd environment-to-Bicep parameter mapping.
- `src/python`, `src/typescript`, `src/go`, `src/dotnet`, `src/java`: Responses API
  examples for API-key and Entra ID authentication.
- `tests/test_samples.py`: builds and tests all five language clients; live tests
  require explicit `AZURE_OPENAI_LIVE_TESTS=1` opt-in.
- `validate.ps1`, `validate.sh`: source-file and Bicep checks, not live inference tests.
- `README.md`, `CLIENT_README.md`: deployment and client setup.
- `images/architecture.svg`, `images/aoaistarterimage.png`: editable and rendered hero diagram.

## Model and Client Contract

- Use the `/openai/v1/` base URL and Responses API; no `api-version` is required.
- Default deployment name: `gpt-6.1-sol`. Honor `AZURE_OPENAI_GPT_DEPLOYMENT_NAME`.
- Supported reasoning efforts: `low`, `medium` (default), `high`, `xhigh`, `max`.
  Reject `none`, `minimal`, blank and unknown values before making requests.
- `AZURE_OPENAI_MAX_OUTPUT_TOKENS` defaults to `16384`; valid range is `16..128000`.
  The budget includes internal reasoning. Incomplete or empty output is not success.
- All examples demonstrate simple text and system/user conversation requests.
- Keep settings and response checks consistent across both auth paths and all languages.
- The .NET and Go examples remain independently runnable; Python, TypeScript and
  Java share helpers within their language directories.
- Entra examples use `DefaultAzureCredential` for development and the
  `https://cognitiveservices.azure.com/.default` scope. Use a specific credential in production.
- Never persist API keys or access tokens in source, test output or documentation.

## Infrastructure

- The region is user-selected from the model's verified GlobalStandard region list.
- `AZURE_OPENAI_CAPACITY` defaults to `10` (10,000 TPM for this model).
- Resource names are generated from `resourceToken`.
- Assign the deploying user `Cognitive Services User` for Entra inference access.
- API-key authentication stays enabled for the key samples.
- `deployGptModel=false` must omit the model deployment and return an empty deployment-name output.
- Check the Azure catalog before changing a model ID, version, region or SKU.

## Validation

Run template validation with `.\validate.ps1` or `bash validate.sh`.

Run local client tests with:

```text
python -m unittest discover -s tests -v
```

With an explicitly authorized test deployment and both credentials configured:

```text
AZURE_OPENAI_LIVE_TESTS=1 python -m unittest discover -s tests -k live_matrix -v
```

The live matrix is billable: 5 languages x 2 auth paths x 5 reasoning efforts x
2 request formats = 100 responses. It uses Azure CLI for Entra authentication.
Do not claim coverage of streaming, tools, Batch, Chat Completions or hosted
managed identities based on these tests. Report skipped or blocked checks honestly.

Keep model/version references, SDK examples, documentation and the diagram aligned.
