# GPT-Farm Skill — AI Agent Usage Guide

## Overview

GPT-Farm is a CLI tool for batch-registering ChatGPT accounts and pushing them to a CPA (CLIProxyAPI) pool for API aggregation.

Current date reference: 2026-05-04. All workflows below have been verified as of this date.

## Quick Commands

All commands accept `--json` for structured output consumable by AI agents.

```bash
# Register N short-term accounts (access_token only, LuckMail random email, fully automated)
gpt-farm farm -n 5 -e luckmail -m access_token --json

# Register N long-term accounts (with refresh_token, Gmail, requires manual step)
gpt-farm farm -n 2 -e gmail -m refresh_token --json

# Push all local accounts to CPA
gpt-farm push

# Check account pool status
gpt-farm status --json

# Import a manually obtained refresh_token
gpt-farm import-rt --token "rt_xxx..."
gpt-farm import-rt --file /path/to/rt.txt

# Export accounts
gpt-farm export -o backup.json
# Import accounts (deduplicated)
gpt-farm import --file backup.json
```

## JSON Output Format

### farm (success)
```json
{"status": "ok", "email": "xxx@outlook.it", "password": "...", "access_token": "...",
 "refresh_token": "", "id_token": "", "account_id": "", "created_at": "..."}
```

### farm (error)
```json
{"status": "error", "error": "Password failed (409): ..."}
```

### status
```json
{"local_accounts": 5, "cpa_pool": 9, "cpa_active": 8}
```

## Two Workflows

### 1. Short-Term Accounts (fully automated)
- Provider: `luckmail`
- Mode: `access_token`
- Lifespan: ~10 days
- Use case: user needs bulk temporary API quota
- Agent steps: run `gpt-farm farm` + `gpt-farm push`

### 2. Long-Term Accounts (one manual step)
- Provider: `gmail`
- Mode: `refresh_token`
- Lifespan: months, auto-refreshs
- Use case: user needs stable long-term API access
- Agent steps:
  1. Run `gpt-farm farm` to get email + password
  2. Instruct user to run `codex login` locally with those credentials
  3. User provides refresh_token
  4. Run `gpt-farm import-rt` + `gpt-farm push`

## Providers

### Email

| Name | Description | Best For |
|------|-------------|----------|
| `luckmail` | Purchased real mailboxes (outlook.it, outlook.sg, etc.) | Short-term, anonymous |
| `gmail` | Gmail plus-aliases via IMAP | Long-term, with refresh_token |

### SMS

| Name | Description |
|------|-------------|
| `herosms` | HeroSMS for phone SMS verification |

## Key Tips

1. **OTP must be filled quickly**: ChatGPT verification codes expire in ~10 minutes. The provider's `wait_for_code` auto-polls.
2. **IP quality determines success rate**: Datacenter IPs often get `registration_disallowed`. Use clean residential proxies.
3. **`luckmail` with `ms_imap` is the most reliable email for short-term accounts**: Random multi-country Outlook domains evade unified blocking.
4. **Retrieving refresh_token may trigger phone verification**: When user runs `codex login`, if prompted for phone number, agent can use HeroSMS to get a number and provide it.
5. **Never hardcode credentials**: All config via `~/.gpt-farm/config.json` or `GPT_FARM_*` environment variables.

## Common Errors

| Error | Cause | Action |
|-------|-------|--------|
| `IP blocked at OAuth` | IP blocked by OpenAI | Switch proxy node |
| `Password failed: 409` | Version too old or anti-fraud | Switch IP and retry |
| `OTP timeout` | Email not received | Check provider config |
| `registration_disallowed` | OpenAI rejected registration | Switch IP + change email domain |

## File Layout

```
~/.gpt-farm/
├── config.json      # Configuration (do NOT commit to git)
└── accounts.json    # Local account store
```
