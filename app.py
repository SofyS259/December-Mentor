import streamlit as st
import requests
import os
import base64
import re

# --- НАСТРОЙКИ ---
# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ НА GOOGLE SCRIPT (обязательно с https:// и /exec)
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwrjnUp0eGnK4yJRxep3hjLMRCg-xA-EN-SLwYhA9QQaPdEJE7PbYQayMDnKJAITHxV/exec"

TOPICS = [
    "Преступление и наказание",
    "Герой нашего времени",
    "Горе от ума",
    "Старуха Изергиль",
    "Обломов",
    "Мертвые души",
    "Евгений Онегин",
    "Капитанская дочка",
    "Вишневый сад",
    "Тарас Бульба"
]

QUESTIONS_PER_TOPIC = 5  # Нужно 5 верных ответов для перехода

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
    except:
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

def ask_gigachat(token, user_message, current_topic, current_question_num, is_hint_mode=False):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    CHATSKY_PERSONA = """
    Ты — Александр Андреевич Чацкий из «Горя от ума». Ты строгий, но справедливый учитель литературы.
    Твоя цель: провести ученика через серию из 5 вопросов по теме.
    
    ПРАВИЛА ПОВЕДЕНИЯ:
    1. ЗАДАВАЙ ВОПРОСЫ ПО ОДНОМУ. Никогда не перечисляй несколько вопросов сразу.
    2. ЕСЛИ ОТВЕТ ВЕРНЫЙ: 
       - Эмоционально похвали («Браво!», «Умно!», «Вот то-то же!»).
       - Сразу задай СЛЕДУЮЩИЙ вопрос (номер N+1). Если это был 5-й вопрос, поздравь с завершением темы.
    3. ЕСЛИ ОТВЕТ НЕВЕРНЫЙ или ученик говорит «не знаю»:
       - НЕ переходи к следующему вопросу.
       - Дай тонкую, ироничную подсказку в стиле Чацкого.
       - Четко напиши, что нужно ответить на ЭТОТ ЖЕ вопрос снова.
    4. СТИЛЬ: Лексика XIX века, цитаты, сарказм, пафос.
    5. ЗАПРЕТЫ: Не отвечай на вопросы не по литературе. Не переходи к следующей теме, пока не получено 5 верных ответов.
    """

    if user_message == "START_TOPIC":
        system_prompt = (
            CHATSKY_PERSONA + 
            f"\n\nНАЧАЛО ЭКЗАМЕНА. Тема: '{current_topic}'. Нужно задать 5 вопросов по очереди."
            "Задай ПЕРВЫЙ вопрос (№1). Будь краток и конкретен."
        )
        user_content = "Начни экзамен."
    else:
        if is_hint_mode:
            instruction = (
                f"Ученик ответил неверно на вопрос №{current_question_num}. "
                "НЕ задавай новый вопрос. Дай подсказку, намекни на ответ, используй иронию. "
                "Затем явно попроси ответить снова на вопрос №{current_question_num}.".format(current_question_num=current_question_num)
            )
        else:
            instruction = (
                f"Ученик дал ответ на вопрос №{current_question_num}. Оцени его строго.\n"
                "- Если ВЕРНО: Похвали и сразу задай вопрос №{next_q} (если 5-й, то заверши тему).\n"
                "- Если НЕВЕРНО: Дай подсказку и потребуй ответить снова на вопрос №{current_q}.".format(
                    next_q=current_question_num + 1, 
                    current_q=current_question_num
                )
            )

        system_prompt = (
            CHATSKY_PERSONA + 
            f"\n\nТЕКУЩАЯ СИТУАЦИЯ: Тема '{current_topic}'. Мы работаем над вопросом №{current_question_num} из 5.\n"
            f"{instruction}"
        )
        user_content = f"Ответ ученика: {user_message}"

    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
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

def send_to_google_sheet(nick, topic):
    if not GOOGLE_SCRIPT_URL or "https://" not in GOOGLE_SCRIPT_URL:
        return False
    payload = {"nick": nick, "topic": topic, "status": 1}
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
        return response.status_code == 200
    except:
        return False

# --- ИНТЕРФЕЙС ---

st.set_page_config(page_title="Экзамен с Чацким", page_icon="🎩")
st.title("🎩 Литературный экзамен: 5 вопросов")
st.markdown("*Наберите 5 верных ответов по теме. Ошибки не страшны — Чацкий даст подсказку, но вопрос не изменится, пока вы не ответите верно.*")

# Инициализация состояния
if "token" not in st.session_state:
    st.session_state.token = None
if "nick" not in st.session_state:
    st.session_state.nick = ""
if "current_topic_index" not in st.session_state:
    st.session_state.current_topic_index = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
# Счетчик ВЕРНЫХ ответов по текущей теме (0..5)
if "correct_count" not in st.session_state:
    st.session_state.correct_count = 0
# Флаг: нужно ли сгенерировать первый вопрос новой темы
if "need_first_question" not in st.session_state:
    st.session_state.need_first_question = True

# Вход
if not st.session_state.nick:
    nick_input = st.text_input("Как вас зовут, сударь/сударыня?", placeholder="Ваше имя")
    if st.button("Начать экзамен"):
        if nick_input.strip():
            st.session_state.nick = nick_input.strip()
            st.session_state.chat_history.append({"role": "assistant", "content": f"Ах, {nick_input}! Добро пожаловать. Я — Чацкий. Правило простое: 5 верных ответов по теме — и вы свободны. Ошибетесь — дам подсказку, но вопрос тот же. Начнем с темы: **«{TOPICS[0]}»**?"})
            st.session_state.need_first_question = True
            st.rerun()
else:
    if not st.session_state.token:
        with st.spinner("Чацкий связывается со Сбером..."):
            st.session_state.token = get_gigachat_token()
            if not st.session_state.token:
                st.stop()

    # Генерация первого вопроса при старте темы
    if st.session_state.need_first_question:
        current_topic = TOPICS[st.session_state.current_topic_index]
        with st.chat_message("assistant"):
            with st.spinner("Чацкий формулирует вопрос №1..."):
                q_num = st.session_state.correct_count + 1
                response_text = ask_gigachat(st.session_state.token, "START_TOPIC", current_topic, q_num)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        st.session_state.need_first_question = False

    # Отображение чата
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Индикатор прогресса
    current_topic_name = TOPICS[st.session_state.current_topic_index]
    current_q_num = st.session_state.correct_count + 1
    st.sidebar.info(f"📚 Тема: {current_topic_name}\n❓ Текущий вопрос: {current_q_num} из {QUESTIONS_PER_TOPIC}\n✅ Верных ответов: {st.session_state.correct_count}")

    if prompt := st.chat_input("Ваш ответ..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        current_topic = TOPICS[st.session_state.current_topic_index]
        # Номер вопроса, на который отвечаем сейчас (он равен correct_count + 1)
        current_q_num = st.session_state.correct_count + 1
        
        with st.chat_message("assistant"):
            with st.spinner("Чацкий оценивает..."):
                response_text = ask_gigachat(st.session_state.token, prompt, current_topic, current_q_num)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # === АНАЛИЗ ОТВЕТА КОДОМ ===
        lower_response = response_text.lower()
        
        # Слова похвалы (означают верный ответ)
        positive_words = ["браво", "отлично", "верно", "правильно", "превосходно", "засчитано", "именно так", "хорошо", "умно", "дельно", "совершенно верно", "принято"]
        # Слова ошибки/подсказки (означают, что нужно остаться на том же вопросе)
        negative_words = ["неверно", "ошибка", "попробуйте снова", "еще раз", "нет", "слабо", "чепуха", "пустяки", "подсказка", "намек", "подумайте", "вспомните", "не совсем"]
        
        has_praise = any(word in lower_response for word in positive_words)
        has_negative = any(word in lower_response for word in negative_words)
        
        # Проверка: упомянул ли он следующий номер вопроса? (например, "Вопрос №2")
        next_q_match = re.search(r'вопрос\s*№?\s*(\d+)', lower_response)
        mentioned_next_q = False
        if next_q_match:
            matched_num = int(next_q_match.group(1))
            if matched_num > current_q_num:
                mentioned_next_q = True

        # ЛОГИКА РЕШЕНИЯ:
        # Ответ верный, если:
        # 1. Есть похвала И нет слов ошибки/подсказки.
        # ИЛИ
        # 2. Бот явно перешел к следующему номеру вопроса.
        is_correct = (has_praise and not has_negative) or mentioned_next_q

        if is_correct:
            st.success("✅ Ответ верный! +1 балл.")
            st.session_state.correct_count += 1
            
            # Проверка: набрали ли 5 баллов?
            if st.session_state.correct_count >= QUESTIONS_PER_TOPIC:
                st.balloons()
                st.success(f"🎉 Тема «{current_topic}» ПРОЙДЕНА (5/5)! Запись в журнал...")
                success = send_to_google_sheet(st.session_state.nick, current_topic)
                if success:
                    st.success("✅ Оценка «1» записана в таблицу!")
                
                # Сброс и переход к следующей теме
                st.session_state.current_topic_index += 1
                st.session_state.correct_count = 0
                st.session_state.need_first_question = True
                
                if st.session_state.current_topic_index < len(TOPICS):
                    next_topic = TOPICS[st.session_state.current_topic_index]
                    st.info(f"Переходим к следующей теме: **{next_topic}**.")
                    st.rerun()
                else:
                    st.session_state.chat_history.append({"role": "assistant", "content": "🎉 Поздравляю, сударь! Вы прошли весь курс литературы. Экзамен окончен!"})
                    st.stop()
            else:
                # Просто продолжаем диалог, счетчик увеличен, следующий вопрос уже задан в тексте ответа
                st.rerun()
        else:
            st.warning("⚠️ Ответ неверный. Балл не начислен. Чацкий дал подсказку. Ответьте снова на этот же вопрос.")
            # Счетчик НЕ увеличиваем. Вопрос остается тем же.
            st.rerun()
