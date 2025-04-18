import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("FEEDBACK_GS_URL") # замени на свой
data = {
    "comment": "тестовый отзыв",
    "rate": 5
}

response = requests.post(url, json=data)
print("Статус:", response.status_code)
print("Ответ:", response.text)
