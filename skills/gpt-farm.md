# GPT-Farm Skill — AI Agent 使用指南

## 概述

GPT-Farm 是一个 ChatGPT 账号农场 CLI 工具，支持批量注册 ChatGPT 账号并推送到 CPA（CLIProxyAPI）池中进行 API 聚合。

当前日期参考：2026-05-04，以下工作流均在此日期验证可用。

## 快速命令

所有命令支持 `--json` 标志输出结构化 JSON，供 AI Agent 解析。

```bash
# 注册 N 个短期号（仅 access_token，LuckMail 随机邮箱，全自动）
gpt-farm farm -n 5 -e luckmail -m access_token --json

# 注册 N 个长期号（含 refresh_token，Gmail 真实邮箱，需后续人工介入）
gpt-farm farm -n 2 -e gmail -m refresh_token --json

# 推送所有本地账号到 CPA
gpt-farm push

# 查看账号池状态
gpt-farm status --json

# 导入人工获取的 refresh_token
gpt-farm import-rt --token "rt_xxx..."
gpt-farm import-rt --file /path/to/rt.txt
```

## JSON 输出格式

### farm 成功
```json
{"status": "ok", "email": "xxx@outlook.it", "password": "...", "access_token": "...",
 "refresh_token": "", "id_token": "", "account_id": "", "created_at": "..."}
```

### farm 失败
```json
{"status": "error", "error": "Password failed (409): ..."}
```

### status
```json
{"local_accounts": 5, "cpa_pool": 9, "cpa_active": 8}
```

## 两个工作流

### 1. 短期号（全自动）
- Provider: `luckmail`
- Mode: `access_token`
- 生命周期：约 10 天
- 适合场景：用户需要大量临时 API 额度
- 执行方式：Agent 执行 `gpt-farm farm` + `gpt-farm push` 即可

### 2. 长期号（需要一次人工）
- Provider: `gmail`
- Mode: `refresh_token`
- 生命周期：数月，可自动续期
- 适合场景：用户需要稳定长期可用的 API
- 执行方式：Agent 执行 `gpt-farm farm` 拿到邮箱密码 → 指导用户在本地执行 `codex login` → 用户提供 refresh_token → Agent 执行 `gpt-farm import-rt` + `gpt-farm push`

## 关键提示

1. **注册时 OTP 必须快速填入**：ChatGPT 验证码有效期很短（约 10 分钟），Gmail/LuckMail 的 wait_for_code 会自动轮询。
2. **IP 质量决定成功率**：数据中心 IP 容易被 OpenAI 风控（返回 `registration_disallowed`），建议使用干净的住宅代理。
3. **LuckMail `ms_imap` 是目前最稳定的短期邮箱**：随机多国 Outlook 域名，OpenAI 不会统一拦截。
4. **拿 refresh_token 可能触发手机验证**：用户在本地执行 `codex login` 时如果要求输入手机号，Agent 可以用 HeroSMS 获取号码后告知用户填入。
5. **不要硬编码任何密钥**：所有配置通过 `~/.gpt-farm/config.json` 或环境变量 `GPT_FARM_*` 传入。

## 常见错误处理

| 错误 | 原因 | 处理 |
|------|------|------|
| `IP blocked at OAuth` | IP 被 OpenAI 拦截 | 切换代理节点 |
| `Password failed: 409` | 版本太旧或风控 | 切换 IP 重试 |
| `OTP timeout` | 邮箱未收到验证码 | 检查邮箱 provider 配置 |
| `registration_disallowed` | OpenAI 拒绝注册 | 切换 IP + 换邮箱域名 |

## 文件结构

```
~/.gpt-farm/
├── config.json      # 配置文件（不要提交到 Git）
└── accounts.json    # 本地账号库
```
