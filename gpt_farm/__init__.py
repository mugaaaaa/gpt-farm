"""GPT-Farm — Automated ChatGPT account farming toolkit.

Provides CLI and Python API for:
- Batch account registration via multiple email/SMS providers
- Credential management and persistence
- CPA/CLIProxyAPI integration for API aggregation

All credentials are loaded from config file ($GPT_FARM_CONFIG or ~/.gpt-farm/config.json)
or environment variables (prefixed with GPT_FARM_). No secrets are hardcoded.
"""

__version__ = "0.1.0"
