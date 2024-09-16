from flask import Flask, request, abort
import os
import json
from datetime import datetime, timedelta
import dateparser
import requests
import base64

app = Flask(__name__)

# 配置
CORP_ID = os.environ.get('CORP_ID')
CORP_SECRET = os.environ.get('CORP_SECRET')
AGENT_ID = os.environ.get('AGENT_ID')
GITEE_TOKEN = os.environ.get('GITEE_TOKEN')
GITEE_REPO = os.environ.get('GITEE_REPO')
GITEE_OWNER = os.environ.get('GITEE_OWNER')

# Gitee API
GITEE_API_URL = f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/contents/todos.json"

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

def get_todos():
    headers = {'Authorization': f'token {GITEE_TOKEN}'}
    response = requests.get(GITEE_API_URL, headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        return json.loads(content)
    return []

def save_todos(todos):
    headers = {'Authorization': f'token {GITEE_TOKEN}'}
    content = base64.b64encode(json.dumps(todos).encode('utf-8')).decode('utf-8')
    
    # 获取当前文件的 SHA
    response = requests.get(GITEE_API_URL, headers=headers)
    sha = response.json()['sha'] if response.status_code == 200 else None
    
    data = {
        "message": "Update todos",
        "content": content,
        "sha": sha
    }
    
    response = requests.put(GITEE_API_URL, headers=headers, json=data)
    return response.status_code == 200

def add_todo(user_id, content):
    parts = content.split(',')
    if len(parts) < 2:
        return send_message(user_id, "格式错误。请使用'任务内容,截止日期'的格式。")
    
    task = parts[0].strip()
    date_string = parts[1].strip()
    
    deadline = parse_deadline(date_string)
    if not deadline:
        return send_message(user_id, "无法识别的日期格式，请重新输入。")
    
    todo = {
        "任务内容": task,
        "截止时间": deadline.isoformat(),
        "状态": "未完成",
        "用户ID": user_id
    }
    
    todos = get_todos()
    todos.append(todo)
    if save_todos(todos):
        return send_message(user_id, f"已添加待办事项: {task}，截止时间: {deadline.strftime('%Y-%m-%d %H:%M')}")
    else:
        return send_message(user_id, "添加待办事项失败，请稍后重试。")

def query_todos(user_id):
    todos = get_todos()
    user_todos = [todo for todo in todos if todo['用户ID'] == user_id and todo['状态'] == '未完成']
    user_todos.sort(key=lambda x: x['截止时间'])
    
    if not user_todos:
        return send_message(user_id, "当前没有待办事项。")
    
    reply = "您的待办事项：\n"
    for todo in user_todos:
        deadline = datetime.fromisoformat(todo['截止时间'])
        reply += f"- {todo['任务内容']} (截止：{deadline.strftime('%Y-%m-%d %H:%M')})\n"
    
    return send_message(user_id, reply)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
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
    except Exception as e:
        print(f"Error processing message: {e}")
        abort(400)

@app.route('/')
def home():
    return "WeChat Todo App is running!"

if __name__ == '__main__':
    app.run()