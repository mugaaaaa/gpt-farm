"""GPT-Farm CLI — main entry point.

Supports both direct subcommands (for scripting/AI agents) and optional TUI mode.
"""

import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from .config import Config, DEFAULT_CONFIG_FILE
from .providers.email import get as get_email_provider, list_providers as list_email_providers
from .providers.sms import get as get_sms_provider
from .platforms.chatgpt import register as register_chatgpt
from .cpa import push_accounts, get_pool_status


def _load_config(path: Optional[Path] = None) -> Config:
    return Config(path)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ========== CLI ==========

@click.group()
@click.option("--config", "-c", default=None, help="Config file path")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON (for AI agents)")
@click.pass_context
def main(ctx, config, json_output):
    """GPT-Farm — ChatGPT account farming toolkit."""
    cfg_path = Path(config) if config else None
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = _load_config(cfg_path)
    ctx.obj["json"] = json_output


# ========== farm ==========

@main.command()
@click.option("--count", "-n", default=1, help="Number of accounts to register")
@click.option("--email", "-e", "email_provider", default="luckmail",
              type=click.Choice(list_email_providers()), help="Email provider")
@click.option("--mode", "-m", default="at", type=click.Choice(["at", "rt"]),
              help="at=access_token_only (disposable), rt=refresh_token (long-term)")
@click.option("--concurrency", "-p", default=1, help="Number of concurrent registrations")
@click.pass_context
def farm(ctx, count, email_provider, mode, concurrency):
    """Register ChatGPT accounts."""
    cfg: Config = ctx.obj["cfg"]
    use_json: bool = ctx.obj["json"]

    # Resolve email provider
    provider_kwargs = {}
    if email_provider == "gmail":
        provider_kwargs["gmail_user"] = cfg["gmail_user"]
        provider_kwargs["gmail_pass"] = cfg["gmail_pass"]
    elif email_provider == "luckmail":
        provider_kwargs["luckmail_key"] = cfg["luckmail_key"]
        provider_kwargs["luckmail_url"] = cfg["luckmail_url"]
        provider_kwargs["luckmail_email_type"] = cfg["luckmail_email_type"]
        provider_kwargs["proxy"] = cfg["proxy_url"]

    provider = get_email_provider(email_provider, **provider_kwargs)
    proxy = cfg["proxy_url"]

    results = []
    ok = fail = 0
    for i in range(count):
        if not use_json:
            click.echo(f"\n[{i+1}/{count}] ", nl=False)
        try:
            result = register_chatgpt(provider, proxy=proxy, mode=mode)
            entry = {
                "email": result.email,
                "password": result.password,
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "id_token": result.id_token,
                "account_id": result.account_id,
                "created_at": _now_iso(),
                "provider": email_provider,
                "mode": mode,
            }
            results.append(entry)
            ok += 1
            if use_json:
                click.echo(json.dumps({"status": "ok", **entry}, ensure_ascii=False))
            else:
                click.echo(f"✅ {result.email}")
                if result.refresh_token:
                    click.echo(f"   RT: {result.refresh_token[:60]}...")
        except Exception as e:
            fail += 1
            if use_json:
                click.echo(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False))
            else:
                click.echo(f"❌ {e}")
        time.sleep(2)

    # Save to account store
    store = _load_accounts()
    store.extend(results)
    _save_accounts(store)

    if not use_json:
        click.echo(f"\n{'='*50}")
        click.echo(f"Done: ✅ {ok} / ❌ {fail} / total {count}")
        click.echo(f"Store: {_accounts_file()} ({len(store)} accounts)")


# ========== push ==========

@main.command()
@click.option("--all", "push_all", is_flag=True, help="Push all stored accounts")
@click.pass_context
def push(ctx, push_all):
    """Push accounts to CPA/CLIProxyAPI."""
    cfg: Config = ctx.obj["cfg"]
    use_json: bool = ctx.obj["json"]

    if push_all:
        accounts = _load_accounts()
    else:
        # Push only those without RT (AT-only day-trade accounts)
        accounts = [a for a in _load_accounts() if not a.get("refresh_token")]

    if not accounts:
        click.echo("No accounts to push")
        return

    cpa_url = cfg["cpa_url"]
    cpa_key = cfg["cpa_key"]
    ok, fail = push_accounts(accounts, cpa_url, cpa_key)

    if use_json:
        click.echo(json.dumps({"ok": ok, "fail": fail, "total": len(accounts)}))
    else:
        click.echo(f"Pushed: ✅ {ok} / ❌ {fail}")


# ========== status ==========

@main.command()
@click.pass_context
def status(ctx):
    """Show current status."""
    cfg: Config = ctx.obj["cfg"]
    use_json: bool = ctx.obj["json"]

    accounts = _load_accounts()
    pool = {}
    if cfg["cpa_url"]:
        try:
            pool = get_pool_status(cfg["cpa_url"], cfg["cpa_key"])
        except Exception:
            pass

    if use_json:
        click.echo(json.dumps({
            "local_accounts": len(accounts),
            "cpa_pool": pool.get("total", 0),
            "cpa_active": pool.get("active", 0),
        }))
    else:
        click.echo(f"\n  Local: {len(accounts)} accounts")
        for a in accounts[-10:]:
            rt = "✅" if a.get("refresh_token") else "❌"
            click.echo(f"  {a['email'][:45]:45s} RT:{rt}")
        if pool:
            click.echo(f"\n  CPA pool: {pool['total']} total, {pool['active']} active")
            click.echo(f"  Success: {pool['success']} / Failed: {pool['failed']}")


# ========== import-rt ==========

@main.command()
@click.option("--token", "-t", "rt_token", default=None, help="Refresh token string")
@click.option("--file", "-f", "rt_file", default=None, help="File containing refresh token")
@click.pass_context
def import_rt(ctx, rt_token, rt_file):
    """Import a refresh_token and push to CPA."""
    cfg: Config = ctx.obj["cfg"]

    if rt_file:
        rt_token = Path(rt_file).read_text().strip()
    if not rt_token:
        raise click.UsageError("Provide --token or --file")

    click.echo("Exchanging refresh_token...")
    import urllib.request as ur
    from .platforms.chatgpt import CLIENT_ID, TOKEN_URL
    data = ur.urlencode({
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": rt_token,
    }).encode()
    req = ur.Request(TOKEN_URL, data=data,
                   headers={"Content-Type": "application/x-www-form-urlencoded"})
    with ur.urlopen(req, timeout=15) as r:
        tokens = json.loads(r.read())

    at = tokens.get("access_token", "")
    idt = tokens.get("id_token", "")
    parts = idt.split(".")
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==="))
    email = payload.get("email", "unknown")

    account = {
        "email": email,
        "access_token": at,
        "refresh_token": rt_token,
        "id_token": idt,
        "created_at": _now_iso(),
    }
    store = _load_accounts()
    store.append(account)
    _save_accounts(store)

    click.echo(f"  Email: {email}")
    if cfg["cpa_url"]:
        push_accounts([account], cfg["cpa_url"], cfg["cpa_key"])
        click.echo("  Pushed to CPA ✅")


# ========== tui ==========

@main.command()
@click.pass_context
def tui(ctx):
    """Launch interactive TUI mode."""
    try:
        from .tui import run_tui
        run_tui(ctx.obj["cfg"])
    except ImportError:
        click.echo("TUI requires 'textual' package: pip install textual", err=True)
        raise SystemExit(1)


# ========== helpers ==========

def _accounts_file() -> Path:
    d = Path(os.environ.get("GPT_FARM_DATA_DIR", Path.home() / ".gpt-farm"))
    d.mkdir(parents=True, exist_ok=True)
    return d / "accounts.json"


def _load_accounts() -> list[dict]:
    path = _accounts_file()
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return []
    return []


def _save_accounts(accounts: list[dict]) -> None:
    _accounts_file().write_text(json.dumps(accounts, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
