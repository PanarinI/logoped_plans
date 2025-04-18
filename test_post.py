import requests

url = "https://script.google.com/macros/s/ТВОЙ_КОД/exec"  # замени на свой
data = {
    "comment": "тестовый отзыв",
    "rate": 5
}

response = requests.post(url, json=data)
print("Статус:", response.status_code)
print("Ответ:", response.text)
