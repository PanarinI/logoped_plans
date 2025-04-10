from openai import OpenAI
import os
from dotenv import load_dotenv

API_KEY=os.getenv("API_KEY_openai")
load_dotenv()
client = OpenAI(api_key=API_KEY)
VS_ID = os.getenv("VECTOR_STORE_ID")
response = client.responses.create(
    model="gpt-4o-mini",
    input="Придумай упражнения для автоматизации звука Р",
    tools=[{
        "type": "file_search",
        "vector_store_ids": [VS_ID]
    }]
)

print(response.output_text)



