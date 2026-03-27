---
name: gold-daily
version: 1.0.0
description: >
  黄金市场情报官 — 每日自动推送黄金资讯日报（Telegram + 邮件双渠道）。
  含实时金价、三级重要性分类资讯（🔴高/🟡中/🟢一般）、情报官多空观点、
  一句话摘要、金价突变1.5%自动预警。
author: tonyfeng2018
---

# Gold Daily Skill — 黄金资讯日报

## 功能概述

| 功能 | 说明 |
|------|------|
| 📰 日报推送 | 每天 08:00 / 20:00 北京时间自动推送 |
| 💰 实时金价 | Swissquote API，发送时自动获取 XAU/USD |
| 🔴🟡🟢 三级分类 | 高（score≥4）/ 中（2-3）/ 一般（<2）|
| 📝 一句话摘要 | 每条资讯附标题+链接+摘要（VIP文章仅标题）|
| 🧠 情报官观点 | 基于新闻标题智能推断多空方向+技术关键位 |
| ⚡ 突变预警 | 金价1小时内波动≥1.5%立即触发完整日报 |
| 🚫 去重 | 48小时内推送过的资讯不重复发送 |
| 📧 双渠道 | Telegram + 邮件同步发送 |

## 数据来源（优先级）

1. **金十数据** `xnews.jin10.com` — 最快最准，优先
2. **金投网** `cngold.org/xhhj/` — 深度分析文章，补充

## 安装步骤

### 1. 配置参数

编辑 `references/config.md` 填入你的配置，然后在脚本中替换以下变量：

```python
TELEGRAM_BOT_TOKEN = "你的BotToken"
TELEGRAM_CHAT_ID   = "你的Telegram用户ID"
AGENTMAIL_API_KEY  = "am_us_xxx..."
AGENTMAIL_INBOX    = "你的inbox@agentmail.to"
EMAIL_TO           = "你的邮件地址"
```

### 2. 复制脚本

将以下两个脚本放到你的工作目录：
- `scripts/gold_daily.py` — 日报主脚本
- `scripts/gold_alert.py` — 价格突变预警脚本

### 3. 设置定时任务

在 OpenClaw 中添加以下3个 cron 任务：

**早报（08:00 北京时间）：**
```
schedule: { kind: "cron", expr: "0 0 * * *", tz: "Asia/Shanghai" }
payload: 直接运行 python3 /path/to/gold_daily.py
```

**晚报（20:00 北京时间）：**
```
schedule: { kind: "cron", expr: "0 12 * * *", tz: "UTC" }
payload: 直接运行 python3 /path/to/gold_daily.py
```

**价格预警（每5分钟）：**
```
schedule: { kind: "cron", expr: "*/5 * * * *", tz: "UTC" }
payload: 直接运行 python3 /path/to/gold_alert.py
```

### 4. 依赖

无需额外安装，脚本仅使用 Python 标准库（urllib、json、re）。

## 重要性评分规则

### +2分关键词（高权重）
暴涨、暴跌、历史新高、创纪录、大涨、大跌、央行购金、美联储、FOMC、
利率决议、非农、CPI、伊朗、战争、冲突、霍尔木兹、地缘、土耳其、
SPDR、ETF持仓、抛售、突破

### +1分关键词（普通权重）
通胀、美元、利率、避险、摩根大通、高盛、渣打、道明、麦格理、COMEX、
牛市、熊市、调整、反弹、寻底、看涨、看跌

### 分级标准
- **🔴 高重要性**：score ≥ 4（显示最多3条）
- **🟡 中重要性**：score 2-3（显示最多4条）
- **🟢 一般资讯**：score < 2（显示最多3条）

## 情报官观点逻辑

| 信号来源 | 判断 |
|---------|------|
| 地缘/冲突/伊朗/导弹 | 🟢 多头支撑 |
| 机构看涨/结构性牛市 | 🟢 多头支撑 |
| 央行购金 | 🟢 多头支撑 |
| 深V反弹 | 🟢 多头支撑 |
| 抛售/大户减持 | 🔴 空头压力 |
| 美联储鹰派/美元走强 | 🔴 空头压力 |
| 技术承压/调整 | 🔴 空头压力 |
| 多头>空头+1 | 📈 整体偏多 |
| 空头>多头+1 | 📉 整体偏空 |
| 势均力敌 | ⚖️ 多空博弈 |

## 突变预警逻辑

- 每5分钟检测当前金价 vs 1小时前参考价
- 波动 ≥ 1.5% → 立即发 Telegram 预警消息 + 触发完整日报
- 30分钟冷却期，防止频繁报警
- 报警后以当前价为新参考价，避免连续触发

## 文件结构

```
skills/gold-daily/
├── SKILL.md              # 本文件
├── references/
│   └── config.md         # 配置说明
scripts/
├── gold_daily.py         # 日报主脚本
└── gold_alert.py         # 价格突变预警脚本
memory/
├── gold-sent-news.json   # 48h去重记录
└── gold-alert-state.json # 预警状态（参考价、上次报警时间）
```

## 免责声明

本 Skill 输出内容仅供参考，不构成投资建议。金融市场有风险，投资需谨慎。
