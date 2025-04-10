from openai import OpenAI
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_KEY =  os.getenv("API_KEY_openai")
VS_ID = os.getenv("VECTOR_STORE_ID")
client = OpenAI(api_key=API_KEY)

response = client.responses.create(
    model="gpt-4o-mini",
    input="Приведи из базы упражнения дляя автматизации звука Р. Указывай точные названия источников в [квадратных скобках]."
          "Строго: если релевантные сведения в данных по запросу отсутствуют, сообщи об этом. Ответ давай в пределах {max_output_tokens} токенов",
    tools=[{
        "type": "file_search",
        "vector_store_ids": [VS_ID]
    }],
    max_output_tokens=1000,
    include=["file_search_call.results"]
)

print (response.output_text)

