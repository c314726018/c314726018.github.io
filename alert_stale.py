#!/usr/bin/env python3
"""金衡网数据断链实时告警。

监控对象:线上 GitHub Pages 的 data.json(由 GitHub Actions 自续链更新)。
原理:自续链每 5 分钟推一次数据,一旦断链 Pages 的 generated_at 就会停更。
判据:generated_at 距今 > 45 分钟 = 断链,发邮件告警。
防轰炸:同一故障 4 小时内只发一次;恢复后发一封"已恢复"并清除状态。
状态文件:.workbuddy/alert_state.json(持久目录,不放 /tmp)
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, ".workbuddy", "alert_state.json")
RAW = "https://raw.githubusercontent.com/c314726018/c314726018.github.io/main/docs/data.json"
THRESHOLD_MIN = 45          # 超过 45 分钟判定断链
COOLDOWN_MIN = 240          # 同一故障 4 小时内只告警一次
SKILL_DIR = "/Users/cuisiqi/.workbuddy/skills/qq-email"
CRED_FILE = os.path.join(SKILL_DIR, ".local_creds")   # 邮箱凭证:本地不入库
# launchd 环境 PATH 很干净,必须用绝对路径找 node
NODE = "/Users/cuisiqi/.workbuddy/binaries/node/versions/22.22.2-6/bin/node"


def _mail_creds():
    """从 skill 的本地凭证文件读邮箱账号与授权码(不硬编码入库)。"""
    creds = {}
    with open(CRED_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip().strip('"').strip("'")
    return creds.get("QQ_EMAIL_ACCOUNT"), creds.get("QQ_EMAIL_AUTH_CODE")


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)


def fetch_generated_at():
    """从线上 raw 直链取 data.json 的 generated_at 与 HTTP 状态。"""
    url = RAW + "?t=" + str(int(time.time()))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        body = r.read().decode("utf-8", "ignore")
    d = json.loads(body)
    return d.get("generated_at")


def send_mail(subject, body):
    account, auth = _mail_creds()
    if not account or not auth:
        print("发信失败: 邮箱凭证文件读取失败", file=sys.stderr)
        return False
    recipient = "314726018@qq.com"       # 收件人:用户自己的邮箱
    env = dict(os.environ)
    env["QQ_EMAIL_ACCOUNT"] = account
    env["QQ_EMAIL_AUTH_CODE"] = auth
    cmd = [NODE, "scripts/send.js", recipient, subject, body]
    p = subprocess.run(cmd, cwd=SKILL_DIR, env=env, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        print(f"发信失败: {p.stderr[:200]}", file=sys.stderr)
        return False
    print("发信成功:", subject)
    return True


def try_auto_fix():
    """调用 auto_fix_stale.py 自动修复,返回 (是否成功, 说明)。
    成功判定:action=restart 且 verified=true(已重启并确认新run),或 cooldown(4小时内已修过)。
    """
    fixer = os.path.join(HERE, "auto_fix_stale.py")
    PY = "/Users/cuisiqi/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
    if not os.path.exists(fixer):
        return False, "auto_fix_stale.py 不存在"
    try:
        p = subprocess.run([PY, fixer], capture_output=True, text=True, timeout=180)
        out = p.stdout.strip().splitlines()
        data = json.loads(out[-1]) if out else {}
        action = data.get("action")
        detail = data.get("detail", "")
        if action == "restart" and data.get("verified"):
            return True, f"已重启自续链({detail})"
        if action == "cooldown":
            return True, f"4小时内已修复过,跳过({detail})"
        if action == "recovered":
            return True, f"数据已恢复({detail})"
        return False, f"修复动作={action}: {detail}"
    except Exception as e:
        return False, f"调用修复脚本异常: {type(e).__name__}: {str(e)[:100]}"


def main():
    now = datetime.now(CST)
    state = load_state()
    stale = False
    detail = ""

    try:
        gen = fetch_generated_at()
        if not gen:
            stale = True
            detail = "线上 data.json 缺少 generated_at 字段"
        else:
            t = datetime.strptime(gen, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
            age = (now - t).total_seconds() / 60
            detail = f"线上数据时间 {gen}，距今 {age:.0f} 分钟（阈值 {THRESHOLD_MIN} 分钟）"
            stale = age > THRESHOLD_MIN
            if age < 0:
                detail += "（注意：数据时间为未来，可能是时区或时钟异常）"
                stale = True
    except Exception as e:
        stale = True
        detail = f"读取线上 data.json 失败：{type(e).__name__}: {str(e)[:120]}"

    print(f"[{now:%Y-%m-%d %H:%M:%S}] {'断链' if stale else '正常'} — {detail}")

    was_stale = state.get("stale", False)
    last_alert = state.get("last_alert_ts")
    last_alert_dt = None
    if last_alert:
        try:
            last_alert_dt = datetime.fromisoformat(last_alert)
        except Exception:
            pass

    if stale:
        # 先尝试自动修复:调用 auto_fix_stale.py 重启自续链(它内置4小时修复冷却)
        fix_ok, fix_msg = try_auto_fix()
        print(f"  自动修复：{fix_msg}")
        if fix_ok:
            # 修复已触发并验证新 run 启动 —— 静默,不发告警惊动人,记录即可
            state.update(stale=True, last_alert_ts=None, last_fix=now.isoformat(),
                         detail=detail)
            state.pop("last_alert_failed", None)
            print("  已自动修复并验证新run,本次不发告警邮件")
        else:
            # 自动修复失败或未验证 —— 才发告警让人介入
            in_cooldown = (last_alert_dt is not None and
                           (now - last_alert_dt).total_seconds() < COOLDOWN_MIN * 60)
            if not was_stale or not in_cooldown:
                ok = send_mail(
                    "【金衡网告警】数据断链，自动修复未成功",
                    f"检测时间：{now:%Y-%m-%d %H:%M:%S}\n"
                    f"异常：{detail}\n"
                    f"自动修复：{fix_msg}\n\n"
                    "自动重启自续链未成功，需人工介入：\n"
                    "1. 登录 GitHub 手动 dispatch update.yml\n"
                    "2. 或本地执行 python3 auto_fix_stale.py 查看详细错误\n"
                    "参考：~/Documents/workbuddy项目/金衡网/发布备份/发布回滚预案.md"
                )
                state.update(stale=True, last_alert_ts=now.isoformat(), detail=detail)
                if not ok:
                    state["last_alert_failed"] = True
                else:
                    state.pop("last_alert_failed", None)
            else:
                print(f"  冷却期内，跳过重复告警（上次 {last_alert}）")
    else:
        if was_stale:
            send_mail(
                "【金衡网恢复】数据已恢复更新",
                f"检测时间：{now:%Y-%m-%d %H:%M:%S}\n{detail}\n\n数据链路已恢复正常。"
            )
        state.update(stale=False, last_alert_ts=None, last_ok=now.isoformat())
        state.pop("last_alert_failed", None)

    save_state(state)


if __name__ == "__main__":
    main()
