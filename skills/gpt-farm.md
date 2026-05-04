# GPT-Farm Skill — AI Agent Usage Guide

## Overview

GPT-Farm is a CLI tool for batch-registering ChatGPT accounts and pushing them to a CPA/CLIProxyAPI pool for API aggregation.

## Quick Commands

All commands support `--json` flag for structured output suitable for AI agent parsing.

```bash
# Register N accounts (AT-only, disposable)
gpt-farm farm -n 5 -e luckmail -m at --json

# Register N accounts (with refresh_token, long-term)
gpt-farm farm -n 2 -e gmail -m rt --json

# Push all accounts to CPA
gpt-farm push --all

# Check account pool status
gpt-farm status --json

# Import a manually obtained refresh_token
gpt-farm import-rt --token "rt_xxx..."
```

## JSON Output Format

### farm (success):
```json
{"status": "ok", "email": "xxx@outlook.it", "password": "...", "access_token": "...",
 "refresh_token": "", "id_token": "", "account_id": "", "created_at": "..."}
```

### farm (error):
```json
{"status": "error", "error": "Password failed (409): ..."}
```

### status:
```json
{"local_accounts": 5, "cpa_pool": 9, "cpa_active": 8}
```

## Providers

| Name | Description | Config Keys |
|------|-------------|-------------|
| `luckmail` | Purchased real mailboxes | `luckmail_key`, `luckmail_url`, `luckmail_email_type` |
| `gmail` | Gmail plus-aliases via IMAP | `gmail_user`, `gmail_pass` |

## Modes

| Mode | Expiry | Can Get RT? | Best For |
|------|--------|-------------|----------|
| `at` | ~10 days | No | Daily disposal, high volume |
| `rt` | Months | Yes | Long-term, API key replacement |

## Configuration

Config file: `~/.gpt-farm/config.json`

Environment variable override: `GPT_FARM_<KEY>` (e.g. `GPT_FARM_LUCKMAIL_KEY=luck_xxx`)

## Architecture

```
gpt-farm/
├── cli.py           # Click CLI entry
├── config.py        # Config management (file + env)
├── cpa.py           # CPA/CLIProxyAPI push integration
├── platforms/
│   └── chatgpt.py   # Pure-HTTP ChatGPT registration
├── providers/
│   ├── email/
│   │   ├── base.py  # Email provider interface
│   │   ├── gmail.py # Gmail IMAP
│   │   └── luckmail.py
│   └── sms/
│       ├── base.py  # SMS provider interface
│       └── herosms.py
└── tui.py           # TUI stub
```

## Adding a New Provider

1. Create `gpt_farm/providers/email/myprovider.py`
2. Subclass `BaseEmailProvider`
3. Implement `create()` → `EmailAccount`
4. Register with `@register("myprovider")`
5. Done — automatically available as `gpt-farm farm -e myprovider`
