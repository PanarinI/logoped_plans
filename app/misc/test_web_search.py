import os  # Импортируем модуль для работы с переменными окружения
import asyncio  # Импортируем модуль для поддержки асинхронного программирования
from dotenv import load_dotenv  # Импортируем функцию для загрузки переменных окружения из файла .env
from openai import OpenAI
# Загружаем переменные окружения из файла .env
load_dotenv()
api_key=os.getenv("API_KEY_openai")

client = OpenAI(api_key=api_key)

# Тестовый запрос
prompt = "Какие современные методы используются для развития фонематического слуха у детей? Приведи примеры и ссылки на источники."

tools = [
    {
        "type": "web_search_preview",
        "search_context_size": "low",
        "user_location": {
            "type": "approximate",
            "country": "RU"
        }
    }
]

# Отправляем запрос к API
response = client.responses.create(
    model="gpt-4o-mini",
    input=prompt,
    tools=tools,
    max_output_tokens=1000
)

# Выводим результат в консоль
print("Ответ модели:")
print(response.output_text)
