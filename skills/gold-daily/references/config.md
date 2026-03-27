# gold-daily/references/config.md

## 使用者配置（部署时替换）

```
TELEGRAM_BOT_TOKEN = "你的BotToken"
TELEGRAM_CHAT_ID   = "你的Telegram用户ID"

AGENTMAIL_API_KEY  = "am_us_xxx..."
AGENTMAIL_INBOX    = "你的inbox@agentmail.to"
EMAIL_TO           = "你的邮件地址"
```

## 获取方式

- **Telegram Bot Token**：找 @BotFather 创建机器人，获取 token
- **Telegram Chat ID**：向机器人发一条消息后，访问 `https://api.telegram.org/bot<TOKEN>/getUpdates`，找 `chat.id`
- **AgentMail API Key**：注册 https://console.agentmail.to 获取
- **AgentMail Inbox**：调用 AgentMail API 创建，或在控制台新建

## 数据源（无需配置，免费公开）

- 实时金价：`forex-data-feed.swissquote.com`（免费，无需Key）
- 新闻：`xnews.jin10.com`（金十数据）+ `cngold.org`（金投网）
