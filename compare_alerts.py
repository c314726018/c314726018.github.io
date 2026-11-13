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


def latest_quote(data, symbol):
    """返回 (last, prev, unit)——prev 优先昨结/昨收/今开,用于涨跌幅计算。"""
    for it in data.get("items") or []:
        if it.get("symbol") == symbol:
            prev = it.get("prev_close") or it.get("open")
            return it.get("last"), prev, it.get("unit") or ""
    ex = data.get("extra") or {}
    for x in ex.get("futures") or []:
        if x.get("name") == symbol or x.get("code") == symbol:
            prev = x.get("prev_settle") or x.get("prev") or x.get("prev_close")
            return x.get("last"), prev, x.get("unit") or ""
    for x in ex.get("intl") or []:
        if x.get("code") == symbol or x.get("name") == symbol:
            return x.get("last"), x.get("prev"), x.get("unit") or ""
    oil = data.get("oil") or {}
    for k in ("brent", "wti", "sc"):
        x = oil.get(k) or {}
        if symbol in (x.get("name"), k.upper(), {"brent": "布伦特原油", "wti": "WTI原油", "sc": "上海原油"}.get(k)):
            prev = x.get("prev_close") or x.get("prev_settle")
            return x.get("last"), prev, x.get("unit") or ""
    return None, None, ""


def latest_price(data, symbol):
    last, _, _ = latest_quote(data, symbol)
    return last
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

    # 会员白名单(GitHub Secrets: ALERT_MEMBERS,逗号分隔邮箱);非会员免费 3 条,不支持涨跌幅触发
    members = [m.strip().lower() for m in (os.environ.get("ALERT_MEMBERS") or "").split(",") if m.strip()]
    FREE_LIMIT = 3
    free_counts = {}

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
        email = (rule.get("email") or "").strip()
        em = email.lower()
        symbol = rule.get("symbol", "")
        rh = rule_hash(rule)
        if state.get(rh) == today:
            continue  # 今日已发,防重复

        is_member = em in members
        n = free_counts.get(em, 0)
        if not is_member and n >= FREE_LIMIT:
            if not free_counts.get(em + "_notified"):
                print(f"[alerts] {em[:3]}*** 免费版上限 {FREE_LIMIT} 条,多余规则跳过(升级会员解锁)")
                free_counts[em + "_notified"] = True
            continue
        rtype = rule.get("type") or "price"

        if rtype == "pct":
            if not is_member:
                print(f"[alerts] 涨跌幅触发为会员功能,{em[:3]}*** 跳过该规则")
                continue
            pct_dir = rule.get("dir", "up")
            pct = rule.get("pct")
            last, prev, unit = latest_quote(data, symbol)
            if last is None or prev in (None, 0) or pct in (None, ""):
                print(f"[alerts] {symbol} 价格/前收缺失,跳过 {rh}")
                continue
            chg = (float(last) - float(prev)) / float(prev) * 100
            hit = (pct_dir == "up" and chg >= float(pct)) or (pct_dir == "down" and chg <= -float(pct))
            if not hit:
                continue
            arrow = "▲" if chg > 0 else "▼"
            d_txt = "涨幅" if pct_dir == "up" else "跌幅"
            subject = f"【金衡网】{symbol} 单日{d_txt}超 {pct}% · 现报 {arrow}{abs(chg):.2f}%"
            body = (f"您订阅的涨跌幅提醒已触发:\n\n"
                    f"品种:{symbol}\n"
                    f"条件:单日{d_txt}超过 {pct}%\n"
                    f"当前:{last} {unit}(较前一交易日 {arrow} {abs(chg):.2f}%)\n"
                    f"时间:{date.today().isoformat()}\n\n"
                    f"数据来源:金衡网(30 分钟更新)\n"
                    f"如不再需要请回复本邮件退订。")
        else:
            direction = rule.get("dir", "above")
            target = rule.get("target")
            last, _, unit = latest_quote(data, symbol)
            if last is None or target in (None, ""):
                print(f"[alerts] {symbol} 无最新价,跳过 {rh}")
                continue
            hit = (direction == "above" and float(last) >= float(target)) or \
                  (direction == "below" and float(last) <= float(target))
            if not hit:
                continue
            arrow = "≥" if direction == "above" else "≤"
            subject = f"【金衡网】{symbol} {arrow} {target} 触发提醒"
            body = (f"您订阅的价格提醒已触发:\n\n"
                    f"品种:{symbol}\n"
                    f"条件:{arrow} {target} {unit}\n"
                    f"当前:{last} {unit}\n"
                    f"时间:{date.today().isoformat()}\n\n"
                    f"数据来源:金衡网(30 分钟更新)\n"
                    f"如不再需要请回复本邮件退订。")

        try:
            send_mail(email, subject, body)
            sent += 1
            state[rh] = today
            if not is_member:
                free_counts[em] = free_counts.get(em, 0) + 1
            print(f"[alerts] 已发送 {symbol} → {email[:3]}***")
        except Exception as e:
            print(f"[alerts] 发信失败 {rh}: {e}")

    _save_state(state)
    print(f"[alerts] 完成:发送 {sent} 封 / 规则 {len(rules)} 条 / 会员 {len(members)} 人")


if __name__ == "__main__":
    main()
