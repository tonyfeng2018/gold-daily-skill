#!/usr/bin/env python3
"""
gold_alert.py — 黄金价格突变预警脚本
当金价波动超过 ALERT_PCT（默认1.5%）时，立即触发日报推送
运行方式：每5分钟由 cron 调用一次
状态文件：memory/gold-alert-state.json
"""

import urllib.request, json, time, os, sys
from datetime import datetime, timezone, timedelta

ALERT_PCT   = 1.5          # 触发阈值（%）
STATE_FILE  = os.path.expanduser("~/.openclaw/workspace/memory/gold-alert-state.json")
DAILY_SCRIPT = os.path.expanduser("~/.openclaw/workspace/scripts/gold_daily.py")

TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID   = "YOUR_TELEGRAM_CHAT_ID"


def get_price():
    try:
        url = "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD"
        req = urllib.request.Request(url, headers={"User-Agent": "GoldAlert/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())
        bid = d[0]["spreadProfilePrices"][0]["bid"]
        ask = d[0]["spreadProfilePrices"][0]["ask"]
        return round((bid + ask) / 2, 2)
    except Exception as e:
        print(f"[gold_alert] price fetch error: {e}")
        return None


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_alert_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            print(f"[gold_alert] Alert sent: message_id={resp['result']['message_id']}")
    except Exception as e:
        print(f"[gold_alert] Alert send error: {e}")


def escape_mdv2(text):
    chars_to_escape = r'\$!.+=#|{}->'
    return ''.join('\\' + c if c in chars_to_escape else c for c in text)


def main():
    price = get_price()
    if price is None:
        return

    state = load_state()
    now_ts = time.time()
    ref_price = state.get("ref_price")
    ref_ts    = state.get("ref_ts", 0)

    # 每小时更新一次参考价（用于计算1小时内波动）
    if ref_price is None or (now_ts - ref_ts) > 3600:
        state["ref_price"] = price
        state["ref_ts"]    = now_ts
        save_state(state)
        print(f"[gold_alert] Ref price reset to {price}")
        return

    pct_change = (price - ref_price) / ref_price * 100
    direction  = "🚨 暴涨" if pct_change > 0 else "🚨 暴跌"

    print(f"[gold_alert] Current={price}, Ref={ref_price}, Change={pct_change:.2f}%")

    if abs(pct_change) >= ALERT_PCT:
        # 防止短时间内重复报警（30分钟冷却）
        last_alert_ts = state.get("last_alert_ts", 0)
        if now_ts - last_alert_ts < 1800:
            print(f"[gold_alert] Cooldown active, skip alert")
            return

        bj_tz  = timezone(timedelta(hours=8))
        bj_now = datetime.now(bj_tz)

        # 发预警消息
        alert_msg = escape_mdv2(
            f"⚡ 金价突变预警 · {bj_now.strftime('%H:%M')} BJ\n"
            f"{direction} {pct_change:+.2f}%\n"
            f"当前价：${price:,.2f} /oz\n"
            f"参考价：${ref_price:,.2f} /oz\n"
            f"正在推送完整日报..."
        )
        send_alert_tg(alert_msg)

        # 触发完整日报
        import subprocess
        result = subprocess.run(
            ["python3", DAILY_SCRIPT],
            capture_output=True, text=True, timeout=120
        )
        print(result.stdout[-500:] if result.stdout else "")

        # 更新状态
        state["last_alert_ts"] = now_ts
        state["ref_price"]     = price   # 以新价为参考，避免连续触发
        state["ref_ts"]        = now_ts
        save_state(state)
    else:
        save_state(state)


if __name__ == "__main__":
    main()
