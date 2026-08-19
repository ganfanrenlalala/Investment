#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Capture a StockSight HTML report as a long PNG screenshot.

When Playwright is available, this helper uses Chromium's real full-page
screenshot API. Otherwise it falls back to the dependency-free Chrome / Edge
CLI path, so agents can still turn generated HTML reports into shareable
long screenshots without installing Playwright/Pillow.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


DEFAULT_WIDTH = 1440
DEFAULT_HEIGHT = 5200
DEFAULT_ENGINE = "auto"
ENGINES = ("auto", "playwright", "cdp", "chrome")

DISABLE_CAPTURE_ANIMATIONS_SCRIPT = r"""
(() => {
  const id = "stocksight-capture-animation-guard";
  if (document.getElementById(id)) {
    return;
  }
  const style = document.createElement("style");
  style.id = id;
  style.textContent = `
    *, *::before, *::after {
      animation: none !important;
      transition: none !important;
      scroll-behavior: auto !important;
    }
    .panel,
    .judgment-hero,
    header {
      opacity: 1 !important;
      transform: none !important;
    }
  `;
  document.head.appendChild(style);
})();
"""


WINDOWS_BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

BROWSER_COMMANDS = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "msedge",
    "microsoft-edge",
]


class ScreenshotError(RuntimeError):
    """Raised when a screenshot cannot be produced."""


class ScreenshotEngineUnavailable(ScreenshotError):
    """Raised when a screenshot engine cannot run in the current environment."""


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture a StockSight HTML report as a long PNG screenshot.",
    )
    parser.add_argument("html", type=Path, help="Input HTML report path.")
    parser.add_argument(
        "--out",
        type=Path,
        help="Output PNG path. Defaults to input path with .png suffix.",
    )
    parser.add_argument("--browser", type=Path, help="Explicit Chrome/Edge executable path.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Viewport width.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Viewport height.")
    parser.add_argument(
        "--engine",
        choices=ENGINES,
        default=DEFAULT_ENGINE,
        help=(
            "Screenshot engine. 'auto' uses Playwright full-page screenshots "
            "when available, then falls back to Chrome DevTools Protocol."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Browser process timeout in seconds.",
    )
    return parser


def resolve_browser(explicit: Optional[Path] = None) -> Optional[Path]:
    """Find a Chrome/Edge executable suitable for headless screenshots."""
    if explicit:
        return explicit if explicit.exists() else None

    for env_name in ("STOCKSIGHT_BROWSER", "CHROME_BIN", "EDGE_BIN"):
        value = os.environ.get(env_name)
        if value and Path(value).exists():
            return Path(value)

    if os.name == "nt":
        for candidate in WINDOWS_BROWSER_CANDIDATES:
            path = Path(candidate)
            if path.exists():
                return path

    for command in BROWSER_COMMANDS:
        found = shutil.which(command)
        if found:
            return Path(found)
    return None


def build_screenshot_command(
    browser: Path,
    html_path: Path,
    output_path: Path,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> List[str]:
    """Build the browser command without executing it."""
    html_uri = html_path.resolve().as_uri()
    return [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=4000",
        f"--window-size={width},{height}",
        f"--screenshot={output_path.resolve()}",
        html_uri,
    ]


def capture_screenshot_playwright(
    html_path: Path,
    output_path: Path,
    browser_path: Optional[Path] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout: int = 30,
) -> Path:
    """Capture a true full-page screenshot using Playwright, if installed."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ScreenshotEngineUnavailable(
            "Playwright is not installed. Install it with 'pip install playwright' "
            "or use --engine chrome for the dependency-free fallback."
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_uri = html_path.resolve().as_uri()

    launch_kwargs = {"headless": True}
    if browser_path is not None:
        launch_kwargs["executable_path"] = str(browser_path)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_kwargs)
            try:
                page = browser.new_page(
                    viewport={"width": width, "height": max(720, min(height, DEFAULT_HEIGHT))},
                    device_scale_factor=1,
                )
                page.goto(html_uri, wait_until="load", timeout=timeout * 1000)
                page.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")
                page.evaluate(DISABLE_CAPTURE_ANIMATIONS_SCRIPT)
                page.screenshot(
                    path=str(output_path.resolve()),
                    full_page=True,
                    animations="disabled",
                    timeout=timeout * 1000,
                )
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise ScreenshotEngineUnavailable(f"Playwright screenshot failed: {exc}") from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ScreenshotError(f"Playwright finished but screenshot is empty: {output_path}")
    return output_path.resolve()


class _CdpWebSocket:
    """Tiny WebSocket client for local Chrome DevTools Protocol traffic."""

    def __init__(self, websocket_url: str, timeout: int) -> None:
        parsed = urlparse(websocket_url)
        if parsed.scheme != "ws" or not parsed.hostname or not parsed.port:
            raise ScreenshotError(f"Unsupported DevTools websocket URL: {websocket_url}")
        self._host = parsed.hostname
        self._port = parsed.port
        self._path = parsed.path
        if parsed.query:
            self._path += f"?{parsed.query}"
        self._timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._next_id = 1

    def __enter__(self) -> "_CdpWebSocket":
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        sock = socket.create_connection((self._host, self._port), timeout=self._timeout)
        sock.settimeout(self._timeout)
        request = (
            f"GET {self._path} HTTP/1.1\r\n"
            f"Host: {self._host}:{self._port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        sock.sendall(request.encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise ScreenshotError("Chrome DevTools websocket handshake failed")
        self._socket = sock
        return self

    def __exit__(self, *_exc_info: object) -> None:
        if self._socket is not None:
            try:
                self._socket.close()
            finally:
                self._socket = None

    def send(self, method: str, params: Optional[Dict[str, Any]] = None) -> int:
        message_id = self._next_id
        self._next_id += 1
        payload: Dict[str, Any] = {"id": message_id, "method": method}
        if params:
            payload["params"] = params
        self._send_text(json.dumps(payload, separators=(",", ":")))
        return message_id

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        message_id = self.send(method, params)
        while True:
            message = self._recv_json()
            if message.get("id") != message_id:
                continue
            if "error" in message:
                raise ScreenshotError(f"Chrome DevTools error in {method}: {message['error']}")
            return message.get("result", {})

    def wait_for_event(self, method: str, timeout: int) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self._recv_json()
            if message.get("method") == method:
                return
        raise ScreenshotError(f"Timed out waiting for Chrome DevTools event: {method}")

    def _send_text(self, text: str) -> None:
        if self._socket is None:
            raise ScreenshotError("Chrome DevTools websocket is not connected")
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend([0x80 | 126, (length >> 8) & 0xFF, length & 0xFF])
        else:
            header.append(0x80 | 127)
            header.extend(length.to_bytes(8, "big"))
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self._socket.sendall(bytes(header) + mask + masked)

    def _recv_json(self) -> Dict[str, Any]:
        chunks: List[bytes] = []
        while True:
            fin, opcode, payload = self._recv_frame()
            if opcode == 8:
                raise ScreenshotError("Chrome DevTools websocket closed unexpectedly")
            if opcode == 9:
                continue
            if opcode in (1, 0):
                chunks.append(payload)
            if fin:
                return json.loads(b"".join(chunks).decode("utf-8"))

    def _recv_frame(self) -> tuple[bool, int, bytes]:
        if self._socket is None:
            raise ScreenshotError("Chrome DevTools websocket is not connected")
        header = self._recv_exact(2)
        first, second = header
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = int.from_bytes(self._recv_exact(2), "big")
        elif length == 127:
            length = int.from_bytes(self._recv_exact(8), "big")
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return fin, opcode, payload

    def _recv_exact(self, length: int) -> bytes:
        if self._socket is None:
            raise ScreenshotError("Chrome DevTools websocket is not connected")
        chunks = bytearray()
        while len(chunks) < length:
            chunk = self._socket.recv(length - len(chunks))
            if not chunk:
                raise ScreenshotError("Chrome DevTools websocket ended unexpectedly")
            chunks.extend(chunk)
        return bytes(chunks)


def _read_devtools_port(profile_dir: Path, timeout: int) -> tuple[int, str]:
    active_port = profile_dir / "DevToolsActivePort"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if active_port.exists():
            lines = active_port.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) >= 2:
                return int(lines[0]), lines[1]
        time.sleep(0.05)
    raise ScreenshotEngineUnavailable("Chrome DevTools endpoint did not start in time")


def _read_page_websocket_url(port: int, timeout: int) -> str:
    deadline = time.monotonic() + timeout
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/list",
                timeout=min(2, timeout),
            ) as response:
                targets = json.loads(response.read().decode("utf-8"))
            for target in targets:
                if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                    return str(target["webSocketDebuggerUrl"])
        except Exception as exc:  # pragma: no cover - depends on browser startup timing
            last_error = exc
        time.sleep(0.05)
    detail = f": {last_error}" if last_error else ""
    raise ScreenshotEngineUnavailable(f"Chrome DevTools page target did not start{detail}")


def capture_screenshot_cdp(
    html_path: Path,
    output_path: Path,
    browser_path: Optional[Path] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout: int = 30,
) -> Path:
    """Capture a true full-page screenshot through Chrome DevTools Protocol."""
    browser = resolve_browser(browser_path)
    if browser is None:
        raise ScreenshotEngineUnavailable(
            "Chrome/Edge not found. Install Chrome/Edge or set STOCKSIGHT_BROWSER "
            "to the browser executable path."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_root = output_path.parent / ".stocksight-browser"
    temp_root.mkdir(parents=True, exist_ok=True)
    html_uri = html_path.resolve().as_uri()

    with tempfile.TemporaryDirectory(prefix="profile-", dir=str(temp_root)) as profile:
        profile_dir = Path(profile)
        command = [
            str(browser),
            "--headless=new",
            "--remote-debugging-port=0",
            f"--user-data-dir={profile_dir.resolve()}",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            "--run-all-compositor-stages-before-draw",
            "--disable-gpu",
            "--disable-gpu-compositing",
            "--disable-features=UseSkiaRenderer",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--enable-automation",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-breakpad",
            "--disable-crash-reporter",
            "about:blank",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            port, _browser_path = _read_devtools_port(profile_dir, timeout)
            websocket_url = _read_page_websocket_url(port, timeout)
            with _CdpWebSocket(websocket_url, timeout=timeout) as cdp:
                cdp.request("Page.enable")
                cdp.request(
                    "Emulation.setDeviceMetricsOverride",
                    {
                        "width": width,
                        "height": height,
                        "deviceScaleFactor": 1,
                        "mobile": False,
                    },
                )
                cdp.request("Page.navigate", {"url": html_uri})
                cdp.wait_for_event("Page.loadEventFired", timeout=timeout)
                cdp.request(
                    "Runtime.evaluate",
                    {
                        "expression": "document.fonts ? document.fonts.ready : Promise.resolve()",
                        "awaitPromise": True,
                    },
                )
                cdp.request(
                    "Runtime.evaluate",
                    {
                        "expression": DISABLE_CAPTURE_ANIMATIONS_SCRIPT,
                        "awaitPromise": True,
                    },
                )
                cdp.request(
                    "Runtime.evaluate",
                    {
                        "expression": "new Promise(resolve => setTimeout(resolve, 1400))",
                        "awaitPromise": True,
                    },
                )
                metrics = cdp.request("Page.getLayoutMetrics")
                content = metrics.get("contentSize", {})
                content_width = max(width, int(content.get("width", width)))
                content_height = max(1, int(content.get("height", height)))
                cdp.request(
                    "Emulation.setDeviceMetricsOverride",
                    {
                        "width": content_width,
                        "height": content_height,
                        "deviceScaleFactor": 1,
                        "mobile": False,
                    },
                )
                cdp.request(
                    "Runtime.evaluate",
                    {
                        "expression": DISABLE_CAPTURE_ANIMATIONS_SCRIPT,
                        "awaitPromise": True,
                    },
                )
                screenshot = cdp.request(
                    "Page.captureScreenshot",
                    {
                        "format": "png",
                        "fromSurface": True,
                        "captureBeyondViewport": True,
                        "clip": {
                            "x": 0,
                            "y": 0,
                            "width": content_width,
                            "height": content_height,
                            "scale": 1,
                        },
                    },
                )
            output_path.write_bytes(base64.b64decode(screenshot["data"]))
        except Exception:
            process.kill()
            process.communicate(timeout=5)
            raise
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=5)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ScreenshotError(f"Chrome DevTools finished but screenshot is empty: {output_path}")
    return output_path.resolve()


def capture_screenshot_chrome(
    html_path: Path,
    output_path: Path,
    browser_path: Optional[Path] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout: int = 30,
) -> Path:
    """Capture a viewport-sized long screenshot with Chrome / Edge CLI."""
    browser = resolve_browser(browser_path)
    if browser is None:
        raise ScreenshotEngineUnavailable(
            "Chrome/Edge not found. Install Chrome/Edge or set STOCKSIGHT_BROWSER "
            "to the browser executable path."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_screenshot_command(browser, html_path, output_path, width, height)

    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ScreenshotError(f"Browser screenshot timed out after {timeout}s") from exc

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise ScreenshotError(f"Browser screenshot failed: {detail or completed.returncode}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ScreenshotError(f"Browser finished but screenshot is empty: {output_path}")
    return output_path.resolve()


def capture_screenshot(
    html_path: Path,
    output_path: Optional[Path] = None,
    browser_path: Optional[Path] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout: int = 30,
    engine: str = DEFAULT_ENGINE,
) -> Path:
    """Capture a long screenshot and return the resolved PNG path."""
    if not html_path.exists():
        raise ScreenshotError(f"HTML report not found: {html_path}")
    if width <= 0 or height <= 0:
        raise ScreenshotError("width and height must be positive")
    if engine not in ENGINES:
        raise ScreenshotError(f"Unknown screenshot engine: {engine}")

    output = output_path or html_path.with_suffix(".png")
    if engine == "playwright":
        return capture_screenshot_playwright(
            html_path, output, browser_path, width, height, timeout
        )
    if engine == "cdp":
        return capture_screenshot_cdp(
            html_path, output, browser_path, width, height, timeout
        )
    if engine == "chrome":
        return capture_screenshot_chrome(
            html_path, output, browser_path, width, height, timeout
        )

    try:
        return capture_screenshot_playwright(
            html_path, output, browser_path, width, height, timeout
        )
    except ScreenshotEngineUnavailable:
        try:
            return capture_screenshot_cdp(
                html_path, output, browser_path, width, height, timeout
            )
        except ScreenshotEngineUnavailable:
            return capture_screenshot_chrome(
                html_path, output, browser_path, width, height, timeout
            )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    try:
        output = capture_screenshot(
            html_path=args.html,
            output_path=args.out,
            browser_path=args.browser,
            width=args.width,
            height=args.height,
            timeout=args.timeout,
            engine=args.engine,
        )
    except ScreenshotError as exc:
        print(f"StockSight screenshot failed: {exc}", file=sys.stderr)
        return 2
    print(f"Screenshot: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
