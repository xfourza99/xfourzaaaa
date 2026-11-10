import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = ROOT / "docs" / "images" / "bjt-ce-bias-circuit.png"
README = ROOT / "README.md"


class TestDocs(unittest.TestCase):
    def test_readme_embeds_the_circuit_image(self):
        text = README.read_text(encoding="utf-8")
        self.assertIn("docs/images/bjt-ce-bias-circuit.png", text)

    def test_circuit_image_is_a_committed_png(self):
        self.assertTrue(IMAGE.is_file(), "circuit image missing from docs/images")
        self.assertEqual(IMAGE.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")