import requests

API_KEY = ""

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get("https://api.openai.com/v1/models", headers=headers)

print(response.status_code)  # Должно быть 200, если ключ работает
print(response.json())  # Посмотрим, что вернет API
