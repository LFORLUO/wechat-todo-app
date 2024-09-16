from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta
import requests
import json
import base64
import os

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

def get_todos():
    headers = {'Authorization': f'token {GITEE_TOKEN}'}
    response = requests.get(GITEE_API_URL, headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        return json.loads(content)
    return []

def check_todos():
    now = datetime.now()
    soon = now + timedelta(hours=1)
    
    todos = get_todos()
    for todo in todos:
        if todo['状态'] == '未完成':
            deadline = datetime.fromisoformat(todo['截止时间'])
            if now <= deadline < soon:
                user_id = todo['用户ID']
                task = todo['任务内容']
                message = f"提醒：您的待办事项 '{task}' 将在 {deadline.strftime('%Y-%m-%d %H:%M')} 到期。"
                send_message(user_id, message)
    
    return "OK"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        result = check_todos()
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(result.encode())
        return