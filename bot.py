"""bot.

1) Доработан функционал, в том числе:
    - светлая/темная тема, включая кнопки
    - сохранение и загрузка истории чата
    - добавлены уведомления
    - при очистке чата также удаляется и история чата, в том числе и в сохраненном файле
2) Доработан внешний вид
3) Добавлена кнопка 'Очистить чат'.
"""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from kivy.clock import Clock
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# подгружаем переменные окружения
load_dotenv(ROOT_DIR/".env")

client = {
    "api_key": os.environ.get("vsegpt_api_key"),
    "base_url": "https://api.vsegpt.ru/v1"
}

KV = '''
BoxLayout:
    orientation: 'vertical'

    MDBoxLayout:
        size_hint_y: None
        height: self.minimum_height
        padding: 10
        spacing: 10

        MDRaisedButton:
            text: "Светлая тема"
            on_release: app.switch_theme("Light")

        MDRaisedButton:
            text: "Тёмная тема"
            on_release: app.switch_theme("Dark")

    ScrollView:
        id: scroll_view

        MDBoxLayout:
            id: chat_layout
            orientation: 'vertical'
            padding: 10
            spacing: 15
            adaptive_height: True

    MDBoxLayout:
        size_hint_y: None
        height: self.minimum_height
        padding: 10
        spacing: 10

        MDTextField:
            id: user_input
            hint_text: "Введите сообщение"
            mode: "rectangle"
            multiline: False
            on_text_validate: app.send_message()

        MDRaisedButton:
            text: "Отправить"
            on_release: app.send_message()

        MDRaisedButton:
            text: "Очистить чат"
            on_release: app.clear_chat()
            md_bg_color: (0.9, 0.5, 1, 1)  # (0.8, 0.8, 0.8, 1)
'''

class ChatApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Light"  # Устанавливаем светлую тему по умолчанию
        return Builder.load_string(KV)

    def on_start(self):
        """Загружаем историю чата после полной инициализации приложения."""
        self.load_chat_history()

    def switch_theme(self, theme_style):
        self.theme_cls.theme_style = theme_style
        toast(f"Тема переключена на {theme_style}")

    def send_message(self):
        user_input = self.root.ids.user_input
        message = user_input.text.strip()
        if not message:
            toast("Введите сообщение!")
            return

        self.add_message("Вы: " + message, "user")
        self.save_chat_history(message, "user")
        user_input.text = ""
        self.get_response(message)

    def add_message(self, text, sender="user"):
        chat_layout = self.root.ids.chat_layout

        bubble = MDBoxLayout(
            orientation="vertical",
            padding="10dp",
            spacing="5dp",
            size_hint_x=0.8,
            adaptive_height=True,
            md_bg_color=(0.9, 0.9, 1, 1) if sender == "user" else (0.9, 1, 0.9, 1),
            radius=[15, 15, 15, 15],
            pos_hint={"right": 1} if sender == "user" else {"left": 1},
        )

        label = MDLabel(
            text=text,
            theme_text_color="Primary",
            halign="right" if sender == "user" else "left",
            valign="middle",
            size_hint_y=None,
            text_size=(self.root.width * 0.75, None),
            adaptive_height=True,
        )
        label.bind(texture_size=label.setter("size"))
        bubble.add_widget(label)
        chat_layout.add_widget(bubble)
        Clock.schedule_once(self.scroll_to_bottom, 0.1)

    def scroll_to_bottom(self, *args):
        scroll_view = self.root.ids.scroll_view
        scroll_view.scroll_y = 0

    def clear_chat(self):
        chat_layout = self.root.ids.chat_layout
        chat_layout.clear_widgets()
        with open(ROOT_DIR/"chat_history.txt", "w", encoding="utf-8") as file:
            pass  # Очистка файла истории
        toast("Чат очищен")

    def save_chat_history(self, message, sender="user"):
        """Сохраняет историю чата в JSON файл."""
        chat_file = ROOT_DIR / "chat_history.json"

        # Загружаем существующую историю, если файл уже есть
        try:
            with open(chat_file, "r", encoding="utf-8") as file:
                chat_history = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            chat_history = []

        # Добавляем новое сообщение в историю
        chat_history.append({"sender": sender, "message": message})

        # Сохраняем историю обратно в файл
        with open(chat_file, "w", encoding="utf-8") as file:
            json.dump(chat_history, file, ensure_ascii=False, indent=4)

    def load_chat_history(self):
        """Загружает историю чата из JSON файла."""
        chat_file = ROOT_DIR / "chat_history.json"

        try:
            with open(chat_file, "r", encoding="utf-8") as file:
                chat_history = json.load(file)

            # Восстанавливаем сообщения из истории
            for entry in chat_history:
                sender = entry["sender"]
                message = entry["message"]
                sender_alias = "Вы" if sender == "user" else "ChatGPT"
                self.add_message(f"{sender_alias}: {message}", sender=sender)

        except (FileNotFoundError, json.JSONDecodeError):
            pass
    def get_response(self, message):
        headers = {
            "Authorization": f"Bearer {client['api_key']}", 
            "Content-Type": "application/json"
            }
        data = {
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": message}]
        }
        try:
            response = requests.post(
                f"{client['base_url']}/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            answer = f"Ошибка получения ответа: {e}"

        self.add_message("ChatGPT: " + answer, "chatgpt")
        self.save_chat_history(answer, "ChatGPT")


if __name__ == "__main__":
    ChatApp().run()
