from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime, timedelta

# 模拟数据存储
TODOS = [
    {"id": 1, "task": "完成报告", "deadline": "2023-06-01 14:00", "status": "未完成"},
    {"id": 2, "task": "准备会议", "deadline": "2023-06-02 10:00", "status": "未完成"},
]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        current_time = datetime.now()
        response = []

        for todo in TODOS:
            deadline = datetime.strptime(todo['deadline'], "%Y-%m-%d %H:%M")
            if todo['status'] == '未完成' and deadline > current_time and deadline - current_time <= timedelta(hours=1):
                response.append({
                    "task": todo['task'],
                    "deadline": todo['deadline'],
                    "message": f"提醒：任务 '{todo['task']}' 将在 {todo['deadline']} 到期。"
                })

        self.wfile.write(json.dumps({"todos": response}).encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        todo_data = json.loads(post_data.decode('utf-8'))

        # 添加新的待办事项
        new_todo = {
            "id": len(TODOS) + 1,
            "task": todo_data['task'],
            "deadline": todo_data['deadline'],
            "status": "未完成"
        }
        TODOS.append(new_todo)

        self.send_response(201)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Todo added successfully", "todo": new_todo}).encode())