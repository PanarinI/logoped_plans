import openai
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

client = openai.AsyncOpenAI(
        api_key=os.getenv("API_KEY_openai"),
        timeout=60  # Устанавливаем время ожидания в 60 секунд
    )

    # Отправляем запрос с инструментом web_search_preview
    response = await client.responses.create(
        model="gpt-4o-mini",  # Используем модель с поддержкой web_search
        tools=[{"type": "web_search_preview"}],  # Указываем инструмент поиска
        input="What was a positive news story from 1878? Find a different answer each request"  # Ваш запрос
    )

    # Получаем результат
    output_text = response.output_text
    print("Ответ:", output_text)

asyncio.run(main())
