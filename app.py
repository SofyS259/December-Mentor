import streamlit as st
import requests
import os
import base64

# --- НАСТРОЙКИ ---
# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ НА GOOGLE SCRIPT
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

QUESTIONS_PER_TOPIC = 5

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

def ask_gigachat(token, user_message, current_topic, question_number, is_correct_answer=False):
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # === ГЛАВНЫЙ ПРОМПТ ЧАЦКОГО ===
    CHATSKY_PERSONA = """
    Ты — Александр Андреевич Чацкий, герой комедии А.С. Грибоедова «Горе от ума».
    ТВОЯ РОЛЬ: Строгий, пылкий, остроумный учитель литературы, готовящий учеников к Декабрьскому сочинению.
    
    ТВОЙ СТИЛЬ РЕЧИ:
    - Говори эмоционально, с пафосом, иногда с сарказмом и иронией («Свежо предание, а верится с трудом», «А судьи кто?», «Ба! Знакомые всё лица!»).
    - Используй лексику начала XIX века, но понятную современному школьнику (сударь, сударыня, извольте, помилуйте).
    - Будь нетерпим к глупости, лености и пустословию.
    - Обращайся к ученику как к дворянину, обязанному знать классику.

    ТВОИ ЗАДАЧИ:
    1. Задавать вопросы только по русской классической литературе (список тем ограничен школьной программой).
    2. Оценивать ответы ученика строго, но справедливо.
    3. Если ответ верный — похвали ярко («Браво!», «Умно!», «Вот то-то же!») и задай следующий вопрос по этой же теме.
    4. Если ответ неверный — посмейся над невежеством, укажи на ошибку и требуй ответа снова.
    
    СТРОГИЕ ОГРАНИЧЕНИЯ:
    - НИКОГДА не отвечай на вопросы не по теме литературы (математика, погода, сплетни, современные мемы). 
      Если ученик спрашивает ерунду, возмутился: «Что за новости? Какие такие пустяки? Мы здесь литературу разбираем, сударь!». Верни разговор к теме экзамена.
    - НИКОГДА не переходи к следующей теме сам, пока не задано ровно 5 вопросов по текущей.
    - НИКОГДА не будь слишком мягким. Ты Чацкий, а не нянька.
    """

    # Формирование конкретного запроса
    if user_message == "START_TOPIC":
        system_prompt = (
            f"{CHATSKY_PERSONA}\n\n"
            f"СЕЙЧАС: Начало экзамена. Тема: '{current_topic}'. Вопрос №1 из {QUESTIONS_PER_TOPIC}. "
            "Задай первый вопрос по этой теме. Начни с приветствия в стиле Чацкого и сразу переходи к делу."
        )
        user_content = "Начни экзамен."
    else:
        next_q = question_number + 1 if question_number < QUESTIONS_PER_TOPIC else 5
        system_prompt = (
            f"{CHATSKY_PERSONA}\n\n"
            f"СЕЙЧАС: Тема '{current_topic}'. Текущий вопрос №{question_number} из {QUESTIONS_PER_TOPIC}. "
            "Ответ ученика ниже. Оцени его."
            "Если ответ ВЕРНЫЙ: Похвали (в стиле Чацкого). Затем задай СЛЕДУЮЩИЙ вопрос №{next_q} по этой теме. "
            "Если это был вопрос №5: Поздравь с прохождением темы, но скажи, что впереди еще много книг.".format(next_q=next_q)
            "Если ответ НЕВЕРНЫЙ или не по теме: Отчитай ученика, используй сарказм. Если вопрос не по литературе — гневно отвергни его и верни к теме '{current_topic}'. Не задавай новый вопрос, пока не получишь верный ответ на текущий."
        )
        user_content = f"Ответ ученика: {user_message}"

    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.7, # Немного креативности для стиля
        "top_p": 0.9
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Ошибка связи с Сбером: {response.text}"
    except Exception as e:
        return f"Ошибка соединения: {e}"

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
st.title("🎩 Литературный экзамен с А.А. Чацким")
st.markdown("*«Свежо предание, а верится с трудом...» Выдержите ли вы испытание классикой?*")

# Инициализация состояния
if "token" not in st.session_state:
    st.session_state.token = None
if "nick" not in st.session_state:
    st.session_state.nick = ""
if "current_topic_index" not in st.session_state:
    st.session_state.current_topic_index = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "correct_count" not in st.session_state:
    st.session_state.correct_count = 0
if "need_first_question" not in st.session_state:
    st.session_state.need_first_question = True

# Вход
if not st.session_state.nick:
    nick_input = st.text_input("Как вас зовут, сударь/сударыня?", placeholder="Ваше имя")
    if st.button("Начать экзамен"):
        if nick_input.strip():
            st.session_state.nick = nick_input.strip()
            st.session_state.chat_history.append({"role": "assistant", "content": f"Ах, {nick_input}! Добро пожаловать. Я — Чацкий. Готовы ли вы продемонстрировать свои знания русской словесности? Вас ждет суровый экзамен: 5 вопросов по каждой теме. Начнем с **«{TOPICS[0]}»**?"})
            st.session_state.need_first_question = True
            st.rerun()
else:
    if not st.session_state.token:
        with st.spinner("Чацкий связывается со Сбером..."):
            st.session_state.token = get_gigachat_token()
            if not st.session_state.token:
                st.stop()

    # Автостарт вопроса при смене темы
    if st.session_state.need_first_question:
        current_topic = TOPICS[st.session_state.current_topic_index]
        with st.chat_message("assistant"):
            with st.spinner("Чацкий формулирует вопрос..."):
                response_text = ask_gigachat(st.session_state.token, "START_TOPIC", current_topic, 1)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        st.session_state.need_first_question = False

    # Отображение чата
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Индикатор прогресса
    current_topic_name = TOPICS[st.session_state.current_topic_index]
    st.sidebar.info(f"📚 Тема: {current_topic_name}\n✅ Верных ответов: {st.session_state.correct_count} / {QUESTIONS_PER_TOPIC}")

    if prompt := st.chat_input("Ваш ответ..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        current_topic = TOPICS[st.session_state.current_topic_index]
        current_q_num = st.session_state.correct_count + 1
        
        with st.chat_message("assistant"):
            with st.spinner("Чацкий проверяет..."):
                response_text = ask_gigachat(st.session_state.token, prompt, current_topic, current_q_num)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # АНАЛИЗ ОТВЕТА КОДОМ
        lower_response = response_text.lower()
        positive_words = ["браво", "отлично", "верно", "правильно", "превосходно", "засчитано", "именно так", "хорошо", "умно", "дельно"]
        negative_words = ["неверно", "ошибка", "попробуй еще", "снова", "не совсем", "нет", "плохо", "слабо", "пустяки", "чепуха"]
        
        has_praise = any(word in lower_response for word in positive_words)
        has_negative = any(word in lower_response for word in negative_words)
        
        # Логика: если есть похвала и нет явного отрицания -> ответ принят
        is_answer_correct = has_praise and not has_negative

        if is_answer_correct:
            st.session_state.correct_count += 1
            
            if st.session_state.correct_count >= QUESTIONS_PER_TOPIC:
                st.success(f"🎉 Тема «{current_topic}» ПРОЙДЕНА! Запись в журнал...")
                success = send_to_google_sheet(st.session_state.nick, current_topic)
                if success:
                    st.success("✅ Оценка записана в таблицу!")
                
                st.session_state.current_topic_index += 1
                st.session_state.correct_count = 0
                
                if st.session_state.current_topic_index < len(TOPICS):
                    next_topic = TOPICS[st.session_state.current_topic_index]
                    st.info(f"Переходим к следующей теме: **{next_topic}**.")
                    st.session_state.need_first_question = True
                    st.rerun()
                else:
                    st.balloons()
                    st.session_state.chat_history.append({"role": "assistant", "content": "🎉 Поздравляю, сударь! Вы прошли весь курс. Теперь вы истинный знаток словесности!"})
                    st.stop()
        else:
            st.warning("⚠️ Ответ не зачтен. Чацкий требует более глубоких знаний!")
            # Счетчик не меняем

        st.rerun()
