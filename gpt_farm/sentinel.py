"""Playwright SentinelSDK — produce valid p/t/c tokens to pass OpenAI anti-bot.

Uses a shared browser instance (lazy singleton) for efficiency.
Based on the community codex-register approach.
"""

from __future__ import annotations

import json
import os
import threading
import time
import traceback
from typing import Optional

_BROWSER = None
_BROWSER_LOCK = threading.Lock()
_PLAYWRIGHT = None
_BROWSER_PROXY: Optional[str] = None

SDK_WAIT_TIMEOUT = 60000  # ms
SDK_LOAD_WAIT = 10000     # ms


def _get_or_create_browser(proxy: Optional[str] = None) -> tuple:
    """Lazy singleton: create or reuse Playwright + Chromium browser."""
    global _BROWSER, _PLAYWRIGHT, _BROWSER_PROXY

    if _BROWSER is not None and _BROWSER_PROXY == proxy:
        return _PLAYWRIGHT, _BROWSER

    with _BROWSER_LOCK:
        if _BROWSER is not None and _BROWSER_PROXY == proxy:
            return _PLAYWRIGHT, _BROWSER

        # Close old browser if proxy changed
        if _BROWSER is not None:
            try:
                _BROWSER.close()
            except Exception:
                pass

        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        launch_opts = {"headless": True}
        if proxy:
            launch_opts["proxy"] = {"server": proxy}
        browser = pw.chromium.launch(**launch_opts)

        _PLAYWRIGHT = pw
        _BROWSER = browser
        _BROWSER_PROXY = proxy
        return pw, browser


def get_sentinel_token(
    flow: str,
    device_id: Optional[str] = None,
    proxy: Optional[str] = None,
) -> Optional[str]:
    """Produce a full Sentinel token (p/t/c) using Playwright.

    Args:
        flow: "authorize_continue" or "oauth_create_account"
        device_id: OpenAI device ID (oai-did cookie value)
        proxy: HTTP proxy URL

    Returns:
        JSON string like {"p":"...","t":"...","c":"..."} or None on failure.
    """
    try:
        pw, browser = _get_or_create_browser(proxy)
        context_opts = {}
        if proxy:
            context_opts["proxy"] = {"server": proxy}
        context = browser.new_context(**context_opts)
        page = context.new_page()

        # Load Sentinel frame — use the version-matched URL
        sdk_version = os.environ.get("SENTINEL_SDK_VERSION", "20260219f9f6")
        frame_url = f"https://sentinel.openai.com/backend-api/sentinel/frame.html?sv={sdk_version}"
        page.goto(frame_url, wait_until="domcontentloaded", timeout=30000)

        # Wait for the Sentinel SDK to complete and produce token
        sentinel_token = None
        deadline = time.time() + (SDK_WAIT_TIMEOUT / 1000)

        while time.time() < deadline and not sentinel_token:
            try:
                token_str = page.evaluate("""() => {
                    // SentinelSDK calls window.parent.postMessage with the token
                    // The token is available as a global after SDK completes
                    if (window.__sdk_token__) return window.__sdk_token__;
                    return null;
                }""")
                if token_str:
                    sentinel_token = token_str
                    break
            except Exception:
                pass

            # Fallback: try getting p/t/c from the page
            try:
                result = page.evaluate("""() => {
                    const pInput = document.querySelector('input[name="cf-turnstile-response"]');
                    const p = pInput ? pInput.value : '';
                    // Look for t/c tokens in data attributes or JS globals
                    const t = (window.__sentinel_t__) || '';
                    const c = (window.__sentinel_c__) || '';
                    if (p) {
                        return JSON.stringify({p, t, c});
                    }
                    return null;
                }""")
                if result:
                    sentinel_token = result
                    break
            except Exception:
                pass

            time.sleep(1)

        context.close()

        if sentinel_token:
            # Parse and wrap in Sentinel format
            try:
                parsed = json.loads(sentinel_token)
                p_val = parsed.get("p", parsed) if isinstance(parsed, dict) else sentinel_token
                result = json.dumps({
                    "p": str(p_val) if not isinstance(p_val, str) else p_val,
                    "t": str(parsed.get("t", "")) if isinstance(parsed, dict) else "",
                    "c": str(parsed.get("c", "")) if isinstance(parsed, dict) else "",
                    "id": device_id or "",
                    "flow": flow,
                })
                return result
            except Exception:
                pass

        return None

    except Exception as e:
        print(f"[Sentinel] Error: {e}")
        traceback.print_exc()
        return None


def close_browser():
    """Clean up browser resources."""
    global _BROWSER, _PLAYWRIGHT
    with _BROWSER_LOCK:
        if _BROWSER:
            try:
                _BROWSER.close()
            except Exception:
                pass
            _BROWSER = None
        if _PLAYWRIGHT:
            try:
                _PLAYWRIGHT.stop()
            except Exception:
                pass
            _PLAYWRIGHT = None
