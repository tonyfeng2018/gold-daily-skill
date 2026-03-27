# 🏅 Gold Daily Skill — 黄金资讯日报

> 每日自动推送黄金资讯日报，支持 Telegram + 邮件双渠道，含实时金价、三级重要性分类、情报官多空观点、价格突变预警。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 💰 实时金价 | 每次推送时自动获取 XAU/USD 最新价（Swissquote 免费 API）|
| 🔴🟡🟢 三级分类 | 高重要性 / 中重要性 / 一般资讯，自动评分排序 |
| 📝 一句话摘要 | 每条资讯带标题 + 链接 + 摘要（VIP 文章仅显示标题）|
| 🧠 情报官观点 | 基于新闻自动推断多空方向 + 技术关键价位 |
| ⚡ 突变预警 | 金价1小时内波动 ≥1.5% 立即触发完整日报 |
| 🚫 48h 去重 | 推送过的资讯不重复发送 |
| 📧 双渠道 | Telegram + 邮件同步发送（邮件可选） |
| ⏰ 定时推送 | 每天 08:00 / 20:00 北京时间自动发送 |

---

## 📰 日报样例

```
🏅 黄金资讯日报 · 2026-03-27 08:00 BJ
💰 当前金价：XAU/USD = $4,411.38/oz

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 情报官观点 · ⚖️ 多空博弈
多空力量势均力敌，震荡整理格局延续，方向选择需等催化剂

🟢 多头支撑
  ↑ 地缘风险升温，避险需求持续支撑多头
  ↑ 主流机构维持看涨预期，结构性多头逻辑未破
🔴 空头压力
  ↓ 央行/大资金出现阶段性抛售，形成短期压力
📐 技术参考
  • 关键价位：4400、4446、4530 美元区域需重点关注
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 高重要性
• [土耳其两周抛售60吨黄金 现货金承压](链接)
  土耳其央行两周内通过出售与掉期操作抛售58.4吨黄金（超80亿美元）...
  来源：金十数据

🟡 中重要性
• [摩根大通力挺结构性牛市 现货金短线或小幅回调](链接)
  摩根大通称黄金跌17%是历史性买入机会，上调2026年目标价至$6300...
  来源：金投网

🟢 一般资讯
• [道明坚挺4831预测 现货金寻底](链接)
  道明证券维持2026年均价$4831预测，认为油价回落后降息预期将推动黄金...
  来源：金投网

⚠️ 仅供参考，不构成投资建议，请自行决策
```

---

## 🗂 文件结构

```
gold-daily-skill/
├── README.md                        # 本文件
├── scripts/
│   ├── gold_daily.py                # 日报主脚本（抓取+分析+推送）
│   └── gold_alert.py                # 价格突变预警脚本（每5分钟运行）
├── memory/                          # 运行时自动创建，无需手动操作
│   ├── gold-sent-news.json          # 48h 去重记录（首次运行自动生成）
│   └── gold-alert-state.json        # 预警状态：参考价+上次报警时间（自动生成）
└── skills/
    └── gold-daily/
        ├── SKILL.md                 # Skill 完整文档
        └── references/
            └── config.md            # 配置说明
```

> **注意：** `memory/` 目录下的文件由脚本自动创建，首次运行前无需手动创建。

---

## 🚀 快速开始

### 1. 配置参数

编辑 `scripts/gold_daily.py` 和 `scripts/gold_alert.py`，替换以下占位符：

```python
# Telegram（必填）
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"   # @BotFather 获取
TELEGRAM_CHAT_ID   = "YOUR_TELEGRAM_CHAT_ID"      # 你的 Telegram 用户 ID

# AgentMail 邮件（可选，不需要邮件推送可跳过）
AGENTMAIL_API_KEY  = "YOUR_AGENTMAIL_API_KEY"      # console.agentmail.to 获取
AGENTMAIL_INBOX    = "YOUR_INBOX@agentmail.to"     # 创建后填入
EMAIL_TO           = "YOUR_EMAIL@gmail.com"         # 收件邮箱
```

> **只用 Telegram 不需要邮件？** 在 `gold_daily.py` 的 `main()` 函数中注释掉 `send_email(report, bj_now)` 这行即可。

> **如何获取 Telegram Chat ID：** 向你的机器人发一条消息，然后访问
> `https://api.telegram.org/bot<TOKEN>/getUpdates`，找 `chat.id` 字段。

### 2. 创建 memory 目录

```bash
mkdir -p memory
echo '{"sent":[]}' > memory/gold-sent-news.json
echo '{}' > memory/gold-alert-state.json
```

### 3. 测试运行

```bash
python3 scripts/gold_daily.py
```

正常输出应包含：
```
[gold_daily] Price: 4411.38
[gold_daily] Fetched 15 items before dedup
[gold_daily] New items after dedup: 10
[gold_daily] Telegram sent: message_id=xxx
[gold_daily] Email sent: <xxx@email.amazonses.com>
```

### 4. 设置定时任务（OpenClaw Cron）

**早报（每天 08:00 北京时间）：**
```json
{
  "name": "黄金日报 - 早报",
  "schedule": { "kind": "cron", "expr": "0 0 * * *", "tz": "Asia/Shanghai" },
  "payload": { "kind": "agentTurn", "message": "直接运行 python3 /path/to/scripts/gold_daily.py" },
  "sessionTarget": "isolated"
}
```

**晚报（每天 20:00 北京时间）：**
```json
{
  "name": "黄金日报 - 晚报",
  "schedule": { "kind": "cron", "expr": "0 12 * * *", "tz": "UTC" },
  "payload": { "kind": "agentTurn", "message": "直接运行 python3 /path/to/scripts/gold_daily.py" },
  "sessionTarget": "isolated"
}
```

**价格突变预警（每5分钟）：**
```json
{
  "name": "黄金价格突变预警",
  "schedule": { "kind": "cron", "expr": "*/5 * * * *", "tz": "UTC" },
  "payload": { "kind": "agentTurn", "message": "直接运行 python3 /path/to/scripts/gold_alert.py" },
  "sessionTarget": "isolated"
}
```

### 5. 运行依赖

- Python 3.8+
- 仅使用标准库（`urllib`、`json`、`re`），**无需额外安装任何包**

---

## 📊 重要性评分规则

### 高权重关键词（+2分）
`暴涨` `暴跌` `历史新高` `创纪录` `央行购金` `美联储` `FOMC` `利率决议` `非农` `CPI` `伊朗` `战争` `冲突` `霍尔木兹` `地缘` `土耳其` `SPDR` `ETF持仓` `抛售` `突破`

### 普通权重关键词（+1分）
`通胀` `美元` `利率` `避险` `摩根大通` `高盛` `渣打` `道明` `麦格理` `COMEX` `牛市` `熊市` `调整` `反弹` `寻底` `看涨` `看跌`

### 分级标准
| 等级 | 分数 | 最多显示 |
|------|------|---------|
| 🔴 高重要性 | ≥ 4 | 3 条 |
| 🟡 中重要性 | 2–3 | 4 条 |
| 🟢 一般资讯 | < 2 | 3 条 |

---

## ⚡ 价格突变预警逻辑

- 每5分钟抓取一次实时金价
- 与1小时前的参考价对比，波动 ≥ **1.5%** 触发预警
- 预警内容：方向（暴涨/暴跌）+ 涨跌幅 + 当前价 + 参考价
- 预警后自动推送完整日报
- **30分钟冷却期**，防止频繁重复报警

---

## 🔗 数据来源

| 来源 | 用途 | 说明 |
|------|------|------|
| [Swissquote API](https://forex-data-feed.swissquote.com) | 实时金价 | 免费，无需 Key |
| [金十数据 xnews](https://xnews.jin10.com) | 新闻（优先）| 最快最准 |
| [金投网](https://www.cngold.org/xhhj/) | 新闻（补充）| 深度分析文章 |

---

## 📄 License

MIT — 自由使用，欢迎分享。

---

> ⚠️ 本工具输出内容仅供参考，不构成投资建议。金融市场有风险，投资需谨慎。
