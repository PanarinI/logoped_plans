import os
import logging
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
from openai import OpenAI

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
api_key = os.getenv("API_KEY_openai")
client = OpenAI(api_key=api_key)
VS_ID = os.getenv("VECTOR_STORE_ID")
bucket_name = os.getenv("S3_BUCKET_NAME")
prefix = "KB_Logoped"  # Префикс для нужных файлов, должен соответствовать вашей структуре S3

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url='https://s3.timeweb.cloud',
        aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY')
    )

def generate_presigned_url(bucket_name, object_key, expiration=3600):
    """
    Генерирует presigned URL для объекта в S3.
    """
    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.error(f"Ошибка генерации ссылки для {object_key}: {str(e)}")
        return None

def get_file_references(bucket_name, prefix):
    """
    Получает маппинг: имя файла -> путь в S3, основываясь на префиксе.
    """
    s3 = get_s3_client()
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        if 'Contents' not in response:
            raise FileNotFoundError(f"В бакете {bucket_name}/{prefix} не найдено файлов")
        # Отбираем только PDF-файлы и маппим по имени файла
        file_refs = {
            obj['Key'].split('/')[-1]: obj['Key']
            for obj in response['Contents'] if obj['Key'].endswith('.pdf')
        }
        return file_refs
    except Exception as e:
        logger.error(f"Ошибка получения списка файлов: {str(e)}")
        return {}

# Получаем маппинг файлов
file_references = get_file_references(bucket_name, prefix)

# Создаём запрос к OpenAI c инструментом file_search
response = client.responses.create(
    model="gpt-4o-mini",
    instructions=("ты эксперт в составлении логопедических занятий. "
                  "Отвечай строго на основе загруженных источников. "
                  "Если даннных в источниках нет - сообщи об этом"),
    input="примеры упражнений на автоматизацию звука Ц",
    tools=[{"type": "file_search", "vector_store_ids": [VS_ID]}],
)

# Обработка ответа:
# Пытаемся извлечь текст ответа и аннотации (предполагается, что LLM возвращает их во втором элементе output)
try:
    full_text = response.output[1].content[0].text
except (AttributeError, IndexError):
    full_text = "Ответ сгенерирован, но не удалось обработать форматирование."

try:
    annotations = response.output[1].content[0].annotations
except (AttributeError, IndexError):
    annotations = []
    logger.warning("Аннотации не найдены в ответе LLM.")

# Вставляем ссылки из аннотаций в текст ответа
# Итерируем в обратном порядке, чтобы позиции вставки не сбивались
for ann in reversed(annotations):
    filename = ann.filename
    insert_position = ann.index  # позиция, куда нужно вставить ссылку
    file_path = file_references.get(filename)
    if file_path:
        download_link = generate_presigned_url(bucket_name, file_path)
        if download_link:
            clickable_link = f" [{filename}]({download_link})"
            # Вставляем ссылку по указанной позиции
            full_text = full_text[:insert_position] + clickable_link + full_text[insert_position:]
    else:
        logger.info(f"Файл {filename} не найден в S3 маппинге.")

# Выводим итоговый текст в консоль
print("Обработанный текст с вставленными ссылками:")
print(full_text)
