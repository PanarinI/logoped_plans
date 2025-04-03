import requests

API_KEY = "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"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

response = requests.get("https://api.openai.com/v1/models", headers=headers)

print(response.status_code)  # Должно быть 200, если ключ работает
print(response.json())  # Посмотрим, что вернет API
