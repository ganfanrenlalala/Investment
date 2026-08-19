# -*- coding: utf-8 -*-
import unittest
from pathlib import Path

from scripts.screenshot_report import build_screenshot_command


class ScreenshotReportTests(unittest.TestCase):
    def test_build_command_uses_file_uri_and_png_output(self):
        command = build_screenshot_command(
            browser=Path("C:/Chrome/chrome.exe"),
            html_path=Path("reports/sample.html"),
            output_path=Path("docs/images/sample.png"),
            width=1200,
            height=2400,
        )

        self.assertIn("--headless=new", command)
        self.assertIn("--hide-scrollbars", command)
        self.assertIn("--window-size=1200,2400", command)
        self.assertTrue(any(part.startswith("--screenshot=") for part in command))
        self.assertTrue(command[-1].startswith("file:///"))


if __name__ == "__main__":
    unittest.main()
