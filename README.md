# GPT-Farm

ChatGPT 账号农场 — 批量注册、CPA 聚合、API 分发。

> 文档更新时间：2026-05-04，当前工作流已验证可用。

## 安装

```bash
git clone https://github.com/mugaaaaa/gpt-farm.git
cd gpt-farm
pip install -e .
```

## 需要准备的 Key

| 配置项 | 用途 | 获取方式 |
|--------|------|----------|
| `luckmail_key` | LuckMail 购买真实邮箱（用于日抛号） | [mails.luckyous.com](https://mails.luckyous.com) 注册获取 |
| `gmail_user` / `gmail_pass` | Gmail IMAP 收验证码（用于长期号） | 自己的 Gmail + [App Password](https://myaccount.google.com/apppasswords) |
| `herosms_key` | HeroSMS 接码（ChatGPT 要求手机验证时用） | [hero-sms.com](https://hero-sms.com) 注册获取 |
| `yescaptcha_key` | YesCaptcha 打码（Turnstile 验证） | [yescaptcha.com](https://yescaptcha.com) 注册获取 |
| `proxy_url` | 代理地址 | 机场/住宅代理的 HTTP 代理 URL |
| `cpa_url` / `cpa_key` | CPA 服务地址和密钥 | 部署 CLIProxyAPI 后获得 |

## 支持的 Provider

### 邮箱 Provider

| Provider | 说明 | 适合 |
|----------|------|------|
| `luckmail` | 购买真实邮箱，随机域名（`outlook.it` / `outlook.sg` / `outlook.co.il` 等），完全匿名 | 日抛号 |
| `gmail` | 自己的 Gmail，使用加号别名（`user+xxx@gmail.com`），需 App Password | 长期号 |

LuckMail `email_type` 选项：

| `luckmail_email_type` | 域名示例 |
|-----------------------|----------|
| `ms_imap` | `@outlook.it`, `@outlook.sg`, `@outlook.co.il`, `@outlook.com.vn` ... |
| `self_built` | `@caijiuduolian.bbroot.com` 等自建域名 |
| `google_variant` | `@googlemail.com` |

### 短信 Provider

| Provider | 说明 |
|----------|------|
| `herosms` | HeroSMS 接码，ChatGPT 手机验证时使用，配置 `herosms_key`、`herosms_country`（默认 `187` 美国）、`herosms_service`（默认 `dr`） |

## 工作流（2026-05-04 验证可用）

### 日抛号（仅 access_token，约 10 天有效）

全自动，无需人工介入。LuckMail 随机邮箱，注册完自动推送 CPA，即开即用。

> 注意：日抛号只有 access_token，没有 refresh_token，约 10 天后过期作废。适合短期大量使用。

```bash
# 注册 5 个日抛号
gpt-farm farm -n 5 -e luckmail -m access_token

# 推送到 CPA（也可注册后统一推送）
gpt-farm push

# 查看池子状态
gpt-farm status
```

### 长期号（含 refresh_token，可长期续期）

先自动注册拿到 access_token，再人工登录 Codex CLI 获取 refresh_token。

> 注意：拿 refresh_token 的过程中 OpenAI 可能要求手机验证，此时 HeroSMS 自动提供美国号码接码。

```bash
# 第一步：自动注册（服务器）
gpt-farm farm -n 1 -e gmail -m refresh_token

# 第二步：人工拿 refresh_token（本地 Mac）
# brew install openai/tap/codex
# codex login --email <上一步输出的邮箱> --password <密码>
# cat ~/.codex/auth.json | grep refresh_token

# 第三步：导入 refresh_token（服务器）
gpt-farm import-rt --token "rt_xxx..."

# 第四步：推送 CPA
gpt-farm push
```

### 已有 refresh_token 直接导入

如果你已经通过其他方式拿到了 refresh_token：

```bash
gpt-farm import-rt --token "rt_xxx..."
gpt-farm push
```

`import-rt` 会自动交换出新的 access_token、提取账号邮箱、生成 CPA 认证文件并推送。

## 命令参考

| 命令 | 说明 |
|------|------|
| `gpt-farm farm -n N -e <provider> -m <mode>` | 注册 N 个账号，mode 为 `access_token` 或 `refresh_token` |
| `gpt-farm push` | 推送本地所有账号到 CPA |
| `gpt-farm status` | 查看本地账号库 + CPA 池状态 |
| `gpt-farm import-rt --token "rt_..."` | 导入 refresh_token 并推送 CPA |
| `gpt-farm tui` | 交互式管理面板（设置 / 注册 / 状态） |

所有命令支持 `--json` 输出，方便 AI Agent 调用和脚本解析。

## 架构

```
gpt_farm/
├── cli.py              # Click CLI 入口
├── config.py           # 配置管理（文件 + 环境变量，无硬编码密钥）
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

## 扩展 Provider

1. 创建 `gpt_farm/providers/email/myprovider.py`
2. 继承 `BaseEmailProvider`，实现 `create()` → `EmailAccount`
3. 用 `@register("myprovider")` 注册
4. 立即可用：`gpt-farm farm -e myprovider`

## License

MIT
