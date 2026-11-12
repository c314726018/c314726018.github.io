#!/usr/bin/env python3
# 稳重化+移位+邮件表单+右栏固定
import os
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

# ===== 1) 稳重化:圆角收紧、pill→圆角矩形、标题加重 =====
src = src.replace("--r:16px;", "--r:10px;", 1)
src = src.replace("--r-sm:10px;", "--r-sm:7px;", 1)
n16 = src.count("border-radius:16px")
src = src.replace("border-radius:16px", "border-radius:9px")  # tabs/mode/subnav/fbtn 胶囊→圆角矩形
# 金色软底降黄
src = src.replace("--gold-soft:#fdf7e7;", "--gold-soft:#f6f1e6;", 1)
# h2 权威感:字距+紧凑
src = src.replace(".section-head h2{",
                  ".section-head h2{letter-spacing:.5px;", 1)
print("稳重化 OK(radius16x%d→9)" % n16)

# ===== 2) 右栏/左栏 sticky 内滚(内容超视口也能钉住) =====
old = ".portal-l, .portal-r{position:sticky;top:12px;display:flex;flex-direction:column;gap:12px}"
new = (".portal-l, .portal-r{position:sticky;top:12px;display:flex;flex-direction:column;gap:12px;\n"
       "  max-height:calc(100vh - 24px);overflow-y:auto;scrollbar-width:thin;\n"
       "  scrollbar-color:var(--line) transparent;padding-right:2px}")
assert src.count(old) == 1
src = src.replace(old, new, 1)
print("右栏 sticky 内滚 OK")

# ===== 3) alerts 移位:portal 后(全宽) → portal-main 内 hero 之后 =====
i_alert = src.index('  <!-- ============ 价格提醒 ============ -->')
i_end = src.index('</section>', i_alert) + len('</section>')
alert_block = src[i_alert:i_end]
# 从原位置删除(连同后面的空行)
rest = src[i_end:]
rest = rest.lstrip("\n")
src = src[:i_alert] + rest
# 插入点:portal-main 内,行情表注释之前(hero 之后)
i_q = src.index('  <!-- ============ 全宽大行情表 ============ -->')
src = src[:i_q] + alert_block + "\n\n" + src[i_q:]
print("价格提醒移位 OK(频道导航右侧顶部)")

# ===== 4) 邮件提醒表单( mailto 兜底,ALERT_MAIL 配置) =====
# 4a) 常量
src = src.replace('TS = datetime.datetime.now().strftime("%Y%m%d%H%M")  # 构建时间戳(资源版本号)',
                  'TS = datetime.datetime.now().strftime("%Y%m%d%H%M")  # 构建时间戳(资源版本号)\n'
                  'ALERT_MAIL = ""  # 站长接收邮箱(开通邮件提醒用):填写后表单提交将唤起邮件客户端预填订阅信息', 1)
# 4b) 表单块插在 alert-grid 左列末尾(copyNote 后)
old = '''          <div class="hint" id="copyNote">提醒数据保存在浏览器 localStorage；清除浏览器数据会一并删除。页面每 60 秒检查一次最新行情并比对规则。</div>'''
new = '''          <div class="hint" id="copyNote">浏览器通知保存在本机；清除浏览器数据会一并删除。</div>
          <div class="mail-box" id="mailBox">
            <div class="card-head" style="margin-bottom:8px"><h3>邮件提醒（免费）</h3></div>
            <div class="hint">触发目标价时自动发送邮件通知,无需保持页面打开。有效期 1 年,提交后 24h 内开通。</div>
            <div class="alert-row">
              <input id="mailAddr" type="email" placeholder="接收邮箱" aria-label="接收邮箱" style="flex:1 1 180px">
              <button class="btn" id="mailSubmit" type="button">提交订阅</button>
            </div>
            <div class="hint" id="mailNote">按上方选择的品种/方向/目标价开通;邮箱仅用于发送提醒,不公开。</div>
          </div>'''
assert src.count(old) == 1
src = src.replace(old, new, 1)
# 4c) 文案更新
src = src.replace('<p>设定目标价，浏览器会在价格触发时通知你。规则只存在本机，不上传。</p>',
                  '<p>两种提醒方式:①浏览器通知(即时,保持页面打开) ②邮件提醒(免费,触发自动发信,无需挂机)。可同时使用。</p>', 1)
# 4d) mail-box CSS
src = src.replace(".alert-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}",
                  ".alert-row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}\n"
                  ".mail-box{margin-top:14px;padding:12px 14px;border:1px solid var(--line);border-radius:var(--r-sm);background:var(--surface-2)}\n"
                  ".mail-box .hint{margin-bottom:8px}", 1)
open(p, "w").write(src)
print("邮件表单 OK")
