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
    def test_decisions_tabs_include_the_six_real_sample_files(self) -> None:
        article = ROOT / "docs" / "decisions.md"
        text = article.read_text(encoding="utf-8")
        tabs = re.findall(r"^# \[.+\]\(#tab/([a-z]+)\)$", text, re.MULTILINE)
        self.assertEqual(tabs, ["python", "typescript", "go", "java", "ruby", "csharp"])
        includes = re.findall(r"\[!code-[a-z]+\[[^\]]*\]\(([^)]+)\)\]", text)
        self.assertEqual(len(includes), 6)
        for relative in includes:
            with self.subTest(source=relative):
                self.assertTrue((article.parent / relative).resolve().is_file())
        self.assertIn("HttpClient", text)
        self.assertIn("400 questions", text)
        self.assertIn("East US 2", text)

    def test_hero_matches_title_and_describes_optional_deployment(self) -> None:
        root = ET.parse(ROOT / "images" / "architecture.svg").getroot()
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        self.assertEqual(root.find("svg:title", namespace).text, "The Azure OpenAI Starter Kit")
        text = " ".join(root.itertext())
        for required in ("2026-09-29", "2026-09-22", "opt-in", "Decisions REST", "Ruby"):
            self.assertIn(required, text)
        self.assertEqual(root.attrib["viewBox"], "0 0 1440 880")

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
        ):
            with self.subTest(source=source):
                text = (ROOT / source).read_text()
                self.assertIn("AZURE_OPENAI_DEPLOYMENT", text)
                self.assertNotIn("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME", text)
                self.assertIn("--image", text)


if __name__ == "__main__":
    unittest.main()
