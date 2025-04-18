import os
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# Загрузка переменных окружения
load_dotenv()
api_key = os.getenv("API_KEY_openai")


def generate_lesson_plan(params):
    client = OpenAI(api_key=api_key)

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

    tools = []
    tool_choice = None

    if params['разрешен_web_search']:
        tools.append({
            "type": "web_search_preview",
            "search_context_size": "medium",
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
        max_output_tokens=2000
    )
    return response.output_text


# Интерфейс Streamlit
st.title("Генератор логопедических занятий")

# Левая часть с настройками
with st.sidebar:
    st.header("Настройки занятия")

    # Обязательные поля
    нарушение = st.text_input(
        "Основное нарушение*",
        placeholder="Пример: Дислалия (свистящие), ОНР II уровня"
    )

    возраст_ребенка = st.text_input(
        "Возраст ребенка*",
        placeholder="Пример: 5 лет, 6-7 лет"
    )

    цель_занятия = st.text_input(
        "Цель занятия*",
        placeholder="Пример: Автоматизация звука [Р] в слогах"
    )

    # Переключатель формата занятия
    формат_занятия = st.radio(
        "Формат занятия*",
        options=["Индивидуальное", "Групповое"],
        index=0,
        horizontal=True
    )

    количество_детей = 1  # Значение по умолчанию

    if формат_занятия == "Групповое":
        количество_детей = st.number_input(
            "Количество детей в группе*",
            min_value=2,
            max_value=10,
            value=3
        )

    # Дополнительные параметры
    тематика = st.text_input(
        "Тематика занятия",
        placeholder="Пример: Животные, Транспорт"
    )

    особые_условия = st.text_input(
        "Особые условия",
        placeholder="Пример: гиперактивность, РАС"
    )

    # Инвентарь
    st.subheader("Инвентарь")
    инвентарь_чекбоксы = {
        "Зеркало": st.checkbox("Зеркало"),
        "Карточки": st.checkbox("Карточки"),
        "Игрушки": st.checkbox("Игрушки")
    }
    дополнительный_инвентарь = st.text_input("Другое")

    инвентарь = ", ".join([k for k, v in инвентарь_чекбоксы.items() if v])
    if дополнительный_инвентарь:
        инвентарь += f", {дополнительный_инвентарь}"

    # Другие настройки
    длительность_занятия = st.slider(
        "Длительность (минут)",
        min_value=15,
        max_value=60,
        value=30,
        step=5
    )

    наличие_ДЗ = st.checkbox("Домашнее задание")
    разрешен_web_search = st.checkbox("Поиск материалов в интернете")

    # Кнопка генерации
    сгенерировать = st.button("Создать конспект")

# Правая часть с результатом
if сгенерировать:
    if not нарушение or not возраст_ребенка or not цель_занятия:
        st.error("Заполните обязательные поля!")
    else:
        params = {
            "нарушение": нарушение,
            "возраст_ребенка": возраст_ребенка,
            "цель_занятия": цель_занятия,
            "тематика": тематика,
            "формат_занятия": формат_занятия,
            "количество_детей": количество_детей,
            "инвентарь": инвентарь,
            "особые_условия": особые_условия,
            "длительность_занятия": длительность_занятия,
            "наличие_ДЗ": наличие_ДЗ,
            "разрешен_web_search": разрешен_web_search
        }

        with st.spinner("Создаем конспект..."):
            try:
                результат = generate_lesson_plan(params)
                st.success("Готово!")
                st.markdown(результат)
            except Exception as e:
                st.error(f"Ошибка: {e}")