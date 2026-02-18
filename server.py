import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

class TaskManager:
    """Управляет списком задач и их сохранением в файл."""
    def __init__(self, filename='tasks.txt'):
        self.filename = filename
        self.tasks = []
        self.load()

    def load(self):
        """Загружает задачи из файла, если он существует и корректен."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
            except (json.JSONDecodeError, IOError):
                # При ошибке чтения начинаем с пустого списка
                self.tasks = []
        else:
            self.tasks = []

    def save(self):
        """Сохраняет текущий список задач в файл."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except IOError:
            # В реальном проекте здесь стоило бы логировать ошибку
            pass

    def create_task(self, title, priority):
        """
        Создаёт новую задачу с указанным заголовком и приоритетом.
        Присваивает уникальный id, устанавливает isDone=False.
        Сохраняет изменения в файл.
        Возвращает созданную задачу.
        """
        new_id = max((task['id'] for task in self.tasks), default=0) + 1
        task = {
            'id': new_id,
            'title': title,
            'priority': priority,
            'isDone': False
        }
        self.tasks.append(task)
        self.save()
        return task

    def complete_task(self, task_id):
        """
        Отмечает задачу с указанным id как выполненную (isDone=True).
        Если задача уже была выполнена, изменений не происходит.
        Сохраняет изменения в файл только при реальном изменении.
        Возвращает True, если задача найдена, иначе False.
        """
        for task in self.tasks:
            if task['id'] == task_id:
                if not task['isDone']:
                    task['isDone'] = True
                    self.save()
                return True
        return False

    def get_all(self):
        """Возвращает список всех задач."""
        return self.tasks


class TaskHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP-запросов для работы со списком задач."""
    task_manager = TaskManager()  # общий для всех экземпляров обработчика

    def do_GET(self):
        """Обрабатывает GET-запросы. Поддерживается только /tasks."""
        if self.path == '/tasks':
            tasks = self.task_manager.get_all()
            self._send_json_response(200, tasks)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Обрабатывает POST-запросы: создание задачи и отметка о выполнении."""
        # Разбираем путь: /tasks или /tasks/<id>/complete
        parts = self.path.strip('/').split('/')
        if parts == ['tasks']:
            self._handle_create_task()
        elif len(parts) == 3 and parts[0] == 'tasks' and parts[2] == 'complete':
            self._handle_complete_task(parts[1])
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_create_task(self):
        """Обрабатывает POST /tasks: создание новой задачи."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(400, 'Invalid JSON')
            return

        title = data.get('title')
        priority = data.get('priority')
        if not title or not priority:
            self._send_error(400, 'Missing title or priority')
            return
        if priority not in ('low', 'normal', 'high'):
            self._send_error(400, 'Priority must be low, normal, or high')
            return

        task = self.task_manager.create_task(title, priority)
        self._send_json_response(201, task)

    def _handle_complete_task(self, task_id_str):
        """Обрабатывает POST /tasks/<id>/complete: отметка задачи выполненной."""
        try:
            task_id = int(task_id_str)
        except ValueError:
            self.send_response(404)
            self.end_headers()
            return

        if self.task_manager.complete_task(task_id):
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json_response(self, code, data):
        """Отправляет ответ с JSON-данными и указанным HTTP-кодом."""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _send_error(self, code, message):
        """Отправляет простой текстовый ответ с ошибкой."""
        self.send_response(code)
        self.end_headers()
        self.wfile.write(message.encode())

    def log_message(self, format, *args):
        """Подавляет стандартное логирование HTTP-сервера."""
        pass


def run(server_class=HTTPServer, handler_class=TaskHandler, port=8080):
    """Запускает HTTP-сервер на указанном порту."""
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Сервер запущен на порту {port}. Для остановки нажмите Ctrl+C')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nСервер остановлен.')


if __name__ == '__main__':
    run()