import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import time
from datetime import datetime
import calendar
from docx import Document
import tempfile
import random  # для случайного выбора цитаты
from app.quotes import quotes
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)  # Вывод в консоль

# Загрузка переменных окружения
load_dotenv()
api_key = os.getenv("API_KEY_openai")
client = OpenAI(api_key=api_key)

# API_KEY = os.getenv("API_KEY")
# BASE_URL = os.getenv("BASE_URL")
# client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def log_annotations_directly(response):
    try:
        # Проверяем наличие аннотаций в структуре ответа
        if hasattr(response, 'content'):
            for content in response.content:
                if hasattr(content, 'annotations') and content.annotations:
                    logging.info("\n=== НАЙДЕНЫ АННОТАЦИИ ===")  # Используем print для наглядности
                    for annotation in content.annotations:
                        if hasattr(annotation, 'url'):
                            logging.info(f"URL: {annotation.url}")
                            if hasattr(annotation, 'title'):
                                print(f"Title: {annotation.title}")
                            logging.info("------")
                    return

        logging.info("Аннотации не найдены в ответе")

    except Exception as e:
        logging.info(f"Ошибка при логировании аннотаций: {str(e)}")
# Функция генерации плана занятия
def generate_lesson_plan_interface(
        нарушение, возраст_ребенка, особые_условия,
        формат_занятия, количество_детей, цель_занятия, тема, длительность_занятия,
        инвентарь, наличие_ДЗ, разрешен_web_search, web_sources, текущий_месяц=None
):
    # Логика работы с источниками - если есть, передаем
    источники = [web_sources] if разрешен_web_search and web_sources else []


    # Логика определения месяца
    if not текущий_месяц:
        текущий_месяц = datetime.now().month

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
        "разрешен_web_search": разрешен_web_search,
        "источники": источники,
        "текущий_месяц": текущий_месяц
    }

    if формат_занятия == "Индивидуальное":
        params["количество_детей"] = 1
    # Вставка строки с источниками, если они есть
    источники_строка = f"- **Источники поиска:** {'; '.join(источники)}" if разрешен_web_search and источники else ""

    prompt = f"""
        Ты — эксперт в области логопедии, специализирующийся на разработке занятий для детей с речевыми нарушениями. 
        Ты получаешь запрос на разработку занятия со следующими параметрами:
        - **Основное нарушение ребенка:** {params['нарушение']}
        - **Возраст:** {params['возраст_ребенка']}
        - **Цель занятия:** {params['цель_занятия']}
        - **Тема:** {params['тема'] or "не указано. Придумай сам, опираясь на данные о ребенке и цели занятия"}
        - **Формат занятия:** {params['формат_занятия']} ({params['количество_детей']} детей)
        - **Доступный инвентарь:** {params['инвентарь'] or "не указано, на твое усмотрение"}
        - **Особые условия:** {params['особые_условия'] or "отсутствуют"}
        - **Длительность занятия:** {params['длительность_занятия']} минут
        - **Наличие домашнего задания:** {params['наличие_ДЗ']}
        - **Поиск по интернету:** {params['разрешен_web_search']}
        - **Текущий месяц :** {params['текущий_месяц']} (1=январь и т.д.)
        {источники_строка}
        На основе этих параметров составь план занятия, который должен включать:
        1. **Тема занятия, цель и задачи (не более 3-х)** 
        2. **Необходимый инвентарь**
        3. **Ход занятия**. Состоит из логически последовательных этапов.
        В каждый этап встроены конкретные упражнения с достаточным количеством примеров.
        СТРОГО: **если поиск по интернету: True**, то обязательно выстрой занятие на базе упражнений из релевантных источников. 
        Обязательно **приведи ссылки на источники** в тексте ответа.
        5. **Домашнее задание** (только если параметр "наличие домашнего задания: True", иначе пропусти)
        6. **Рекомендации по особым условиям** (если указан параметр "Особые условия", иначе пропусти)
        """

    tools = []
    tool_choice = None

    if params['разрешен_web_search']:
        tools.append({
            "type": "web_search_preview",
            "search_context_size": "low",
            "user_location": {
                "type": "approximate",
                "country": "RU"
            }
        })
        tool_choice = {"type": "web_search_preview"}

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
        tools=tools if tools else None,
        tool_choice=tool_choice,
        max_output_tokens=2000,
        stream=False
    )
####### БЕЗ СТРИМИНГА
    log_annotations_directly(response)
    return response.output_text


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


# Интерфейс Gradio
with gr.Blocks() as demo:
    gr.Markdown("## 🧠 Генератор логопедических занятий")

    with gr.Row():
        # Первый блок настройки (Ребенок)
        with gr.Column(scale=1):
            quote_box = gr.Markdown(random.choice(quotes), elem_classes=["quote-block"])

            gr.Markdown("### 🧒 Ребёнок", elem_classes=["block-title"])
            нарушение = gr.Textbox(label="Основное нарушение*",
                                   placeholder="Пример: Дислалия (свистящие), ОНР II уровня")
            возраст = gr.Textbox(label="Возраст ребенка*", placeholder="Пример: 5 лет, 6-7 лет")
            особые_условия = gr.Textbox(label="Особые условия", placeholder="Пример: гиперактивность, РАС")

            gr.Markdown("### 📄 Занятие", elem_classes=["block-title"])
            формат = gr.Radio(["Индивидуальное", "Групповое"], label="Формат занятия", value="Индивидуальное")
            количество_детей = gr.Slider(
                label="Количество детей в группе", minimum=2, maximum=10, value=2, step=1, visible=False
            )


            def toggle_group_slider(selected_format):
                return gr.update(visible=(selected_format == "Групповое"))


            формат.change(fn=toggle_group_slider, inputs=формат, outputs=количество_детей)

            цель = gr.Textbox(label="Цель занятия*", placeholder="Пример: Автоматизация звука [Р] в слогах")
            тема = gr.Textbox(label="Тема", placeholder="Пример: Животные, Транспорт")
            длительность = gr.Slider(label="Длительность занятия (мин)", minimum=15, maximum=60, value=30, step=5)
            инвентарь = gr.Textbox(label="Инвентарь (через запятую)",
                                   placeholder="Пример: Зеркало, Карточки, Куклы")

            дз = gr.Checkbox(label="Домашнее задание")
            # Выделенный блок для профессиональных ресурсов
            gr.Markdown("---")  # Горизонтальная разделительная линия
            # gr.Markdown("### 🔍 Дополнительные ресурсы", elem_classes=["block-title", "pro-title"])

            with gr.Row(variant="panel"):  # Вариант "panel" добавляет фоновый оттенок
                web = gr.Checkbox(
                    label="📚 Поиск упражнений в логопедических базах",
                    info="Упражнения подбираются из проверенных источников со ссылками",
                    interactive=True
                )

            web_sources = gr.Textbox(
                label="Уточнить источники (необязательно, через запятую):",
                placeholder="Например: Logopedy.ru, Maam.ru, ...",
                visible=False,
            )

            # Логика отображения поля источников
            web.change(
                fn=lambda x: gr.update(visible=x),
                inputs=web,
                outputs=web_sources
            )

            # Кнопка создания конспекта
            btn = gr.Button("Создать конспект", variant="primary")

        # Правая колонка — результат (output)
        with gr.Column(scale=2):  # Правая колонка — результат
            download_btn = gr.DownloadButton(
                label="⬇️ Скачать .docx",
                visible=False
            )
            output = gr.Markdown("")  # Поле для вывода конспекта

    # Ввод параметров
    all_inputs = [
        нарушение, возраст, особые_условия,
        формат, количество_детей, цель, тема, длительность,
        инвентарь, дз, web, web_sources
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
#           gr.update(visible=False)
#        )

#       full_response = []
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
    demo.launch(share=True)