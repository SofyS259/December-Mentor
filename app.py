import streamlit as st
import requests
import os
import base64
import re

# --- НАСТРОЙКИ ---
# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ НА GOOGLE SCRIPT (обязательно с https:// и /exec)
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwrjnUp0eGnK4yJRxep3hjLMRCg-xA-EN-SLwYhA9QQaPdEJE7PbYQayMDnKJAITHxV/exec"

# Список тем (столбцы в таблице)
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

MAX_SCORE = 5  # Количество вопросов для полного прохождения темы

GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")

# --- ФУНКЦИИ ---

def get_gigachat_token():
    if not GIGACHAT_CLIENT_ID or not GIGACHAT_CLIENT_SECRET:
        st.error("❌ Ошибка: Ключи API не найдены в настройках Railway!")
        return None
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    credentials = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
    try:
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    except Exception as e:
        st.error(f"Ошибка кодирования ключей: {e}")
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
            st.error(f"❌ Сбер отверг ключи: {response.text}")
            return None
    except Exception as e:
        st.error(f"❌ Ошибка соединения: {e}")
        return None

def ask_gigachat(token, user_message, current_topic, current_score, is_hint_mode=False):
    """
    Генерирует ответ Чацкого.
    current_score: текущее количество баллов (0..4). Следующий вопрос будет номер (current_score + 1).
    """
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # === ПРОМПТ ЛИЧНОСТИ ЧАЦКОГО ===
    CHATSKY_PERSONA = """
    Ты — Александр Андреевич Чацкий из комедии А.С. Грибоедова «Горе от ума».
    ТЫ — СТРОГИЙ УЧИТЕЛЬ ЛИТЕРАТУРЫ, готовящий дворян к Декабрьскому сочинению и экзаменам.
    
    ТВОЙ СТИЛЬ РЕЧИ:
    - Эмоциональный, пылкий, саркастичный, местами гневный.
    - Используй лексику XIX века: «сударь», «сударыня», «извольте», «помилуйте», «фамусовское общество», «служить бы рад, прислуживаться тошно».
    - Цитируй или обыгрывай фразы из «Горя от ума».
    
    ТВОИ ЗАДАЧИ:
    1. Задавать вопросы ТОЛЬКО по русской классической литературе (школьная программа).
    2. Обсуждать ТОЛЬКО темы экзаменов, сочинений и литературных произведений.
    3. ЕСЛИ УЧЕНИК СПРАШИВАЕТ О ПОГОДЕ, МЕМАХ, МАТЕМАТИКЕ ИЛИ ДРУГОМ: 
       - Гневно откажись отвечать! Скажи: «Что за пустяки? Какие такие новости? Мы здесь высокую словесность разбираем, сударь!».
       - Верни разговор к литературе.
    
    ПРАВИЛА ЭКЗАМЕНА (СЕРИЯ ИЗ 5 ВОПРОСОВ):
    - Твоя цель: провести ученика через 5 вопросов по текущей теме («{topic}»).
    - Счетчик баллов ученика сейчас: {score}. Тебе нужно задать вопрос номер {next_q}.
    
    СЦЕНАРИЙ ОТВЕТА:
    А) ЕСЛИ ОТВЕТ УЧЕНИКА ВЕРНЫЙ:
       - Яростно похвали («Браво!», «Умно!», «Вот то-то же!», «Дельно!»).
       - Запиши мысленно +1 балл.
       - Если баллов стало 5: Поздравь с окончанием темы.
       - Если баллов меньше 5: Сразу задай СЛЕДУЮЩИЙ вопрос (номер {next_q_plus_1}) по этой же теме.
       
    Б) ЕСЛИ ОТВЕТ НЕВЕРНЫЙ, КОРОТКИЙ ИЛИ «НЕ ЗНАЮ»:
       - НЕ начисляй балл.
       - НЕ переходи к следующему вопросу.
       - Дай ироничную, но полезную подсказку.
       - Потребуй ответить на ЭТОТ ЖЕ вопрос снова.
    """

    next_q = current_score + 1
    next_q_plus_1 = current_score + 2
    
    # Формирование системного сообщения
    system_instruction = CHATSKY_PERSONA.format(
        topic=current_topic, 
        score=current_score, 
        next_q=next_q, 
        next_q_plus_1=next_q_plus_1
    )

    if user_message == "START_GREETING":
        # Самый первый старт диалога
        full_prompt = (
            system_instruction + 
            "\n\nСИТУАЦИЯ: Экзамен еще не начался. Пользователь только что поздоровался."
            "\nЗАДАЧА: Ответь на приветствие в стиле Чацкого, представься, объясни правила (5 вопросов по теме для получения балла) и сразу задай ПЕРВЫЙ вопрос (№1) по теме '{topic}'.".format(topic=current_topic)
        )
        user_content = "Здравствуйте!"
    elif user_message == "NEXT_TOPIC_START":
        # Начало новой темы
        full_prompt = (
            system_instruction + 
            "\n\nСИТУАЦИЯ: Предыдущая тема завершена на 5 баллов. Начата новая тема."
            "\nЗАДАЧА: Кратко объяви новую тему и задай ПЕРВЫЙ вопрос (№1) по ней."
        )
        user_content = "Готов к новой теме."
    else:
        # Обычный ход экзамена
        if is_hint_mode:
            instruction_detail = (
                f"Ученик ответил неверно на вопрос №{next_q}. "
                "НЕ хвали его. НЕ задавай новый вопрос. "
                "Дай подсказку, используй сарказм, но помоги понять суть. "
                "Затем четко скажи: 'Извольте ответить на вопрос №{n} еще раз'.".format(n=next_q)
            )
        else:
            instruction_detail = (
                f"Ученик дал ответ на вопрос №{next_q}. Оцени его строго.\n"
                "- Если ВЕРНО: Похвали, зафиксируй успех и задай вопрос №{n_next} (или заверши тему, если это был 5-й).\n"
                "- Если НЕВЕРНО: Дай подсказку и требуй ответа на вопрос №{n_curr}.".format(
                    n_next=next_q_plus_1, 
                    n_curr=next_q
                )
            )
        
        full_prompt = system_instruction + f"\n\nСИТУАЦИЯ: {instruction_detail}"
        user_content = f"Ответ ученика: {user_message}"

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
            return f"Ошибка связи с Сбером: {response.text}"
    except Exception as e:
        return f"Ошибка соединения: {e}"

def update_google_sheet_score(nick, topic, new_score):
    """
    Обновляет балл в таблице. 
    Логика: находит строку с ником, ставит new_score в столбец темы.
    """
    if not GOOGLE_SCRIPT_URL or "https://" not in GOOGLE_SCRIPT_URL:
        st.warning("⚠️ Ссылка на Google Script не настроена!")
        return False
        
    payload = {
        "nick": nick,
        "topic": topic,
        "score": new_score  # Передаем конкретное число баллов (1, 2, 3...)
    }
    
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Ошибка записи в таблицу: {e}")
        return False

# --- ИНТЕРФЕЙС STREAMLIT ---

st.set_page_config(page_title="Экзамен с Чацким", page_icon="🎩")
st.title("🎩 Литературный экзамен с А.А. Чацким")
st.markdown("*«Свежо предание, а верится с трудом...» Наберите 5 баллов по каждой теме, чтобы перейти к следующей.*")

# --- СОСТОЯНИЕ СЕССИИ ---
if "token" not in st.session_state:
    st.session_state.token = None
if "nick" not in st.session_state:
    st.session_state.nick = ""
if "current_topic_index" not in st.session_state:
    st.session_state.current_topic_index = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
# Текущие баллы по активной теме (0..5)
if "current_score" not in st.session_state:
    st.session_state.current_score = 0
# Флаг состояния: нужно ли начать диалог или задать следующий вопрос
# States: 'GREET', 'NEXT_TOPIC', 'WAIT_ANSWER', 'HINT_MODE'
if "bot_state" not in st.session_state:
    st.session_state.bot_state = 'GREET' 

# --- ЛОГИКА ---

if not st.session_state.nick:
    # Экран входа
    nick_input = st.text_input("Как вас зовут, сударь/сударыня?", placeholder="Ваше имя")
    if st.button("Начать экзамен"):
        if nick_input.strip():
            st.session_state.nick = nick_input.strip()
            st.session_state.bot_state = 'GREET'
            st.rerun()
else:
    # Получение токена
    if not st.session_state.token:
        with st.spinner("Чацкий связывается со Сбером..."):
            st.session_state.token = get_gigachat_token()
            if not st.session_state.token:
                st.stop()

    # Обработка состояний бота (генерация сообщений без ввода пользователя)
    if st.session_state.bot_state in ['GREET', 'NEXT_TOPIC']:
        current_topic = TOPICS[st.session_state.current_topic_index]
        
        msg_type = "START_GREETING" if st.session_state.bot_state == 'GREET' else "NEXT_TOPIC_START"
        
        with st.chat_message("assistant"):
            with st.spinner("Чацкий готовится..." if st.session_state.bot_state == 'GREET' else "Чацкий формулирует вопрос..."):
                response_text = ask_gigachat(st.session_state.token, msg_type, current_topic, st.session_state.current_score)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        
        # После приветствия или старта темы ждем ответа пользователя
        st.session_state.bot_state = 'WAIT_ANSWER'
        st.rerun()

    # Отображение истории чата
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Боковая панель с прогрессом
    current_topic_name = TOPICS[st.session_state.current_topic_index]
    st.sidebar.info(
        f"📚 **Тема:** {current_topic_name}\n"
        f" **Баллы:** {st.session_state.current_score} из {MAX_SCORE}\n"
        f"📊 **Статус:** {'ТЕМА ПРОЙДЕНА' if st.session_state.current_score >= MAX_SCORE else 'Идет экзамен'}"
    )

    # Ввод пользователя
    if prompt := st.chat_input("Ваш ответ..."):
        # Добавляем сообщение пользователя
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        current_topic = TOPICS[st.session_state.current_topic_index]
        current_score = st.session_state.current_score
        
        # Определяем, в каком режиме спрашиваем ИИ (обычный или подсказка)
        # По умолчанию считаем, что это обычная проверка ответа
        is_hint = (st.session_state.bot_state == 'HINT_MODE')
        
        with st.chat_message("assistant"):
            with st.spinner("Чацкий оценивает ваш ответ..."):
                response_text = ask_gigachat(st.session_state.token, prompt, current_topic, current_score, is_hint_mode=is_hint)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # === АНАЛИЗ ОТВЕТА ДЛЯ ОБНОВЛЕНИЯ БАЛЛОВ ===
        lower_response = response_text.lower()
        
        # Маркеры успеха
        positive_words = ["браво", "отлично", "верно", "правильно", "превосходно", "засчитано", "именно так", "хорошо", "умно", "дельно", "принято", "так держать"]
        # Маркеры неудачи/подсказки
        negative_words = ["неверно", "ошибка", "попробуйте снова", "еще раз", "нет", "слабо", "чепуха", "пустяки", "подсказка", "намек", "подумайте", "вспомните", "не совсем", "плохо"]
        
        has_praise = any(word in lower_response for word in positive_words)
        has_negative = any(word in lower_response for word in negative_words)
        
        # Проверка на явный переход к следующему вопросу (например, "Вопрос №2")
        next_q_match = re.search(r'вопрос\s*№?\s*(\d+)', lower_response)
        mentioned_next_q = False
        if next_q_match:
            matched_num = int(next_q_match.group(1))
            # Если упомянутый номер больше текущего ожидаемого (score + 1), значит шаг сделан
            if matched_num > (current_score + 1):
                mentioned_next_q = True

        # Логика решения: ответ верный?
        is_correct = (has_praise and not has_negative) or mentioned_next_q

        if is_correct:
            # ✅ ПРАВИЛЬНЫЙ ОТВЕТ
            new_score = current_score + 1
            st.success(f"✅ Верно! +1 балл. Всего: {new_score}")
            
            # Обновляем балл в Google Таблице
            if update_google_sheet_score(st.session_state.nick, current_topic, new_score):
                st.toast(f"Балл ({new_score}) записан в таблицу!")
            else:
                st.toast("⚠️ Не удалось записать балл в таблицу (проверьте скрипт)")

            st.session_state.current_score = new_score

            # Проверка завершения темы
            if new_score >= MAX_SCORE:
                st.balloons()
                st.success(f"🎉 Тема «{current_topic}» ПРОЙДЕНА на 5 баллов!")
                st.session_state.chat_history.append({"role": "assistant", "content": f"Поздравляю, сударь! Тема «{current_topic}» вами полностью освоена. Переходим к следующему предмету."})
                
                # Переход к следующей теме
                if st.session_state.current_topic_index < len(TOPICS) - 1:
                    st.session_state.current_topic_index += 1
                    st.session_state.current_score = 0
                    st.session_state.bot_state = 'NEXT_TOPIC' # Триггер на генерацию первого вопроса новой темы
                    st.rerun()
                else:
                    st.session_state.chat_history.append({"role": "assistant", "content": "🎉 Вы прошли весь курс литературы! Экзамен окончен. Вы истинный знаток слова!"})
                    st.stop()
            else:
                # Тема не закончена, просто ждем следующего ввода (вопрос уже задан в тексте ответа ИИ)
                st.session_state.bot_state = 'WAIT_ANSWER'
                st.rerun()

        else:
            # ❌ НЕВЕРНЫЙ ОТВЕТ
            st.warning("⚠️ Ответ неверен. Балл не начислен. Чацкий дал подсказку.")
            # Балл НЕ меняем.
            # Ставим флаг, что следующий запрос должен быть в режиме "подсказка/повтор"
            st.session_state.bot_state = 'HINT_MODE' 
            st.rerun()
