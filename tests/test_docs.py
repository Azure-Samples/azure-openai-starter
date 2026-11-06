"""Keep the documentation tabs linked to the runnable public samples."""

from pathlib import Path
import hashlib
import json
import re
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_decisions_tabs_include_the_real_text_and_multimodal_sample_files(self) -> None:
        article = ROOT / "docs" / "decisions.md"
        text = article.read_text(encoding="utf-8")
        languages = ["python", "typescript", "go", "java", "ruby", "csharp"]
        tabs = re.findall(r"^# \[.+\]\(#tab/([a-z]+)\)$", text, re.MULTILINE)
        self.assertEqual(tabs, languages * 2)
        includes = re.findall(r"\[!code-[a-z]+\[[^\]]*\]\(([^)]+)\)\]", text)
        self.assertEqual(len(includes), 12)
        # The text examples come first, then the multimodal examples, in the same language order.
        self.assertEqual(["multimodal" in relative.lower() for relative in includes], [False] * 6 + [True] * 6)
        for relative in includes:
            with self.subTest(source=relative):
                self.assertTrue((article.parent / relative).resolve().is_file())
        self.assertIn("DecisionsClient", text)
        self.assertNotIn("HttpClient", text)
        self.assertIn("400 questions", text)
        self.assertIn("East US 2", text)

    def test_hero_matches_title_and_describes_optional_deployment(self) -> None:
        root = ET.parse(ROOT / "images" / "architecture.svg").getroot()
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", readme, re.MULTILINE)
        self.assertIsNotNone(title)
        self.assertEqual(root.find("svg:title", namespace).text, title.group(1))
        text = " ".join(root.itertext())
        for required in ("2026-09-29", "2026-09-22", "opt-in", "Six native Decisions SDKs", "Ruby"):
            self.assertIn(required, text)
        self.assertNotIn("REST", text)
        self.assertEqual(root.attrib["viewBox"], "0 0 1440 880")
        for group, required, forbidden in (
            ("responses-api", ("Responses API", "GPT-6.1 Sol", "DEFAULT", "POST /openai/v1/responses"),
             ("GPT-6 Luna", "OPT-IN")),
            ("decisions-api", ("Decisions API", "GPT-6 Luna", "OPT-IN", "POST /openai/v1/decisions"),
             ("GPT-6.1 Sol", "DEFAULT")),
        ):
            with self.subTest(api=group):
                card = root.find(f".//svg:g[@id='{group}']", namespace)
                self.assertIsNotNone(card)
                visible = " ".join("".join(item.itertext()) for item in card.findall(".//svg:text", namespace))
                for label in required:
                    self.assertIn(label, visible)
                for label in forbidden:
                    self.assertNotIn(label, visible)

    def test_hero_png_is_readme_sized_and_svg_is_self_contained(self) -> None:
        image = (ROOT / "images" / "aoaistarterimage.png").read_bytes()
        self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack(">II", image[16:24]), (1100, 672))
        root = ET.parse(ROOT / "images" / "architecture.svg").getroot()
        for logo in root.findall(".//{http://www.w3.org/2000/svg}image"):
            self.assertTrue(logo.attrib["href"].startswith("data:image/"))

    def test_readme_overview_links_to_both_quickstarts(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        start = readme.index("## Overview")
        end = readme.index("## Architecture")
        self.assertLess(start, end)
        overview = readme[start:end]
        for required in (
            "Responses API", "Decisions API", "GPT-6.1 Sol (default)", "GPT-6 Luna (opt-in)",
            "(#quick-start-responses)", "(#quick-start-decisions)",
        ):
            with self.subTest(content=required):
                self.assertIn(required, overview)
        prose = " ".join(line for line in overview.splitlines() if not line.startswith(("#", "|")))
        self.assertLessEqual(len(prose.split()), 55)
        self.assertEqual(len([line for line in overview.splitlines() if line.startswith("|")]), 4)
        self.assertIn("## Quick start: Responses", readme)
        self.assertIn("## Quick start: Decisions", readme)
        self.assertNotIn("## New: Decisions API", readme)
        self.assertIn("](./images/aoaistarterimage.png)", readme)

    def test_decisions_quickstart_is_short_and_runnable(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(r"^## Quick start: Decisions\n(.*?)(?=^## |\Z)", readme, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match)
        quickstart = match.group(1).strip()
        self.assertLessEqual(len(quickstart.splitlines()), 60)
        prose = re.sub(r"```.*?```", "", quickstart, flags=re.DOTALL)
        self.assertLessEqual(len(prose.split()), 150)
        for required in (
            "GPT-6 Luna", "AZURE_OPENAI_DEPLOY_DECISIONS true", "azd up",
            "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT",
            "decisions_example.py", "decisions_multimodal_example.py",
            "```bash", "```powershell", "CLIENT_README.md",
        ):
            with self.subTest(content=required):
                self.assertIn(required, quickstart)
        self.assertNotIn("azd env set AZURE_LOCATION", quickstart)
        self.assertNotIn("## Azure behavior and latency notes", readme)

    def test_readme_detail_links_resolve_in_client_guide(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "CLIENT_README.md").read_text(encoding="utf-8")
        for required in (
            "## Decisions deployment", "## Decisions API notes", "East US 2",
            "DataZoneStandard", "GlobalStandard", "AZURE_OPENAI_DECISIONS_MODEL_VERSION",
            "AZURE_OPENAI_DECISIONS_CAPACITY",
        ):
            with self.subTest(content=required):
                self.assertIn(required, guide)
        headings = re.findall(r"^#{1,6} (.+)$", guide, re.MULTILINE)
        anchors = {re.sub(r"[^\w\s-]", "", heading).lower().replace(" ", "-") for heading in headings}
        links = re.findall(r"\]\(\./CLIENT_README\.md#([^)]+)\)", readme)
        self.assertTrue(links)
        for anchor in links:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, anchors)

    def test_photo_is_the_attributed_real_public_domain_fixture(self) -> None:
        photo = (ROOT / "images" / "decisions-photo.png").read_bytes()
        self.assertTrue(photo.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack(">II", photo[16:24]), (512, 512))
        self.assertEqual(hashlib.sha256(photo).hexdigest(),
                         "88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5")
        attribution = (ROOT / "images" / "decisions-photo.md").read_text()
        self.assertIn("public domain", attribution)
        self.assertIn("v0.25.2", attribution)

    def test_exact_sdk_pins_and_common_decisions_configuration(self) -> None:
        self.assertIn("openai==3.37.0", (ROOT / "src" / "python" / "requirements.txt").read_text())
        manifest = json.loads((ROOT / "src" / "typescript" / "package.json").read_text())
        lock = json.loads((ROOT / "src" / "typescript" / "package-lock.json").read_text())
        self.assertEqual(manifest["dependencies"]["openai"], "7.43.0")
        self.assertEqual(lock["packages"][""]["dependencies"]["openai"], "7.43.0")
        self.assertIn("AZURE_OPENAI_DEPLOYMENT=", (ROOT / ".env.example").read_text())
        for source in (
            "src/python/decisions_example.py", "src/typescript/decisions_example.ts",
            "src/go/decisions_example/main.go",
            "src/java/src/main/java/com/azure/openai/starter/DecisionsExample.java",
            "src/dotnet/decisions_example.cs", "src/ruby/decisions_example.rb",
            "src/python/decisions_multimodal_example.py", "src/typescript/decisions_multimodal_example.ts",
            "src/go/decisions_multimodal_example/main.go",
            "src/java/src/main/java/com/azure/openai/starter/DecisionsMultimodalExample.java",
            "src/dotnet/decisions_multimodal_example.cs", "src/ruby/decisions_multimodal_example.rb",
        ):
            with self.subTest(source=source):
                text = (ROOT / source).read_text()
                self.assertIn("AZURE_OPENAI_DEPLOYMENT", text)
                self.assertNotIn("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME", text)
                # Only the multimodal examples take an image, and they default to the documented photo.
                self.assertEqual("v0.25.2/skimage/data/astronaut.png" in text, "multimodal" in source.lower())
                self.assertNotIn("--image", text)

    def test_dotnet_configuration_example_contains_no_secret_and_matches_sections(self) -> None:
        settings = json.loads((ROOT / "src" / "dotnet" / "appsettings.example.json").read_text())
        self.assertEqual(set(settings["Clients"]), {"Responses", "Decisions"})
        for name, deployment in (("Responses", "gpt-6.1-sol"), ("Decisions", "gpt-6-luna")):
            with self.subTest(client=name):
                client = settings["Clients"][name]
                self.assertEqual(client["Model"], deployment)
                self.assertEqual(client["Credential"]["CredentialSource"], "AzureDeveloperCliCredential")
                self.assertNotIn("Key", client["Credential"])
                self.assertEqual(client["Credential"]["Scope"], "https://cognitiveservices.azure.com/.default")
                self.assertTrue(client["Options"]["Endpoint"].endswith("/openai/v1/"))
                self.assertIn("YOUR-RESOURCE", client["Options"]["Endpoint"])

    def test_dotnet_readme_registration_snippet_matches_both_responses_samples(self) -> None:
        readme = (ROOT / "src" / "dotnet" / "README.md").read_text(encoding="utf-8")
        match = re.search(r"```csharp\n(.*?)```", readme, re.DOTALL)
        self.assertIsNotNone(match)
        snippet = [line.strip() for line in match.group(1).splitlines() if line.strip()]
        self.assertGreater(len(snippet), 1)
        for filename in ("responses_example.cs", "responses_example_entra.cs"):
            with self.subTest(source=filename):
                text = (ROOT / "src" / "dotnet" / filename).read_text(encoding="utf-8")
                source = [line.strip() for line in text.splitlines()]
                position = 0
                for line in snippet:
                    self.assertIn(line, source[position:], f"{filename} no longer matches README line: {line}")
                    position = source.index(line, position) + 1

    def test_samples_use_native_openai_clients_without_azure_openai_wrappers(self) -> None:
        forbidden = re.compile(
            r"\bAzureOpenAI(?:Client|ClientBuilder)?\b|Azure\.AI\.OpenAI|@azure/openai|"
            r"azure-ai-openai|com\.azure\.ai\.openai|sdk/ai/azopenai"
        )
        source = ROOT / "src"
        patterns = (
            "python/*.py", "python/requirements.txt",
            "typescript/*.ts", "typescript/package*.json",
            "go/*/main.go", "go/*/go.mod", "go/*/go.sum",
            "java/pom.xml", "java/src/main/java/com/azure/openai/starter/*.java",
            "dotnet/*.cs", "ruby/*.rb", "ruby/Gemfile*",
        )
        for pattern in patterns:
            for path in source.glob(pattern):
                with self.subTest(source=path.relative_to(ROOT)):
                    self.assertIsNone(forbidden.search(path.read_text(encoding="utf-8-sig")))
        for filename in ("responses_example.cs", "responses_example_entra.cs"):
            text = (source / "dotnet" / filename).read_text()
            self.assertIn('builder.AddResponsesClient("Clients:Responses")', text)
            self.assertNotIn("AddAzureClient", text)
            self.assertNotIn('builder.Configuration["AZURE_OPENAI_', text)
            self.assertNotIn('settings["Credential:', text)

    def test_dotnet_readme_decisions_snippet_matches_both_decisions_samples(self) -> None:
        readme = (ROOT / "src" / "dotnet" / "README.md").read_text(encoding="utf-8")
        blocks = [block for block in re.findall(r"```csharp\n(.*?)```", readme, re.DOTALL)
                  if "AddDecisionsClient" in block]
        self.assertEqual(len(blocks), 1, "Expected one registration snippet for the Decisions client")
        snippet = [line.strip() for line in blocks[0].splitlines() if line.strip()]
        self.assertGreater(len(snippet), 1)
        for filename in ("decisions_example.cs", "decisions_multimodal_example.cs"):
            with self.subTest(source=filename):
                text = (ROOT / "src" / "dotnet" / filename).read_text(encoding="utf-8")
                source = [line.strip() for line in text.splitlines()]
                position = 0
                for line in snippet:
                    self.assertIn(line, source[position:], f"{filename} no longer matches README line: {line}")
                    position = source.index(line, position) + 1

    def test_dotnet_decisions_uses_the_typed_client_without_protocol_methods(self) -> None:
        for filename in ("decisions_example.cs", "decisions_multimodal_example.cs"):
            with self.subTest(source=filename):
                text = (ROOT / "src" / "dotnet" / filename).read_text(encoding="utf-8")
                self.assertIn('builder.AddDecisionsClient("Clients:Decisions")', text)
                self.assertIn("decisionsClient.CreateDecisionAsync(options)", text)
                # Comments may mention these APIs to explain what the sample avoids; only code is checked.
                code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("//"))
                for forbidden in ("BinaryContent", "HttpClient", "HttpRequestMessage", "ModelReaderWriter",
                                  "JsonSerializer"):
                    self.assertNotIn(forbidden, code)

    def test_dotnet_samples_pin_the_openai_version_documented_in_the_readme(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        documented = re.search(r"nuget\.org/packages/OpenAI/(\d+\.\d+\.\d+)\)", readme)
        self.assertIsNotNone(documented, "The README SDK baseline table must link the .NET OpenAI version")
        pins = {}
        for path in sorted((ROOT / "src" / "dotnet").glob("*.cs")):
            match = re.search(r"^#:package OpenAI@(\S+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
            self.assertIsNotNone(match, f"{path.name} does not pin the OpenAI package")
            pins[path.name] = match.group(1)
        self.assertEqual(set(pins.values()), {documented.group(1)}, pins)


if __name__ == "__main__":
    unittest.main()
