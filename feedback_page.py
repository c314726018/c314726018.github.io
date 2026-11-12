#!/usr/bin/env python3
"""留言页 main 内核(build.py 负责完整页面包装)。"""


def main_html():
    parts = []
    a = parts.append
    a('<main>')
    a('<section class="section" id="feedback">')
    a('<div class="section-head"><div><div class="lbl">FEEDBACK</div>'
      '<h2>留言反馈</h2>'
      '<p>意见、建议、功能需求、合作洽谈——留言直达站长邮箱,每封都会读。</p></div></div>')
    a('<div class="card" style="max-width:760px">')
    a('<div class="alert-row" style="flex-direction:column;align-items:stretch">')
    a('<input id="fbName" type="text" placeholder="称呼(选填)">')
    a('<input id="fbMail" type="email" placeholder="你的邮箱(选填,需要回复时填写)">')
    a('<textarea id="fbBody" rows="6" placeholder="留言内容(必填):意见、建议、需求……" style="resize:vertical"></textarea>')
    a('</div>')
    a('<button class="btn" id="fbSubmit" type="button">发送留言</button>')
    a('<div class="hint" id="fbNote" style="margin-top:10px">点击发送将唤起邮件客户端(内容已预填),直达站长邮箱;通常 24h 内回复。</div>')
    a('</div></section></main>')
    return "".join(parts)
