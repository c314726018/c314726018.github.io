#!/usr/bin/env python3
"""金衡网断链自动检测+修复。

直接读线上 GitHub Pages 的 data.json，不经过邮箱。
超 45 分钟未更新 = 自续链中断 → 调 GitHub API dispatch update.yml 重启，
并验证新一轮 run 确实启动。输出结构化 JSON，供自动化任务判断是否通知用户。

防重复：4 小时内已修过则不再 dispatch（避免疯狂触发）。
状态文件：.workbuddy/autofix_state.json
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, ".workbuddy", "autofix_state.json")
# 主源用 Pages 主站,备源用 raw 直链(两者都指向同一 data.json)
RAW_PRIMARY = "https://c314726018.github.io/data.json"
RAW_FALLBACK = "https://raw.githubusercontent.com/c314726018/c314726018.github.io/main/docs/data.json"
REPO = "c314726018/c314726018.github.io"
WORKFLOW = "update.yml"
# token 存本地不入库配置(.workbuddy 已 gitignore),避免 GitHub 推送保护拦截
TOKEN_FILE = os.path.join(HERE, ".workbuddy", "gh_token.txt")


def _token():
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return f.read().strip()
THRESHOLD_MIN = 45
COOLDOWN_MIN = 240          # 4 小时内不重复修复


def api(url, method="GET", data=None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={"Authorization": f"Bearer {_token()}", "User-Agent": "jinhengwang-autofix",
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, r.read().decode("utf-8", "ignore")


def _fetch_one(url):
    """单源取 generated_at，超时放宽到 40s（国内访问 GitHub 常需 4-12s）。"""
    req = urllib.request.Request(url + "?t=" + str(int(time.time())),
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.loads(r.read().decode("utf-8", "ignore"))
    return d.get("generated_at")


def check_data():
    """返回 (是否断链, 说明)。主备双源 + 失败重试，避免网络抖动误判为断链。"""
    last_err = ""
    gen = None
    # 最多 3 次尝试：主源 → 备源 → 主源。任一次成功即采信。
    for src in (RAW_PRIMARY, RAW_FALLBACK, RAW_PRIMARY):
        try:
            gen = _fetch_one(src)
            if gen:
                break
            last_err = "返回无 generated_at"
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:60]}"
            time.sleep(3)
    if not gen:
        # 三次都没拿到 —— 判定为"取数失败"而非"数据陈旧"，交给上层重试确认
        return None, f"取数失败(主备源均不可用): {last_err}"
    t = datetime.strptime(gen, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
    age = (datetime.now(CST) - t).total_seconds() / 60
    if age < 0:
        return True, f"数据时间异常(未来): {gen}"
    detail = f"线上数据 {gen}，距今 {age:.0f} 分钟"
    return age > THRESHOLD_MIN, detail


DRY_RUN = "--dry-run" in sys.argv


def dispatch():
    """触发 workflow，返回 (成功, 说明)。dry-run 模式只模拟不真触发。"""
    if DRY_RUN:
        return True, "dispatch [DRY-RUN 模拟成功，未真实触发]"
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches"
    try:
        status, _ = api(url, method="POST", data={"ref": "main"})
        return status in (200, 201, 204), f"dispatch HTTP {status}"
    except Exception as e:
        return False, f"dispatch 异常: {type(e).__name__}: {str(e)[:100]}"


def verify_run(started_at):
    """确认有新 run 启动。"""
    url = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=5"
    try:
        _, body = api(url)
        runs = json.loads(body).get("workflow_runs", [])
        for r in runs:
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            if created >= started_at - timedelta(minutes=2):
                return True, f"新 run #{r['id']} {r['status']}"
        return False, "未发现新 run"
    except Exception as e:
        return False, f"验证异常: {str(e)[:80]}"


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


def main():
    now = datetime.now(CST)
    state = load_state()
    result = {"time": now.isoformat(), "action": "none", "notify": False, "detail": ""}

    try:
        stale, detail = check_data()
        # 取数失败(None):可能是网络抖动,等 30 秒再确认一次,连续失败才当断链处理
        if stale is None:
            result["detail"] = detail + "；30秒后二次确认"
            time.sleep(30)
            stale, detail2 = check_data()
            if stale is None:
                # 两次都取不到,才判定异常
                stale = True
                detail = detail + "；二次确认仍失败: " + detail2
            else:
                detail = detail2 + "（二次确认成功）"
        result["detail"] = detail
    except Exception as e:
        stale = True
        result["detail"] = f"检测失败: {type(e).__name__}: {str(e)[:100]}"

    if not stale:
        result["status"] = "healthy"
        # 从断链恢复
        if state.get("was_stale"):
            result["action"] = "recovered"
            result["notify"] = True
            result["detail"] += "；数据链路已恢复"
        state.update(was_stale=False, last_ok=now.isoformat())
        save_state(state)
        print(json.dumps(result, ensure_ascii=False))
        return

    # 断链
    result["status"] = "stale"
    last_fix = state.get("last_fix_ts")
    if last_fix:
        try:
            lf = datetime.fromisoformat(last_fix)
            if (now - lf).total_seconds() < COOLDOWN_MIN * 60:
                result["action"] = "cooldown"
                result["detail"] += f"；4小时内已修复过({last_fix[:19]})，跳过"
                save_state(state)
                print(json.dumps(result, ensure_ascii=False))
                return
        except Exception:
            pass

    # 执行修复
    started = datetime.now(CST)
    ok, msg = dispatch()
    result["action"] = "restart" if ok else "restart_failed"
    result["notify"] = True
    result["detail"] += f"；{msg}"

    if ok:
        time.sleep(8)
        vok, vmsg = verify_run(started)
        result["verified"] = vok
        result["detail"] += f"；{vmsg}"
    else:
        result["verified"] = False

    state.update(was_stale=True, last_fix_ts=now.isoformat())
    save_state(state)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
