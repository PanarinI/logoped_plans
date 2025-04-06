import os
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st

# Загрузка переменных окружения
load_dotenv()
#api_key = os.getenv("API_KEY_openai")
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")


def generate_lesson_plan(params):
#   client = OpenAI(api_key=api_key)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
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


# Интерфейс Streamlit
st.title("Генератор логопедических занятий")

# Инициализация флагов в session_state
if "loading" not in st.session_state:
    st.session_state["loading"] = False
if "lesson_plan" not in st.session_state:
    st.session_state["lesson_plan"] = ""

# Используем обычный блок в сайдбаре для динамических виджетов
with st.sidebar:
    st.header("Настройки занятия")

    нарушение = st.text_input(
        "Основное нарушение*",
        placeholder="Пример: Дислалия (свистящие), ОНР II уровня",
        disabled=st.session_state["loading"]
    )
    возраст_ребенка = st.text_input(
        "Возраст ребенка*",
        placeholder="Пример: 5 лет, 6-7 лет",
        disabled=st.session_state["loading"]
    )
    цель_занятия = st.text_input(
        "Цель занятия*",
        placeholder="Пример: Автоматизация звука [Р] в слогах",
        disabled=st.session_state["loading"]
    )

    формат_занятия = st.radio(
        "Формат занятия*",
        options=["Индивидуальное", "Групповое"],
        index=0,
        horizontal=True,
        disabled=st.session_state["loading"]
    )

    # Это поле появляется динамически, когда выбрано "Групповое"
    if формат_занятия == "Групповое":
        количество_детей = st.number_input(
            "Количество детей в группе*",
            min_value=2,
            max_value=10,
            value=3,
            disabled=st.session_state["loading"]
        )
    else:
        количество_детей = 1

    тематика = st.text_input(
        "Тематика занятия",
        placeholder="Пример: Животные, Транспорт",
        disabled=st.session_state["loading"]
    )
    особые_условия = st.text_input(
        "Особые условия",
        placeholder="Пример: гиперактивность, РАС",
        disabled=st.session_state["loading"]
    )

    st.subheader("Инвентарь")
    инвентарь_чекбоксы = {
        "Зеркало": st.checkbox("Зеркало", disabled=st.session_state["loading"]),
        "Карточки": st.checkbox("Карточки", disabled=st.session_state["loading"]),
        "Игрушки": st.checkbox("Игрушки", disabled=st.session_state["loading"])
    }
    дополнительный_инвентарь = st.text_input("Другое", disabled=st.session_state["loading"])
    инвентарь = ", ".join([k for k, v in инвентарь_чекбоксы.items() if v])
    if дополнительный_инвентарь:
        инвентарь += f", {дополнительный_инвентарь}"
    инвентарь = инвентарь.strip(", ")

    длительность_занятия = st.slider(
        "Длительность (минут)",
        min_value=15,
        max_value=60,
        value=30,
        step=5,
        disabled=st.session_state["loading"]
    )
    наличие_ДЗ = st.checkbox("Домашнее задание", disabled=st.session_state["loading"])
    разрешен_web_search = st.checkbox("Поиск материалов в интернете", disabled=st.session_state["loading"])

    # Кнопка отправки, блокируется если идет генерация
    submit = st.button("Создать конспект", disabled=st.session_state["loading"], key="submit_btn")

# Если кнопка нажата, запускаем генерацию
if submit:
    if not нарушение or not возраст_ребенка or not цель_занятия:
        st.sidebar.error("Заполните обязательные поля!")
    else:
        st.session_state["loading"] = True  # Блокируем виджеты
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
                st.session_state["lesson_plan"] = результат
                st.success("Готово!")
            except Exception as e:
                st.error(f"Ошибка: {e}")
            finally:
                st.session_state["loading"] = False

# Отображаем ранее сгенерированный конспект, если он есть и генерация не идёт
if st.session_state.get("lesson_plan", "") and not st.session_state["loading"]:
    st.markdown(st.session_state["lesson_plan"])