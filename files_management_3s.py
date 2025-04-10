import os
import json
import hashlib
import logging
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
client = OpenAI(api_key=os.getenv("API_KEY_openai"))

# ==== Управление этапами через флаги ====
RUN_CREATE_VECTOR_STORE = False
RUN_UPLOAD_FILES = False
RUN_GENERATE_TEMPLATE = True
RUN_UPDATE_ATTRIBUTES = False
RUN_DELETE_FILE = False

# ==== Параметры ====
VECTOR_STORE_NAME = "Logoped_KB"
FILES_DIR = "app/data/materials/vector_store"
ATTRIBUTES_FILE = "app/data/attributes_template.json"
VS_ID = os.getenv("VECTOR_STORE_ID")
FILE_NAME_DELETE = ""

# Функция для получения клиента S3 с кэшированием
@st.cache_resource
def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url='https://s3.timeweb.cloud',
        aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY')
    )

# Функция для генерации кликабельной ссылки из S3 с кэшированием результата (если нужно)
def generate_presigned_url(bucket_name, object_key, expiration=3600):
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

# 1. Создание векторного хранилища
def create_vector_store(name: str) -> str:
    """Создает новое векторное хранилище, если его еще нет, и возвращает его ID"""

    # Получаем список всех векторных хранилищ
    existing_stores = client.vector_stores.list()

    # Проверяем, существует ли хранилище с таким же именем
    for store in existing_stores:
        if store.name == name:
            logger.info(f"Хранилище с именем '{name}' уже существует, его ID: {store.id}")
            return store.id  # Возвращаем существующий ID хранилища

    # Если хранилище не найдено, создаем новое
    vector_store = client.vector_stores.create(name=name)
    logger.info(f"Создано хранилище: {vector_store.id}")
    return vector_store.id

# Вспомогательные функции для вычисления хэша и работы с локальным кэшем
def calculate_hash(file_path: str) -> str:
    """Вычисляет SHA-256 хеш файла для отслеживания изменений"""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha.update(data)
    return sha.hexdigest()

# 2. Загрузка файлов с проверкой дубликатов
def upload_files(vector_store_id: str, files_dir: str):
    """
    Загружает новые файлы в хранилище, пропуская уже существующие.
    Возвращает список file_id новых файлов.
    """
    existing = load_existing_files()
    new_files = []
    # Получаем список файлов из S3 через Timeweb S3-хранилище,
    # если потребуется интеграция с S3, можно заменить os.listdir на получение списка из S3.
    # Здесь мы предполагаем, что локальные файлы уже скачаны/синхронизированы с S3.
    for filename in os.listdir(files_dir):
        file_path = os.path.join(files_dir, filename)
        file_hash = calculate_hash(file_path)
        if filename in existing and existing[filename]['hash'] == file_hash:
            logger.info(f"Файл {filename} уже загружен, пропуск")
            continue
        try:
            with open(file_path, "rb") as f:
                uploaded_file = client.files.create(file=f, purpose="assistants")
            client.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=uploaded_file.id,
                attributes={}
            )
            existing[filename] = {
                'file_id': uploaded_file.id,
                'hash': file_hash,
                'attributes': {}
            }
            new_files.append(uploaded_file.id)
        except Exception as e:
            logger.error(f"Ошибка загрузки {filename}: {str(e)}")
    save_existing_files(existing)
    return new_files


# 3. Генерация шаблона метаданных
def generate_attributes_template(vector_store_id: str):
    """Создает JSON-файл с текущими метаданными для ручного редактирования"""
    files_info = load_existing_files()
    vector_files = client.vector_stores.files.list(vector_store_id=vector_store_id)
    template = {}
    for v_file in vector_files:
        filename = next((k for k, v in files_info.items() if v['file_id'] == v_file.id), None)
        if filename:
            template[v_file.id] = {
                "filename": filename,
                "attributes": files_info[filename].get('attributes', {})
            }
    with open("app/data/attributes_template.json", "w") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    logger.info("Шаблон метаданных сгенерирован")

# 4. Обновление метаданных
def update_attributes(vector_store_id: str, attributes_file: str):
    """Обновляет метаданные файлов на основе редактированного шаблона"""
    with open(attributes_file, "r") as f:
        attributes = json.load(f)
    existing = load_existing_files()
    updated = 0
    for file_id, data in attributes.items():
        filename = data['filename']
        if filename not in existing:
            continue
        try:
            client.vector_stores.files.update(
                vector_store_id=vector_store_id,
                file_id=file_id,
                attributes=data['attributes']
            )
            existing[filename]['attributes'] = data['attributes']
            updated += 1
        except Exception as e:
            logger.error(f"Ошибка обновления {filename}: {str(e)}")
    save_existing_files(existing)
    logger.info(f"Обновлено {updated} записей")


def load_existing_files() -> dict:
    """Загружает информацию о ранее загруженных файлах"""
    try:
        with open("app/data/existing_files.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_existing_files(data: dict):
    """Сохраняет информацию о загруженных файлах"""
    with open("app/data/existing_files.json", "w") as f:
        json.dump(data, f, indent=2)


def delete_file_by_filename(filename: str):
    """Удаляет файл из OpenAI по имени (если он есть в existing_files.json)"""
    existing = load_existing_files()
    if filename not in existing:
        logger.info(f"Файл '{filename}' не найден в existing_files.json")
        return
    file_id = existing[filename]['file_id']
    try:
        client.vector_stores.files.delete(
            vector_store_id=VS_ID,
            file_id=file_id
        )
        logger.info(f"Файл '{filename}' c ID {file_id} успешно удалён")
        del existing[filename]
        save_existing_files(existing)
    except Exception as e:
        logger.error(f"Ошибка при удалении файла '{filename}': {str(e)}")

if __name__ == "__main__":

    # ==== Запуск этапов ====
    if RUN_CREATE_VECTOR_STORE:
        VS_ID = create_vector_store(VECTOR_STORE_NAME)

    if RUN_UPLOAD_FILES:
        new_files = upload_files(VS_ID, FILES_DIR)
    else:
        new_files = []

    if RUN_GENERATE_TEMPLATE:
        generate_attributes_template(VS_ID)

    if RUN_UPDATE_ATTRIBUTES:
        update_attributes(VS_ID, ATTRIBUTES_FILE)

    if RUN_DELETE_FILE:
        delete_file_by_filename(FILE_NAME_DELETE)

