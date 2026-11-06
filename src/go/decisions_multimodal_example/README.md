# Go Decisions multimodal example

Requires Go **1.26 or later**, the minimum required by OpenAI Go `v3.86.0`.
From this directory:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-6-luna"
go run .
go run . ..\..\..\images\decisions-photo.png
go run . "https://example.com/your-photo.png"
```

With no argument, the example sends a public-domain NASA photo by HTTPS URL, which
Azure fetches. Pass your own public HTTPS image URL or the path to a PNG, JPEG, WebP
or GIF file instead. A local file's bytes are base64-encoded inline with the
matching MIME type. The example asks about visible damage, the object category (with
an `other` fallback) and damage severity, and sends one image, below the API's
128-image limit. It never downloads the image itself.

Authentication, endpoint and deployment settings are the same as the
[text example](../decisions_example/README.md). All three questions are batched in
one call, and the output has the same shape: named answers, option probabilities
and token usage.
