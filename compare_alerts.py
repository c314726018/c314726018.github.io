#!/usr/bin/env python3
"""邮件提醒引擎:读 ALERT_RULES(JSON,GitHub Secrets)比对最新行情,触发即发信。
state(alerts_state.json)记录每条规则当日已发标记,防重复。规则 hash 不含邮箱明文。"""
import base64
import hashlib
import json
import os
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE, "alerts_state.json")
DATA_PATH = os.path.join(BASE, "docs", "data.json")

MAIL_USER = os.environ.get("MAIL_USER", "")
MAIL_PASS = os.environ.get("MAIL_PASS", "")
ALERT_RULES = os.environ.get("ALERT_RULES", "[]")

SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465


def latest_price(data, symbol):
    """按 symbol(代码/名称含匹配)从各数据组取最新价与单位。"""
    for it in data.get("items", []):
        if it.get("symbol") == symbol or it.get("label") == symbol:
            return it.get("last"), it.get("unit", "元/克")
    for key, nm in (("brent", "布伦特原油"), ("wti", "WTI原油"), ("sc", "上海原油")):
        if symbol == key.upper() or symbol in nm:
            o = data.get("oil", {}).get(key, {})
            return o.get("last"), o.get("unit", "美元/桶")
    for group in ("intl", "futures", "indices"):
        for x in data.get("extra", {}).get(group, []):
            if x.get("code") == symbol or symbol in (x.get("name") or ""):
                return x.get("last"), x.get("unit", "点")
    return None, ""


def rule_hash(rule):
    raw = "|".join(str(rule.get(k, "")) for k in ("email", "symbol", "dir", "target"))
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def send_mail(to, subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = MAIL_USER
    msg["To"] = to
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.login(MAIL_USER, MAIL_PASS)
        s.sendmail(MAIL_USER, [to], msg.as_string())


def _save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def main():
    try:
        rules = json.loads(ALERT_RULES or "[]")
    except json.JSONDecodeError:
        print("[alerts] ALERT_RULES 解析失败,跳过")
        _save_state({})
        return
    if not (MAIL_USER and MAIL_PASS):
        print("[alerts] MAIL_USER/MAIL_PASS 未配置,跳过(state 已初始化)")
        _save_state({})
        return
    if not rules:
        _save_state({})
        print("[alerts] 无订阅规则(state 已初始化)")
        return

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}

    today = date.today().isoformat()
    sent = 0
    for rule in rules:
        email = rule.get("email", "")
        symbol = rule.get("symbol", "")
        direction = rule.get("dir", "above")
        target = rule.get("target")
        rh = rule_hash(rule)
        if state.get(rh) == today:
            continue  # 今日已发,防重复
        last, unit = latest_price(data, symbol)
        if last is None or target in (None, ""):
            print(f"[alerts] {symbol} 无最新价,跳过 {rh}")
            continue
        hit = (direction == "above" and float(last) >= float(target)) or \
              (direction == "below" and float(last) <= float(target))
        if not hit:
            continue
        arrow = "≥" if direction == "above" else "≤"
        subject = f"【金潮网】{symbol} {arrow} {target} 触发提醒"
        body = (f"您订阅的价格提醒已触发:\n\n"
                f"品种:{symbol}\n"
                f"条件:{arrow} {target} {unit}\n"
                f"当前:{last} {unit}\n"
                f"时间:{date.today().isoformat()}\n\n"
                f"数据来源:金潮网(30 分钟更新)\n"
                f"本提醒为免费订阅,如不再需要请回复本邮件退订。")
        try:
            send_mail(email, subject, body)
            sent += 1
            state[rh] = today
            print(f"[alerts] 已发送 {symbol} {arrow}{target} → {email[:3]}***")
        except Exception as e:
            print(f"[alerts] 发信失败 {rh}: {e}")

    _save_state(state)
    print(f"[alerts] 完成:发送 {sent} 封 / 规则 {len(rules)} 条")


if __name__ == "__main__":
    main()
