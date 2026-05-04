"""GPT-Farm TUI — 基于 Textual 的交互式管理面板。

功能：
  - 仪表盘：账号池 + CPA 状态总览
  - 设置：配置 API Key / Provider
  - 注册：批量注册账号
  - 推送：推送到 CPA

运行: gpt-farm tui
依赖: pip install textual
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)

# ---- config helpers (avoid circular import) ----

CONFIG_DIR = Path(os.environ.get("GPT_FARM_CONFIG_DIR", Path.home() / ".gpt-farm"))
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "email_provider": "luckmail",
    "luckmail_key": "",
    "luckmail_url": "https://mails.luckyous.com/",
    "luckmail_email_type": "ms_imap",
    "gmail_user": "",
    "gmail_pass": "",
    "herosms_key": "",
    "herosms_country": "187",
    "herosms_service": "dr",
    "yescaptcha_key": "",
    "proxy_url": "",
    "cpa_url": "",
    "cpa_key": "",
}

ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"


def _load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text()))
        except Exception:
            pass
    return cfg


def _save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    to_save = {k: v for k, v in cfg.items() if v and v != DEFAULTS.get(k)}
    CONFIG_FILE.write_text(json.dumps(to_save, indent=2, ensure_ascii=False))


def _load_accounts() -> list[dict]:
    if ACCOUNTS_FILE.exists():
        try:
            return json.loads(ACCOUNTS_FILE.read_text())
        except Exception:
            return []
    return []


def _save_accounts(accounts: list[dict]) -> None:
    ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2, ensure_ascii=False))


# ---- screens ----

class Dashboard(Screen):
    """主仪表盘"""

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("📊 总览"):
                yield Static("[bold]本地账号[/]")
                yield DataTable(id="local-table")
                yield Static("[bold]CPA 池[/]")
                yield DataTable(id="cpa-table")
                yield Static(id="stats-label")
            with TabPane("🔄 注册"):
                yield Static("数量:")
                yield Input(value="5", id="farm-count", placeholder="注册数量")
                yield Static("Provider:")
                yield Select(
                    [("LuckMail (短期)", "luckmail"), ("Gmail (长期)", "gmail")],
                    value="luckmail",
                    id="farm-provider",
                )
                yield Static("模式:")
                yield Select(
                    [("access_token (短期)", "access_token"), ("refresh_token (长期)", "refresh_token")],
                    value="access_token",
                    id="farm-mode",
                )
                yield Button("开始注册", id="btn-farm", variant="primary")
                yield RichLog(id="farm-log", max_lines=30)
                yield ProgressBar(total=100, id="farm-progress")
            with TabPane("⚙️ 设置"):
                with VerticalScroll():
                    for key, default in DEFAULTS.items():
                        label = key.replace("_", " ").title()
                        is_secret = any(s in key.lower() for s in ("key", "pass", "password", "secret", "token"))
                        yield Label(f"{label}:")
                        yield Input(
                            value=_load_config().get(key, default),
                            id=f"cfg-{key}",
                            password=is_secret,
                            placeholder=default if is_secret else "",
                        )
                    yield Button("💾 保存设置", id="btn-save-settings", variant="success")
                    yield Static(id="settings-msg")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        # Local accounts
        accounts = _load_accounts()
        table = self.query_one("#local-table", DataTable)
        table.clear()
        if not table.columns:
            table.add_columns("邮箱", "access_token", "refresh_token", "时间")
        for a in accounts[-15:]:
            at = "✅" if a.get("access_token") else "❌"
            rt = "✅" if a.get("refresh_token") else "❌"
            ts = a.get("created_at", "")[:19] if a.get("created_at") else "-"
            table.add_row(a["email"][:50], at, rt, ts)

        # CPA pool
        cfg = _load_config()
        cpa_table = self.query_one("#cpa-table", DataTable)
        cpa_table.clear()
        if not cpa_table.columns:
            cpa_table.add_columns("邮箱", "成功", "失败", "状态")

        pool = {}
        try:
            if cfg.get("cpa_url"):
                import requests
                r = requests.get(
                    f"{cfg['cpa_url']}/v0/management/auth-files",
                    headers={"Authorization": f"Bearer {cfg.get('cpa_key','')}"},
                    timeout=5,
                )
                for f in r.json().get("files", []):
                    cpa_table.add_row(
                        f.get("account", "")[:45],
                        str(f.get("success", 0)),
                        str(f.get("failed", 0)),
                        "✅" if not f.get("disabled") else "🚫",
                    )
                pool = {"total": len(r.json().get("files", []))}
        except Exception:
            pass

        self.query_one("#stats-label", Static).update(
            f"本地: {len(accounts)} 个  |  CPA 池: {pool.get('total', '?')} 个"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-farm":
            self._start_farm()
        elif event.button.id == "btn-save-settings":
            self._save_settings()

    def _start_farm(self) -> None:
        count = int(self.query_one("#farm-count", Input).value or "1")
        provider = self.query_one("#farm-provider", Select).value
        mode = self.query_one("#farm-mode", Select).value
        log = self.query_one("#farm-log", RichLog)
        progress = self.query_one("#farm-progress", ProgressBar)

        log.clear()
        log.write(f"[bold]开始注册 {count} 个账号[/]")
        log.write(f"Provider: {provider}, Mode: {mode}")
        progress.update(progress=0)

        def _run():
            from .config import Config
            from .providers.email import get as get_provider
            from .platforms.chatgpt import register as do_register

            cfg = Config()
            pkwargs = {}
            if provider == "gmail":
                pkwargs["gmail_user"] = cfg["gmail_user"]
                pkwargs["gmail_pass"] = cfg["gmail_pass"]
            else:
                pkwargs["luckmail_key"] = cfg["luckmail_key"]
                pkwargs["luckmail_url"] = cfg["luckmail_url"]
                pkwargs["luckmail_email_type"] = cfg["luckmail_email_type"]
                pkwargs["proxy"] = cfg["proxy_url"]

            email_provider = get_provider(provider, **pkwargs)
            proxy = cfg["proxy_url"]

            ok = fail = 0
            for i in range(count):
                try:
                    result = do_register(
                        email_provider,
                        proxy=proxy,
                        mode="refresh_token" if mode == "refresh_token" else "at",
                    )
                    entry = {
                        "email": result.email,
                        "password": result.password,
                        "access_token": result.access_token,
                        "refresh_token": result.refresh_token,
                        "id_token": result.id_token,
                        "account_id": result.account_id,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "provider": provider,
                        "mode": mode,
                    }
                    accounts = _load_accounts()
                    accounts.append(entry)
                    _save_accounts(accounts)
                    ok += 1
                    self.call_from_thread(log.write, f"✅ {result.email}")
                except Exception as e:
                    fail += 1
                    self.call_from_thread(log.write, f"❌ {e}")
                pct = int((i + 1) / count * 100)
                self.call_from_thread(progress.update, progress=pct)
                time.sleep(2)

            self.call_from_thread(log.write, f"\n[bold]完成: ✅ {ok} / ❌ {fail}[/]")
            self.call_from_thread(self._refresh)

        threading.Thread(target=_run, daemon=True).start()

    def _save_settings(self) -> None:
        new_cfg = dict(DEFAULTS)
        for key in DEFAULTS:
            widget = self.query_one(f"#cfg-{key}", Input)
            new_cfg[key] = widget.value
        _save_config(new_cfg)
        msg = self.query_one("#settings-msg", Static)
        msg.update("[green]✅ 已保存[/]")
        self.set_timer(3, lambda: msg.update(""))


# ---- app ----

class GptFarmApp(App):
    """GPT-Farm TUI"""

    TITLE = "GPT-Farm"
    SUB_TITLE = "ChatGPT Account Farm"
    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("d", "show_dashboard", "仪表盘"),
        Binding("r", "refresh", "刷新"),
    ]
    CSS = """
    Screen { align: center middle; }
    #stats-label { margin-top: 1; color: $text-muted; }
    DataTable { height: 12; margin-bottom: 1; }
    #farm-log { height: 12; }
    #farm-progress { height: 1; margin-top: 1; display: none; }
    Input { margin-bottom: 1; }
    Button { margin-top: 1; }
    #settings-msg { margin-top: 1; }
    Label { margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Dashboard()

    def action_refresh(self) -> None:
        if hasattr(self, "query_one"):
            self.query_one(Dashboard)._refresh()


def run_tui(cfg=None) -> None:
    """Entry point for gpt-farm tui command."""
    app = GptFarmApp()
    app.run()
