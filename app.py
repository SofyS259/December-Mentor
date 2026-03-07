import streamlit as st
import requests
import json
import os
import base64
from datetime import datetime

# --- НАСТРОЙКИ ---
# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ НА GOOGLE SCRIPT (обязательно с https:// и /exec в конце)
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwrjnUp0eGnK4yJRxep3hjLMRCg-xA-EN-SLwYhA9QQaPdEJE7PbYQayMDnKJAITHxV/exec"

# Список тем (книг)
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

# Ключи API (берутся из переменных окружения Railway)
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")

# --- ФУНКЦИИ ---

def get_gigachat_token():
    """Получает токен доступа к GigaChat"""
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

def ask_gigachat(token, user_message, context=""):
    """Отправляет запрос к GigaChat и получает ответ"""
    if not token:
        return "Ошибка авторизации."

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    system_prompt = (
        "Ты — Александр Андреевич Чацкий. Ты строгий, но справедливый учитель. "
        "Твоя задача: проверять знания ученика по русской классике. "
        "1. Если ответ ученика ВЕРНЫЙ: Похвали его (используй слова 'Браво', 'Отлично', 'Превосходно', 'Засчитано'). "
        "   После похвалы сразу задай вопрос по СЛЕДУЮЩЕЙ теме из списка или поздравь с окончанием. "
        "2. Если ответ НЕВЕРНЫЙ или короткий: Покритикуй с иронией, объясни ошибку и попроси ответить еще раз по ЭТОЙ ЖЕ теме. "
        "Не пиши слишком длинно. Будь живым и эмоциональным."
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\nУченик говорит: {user_message}"}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Ошибка GigaChat: {response.text}"
    except Exception as e:
        return f"Ошибка соединения: {e}"

def send_to_google_sheet(nick, topic):
    """Отправляет данные о пройденной теме в Google Таблицу"""
    if not GOOGLE_SCRIPT_URL or "https://" not in GOOGLE_SCRIPT_URL:
        return False
        
    payload = {"nick": nick, "topic": topic, "status": 1}
    
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
        return response.status_code == 200
    except Exception:
        return False

# --- ИНТЕРФЕЙС STREAMLIT ---

st.set_page_config(page_title="Урок с Чацким", page_icon="🎩")
st.title("🎩 Литературный экзамен с Чацким")
st.markdown("*«Свежо предание, а верится с трудом...»*)")

# Инициализация состояния
if "token" not in st.session_state:
    st.session_state.token = None
if "nick" not in st.session_state:
    st.session_state.nick = ""
if "current_topic_index" not in st.session_state:
    st.session_state.current_topic_index = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
# Флаг, чтобы не засчитывать тему дважды за один ответ
if "last_processed_index" not in st.session_state:
    st.session_state.last_processed_index = -1

# Шаг 1: Вход
if not st.session_state.nick:
    nick_input = st.text_input("Как вас зовут?", placeholder="Введите никнейм")
    if st.button("Начать экзамен"):
        if nick_input.strip():
            st.session_state.nick = nick_input.strip()
            st.session_state.chat_history.append({"role": "assistant", "content": f"Ах, {nick_input}! Добро пожаловать. Я — Чацкий. Готовы ли вы продемонстрировать свои знания? Начнем с первой темы."})
            st.rerun()
else:
    # Получение токена
    if not st.session_state.token:
        with st.spinner("Чацкий связывается со Сбером..."):
            st.session_state.token = get_gigachat_token()
            if not st.session_state.token:
                st.stop()

    # Чат
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Ваш ответ..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        current_topic = TOPICS[st.session_state.current_topic_index]
        context = f"Текущая тема: {current_topic}."
        
        with st.chat_message("assistant"):
            with st.spinner("Чацкий размышляет..."):
                response_text = ask_gigachat(st.session_state.token, prompt, context)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # --- УМНАЯ ПРОВЕРКА ---
        # Мы засчитываем тему ТОЛЬКО если:
        # 1. В ответе есть явная похвала (Браво, Отлично, Засчитано).
        # 2. В ответе НЕТ вопросительного знака (?) сразу после ключевых слов сомнений.
        # 3. Мы еще не засчитывали этот конкретный шаг (защита от дублей).
        
        positive_markers = ["браво", "отлично", "превосходно", "засчитано", "принято", "верно, следующая"]
        is_praise = any(marker in response_text.lower() for marker in positive_markers)
        
        # Важная проверка: если это вопрос ("Верно ли?"), то не засчитываем.
        # Простая эвристика: если есть "?" и нет явного "Засчитано/Браво", то скорее всего это вопрос.
        is_question = "?" in response_text and not any(word in response_text.lower() for word in ["засчитано", "браво", "принято"])

        if is_praise and not is_question and st.session_state.current_topic_index != st.session_state.last_processed_index:
            success = send_to_google_sheet(st.session_state.nick, current_topic)
            if success:
                st.success(f"✅ Тема «{current_topic}» зачтена и записана в журнал!")
            
            # Переход к следующей теме
            st.session_state.current_topic_index += 1
            st.session_state.last_processed_index = st.session_state.current_topic_index # Запоминаем, что шагнули дальше
            
            if st.session_state.current_topic_index < len(TOPICS):
                next_topic = TOPICS[st.session_state.current_topic_index]
                # Добавляем системное сообщение о переходе, чтобы пользователь видел новую тему
                transition_msg = f"---\n**Следующая тема:** {next_topic}. Что вы можете о ней сказать?"
                st.session_state.chat_history.append({"role": "assistant", "content": transition_msg})
            else:
                st.session_state.chat_history.append({"role": "assistant", "content": "🎉 Поздравляю! Курс окончен."})
            
            st.rerun()
