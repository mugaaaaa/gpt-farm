# GPT-Farm

ChatGPT 账号农场 — 批量注册、CPA 聚合、API 分发。

## 安装

```bash
git clone https://github.com/mugaaaaa/gpt-farm.git
cd gpt-farm
pip install -e .
```

## 配置

```bash
cp config.example.json ~/.gpt-farm/config.json
```

编辑 `~/.gpt-farm/config.json`，填入你的 API key。也支持环境变量覆盖，如 `GPT_FARM_LUCKMAIL_KEY=luck_xxx`。

## 支持的 Provider

### 邮箱 Provider

| Provider | 说明 | 配置字段 | 适合 |
|----------|------|----------|------|
| `luckmail` | 购买真实邮箱（outlook.it / outlook.sg 等），可指定多国域名 | `luckmail_key`, `luckmail_email_type` | 日抛号，邮箱匿名 |
| `gmail` | Gmail IMAP 收件，使用加号别名（`user+xxx@gmail.com`） | `gmail_user`, `gmail_pass` | 长期号，需拿 RT |

LuckMail 支持的类型：

| `luckmail_email_type` | 域名示例 | 价格 |
|-----------------------|----------|------|
| `ms_imap` | `@outlook.it`, `@outlook.sg`, `@outlook.co.il` ... | $0.02 |
| `self_built` | `@caijiuduolian.bbroot.com` 等自建域名 | $0.002 |
| `google_variant` | `@googlemail.com` | $0.01 |

### 短信 Provider

| Provider | 说明 | 配置字段 |
|----------|------|----------|
| `herosms` | HeroSMS 接码，用于 ChatGPT 手机验证 | `herosms_key`, `herosms_country`, `herosms_service` |

## 工作流

### 工作流 A：刷日抛号（AT only）

全自动，无需人工介入。LuckMail 随机邮箱，`access_token_only` 模式，约 10 天有效期。

```bash
# 注册 5 个
gpt-farm farm -n 5 -e luckmail -m at

# 推送到 CPA
gpt-farm push

# 查看状态
gpt-farm status
```

注册 → 推送 CPA → 池子里自动轮换 → API 直接可用。

适合：量大、用完扔、不介意有效期。

### 工作流 B：刷长期号（RT）

需要一次人工介入拿 refresh_token。Gmail 真实邮箱，拿到的 RT 可以长期续期。

```bash
# 注册（拿到 at）
gpt-farm farm -n 1 -e gmail -m rt

# 在本机安装 Codex CLI 登录拿 RT：
#   brew install openai/tap/codex
#   codex login --email <上面注册的邮箱> --password <密码>
#   cat ~/.codex/auth.json | grep refresh_token

# 导入 RT
gpt-farm import-rt --token "rt_xxx..."

# 推送
gpt-farm push
```

适合：长期稳定使用、需要可靠 API。

### 工作流 C：已有 RT 直接导入

```bash
gpt-farm import-rt --token "rt_xxx..."
gpt-farm push
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `gpt-farm farm -n N -e <provider> -m <mode>` | 注册 N 个账号 |
| `gpt-farm push` | 推送全部账号到 CPA |
| `gpt-farm status` | 查看账号池状态 |
| `gpt-farm import-rt --token "rt_..."` | 导入 refresh_token |
| `gpt-farm tui` | 交互式 TUI |

所有命令支持 `--json` 输出，方便 AI Agent 调用。

## 架构

```
gpt_farm/
├── cli.py              # Click CLI 入口
├── config.py           # 配置管理（文件 + 环境变量）
├── cpa.py              # CPA 推送
├── tui.py              # TUI 预留
├── platforms/
│   └── chatgpt.py      # ChatGPT 纯协议注册
├── providers/
│   ├── email/           # 邮箱 Provider
│   │   ├── base.py
│   │   ├── gmail.py
│   │   └── luckmail.py
│   └── sms/             # 短信 Provider
│       ├── base.py
│       └── herosms.py
└── skills/
    └── gpt-farm.md      # AI Agent 技能文件
```

## 扩展

添加新 Provider：

1. 创建 `gpt_farm/providers/email/myprovider.py`
2. 继承 `BaseEmailProvider`，实现 `create()` → `EmailAccount`
3. 用 `@register("myprovider")` 注册
4. 立即可用：`gpt-farm farm -e myprovider`

## License

MIT
