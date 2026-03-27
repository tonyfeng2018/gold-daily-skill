#!/usr/bin/env python3
"""
gold_daily.py — 黄金资讯日报自动推送脚本
数据源：金投网(cngold.org) + 金十数据(jin10.com) + Swissquote API（实时金价）
推送：Telegram Bot
去重：memory/gold-sent-news.json（保留48小时内已发过的链接）
"""

import urllib.request
import json
import re
import time
import os
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser

# ── 配置 ──────────────────────────────────────────────
SENT_FILE = os.path.expanduser(
    "~/.openclaw/workspace/memory/gold-sent-news.json"
)
DEDUP_HOURS = 48  # 去重窗口（小时）

# Telegram 配置（直接调 Bot API，不经过 agent）
TELEGRAM_BOT_TOKEN = "8712545638:AAGjQGZ8QD1XN8xVEE19dHJex_DYsGTEFpM"
TELEGRAM_CHAT_ID   = "7796298136"

# AgentMail 邮件配置
AGENTMAIL_API_KEY = "am_us_30c1c67833ee414b2694fa640dd43fa61ee736e0497f5c83028bd79320578e8e"
AGENTMAIL_INBOX   = "gater-gold@agentmail.to"
EMAIL_TO          = "tongfweb3@gmail.com"

# ── 工具函数 ──────────────────────────────────────────

def fetch(url, timeout=10):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GoldBot/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def get_gold_price():
    """从 Swissquote 免费 API 获取 XAU/USD 实时价格"""
    try:
        url = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD"
        data = json.loads(fetch(url, timeout=8))
        bid = data[0]["spreadProfilePrices"][0]["bid"]
        ask = data[0]["spreadProfilePrices"][0]["ask"]
        mid = round((bid + ask) / 2, 2)
        return mid
    except Exception as e:
        return None


class SimpleHTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
    def handle_data(self, d):
        self.result.append(d)
    def get_text(self):
        return "".join(self.result)


def strip_html(text):
    s = SimpleHTMLStripper()
    s.feed(text)
    return s.get_text().strip()


# ── 去重管理 ──────────────────────────────────────────

def load_sent():
    try:
        with open(SENT_FILE) as f:
            data = json.load(f)
        # 清理超过 48h 的旧记录
        cutoff = time.time() - DEDUP_HOURS * 3600
        data["sent"] = [x for x in data.get("sent", []) if x["ts"] > cutoff]
        return data
    except Exception:
        return {"sent": []}


def save_sent(data):
    with open(SENT_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_new(url, sent_data):
    known = {x["url"] for x in sent_data.get("sent", [])}
    return url not in known


def mark_sent(url, sent_data):
    sent_data["sent"].append({"url": url, "ts": time.time()})


# ── 新闻抓取 ──────────────────────────────────────────

def fetch_cngold_news():
    """金投网现货黄金新闻列表，附带正文摘要"""
    try:
        html = fetch("https://www.cngold.org/xhhj/", timeout=12)
        pattern = r'href="(https://www\.cngold\.org/c/2026-\d{2}-\d{2}/[^"]+\.html)"[^>]*>([^<]{10,80})</a>'
        items = re.findall(pattern, html)
        results = []
        for url, title in items:
            title = strip_html(title).strip()
            if re.match(r'^今日现货黄金价格多少', title): continue
            if re.match(r'^今日现货黄金走势实时行情', title): continue
            if len(title) < 8: continue
            summary = _fetch_summary(url)
            results.append({"title": title, "url": url, "source": "金投网", "summary": summary})
        return results[:15]
    except Exception:
        return []


def fetch_jin10_gold_news():
    """金十数据 xnews 黄金相关文章"""
    try:
        html = fetch("https://xnews.jin10.com/", timeout=12)
        pattern = r'href="(https://xnews\.jin10\.com/details/(\d+))"[^>]*>\s*([^<]{10,80})\s*(?:</a>|<)'
        items = re.findall(pattern, html)
        gold_kw = ["黄金", "金价", "XAU", "金市", "贵金属", "避险", "美联储", "通胀",
                   "央行购金", "COMEX", "SPDR", "伊朗", "地缘", "美元", "利率", "鲍威尔"]
        results = []
        seen_ids = set()
        for url, art_id, title in items:
            title = strip_html(title).strip()
            if art_id in seen_ids: continue
            if any(k in title for k in gold_kw) and len(title) > 8:
                seen_ids.add(art_id)
                summary = _fetch_summary(url)
                results.append({"title": title, "url": url, "source": "金十数据", "summary": summary})
        return results[:8]
    except Exception:
        return []


def _fetch_summary(url, max_chars=80):
    """抓取文章正文第一句话作为摘要"""
    try:
        html = fetch(url, timeout=8)
        # 找【要闻速递】后的第一段正文
        m = re.search(r'【要闻速递】\s*\n+(.{20,200}?)[\n。！？]', html)
        if m:
            return m.group(1).strip()[:max_chars]
        # 否则取 <p> 第一段
        m = re.search(r'<p[^>]*>([^<]{20,200})</p>', html)
        if m:
            return strip_html(m.group(1)).strip()[:max_chars]
        return ""
    except Exception:
        return ""


# ── 重要性评分 ─────────────────────────────────────────

# 高权重：命中即 score+2
HIGH_KW_2 = [
    "暴涨", "暴跌", "历史新高", "创纪录", "大涨", "大跌",
    "央行购金", "美联储", "FOMC", "利率决议", "非农", "CPI",
    "伊朗", "战争", "冲突", "霍尔木兹", "地缘",
    "土耳其", "SPDR", "ETF持仓", "抛售", "突破",
]
# 普通权重：命中 score+1
HIGH_KW_1 = [
    "通胀", "美元", "利率", "避险",
    "摩根大通", "高盛", "渣打", "道明", "麦格理", "COMEX",
    "牛市", "熊市", "调整", "反弹", "寻底", "看涨", "看跌",
]

def score_item(item):
    score = 0
    title = item["title"]
    for kw in HIGH_KW_2:
        if kw in title:
            score += 2
    for kw in HIGH_KW_1:
        if kw in title:
            score += 1
    return score


# ── 市场观点生成（基于当前新闻信号）────────────────────

def build_market_view(news_items, gold_price):
    """
    根据新闻标题信号综合判断市场多空趋势，输出结构化观点。
    逻辑：
      - 地缘/战争/冲突/避险 → 利多信号
      - 央行抛售/大户抛售/美联储鹰派 → 利空信号
      - 机构看涨/结构性牛市 → 多头支撑
      - 支撑/阻力关键位 → 技术参考
    """
    all_titles = " ".join(x["title"] for x in news_items)

    # ── 信号计数 ──
    bull_signals = []
    bear_signals = []
    tech_notes = []

    # 多头信号
    if any(k in all_titles for k in ["地缘", "冲突", "战争", "里海", "伊朗", "导弹", "避险"]):
        bull_signals.append("地缘风险升温，避险需求持续支撑多头")
    if any(k in all_titles for k in ["摩根大通", "高盛", "渣打", "道明", "麦格理", "结构性牛市", "力挺", "看涨"]):
        bull_signals.append("主流机构维持看涨预期，结构性多头逻辑未破")
    if any(k in all_titles for k in ["央行购金", "世界黄金协会", "央行继续买"]):
        bull_signals.append("央行购金趋势延续，长期需求端有力托底")
    if any(k in all_titles for k in ["深V", "V型", "暴力反弹", "反弹", "回升"]):
        bull_signals.append("价格出现深V修复形态，多头有反击迹象")

    # 空头信号
    if any(k in all_titles for k in ["抛售", "大户抛售", "减持", "卖出", "土耳其"]):
        bear_signals.append("央行/大资金出现阶段性抛售，形成短期压力")
    if any(k in all_titles for k in ["美联储", "鹰派", "加息", "高利率", "美元走强"]):
        bear_signals.append("美联储鹰派信号或美元走强，压制金价上行空间")
    if any(k in all_titles for k in ["调整", "回调", "寻底", "跌", "下跌", "承压", "难守"]):
        bear_signals.append("短线技术面承压，价格处于调整修复阶段")

    # 技术面关键位提取（从标题中找数字关键位）
    levels = re.findall(r'(\d{4,5})(?:支撑|阻力|关口|上看|一线)', all_titles)
    if levels:
        unique_levels = sorted(set(int(x) for x in levels))
        tech_notes.append(f"关键价位：{'、'.join(str(x) for x in unique_levels)} 美元区域需重点关注")

    # 价格对比
    if gold_price:
        tech_notes.append(f"当前价 ${gold_price:,.2f}，处于{'高位震荡' if gold_price > 4400 else '支撑区间'}")

    # ── 综合趋势判断 ──
    bull_count = len(bull_signals)
    bear_count = len(bear_signals)

    if bull_count > bear_count + 1:
        trend = "📈 整体偏多"
        trend_desc = "多头逻辑主导，地缘风险与机构支撑形成合力，趋势性上行概率较高"
    elif bear_count > bull_count + 1:
        trend = "📉 整体偏空"
        trend_desc = "空头压力占优，抛售压力与技术面调整共振，短期上行受阻"
    else:
        trend = "⚖️ 多空博弈"
        trend_desc = "多空力量势均力敌，价格进入震荡整理区间，方向选择需等待催化剂"

    # ── 组装观点文本 ──
    view_lines = []
    view_lines.append("━" * 28)
    view_lines.append(f"🧠 *情报官观点 · {trend}*")
    view_lines.append(f"_{trend_desc}_")
    view_lines.append("")

    if bull_signals:
        view_lines.append("🟢 *多头支撑*")
        for s in bull_signals:
            view_lines.append(f"  ↑ {s}")

    if bear_signals:
        view_lines.append("🔴 *空头压力*")
        for s in bear_signals:
            view_lines.append(f"  ↓ {s}")

    if tech_notes:
        view_lines.append("📐 *技术参考*")
        for t in tech_notes:
            view_lines.append(f"  • {t}")

    view_lines.append("━" * 28)
    return "\n".join(view_lines)


# ── 日报生成 ──────────────────────────────────────────

def build_report(news_items, gold_price, bj_time):
    lines = []
    lines.append(f"🏅 *黄金资讯日报 · {bj_time.strftime('%Y-%m-%d %H:%M')} BJ*")
    lines.append(f"💰 *当前金价：XAU/USD = ${gold_price:,.2f}/oz*" if gold_price else "💰 *当前金价：获取失败，请稍后查看*")
    lines.append("")

    # 观点总结放在正文前面
    lines.append(build_market_view(news_items, gold_price))
    lines.append("")

    high   = [x for x in news_items if x.get("score", 0) >= 4]
    medium = [x for x in news_items if 2 <= x.get("score", 0) < 4]
    low    = [x for x in news_items if x.get("score", 0) < 2]

    if high:
        lines.append("🔴 *高重要性*")
        for item in high[:3]:
            lines.append(f"• [{item['title']}]({item['url']})")
            lines.append(f"  _{item.get('summary', '')}_ _来源：{item['source']}_")
        lines.append("")

    if medium:
        lines.append("🟡 *中重要性*")
        for item in medium[:4]:
            lines.append(f"• [{item['title']}]({item['url']})")
            lines.append(f"  _{item.get('summary', '')}_ _来源：{item['source']}_")
        lines.append("")

    if low:
        lines.append("🟢 *一般资讯*")
        for item in low[:3]:
            lines.append(f"• [{item['title']}]({item['url']})")
            lines.append(f"  _{item.get('summary', '')}_ _来源：{item['source']}_")

    lines.append("")
    lines.append("_⚠️ 仅供参考，不构成投资建议，请自行决策_")
    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────

def main():
    bj_tz = timezone(timedelta(hours=8))
    bj_now = datetime.now(bj_tz)

    # 获取实时金价
    price = get_gold_price()
    print(f"[gold_daily] Price: {price}")

    # 加载去重记录
    sent_data = load_sent()

    # 抓取新闻
    all_news = fetch_cngold_news() + fetch_jin10_gold_news()
    print(f"[gold_daily] Fetched {len(all_news)} items before dedup")

    # 去重 + 评分
    new_items = []
    for item in all_news:
        if is_new(item["url"], sent_data):
            item["score"] = score_item(item)
            new_items.append(item)

    # 按重要性排序，高分优先
    new_items.sort(key=lambda x: x["score"], reverse=True)
    # 去掉重复标题
    seen_titles = set()
    deduped = []
    for item in new_items:
        if item["title"] not in seen_titles:
            seen_titles.add(item["title"])
            deduped.append(item)

    top_items = deduped[:10]
    print(f"[gold_daily] New items after dedup: {len(top_items)}")

    if not top_items:
        print("[gold_daily] No new items, skip sending")
        return

    # 生成报告
    report = build_report(top_items, price, bj_now)

    # 标记已发送
    for item in top_items:
        mark_sent(item["url"], sent_data)
    save_sent(sent_data)

    # ── 直接调 Telegram Bot API 发送 ─────────────────────
    send_telegram(report)

    # ── 发送邮件 ──────────────────────────────────────
    send_email(report, bj_now)

    # 输出供日志查看
    print("=== REPORT ===")
    print(report)
    print("=== END ===")

    return report


def send_telegram(report_text):
    """直接调 Telegram Bot API，支持 MarkdownV2 格式"""
    try:
        # 转义 MarkdownV2 特殊字符（保留 Markdown 语法结构）
        escaped = _escape_mdv2(report_text)
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": escaped,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            if resp.get("ok"):
                print(f"[gold_daily] Telegram sent: message_id={resp['result']['message_id']}")
            else:
                print(f"[gold_daily] Telegram error: {resp}")
    except Exception as e:
        print(f"[gold_daily] Telegram exception: {e}")


def _escape_mdv2(text):
    """转义 MarkdownV2 中需要转义的特殊字符，不动 Markdown 语法符号"""
    # MarkdownV2 中所有需要转义的特殊字符
    # 但要保留 *_`[]()~ 这些 Markdown 控制字符
    chars_to_escape = r'\$!.+=#|{}->'
    result = []
    for c in text:
        if c in chars_to_escape:
            result.append('\\' + c)
        else:
            result.append(c)
    return ''.join(result)


def send_email(report_text, bj_time):
    """通过 AgentMail API 发送邮件"""
    import urllib.parse
    try:
        subject = f"🏅 黄金资讯日报 · {bj_time.strftime('%Y-%m-%d %H:%M')} BJ"
        # 去掉 Telegram Markdown 符号（*、_、\）还原纯文本
        plain = re.sub(r'(?<!\\)[*_]', '', report_text)
        plain = plain.replace('\\', '')

        payload = json.dumps({
            "to": EMAIL_TO,
            "subject": subject,
            "text": plain
        }).encode("utf-8")

        inbox_enc = urllib.parse.quote(AGENTMAIL_INBOX, safe='')
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_enc}/messages/send"
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Authorization", f"Bearer {AGENTMAIL_API_KEY}")
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            print(f"[gold_daily] Email sent: {resp.get('message_id','?')}")
    except Exception as e:
        print(f"[gold_daily] Email error: {e}")


if __name__ == "__main__":
    main()
