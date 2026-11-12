#!/usr/bin/env python3
# 留言页(拼接式,避免 f-string 嵌套)
import os, re
B = "/Users/cuisiqi/WorkBuddy/2026-11-10-16-34-12/gold-site/"
p = B + "build.py"
src = open(p).read()

if "def page_feedback" in src:
    print("page_feedback 已存在,跳过创建")
else:
    anchor = "def page_about(data):"
    assert src.count(anchor) == 1
    FEEDBACK = (
        "def page_feedback(data):\n"
        "    head = head_html(\n"
        '        "留言反馈 - 意见建议与需求沟通 - 金潮网",\n'
        '        "向金潮网发送意见、建议与功能需求,直达站长邮箱。",\n'
        '        SITE + "feedback.html")\n'
        '    parts = []\n'
        "    parts.append(topbar_html(data))\n"
        "    parts.append(ticker_html(data))\n"
        "    parts.append(nav_html(\"feedback\"))\n"
        "    parts.append(subnav_html(\"feedback\"))\n"
        "    parts.append('<div class=\"wrap\"><div class=\"portal\">')\n"
        "    parts.append(side_left(\"feedback\"))\n"
        "    parts.append('<div class=\"portal-main\">')\n"
        "    parts.append('<main>')\n"
        "    parts.append('<section class=\"section\" id=\"feedback\">')\n"
        "    parts.append('<div class=\"section-head\"><div><div class=\"lbl\">FEEDBACK</div>'\n"
        "                 '<h2>留言反馈</h2>'\n"
        "                 '<p>意见、建议、功能需求、合作洽谈——留言直达站长邮箱,每封都会读。</p></div></div>')\n"
        "    parts.append('<div class=\"card\" style=\"max-width:760px\">')\n"
        "    parts.append('<div class=\"alert-row\" style=\"flex-direction:column;align-items:stretch\">')\n"
        "    parts.append('<input id=\"fbName\" type=\"text\" placeholder=\"称呼(选填)\">')\n"
        "    parts.append('<input id=\"fbMail\" type=\"email\" placeholder=\"你的邮箱(选填,需要回复时填写)\">')\n"
        "    parts.append('<textarea id=\"fbBody\" rows=\"6\" placeholder=\"留言内容(必填):意见、建议、需求……\" style=\"resize:vertical\"></textarea>')\n"
        "    parts.append('</div>')\n"
        "    parts.append('<button class=\"btn\" id=\"fbSubmit\" type=\"button\">发送留言</button>')\n"
        "    parts.append('<div class=\"hint\" id=\"fbNote\" style=\"margin-top:10px\">点击发送将唤起邮件客户端(内容已预填),发送后直达站长邮箱;通常 24h 内回复。</div>')\n"
        "    parts.append('</div></section></main></div>')\n"
        "    parts.append(side_right(data))\n"
        "    parts.append('</div></div>')\n"
        "    parts.append(footer_html())\n"
        "    parts.append('<script id=\"app-data\" type=\"application/json\">{}</script>')\n"
        "    parts.append('<script src=\"./ads.js\"></script>')\n"
        "    parts.append('<script src=\"./common.js?v=' + TS + '\"></script>')\n"
        "    parts.append('<script src=\"./app.js?v=' + TS + '\"></script>')\n"
        "    parts.append('<script>')\n"
        "    parts.append('(function(){')\n"
        "    parts.append('  var s = document.getElementById(\"fbSubmit\");')\n"
        "    parts.append('  if (!s) return;')\n"
        "    parts.append('  s.addEventListener(\"click\", function () {')\n"
        "    parts.append('    var body = (document.getElementById(\"fbBody\") || {}).value || \"\";')\n"
        "    parts.append('    var name = (document.getElementById(\"fbName\") || {}).value || \"匿名\";')\n"
        "    parts.append('    var mail = (document.getElementById(\"fbMail\") || {}).value || \"未填写\";')\n"
        "    parts.append('    if (!body.trim()) { alert(\"请填写留言内容\"); return; }')\n"
        "    parts.append('    var full = \"称呼:\" + name + \"\\\\n联系邮箱:\" + mail + \"\\\\n\\\\n留言内容:\\\\n\" + body + \"\\\\n\\\\n时间:\" + new Date().toLocaleString();')\n"
        "    parts.append('    window.location.href = \"mailto:\" + (window.DATA && window.DATA.alert_mail || \"314726018@qq.com\") +')\n"
        "    parts.append('      \"?subject=\" + encodeURIComponent(\"【金潮网】用户留言 - \" + name) +')\n"
        "    parts.append('      \"&body=\" + encodeURIComponent(full);')\n"
        "    parts.append('    var n = document.getElementById(\"fbNote\");')\n"
        "    parts.append('    if (n) n.innerHTML = \"已唤起邮件客户端,请点击发送完成留言。\";')\n"
        "    parts.append('  });')\n"
        "    parts.append('})();')\n"
        "    parts.append('</script>')\n"
        "    parts.append('</body></html>')\n"
        "    return head + \"\".join(parts)\n"
        "\n"
        "\n")
    src = src.replace(anchor, FEEDBACK + anchor, 1)
    # 生成调用
    m = re.search(r'(with open\(os\.path\.join\(DOCS, "about\.html"\)[^)]*\) as f:\n\s+f\.write\(page_about\(data\)\))', src)
    if m:
        add = (m.group(1) +
               '\n    with open(os.path.join(DOCS, "feedback.html"), "w", encoding="utf-8") as f:\n'
               '        f.write(page_feedback(data))')
        src = src.replace(m.group(1), add, 1)
        print("feedback.html 生成调用 OK")
    else:
        print("⚠️ about 生成锚点未命中")

# footer 链接
src = open(p).read()
if "留言反馈</a>" not in src:
    m = re.search(r'(<a href="\./about\.html">关于本站</a>)', src)
    if m:
        src = src.replace(m.group(1), '<a href="./feedback.html">留言反馈</a>' + m.group(1), 1)
        print("footer 留言链接 OK")

open(p, "w").write(src)
print("留言页完成")
