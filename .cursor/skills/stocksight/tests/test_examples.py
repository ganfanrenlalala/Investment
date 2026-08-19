# -*- coding: utf-8 -*-
import tempfile
import unittest
from pathlib import Path

from scripts.render_examples import DEFAULT_EXAMPLES, render_examples


class ExampleSnapshotTests(unittest.TestCase):
    def test_fixed_examples_render_to_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            html_dir = base / "html"
            md_dir = base / "md"

            rendered = render_examples(out_dir=html_dir, markdown_dir=md_dir)

            self.assertEqual(len(rendered), len(DEFAULT_EXAMPLES))
            for html_path in rendered:
                html = html_path.read_text(encoding="utf-8")
                markdown = (md_dir / f"{html_path.stem}.md").read_text(encoding="utf-8")
                self.assertIn("<!doctype html>", html.lower())
                self.assertIn("报告口径", markdown)
                self.assertIn("Snapshot", html)


if __name__ == "__main__":
    unittest.main()
