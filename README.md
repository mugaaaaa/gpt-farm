# GPT-Farm

ChatGPT account farming toolkit — batch register, CPA aggregation, API distribution.

## Install

```bash
git clone https://github.com/YOUR_USER/gpt-farm.git
cd gpt-farm
pip install -e .
```

## Quick Start

```bash
# Setup config
cp config.example.json ~/.gpt-farm/config.json
# Edit with your credentials

# Register 5 disposable accounts (LuckMail random emails)
gpt-farm farm -n 5 -e luckmail -m at

# Push to CPA
gpt-farm push

# Check status
gpt-farm status
```

## Commands

| Command | Description |
|---------|-------------|
| `gpt-farm farm -n N` | Register N accounts |
| `gpt-farm push` | Push to CPA |
| `gpt-farm status` | Pool status |
| `gpt-farm import-rt --token "rt_..."` | Import refresh token |
| `gpt-farm tui` | Interactive TUI (optional) |

All commands support `--json` for AI agent consumption.

## Architecture

```
gpt_farm/
├── cli.py              # Click CLI
├── config.py           # Config (file + env)
├── cpa.py              # CPA push
├── platforms/
│   └── chatgpt.py      # Registration engine
├── providers/
│   ├── email/           # Email providers
│   │   ├── base.py
│   │   ├── gmail.py
│   │   └── luckmail.py
│   └── sms/             # SMS providers
│       ├── base.py
│       └── herosms.py
└── skills/
    └── gpt-farm.md      # AI agent guide
```

## License

MIT
