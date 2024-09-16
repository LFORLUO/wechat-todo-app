from flask import Flask, request, abort
import requests
import json
from pyairtable import Table
import os
from datetime import datetime, timedelta
import dateparser

app = Flask(__name__)

# 配置
CORP_ID = os.environ.get('CORP_ID')
CORP_SECRET = os.environ.get('CORP_SECRET')
AGENT_ID = os.environ.get('AGENT_ID')
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME')
TOKEN = os.environ.get('TOKEN')
ENCODING_AES_KEY = os.environ.get('ENCODING_AES_KEY')

airtable = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

def get_access_token():
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={CORP_SECRET}"
    r = requests.get(url)
    return r.json()['access_token']

def send_message(user_id, content):
    access_token = get_access_token()
    url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
    data = {
        "touser": user_id,
        "msgtype": "text",
        "agentid": AGENT_ID,
        "text": {
            "content": content
        }
    }
    r = requests.post(url, json=data)
    return r.json()

def parse_deadline(date_string):
    parsed_date = dateparser.parse(date_string, languages=['zh', 'en'])
    if parsed_date:
        if parsed_date.time() == datetime.min.time():
            parsed_date = parsed_date.replace(hour=23, minute=59, second=59)
        return parsed_date
    return None

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # 验证URL
        msg_signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        # 这里需要实现验证逻辑，返回解密后的 echostr
        # 由于涉及到加密解密，这里省略具体实现
        return echostr

    # 处理POST请求（接收消息）
    try:
        data = json.loads(request.data)
        # 这里需要实现消息解密逻辑
        # 由于涉及到加密解密，这里假设已经解密，直接处理明文
        return handle_message(data)
    except Exception as e:
        print(e)
        abort(400)

def handle_message(data):
    msg_type = data.get('MsgType')
    from_username = data.get('FromUserName')
    content = data.get('Content', '')

    if msg_type == 'text':
        if content.startswith('添加:'):
            return add_todo(from_username, content[3:])
        elif content == '查询':
            return query_todos(from_username)
        else:
            return send_message(from_username, "无法识别的命令。请使用'添加:任务内容,截止日期'来添加待办事项，或发送'查询'来查看待办事项。")
    else:
        return send_message(from_username, "请发送文本消息。")

def add_todo(user_id, content):
    parts = content.split(',')
    if len(parts) < 2:
        return send_message(user_id, "格式错误。请使用'任务内容,截止日期'的格式。")
    
    task = parts[0].strip()
    date_string = parts[1].strip()
    
    deadline = parse_deadline(date_string)
    if not deadline:
        return send_message(user_id, "无法识别的日期格式，请重新输入。")
    
    airtable.create({'任务内容': task, '截止时间': deadline.isoformat(), '状态': '未完成', '用户ID': user_id})
    
    return send_message(user_id, f"已添加待办事项: {task}，截止时间: {deadline.strftime('%Y-%m-%d %H:%M')}")

def query_todos(user_id):
    todos = airtable.all(formula=f"AND({{用户ID}}='{user_id}', {{状态}}='未完成')", sort=['截止时间'])
    
    if not todos:
        return send_message(user_id, "当前没有待办事项。")
    
    reply = "您的待办事项：\n"
    for todo in todos:
        deadline = datetime.fromisoformat(todo['fields']['截止时间'])
        reply += f"- {todo['fields']['任务内容']} (截止：{deadline.strftime('%Y-%m-%d %H:%M')})\n"
    
    return send_message(user_id, reply)

@app.route('/check_todos', methods=['GET'])
def check_todos():
    now = datetime.now()
    soon = now + timedelta(hours=1)
    
    formula = f"AND(IS_BEFORE({{截止时间}}, '{soon.isoformat()}'), IS_AFTER({{截止时间}}, '{now.isoformat()}'), {{状态}}='未完成')"
    records = airtable.all(formula=formula)
    
    for record in records:
        user_id = record['fields']['用户ID']
        task = record['fields']['任务内容']
        deadline = datetime.fromisoformat(record['fields']['截止时间'])
        message = f"提醒：您的待办事项 '{task}' 将在 {deadline.strftime('%Y-%m-%d %H:%M')} 到期。"
        send_message(user_id, message)
    
    return "OK", 200

if __name__ == '__main__':
    app.run()