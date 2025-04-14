import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import time
from datetime import datetime
import calendar
from docx import Document
import tempfile
import boto3
from botocore.exceptions import ClientError
import random
import logging

from app.quotes import quotes
from app.drawings import drawings
import app.prompt

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # Вывод в консоль
)

# Загрузка переменных окружения
load_dotenv()
api_key = os.getenv("API_KEY_openai")
client = OpenAI(api_key=api_key)
VS_ID = os.getenv("VECTOR_STORE_ID")


# Функция для генерации presigned URL для S3
def generate_presigned_url(bucket_name, object_key, expiration=3600):
    s3 = boto3.client(
        's3',
        endpoint_url='https://s3.timeweb.cloud',
        aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('S3_SECRET_KEY')
    )
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logging.error(f"Ошибка генерации ссылки S3: {str(e)}")
        return None



# Функция генерации плана занятия
def generate_lesson_plan_interface(
        нарушение, возраст_ребенка, особые_условия,
        формат_занятия, количество_детей, цель_занятия, тема, длительность_занятия,
        инвентарь, наличие_ДЗ, разрешен_file_search, текущий_месяц=None
):
    # Логика работы с источниками - если есть, передаем
    #источники = [web_sources] if разрешен_web_search and web_sources else []


    # Логика определения месяца
    if not текущий_месяц:
        текущий_месяц = calendar.month_name[datetime.now().month]

    # все параметры
    params = {
        "нарушение": нарушение,
        "возраст_ребенка": возраст_ребенка,
        "цель_занятия": цель_занятия,
        "формат_занятия": формат_занятия,
        "количество_детей": количество_детей,
        "тема": тема,
        "особые_условия": особые_условия,
        "инвентарь": инвентарь,
        "длительность_занятия": длительность_занятия,
        "наличие_ДЗ": наличие_ДЗ,
        "разрешен_file_search": разрешен_file_search,
        #"источники": источники,
        "текущий_месяц": текущий_месяц
    }

    if формат_занятия == "Индивидуальное":
        количество_детей = 1  # Принудительно для индивидуального занятия
        params["количество_детей"] = 1  # И обновляем словарь параметров

    # instructions =

#    file_search_section = ""
#    if разрешен_file_search:
#        file_search_section = """
#      Правила:
#    - План составьте строго на основе упражнений из загруженных источников
#    - Если подходящих упражнений в источниках нет - сообщи об этом и не создавай план


#    """
#    instructions = instructions + file_search_section

    prompt = f"""
    Параметры занятия:
    - **Основное нарушение:** {нарушение}
    - **Возраст:** {возраст_ребенка}
    - **Цель занятия:** {цель_занятия}
    - **Тема:** {тема or "не указано - определи самостоятельно"}
    - **Формат:** {формат_занятия} ({количество_детей} детей)
    - **Инвентарь:** {инвентарь or "не указан - на твое усмотрение"}
    - **Наличие домашнего задания:** {наличие_ДЗ or "не требуется"}
    - **Индивидуальные особенности:** {особые_условия or "нет"}
    - **Длительность:** {длительность_занятия} минут
    - **Месяц года:** {текущий_месяц}
    """

    tools = []
    tool_choice = None
    #FILE SEARCH
    if params['разрешен_file_search']:
        tools.append({
            "type": "file_search",
            "vector_store_ids": [VS_ID],
            "max_num_results": 20
        })
        tool_choice = {"type": "file_search"}
    #WEB SEARCH
#    if params['разрешен_web_search']:
#        tools.append({
#            "type": "web_search_preview",
#           "search_context_size": "medium",
#            "user_location": {"type": "approximate", "country": "RU"}
#        })
#        tool_choice = {"type": "web_search_preview"}

    response = client.responses.create(
        instructions=app.prompt.INSTRUCTIONS_1,
        input=prompt,
        model="gpt-4o-mini", # gpt-4o-mini   o3-mini
        tools=tools if tools else None,
        tool_choice=tool_choice,
        include=["file_search_call.results"],
        max_output_tokens=4096,
        #temperature=float(os.getenv("TEMPERATURE", 1)),
        #reasoning= {"effort":"medium"},
        stream=False
    )


####### БЕЗ СТРИМИНГА
#    return response.output_text  # Основной вывод без изменений

    try:
        # 1. Получаем основной текст ответа
        full_text = response.output[0].content[0].text
    except (AttributeError, IndexError) as e:
        full_text = "Не удалось получить текст ответа"
        logging.error(f"Ошибка при получении текста ответа: {str(e)}")
        return full_text

    # 2. Получаем аннотации если есть
    try:
        annotations = [
            ann for ann in response.output[0].content[0].annotations
            if ann.type == "file_citation"
        ]
        logging.debug(f"Найдено аннотаций: {len(annotations)}")
    except (AttributeError, IndexError) as e:
        annotations = []
        logging.warning(f"Не найдены аннотации в ответе: {str(e)}")

    # 3. Если есть аннотации - обрабатываем их
    if annotations:
        # Инициализация S3 клиента
        try:
            s3 = boto3.client(
                's3',
                endpoint_url='https://s3.timeweb.cloud',
                aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
                aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
            )

            bucket_name = os.getenv('S3_BUCKET_NAME')
            prefix = "KB_Logoped"

            # Получаем список файлов из S3
            response_s3 = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            file_references = {
                obj['Key'].split('/')[-1]: obj['Key']
                for obj in response_s3.get('Contents', [])
                if obj['Key'].endswith(('.pdf', '.docx'))
            }
        except ClientError as e:
            logging.error(f"Ошибка доступа к S3: {str(e)}")
            file_references = {}
        except Exception as e:
            logging.error(f"Неожиданная ошибка при работе с S3: {str(e)}")
            file_references = {}

        # Сортируем аннотации по убыванию позиции для корректной вставки
        sorted_annotations = sorted(annotations, key=lambda x: x.index, reverse=True)

        for ann in sorted_annotations:
            try:
                filename = ann.filename
                insert_pos = ann.index

                # Проверка корректности позиции
                if insert_pos > len(full_text):
                    logging.warning(f"Позиция аннотации {insert_pos} превышает длину текста")
                    continue

                if filename in file_references:
                    url = generate_presigned_url(
                        bucket_name=bucket_name,
                        object_key=file_references[filename]
                    )
                    if url:
                        # Форматируем ссылку (без пробела в начале)
                        link_text = f"[📚 {filename}]({url})"
                        full_text = f"{full_text[:insert_pos]}{link_text}{full_text[insert_pos:]}"
                else:
                    logging.warning(f"Файл {filename} не найден в S3")
            except Exception as e:
                logging.error(f"Ошибка обработки аннотации: {str(e)}")
                continue

    return full_text

# АННОТАЦИИ В ЛОГ
#    if params['разрешен_web_search']:  # Только логируем аннотации при веб-поиске
#        try:
#            content_block = response.output[1].content[0]
#            # logging.info(f"=== ПОЛНЫЙ КОНТЕНТ БЛОКА ===")
#            # logging.info(f"Тип: {content_block.type}")
#            # logging.info(f"Текст: {content_block.text[:200]}...")  # Первые 200 символов текста
#            logging.info(f"Аннотации: {content_block.annotations}")
#            # logging.info(f"Сырые данные: {vars(content_block)}")  # Вся техническая информация
#        except (IndexError, AttributeError) as e:
#            logging.warning(f"Не удалось получить аннотации: {str(e)}")

####### СТРИМИНГ
#    try:
#        for event in response:
#            if event.type == 'response.output_text.delta':
#                yield event.delta
#            elif event.type == 'response.completed':
#                break
#    except Exception as e:
#        yield f"Ошибка: {str(e)}"


############# COMPLETIONS (РАБОТАЕТ БЕЗ TOOLS)
#    response = client.chat.completions.create(
#        model="gpt-4o-mini",
#        messages=[
#            {"role": "system", "content": "Ты — эксперт в области логопедии."},
#            {"role": "user", "content": prompt}
#        ],
#        max_tokens=2000,
#        stream=True  # Включаем потоковый режим
#    )

#    for chunk in response:
#        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
#            yield chunk.choices[0].delta.content


# Случайный рисунок в блокноте
drawing = random.choice(drawings)
# Текст с подсказкой и рисунком в блокноте
hint_text = f"""Здесь появится план занятия — заполните вводные и нажмите кнопку **Создать конспект**

<pre>
{drawing}
</pre>
"""

########## ИНТЕРФЕЙС
#ТЕМА И СТИЛИ

### css привязывать именно так
#theme='earneleh/paris'
theme = gr.themes.Base(
    secondary_hue="rose",
    neutral_hue="stone",
).set(
    body_background_fill='*primary_50',
    body_text_color='*primary_900',
    body_text_size='*text_lg',
    body_text_color_subdued='*primary_700',
    body_text_weight='600',
)
css_path = os.path.join(os.path.dirname(__file__), "styles.css")

# ИНТЕРФЕЙС
with gr.Blocks(theme=theme, css_paths=css_path) as demo:
    gr.Markdown("# Логопедический конспект", elem_classes=["main-title"])
    quote_box = gr.Markdown(random.choice(quotes), elem_classes=["quote-block"])

    with gr.Row():
        # Левый блок (все поля)
        with gr.Column(elem_classes=["left-col"], scale=1):
            # Блок 1: Ребёнок (заголовок + поля)
            with gr.Column(variant="panel"):  # <<< Обертка для первого блока
                gr.Markdown("### 🧒 Ребёнок", elem_classes=["block-title"])
                нарушение = gr.Textbox(label="Основное нарушение*", placeholder="Пример: Дислалия (свистящие), ОНР II уровня")
                возраст = gr.Textbox(label="Возраст ребенка*", placeholder="Пример: 5 лет, 6-7 лет")
                особые_условия = gr.Textbox(label="Особые условия", placeholder="Пример: гиперактивность, РАС")



            # Блок 2: Занятие (заголовок + поля)
            with gr.Column(variant="panel"):  # <<< Обертка для второго блока
                gr.Markdown("### 📄 Занятие", elem_classes=["block-title"])
                формат = gr.Radio(["Индивидуальное", "Групповое"], label="Формат занятия", value="Индивидуальное")
                количество_детей = gr.Slider(label="Количество детей в группе", minimum=2, maximum=10, value=2, step=1, visible=False)
                def toggle_group_slider(selected_format):
                    if selected_format == "Индивидуальное":
                        return gr.update(visible=False, value=1)  # Скрыть слайдер и установить значение 1
                    else:
                        return gr.update(visible=True, value=2)  # Показать слайдер и установить значение 2
                # Привязываем изменение формата к функции
                формат.change(fn=toggle_group_slider, inputs=формат, outputs=количество_детей)

                цель = gr.Textbox(label="Цель занятия*", placeholder="Пример: Автоматизация звука [Р] в слогах")
                тема = gr.Textbox(label="Тема", placeholder="Пример: Животные, Транспорт")
                длительность = gr.Slider(label="Длительность занятия (мин)", minimum=15, maximum=60, value=30, step=5)
                инвентарь = gr.Textbox(label="Инвентарь (через запятую)", placeholder="Пример: Зеркало, Карточки, Куклы")
                дз = gr.Checkbox(label="Домашнее задание")
                # Выделенный блок для профессиональных ресурсов
                gr.Markdown("---")  # Разделительная линия
                # gr.Markdown("### 🔍 Дополнительные ресурсы", elem_classes=["block-title", "pro-title"])

                with gr.Row(variant="panel"):  # Вариант "panel" добавляет фоновый оттенок
                    file_search = gr.Checkbox(
                        label="📚 Поиск упражнений в логопедических базах",
                        info="Упражнения подбираются из проверенных источников со ссылками (FS)",
                        interactive=True
                    )

            #web_sources = gr.Textbox(
            #    label="Уточнить источники (необязательно, через запятую):",
            #    placeholder="Например: Logopedy.ru, Maam.ru, ...",
            #    visible=False,
            #)

            # Логика отображения поля источников
            #web.change(
            #    fn=lambda x: gr.update(visible=x),
            #    inputs=web,
            #    outputs=web_sources
            #)

            # Кнопка создания конспекта
            btn = gr.Button("Создать конспект", variant="primary")

        # Правая колонка — результат (output)
        with gr.Column(elem_classes=["right-col"], scale=2):
            # Общий блок-панель для правой колонки
            with gr.Column(variant="panel"):  # <<< Главная панель
                gr.Markdown("### Конспект", elem_classes=["block-title"])  # Заголовок ВНУТРИ панели
                # Блок с выводом конспекта
                output = gr.Markdown(
                    hint_text,
                    elem_id="plan-output"
                )
                # Кнопка скачивания (оставляем внутри панели)
                download_btn = gr.DownloadButton(
                    label="⬇️ Скачать .docx",
                    visible=False
                )

    # Ввод параметров
    all_inputs = [
        нарушение, возраст, особые_условия,
        формат, количество_детей, цель, тема, длительность,
        инвентарь, дз, file_search #web_sources
    ]


    # Функция для генерации docx файла
    def generate_docx(text: str):
        doc = Document()
        for line in text.split("\n"):
            doc.add_paragraph(line)
        tmp_dir = tempfile.gettempdir()
        file_path = os.path.join(tmp_dir, "Конспект_занятия.docx")
        doc.save(file_path)
        return file_path

################### СТРИМИНГ
#    def on_submit_with_spinner(*args):
#        # Проверка обязательных полей (остается без изменений)
#        if not args[0] or not args[1] or not args[5]:
#            yield (
#                *[gr.update(interactive=True) for _ in all_inputs],
#                gr.update(value="❗Заполните обязательные поля: нарушение, возраст, цель занятия"),
#                gr.update(visible=False)
#            )
#            return

        # Блокируем интерфейс
#        yield (
#            *[gr.update(interactive=False) for _ in all_inputs],
#            gr.update(value="⏳ Конспект создается..."),
#            gr.update(visible=False)
#        )

#        full_response = []
#        try:
#            for chunk in generate_lesson_plan_interface(*args):
#                full_response.append(chunk)
#                yield (
#                    *[gr.update(interactive=False) for _ in all_inputs],
#                    gr.update(value="".join(full_response)),
#                    gr.update(visible=False)
#                )

            # После завершения стрима
#            file_path = generate_docx("".join(full_response))
#            yield (
#                *[gr.update(interactive=True) for _ in all_inputs],
#                gr.update(value="".join(full_response)),
#                gr.update(visible=True, value=file_path)
#            )

#        except Exception as e:
#            yield (
#                *[gr.update(interactive=True) for _ in all_inputs],
#                gr.update(value=f"❌ Ошибка: {str(e)}"),
#                gr.update(visible=False)
#            )

################## БЕЗ СТРИМИНГА
    def on_submit_with_spinner(*args):
        if not args[0] or not args[1] or not args[5]:
            return (
                *[gr.update(interactive=True) for _ in all_inputs],
                gr.update(value="❗Заполните обязательные поля: нарушение, возраст, цель занятия"),
                gr.update(visible=False)
            )

        # Блокируем интерфейс
        try:
            response_text = generate_lesson_plan_interface(*args)
            file_path = generate_docx(response_text)
            return (
                *[gr.update(interactive=True) for _ in all_inputs],
                gr.update(value=response_text),
                gr.update(visible=True, value=file_path)
            )

        except Exception as e:
            return (
                *[gr.update(interactive=True) for _ in all_inputs],
                gr.update(value=f"❌ Ошибка: {str(e)}"),
                gr.update(visible=False)
            )


    # Привязываем обработчики
    btn.click(
        fn=on_submit_with_spinner,
        inputs=all_inputs,
        outputs=[*all_inputs, output, download_btn]) # <- скобку если не стримминг
#    ).then(
#        lambda: None,
#        inputs=[],
#        outputs=[]
#    )

if __name__ == "__main__":
    demo.launch()