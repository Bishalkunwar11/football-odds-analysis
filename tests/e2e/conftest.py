"""Playwright fixtures for Streamlit E2E tests."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_PATH = REPO_ROOT / "src" / "app.py"
STREAMLIT_PORT = 8504
BASE_URL = f"http://127.0.0.1:{STREAMLIT_PORT}"


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


def _wait_for_http(url: str, timeout_seconds: float = 45.0) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            with urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for Streamlit app at {url}")


def _wait_for_frontend_ready(page: Page, timeout_seconds: float = 45.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            ready_state = page.evaluate("() => document.readyState")
            body_visible = page.evaluate(
                """
                () => {
                    const b = document.body;
                    if (!b) return false;
                    const style = window.getComputedStyle(b);
                    return style.visibility !== 'hidden' && style.display !== 'none';
                }
                """
            )
            button_count = page.get_by_role("button").count()
            if ready_state == "complete" and body_visible and button_count > 0:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def streamlit_app() -> Generator[str, None, None]:
    if _is_port_open(STREAMLIT_PORT):
        yield BASE_URL
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    command = [
        str(REPO_ROOT / ".venv" / "bin" / "streamlit"),
        "run",
        str(APP_PATH),
        "--server.headless",
        "true",
        "--server.port",
        str(STREAMLIT_PORT),
        "--server.address",
        "127.0.0.1",
    ]

    proc = subprocess.Popen(
        command,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        _wait_for_http(BASE_URL)
        yield BASE_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="function")
def page(
    browser: Browser,
    request: pytest.FixtureRequest,
    streamlit_app: str,
) -> Generator[Page, None, None]:
    context: BrowserContext = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(streamlit_app)
    page.wait_for_load_state("domcontentloaded")
    if not _wait_for_frontend_ready(page):
        context.close()
        pytest.skip("Streamlit frontend did not become interactive in time.")

    yield page

    failed = getattr(request.node, "rep_call", None)
    if failed and failed.failed:
        artifacts = REPO_ROOT / "tests" / "e2e" / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        screenshot_path = artifacts / f"{request.node.name}.png"
        try:
            page.screenshot(path=str(screenshot_path), full_page=True, timeout=5000)
        except Exception:
            pass

    context.close()
