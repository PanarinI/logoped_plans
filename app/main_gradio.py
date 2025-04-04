import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import time

# Загрузка переменных окружения
load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
#client = OpenAI(api_key=api_key)
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# Функция генерации плана занятия
def generate_lesson_plan_interface(
    нарушение, возраст_ребенка, цель_занятия, формат_занятия,
    количество_детей, тематика, особые_условия,
    зеркало, карточки, игрушки, дополнительный_инвентарь,
    длительность_занятия, наличие_ДЗ, разрешен_web_search
):
    инвентарь = []
    if зеркало: инвентарь.append("Зеркало")
    if карточки: инвентарь.append("Карточки")
    if игрушки: инвентарь.append("Игрушки")
    if дополнительный_инвентарь: инвентарь.append(дополнительный_инвентарь)
    инвентарь = ", ".join(инвентарь)

    params = {
        "нарушение": нарушение,
        "возраст_ребенка": возраст_ребенка,
        "цель_занятия": цель_занятия,
        "формат_занятия": формат_занятия,
        "количество_детей": количество_детей,
        "тематика": тематика,
        "особые_условия": особые_условия,
        "инвентарь": инвентарь,
        "длительность_занятия": длительность_занятия,
        "наличие_ДЗ": наличие_ДЗ,
        "разрешен_web_search": разрешен_web_search
    }

    prompt = f"""
        Ты — эксперт в области логопедии, специализирующийся на разработке занятий для детей с речевыми нарушениями. На вход ты получаешь следующие параметры:
        - **Основное нарушение:** {params['нарушение']}
        - **Возраст ребенка:** {params['возраст_ребенка']}
        - **Цель занятия:** {params['цель_занятия']}
        - **Тематика:** {params['тематика']}
        - **Формат занятия:** {params['формат_занятия']} ({params['количество_детей']} детей)
        - **Инвентарь:** {params['инвентарь']}
        - **Особые условия:** {params['особые_условия']}
        - **Длительность занятия:** {params['длительность_занятия']} минут
        - **Наличие домашнего задания:** {params['наличие_ДЗ']}
        - **Разрешен web search:** {params['разрешен_web_search']}

        На основе этих параметров составь конспект занятия, который должен включать:
        1. **Тема занятия, цель и задачи** 
        2. **Необходимые материалы**
        3. **Ход занятия**. Разбей занятие на логически последовательные этапы.
        В каждый этап встрой конкретные упражнения с достаточным количеством примеров.
        ВАЖНО: если разрешен web search: True, подбери примеры для упражнений из релевантных источников. 
        Обязательно интегрируй ссылки на найденные источники в текст ответа.
        5. **Домашнее задание** (если параметр "наличие домашнего задания: True")
        6. **Рекомендации по особым условиям** (если указан параметр "Особые условия")
        """

    #    tools = []
    #    tool_choice = None

    #    if params['разрешен_web_search']:
    #        tools.append({
    #            "type": "web_search_preview",
    #            "search_context_size": "medium",
    #            "user_location": {
    #                "type": "approximate",
    #                "country": "RU"
    #            }
    #        })
    #        tool_choice = {"type": "web_search_preview"}

    #    response = client.responses.create(
    #        model="gpt-4o-mini",
    #        input=prompt,
    #        tools=tools if tools else None,
    #        tool_choice=tool_choice,
    #        max_output_tokens=2000
    #    )
    #    return response.output_text
    #
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты — эксперт в области логопедии."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000
    )
    return response.choices[0].message.content

# Интерфейс Gradio
with gr.Blocks() as demo:
    gr.Markdown("## 🧠 Генератор логопедических занятий")

    with gr.Row():
        нарушение = gr.Textbox(label="Основное нарушение*", placeholder="Пример: Дислалия (свистящие), ОНР II уровня")
        возраст = gr.Textbox(label="Возраст ребенка*", placeholder="Пример: 5 лет, 6-7 лет")
        цель = gr.Textbox(label="Цель занятия*", placeholder="Пример: Автоматизация звука [Р] в слогах")

    тематика = gr.Textbox(label="Тематика", placeholder="Пример: Животные, Транспорт")
    особые_условия = gr.Textbox(label="Особые условия", placeholder="Пример: гиперактивность, РАС")

    формат = gr.Radio(["Индивидуальное", "Групповое"], label="Формат занятия*", value="Индивидуальное")
    количество_детей = gr.Slider(
        label="Количество детей в группе", minimum=2, maximum=10, value=2, step=1, visible=False
    )

    def toggle_group_slider(selected_format):
        return gr.update(visible=(selected_format == "Групповое"))


    формат.change(fn=toggle_group_slider, inputs=формат, outputs=количество_детей)

    with gr.Group():
        gr.Markdown("### Инвентарь")
        зеркало = gr.Checkbox(label="Зеркало")
        карточки = gr.Checkbox(label="Карточки")
        игрушки = gr.Checkbox(label="Игрушки")
        дополнительный = gr.Textbox(label="Дополнительно", placeholder="Пример: мячи, планшеты")

    длительность = gr.Slider(label="Длительность занятия (мин)", minimum=15, maximum=60, value=30, step=5)
    дз = gr.Checkbox(label="Домашнее задание")
    web = gr.Checkbox(label="Разрешить поиск в интернете")

    btn = gr.Button("Создать конспект")
    output = gr.Markdown()

    def on_submit(*args):
        return generate_lesson_plan_interface(*args)

    # Элементы, которые будем блокировать во время генерации
    all_inputs = [
        нарушение, возраст, цель, формат, количество_детей,
        тематика, особые_условия, зеркало, карточки, игрушки,
        дополнительный, длительность, дз, web, btn
    ]

    def on_submit_with_spinner(
        нарушение, возраст, цель, формат, количество_детей,
        тематика, особые_условия, зеркало, карточки, игрушки,
        дополнительный, длительность, дз, web
    ):
        # Блокируем все элементы и выводим "Генерация..."
        for elem in all_inputs:
            elem.interactive = False
        yield gr.update(value="⏳ Генерация конспекта...")

        # Генерация
        result = generate_lesson_plan_interface(
            нарушение, возраст, цель, формат, количество_детей,
            тематика, особые_условия, зеркало, карточки, игрушки,
            дополнительный, длительность, дз, web
        )

        # Выводим результат
        yield gr.update(value=result)

        # Разблокируем элементы
        for elem in all_inputs:
            elem.interactive = True

    btn.click(
        fn=on_submit_with_spinner,
        inputs=[
            нарушение, возраст, цель, формат, количество_детей,
            тематика, особые_условия, зеркало, карточки, игрушки,
            дополнительный, длительность, дз, web
        ],
        outputs=output,
        show_progress=True
    )

if __name__ == "__main__":
    demo.launch()