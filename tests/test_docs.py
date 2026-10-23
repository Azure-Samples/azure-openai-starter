"""Keep the documentation tabs linked to the runnable public samples."""

from pathlib import Path
import re
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


if __name__ == "__main__":
    unittest.main()
