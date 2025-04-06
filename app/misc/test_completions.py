import os
from openai import OpenAI
from dotenv import load_dotenv

# 5. Загрузка переменных окружения
load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

# 6. Инициализация клиента OpenAI
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# Отправка запроса к chat.completions
response = client.chat.completions.create(
    model="gpt-4o-mini",  # Можно заменить на другую доступную модель
    messages=[
        {"role": "user", "content": "Найди свежие новости про искусственный интеллект и дай мне ссылки."}
    ]
)

# Вывод ответа в консоль
print(response.choices[0].message.content)
