import requests

url = "https://script.google.com/macros/s/AKfycbxEEWarPE7e8gcR4uVA83ciWdrFfNfro9VZkyW3x3Yw_e2yJfKEGg0GA6YeuO2FPAN2/exec"  # замени на свой
data = {
    "comment": "тестовый отзыв",
    "rate": 5
}

response = requests.post(url, json=data)
print("Статус:", response.status_code)
print("Ответ:", response.text)
