import streamlit as st
import requests
import os
import base64
import re

# --- НАСТРОЙКИ ---
# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ НА GOOGLE SCRIPT (обязательно с https:// и /exec)
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwrjnUp0eGnK4yJRxep3hjLMRCg-xA-EN-SLwYhA9QQaPdEJE7PbYQayMDnKJAITHxV/exec"

# Список тем и 5 УНИКАЛЬНЫХ АСПЕКТОВ для каждой (чтобы вопросы не повторялись)
# Структура: "Название темы": ["Аспект 1", "Аспект 2", "Аспект 3", "Аспект 4", "Аспект 5"]
TOPICS_DATA = {
    "Преступление и наказание": [
        "теория Раскольникова о 'тварях дрожащих и право имеющих'",
        "образ Сони Мармеладовой и её роль в спасении Раскольникова",
        "символика сна о моровой язве в эпилоге романа",
        "мотивы преступления Раскольникова: нужда, гордыня или эксперимент?",
        "образ Петербурга как душного, давящего пространства"
    ],
    "Герой нашего времени": [
        "психологический портрет Печорина и его внутренний конфликт",
        "история любви Печорина и Бэлы: эгоизм или судьба?",
        "роль судьбы и фатализма в жизни Грушницкого и Печорина",
        "анализ главы 'Княжна Мери': дуэль и интриги",
        "феномен 'лишнего человека' на примере Печорина"
    ],
    "Горе от ума": [
        "конфликт Чацкого с фамусовским обществом: век нынешний и век минувший",
        "образ Софьи Фамусовой: жертва или соучастница?",
        "монологи Чацкого как выражение идей декабристов",
        "сплетня о сумасшествии Чацкого: почему она так быстро распространилась?",
        "проблема ума и безумия в комедии"
    ],
    "Старуха Изергиль": [
        "легенда о Данко: смысл подвига и отношение людей к герою",
        "легенда о Ларре: наказание гордыней и одиночеством",
        "контраст между образами Данко, Ларры и самой Изергиль",
        "романтизм произведения: исключительные герои в исключительных обстоятельствах",
        "проблема смысла жизни в рассказе"
    ],
    "Обломов": [
        "понятие 'обломовщины' как социального и нравственного явления",
        "сон Обломова: ключ к пониманию характера героя",
        "сравнение образов Обломова и Штольца: два пути жизни",
        "любовная линия: почему отношения с Ольгой Ильинской не сложились?",
        "роль Захара в жизни Ильи Ильича: зеркало хозяина"
    ],
    "Мертвые души": [
        "образ Чичикова: кто он, авантюрист или герой времени?",
        "галерея помещиков: Манилов, Коробочка, Ноздрев, Собакевич, Плюшкин (общая характеристика)",
        "смысл названия поэмы: кто такие 'мертвые души'?",
        "образ России-тройки в лирическом отступлении",
        "система чиновников города N: взяточничество и казнокрадство"
    ],
    "Евгений Онегин": [
        "эволюция образа Онегина: от скуки до любви",
        "образ Татьяны Лариной: 'милый идеал' Пушкина",
        "письмо Татьяны и ответ Онегина: анализ чувств и морали",
        "быт и нравы дворянской усадьбы и Петербурга",
        "финал романа: почему Онегин отвергнут?"
    ],
    "Капитанская дочка": [
        "образ Емельяна Пугачева: жестокий бунтовщик или справедливый лидер?",
        "нравственный выбор Петра Гринева: честь и долг",
        "образ Маши Мироновой: тихая героиня",
        "тема милосердия в повести (сцена с зайцем, помилование Гринева)",
        "историческая правда и художественный вымысел в произведении"
    ],
    "Вишневый сад": [
        "символика вишневого сада: прошлое, настоящее и будущее",
        "образ Раневской: непрактичность и детская непосредственность",
        "Лопахин: деловой человек с душой поэта или хищник?",
        "образ Пети Трофимова и тема будущего России",
        "звуковой ряд пьесы: звук лопнувшей струны и стук топора"
    ],
    "Тарас Бульба": [
        "образ Тараса Бульбы: воплощение народного характера",
        "трагедия отца и сыновей: Остап и Андрий",
        "товарищество как высшая ценность для запорожцев",
        "описание битв и воинской доблести",
        "патриотизм и жестокость в повести"
    ]
}

TOPIC_NAMES = list(TOPICS_DATA.keys())
MAX_SCORE = 5

GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")

# --- ФУНКЦИИ ---

def get_gigachat_token():
    if not GIGACHAT_CLIENT_ID or not GIGACHAT_CLIENT_SECRET:
        st.error("❌ Ошибка: Ключи API не найдены!")
        return None
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    credentials = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
    try:
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    except Exception as e:
        st.error(f"Ошибка кодирования: {e}")
        return None
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "RqUID": "00000000-0000-0000-0000-000000000000",
        "Authorization": f"Basic {encoded_credentials}"
    }
    data = {"scope": "GIGACHAT_API_PERS"}
    
    try:
        response = requests.post(url, headers=headers, data=data, verify=False)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            st.error(f"Ошибка токена: {response.text}")
            return None
    except Exception as e:
        st.error(f"Ошибка соединения: {e}")
        return None

def ask_gigachat(token, user_message, current_topic, current_aspect, current_score, is_hint_mode=False):
    """
    current_aspect: конкретная тема вопроса (например, 'образ Сони'), чтобы вопросы были разными.
    """
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    CHATSKY_PERSONA = """
    Ты — Александр Андреевич Чацкий. Строгий учитель литературы.
    ТВОЙ СТИЛЬ: Эмоциональный, саркастичный, лексика XIX века («сударь», «помилуйте», цитаты из «Горя от ума»).
    ЗАПРЕТЫ: Никаких разговоров о погоде, мемах, математике. Только литература, экзамены, сочинения!
    
    ТВОЯ ЗАДАЧА СЕЙЧАС:
    Тема произведения: "{topic}".
    Конкретный аспект для вопроса №{q_num}: "{aspect}".
    
    ПРАВИЛА:
    1. Сформулируй ВОПРОС строго по аспекту "{aspect}". Не спрашивай ни о чем другом.
    2. Если ответ ученика ВЕРНЫЙ: Похвали ярко. Если это был 5-й вопрос — поздравь с окончанием темы. Если нет — скажи, что переходим к следующему аспекту (но сам следующий вопрос задавать не надо, это сделает система).
    3. Если ответ НЕВЕРНЫЙ: Дай ироничную подсказку, связанную с аспектом "{aspect}", и потребуй ответить снова. Не переходи к другому аспекту!
    """

    q_num = current_score + 1
    
    system_prompt = CHATSKY_PERSONA.format(
        topic=current_topic,
        aspect=current_aspect,
        q_num=q_num
    )

    if user_message == "START_QUESTION":
        full_prompt = (
            system_prompt + 
            "\n\nСИТУАЦИЯ: Начало вопроса. Задай свой вопрос ученику по аспекту '{aspect}' в стиле Чацкого.".format(aspect=current_aspect)
        )
        user_content = "Задай вопрос."
    else:
        if is_hint_mode:
            instruction = (
                f"Ученик ответил неверно. Аспект все тот же: '{current_aspect}'. "
                "НЕ меняй тему вопроса. Дай подсказку именно по этому аспекту. "
                "Потребуй ответа снова."
            )
        else:
            instruction = (
                f"Ученик ответил на вопрос по аспекту '{current_aspect}'. Оцени ответ.\n"
                "- Если ВЕРНО: Похвали. Скажи, что вопрос закрыт.\n"
                "- Если НЕВЕРНО: Дай подсказку по этому аспекту и требуй ответа снова."
            )
        
        full_prompt = system_prompt + f"\n\nСИТУАЦИЯ: {instruction}\nОтвет ученика: {user_message}"
        user_content = "Оцени ответ."

    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": full_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Ошибка связи: {response.text}"
    except Exception as e:
        return f"Ошибка: {e}"

def update_google_sheet_score(nick, topic, new_score):
    if not GOOGLE_SCRIPT_URL or "https://" not in GOOGLE_SCRIPT_URL:
        return False
    payload = {"nick": nick, "topic": topic, "score": new_score}
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
        return response.status_code == 200
    except:
        return False

# --- ИНТЕРФЕЙС ---

st.set_page_config(page_title="Экзамен с Чацким", page_icon="🎩")
st.title("🎩 Литературный экзамен: 5 уникальных вопросов")
st.markdown("*5 тем → 5 разных аспектов в каждой. Наберите 5 баллов для перехода.*")

# СОСТОЯНИЕ
if "token" not in st.session_state: st.session_state.token = None
if "nick" not in st.session_state: st.session_state.nick = ""
if "current_topic_index" not in st.session_state: st.session_state.current_topic_index = 0
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "current_score" not in st.session_state: st.session_state.current_score = 0
if "bot_state" not in st.session_state: st.session_state.bot_state = 'GREET' # GREET, ASK_Q, WAIT, HINT

if not st.session_state.nick:
    nick_input = st.text_input("Как вас зовут?", placeholder="Имя")
    if st.button("Начать"):
        if nick_input.strip():
            st.session_state.nick = nick_input.strip()
            st.session_state.bot_state = 'GREET'
            st.rerun()
else:
    if not st.session_state.token:
        with st.spinner("Связь со Сбером..."):
            st.session_state.token = get_gigachat_token()
            if not st.session_state.token: st.stop()

    # Автоматическая генерация вопросов
    if st.session_state.bot_state in ['GREET', 'ASK_Q']:
        current_topic = TOPIC_NAMES[st.session_state.current_topic_index]
        current_score = st.session_state.current_score
        
        # Получаем уникальный аспект для текущего вопроса (индекс равен текущему счету)
        aspects_list = TOPICS_DATA[current_topic]
        current_aspect = aspects_list[current_score] # 0 -> аспект 1, 1 -> аспект 2 и т.д.
        
        msg_type = "START_GREETING" if st.session_state.bot_state == 'GREET' else "START_QUESTION"
        
        # Для приветствия нужен особый текст, но мы используем ту же функцию, передавая первый аспект
        if st.session_state.bot_state == 'GREET':
             # Специальный хак для первого приветствия, чтобы он представился
             with st.chat_message("assistant"):
                 st.write(f"Ах, {st.session_state.nick}! Я — Чацкий. Готовы к испытанию? Мы пройдемся по 5 уникальным аспектам темы **«{current_topic}»**. Ошибаться можно, но я буду давать подсказки, пока вы не ответите верно. Начнем!")
                 st.session_state.chat_history.append({"role": "assistant", "content": f"Ах, {st.session_state.nick}! Я — Чацкий..."}) # Краткая запись
                 # Сразу переходим к генерации первого вопроса
                 st.session_state.bot_state = 'ASK_Q'
                 st.rerun()
        
        # Генерация вопроса по аспекту
        with st.chat_message("assistant"):
            with st.spinner("Чацкий формулирует вопрос..."):
                # Передаем аспект, чтобы вопрос был уникальным
                response_text = ask_gigachat(st.session_state.token, "START_QUESTION", current_topic, current_aspect, current_score)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        
        st.session_state.bot_state = 'WAIT_ANSWER'
        st.rerun()

    # Отображение чата
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Прогресс
    current_topic_name = TOPIC_NAMES[st.session_state.current_topic_index]
    aspects_list = TOPICS_DATA[current_topic_name]
    current_aspect_name = aspects_list[st.session_state.current_score] if st.session_state.current_score < 5 else "Завершено"
    
    st.sidebar.info(
        f"📚 **Тема:** {current_topic_name}\n"
        f"🎯 **Аспект вопроса:** {current_aspect_name}\n"
        f"💯 **Баллы:** {st.session_state.current_score} / {MAX_SCORE}"
    )

    if prompt := st.chat_input("Ваш ответ..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        current_topic = TOPIC_NAMES[st.session_state.current_topic_index]
        current_score = st.session_state.current_score
        current_aspect = aspects_list[current_score]
        
        is_hint = (st.session_state.bot_state == 'HINT_MODE')
        
        with st.chat_message("assistant"):
            with st.spinner("Чацкий оценивает..."):
                response_text = ask_gigachat(st.session_state.token, prompt, current_topic, current_aspect, current_score, is_hint_mode=is_hint)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # Анализ
        lower_response = response_text.lower()
        positive_words = ["браво", "отлично", "верно", "правильно", "превосходно", "засчитано", "именно так", "хорошо", "умно", "дельно", "принято"]
        negative_words = ["неверно", "ошибка", "попробуйте снова", "еще раз", "нет", "слабо", "чепуха", "пустяки", "подсказка", "намек", "подумайте", "вспомните", "не совсем"]
        
        has_praise = any(word in lower_response for word in positive_words)
        has_negative = any(word in lower_response for word in negative_words)
        
        is_correct = has_praise and not has_negative

        if is_correct:
            new_score = current_score + 1
            st.success(f"✅ Верно! +1 балл. Всего: {new_score}")
            
            if update_google_sheet_score(st.session_state.nick, current_topic, new_score):
                st.toast(f"Балл ({new_score}) записан!")
            
            st.session_state.current_score = new_score

            if new_score >= MAX_SCORE:
                st.balloons()
                st.success(f"🎉 Тема пройдена на 5 баллов!")
                st.session_state.chat_history.append({"role": "assistant", "content": "Браво! Тема освоена полностью. Переходим к следующей книге!"})
                
                if st.session_state.current_topic_index < len(TOPIC_NAMES) - 1:
                    st.session_state.current_topic_index += 1
                    st.session_state.current_score = 0
                    st.session_state.bot_state = 'GREET' # Приветствие новой темы
                    st.rerun()
                else:
                    st.session_state.chat_history.append({"role": "assistant", "content": "🎉 Курс окончен! Вы великий знаток!"})
                    st.stop()
            else:
                # Следующий вопрос (новый аспект)
                st.session_state.bot_state = 'ASK_Q'
                st.rerun()
        else:
            st.warning("⚠️ Неверно. Балл не начислен. Подсказка дана.")
            st.session_state.bot_state = 'HINT_MODE'
            st.rerun()
