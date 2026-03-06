import streamlit as st
import requests
import json
import os
import base64
from datetime import datetime

# --- НАСТРОЙКИ ---
# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ НА GOOGLE SCRIPT (из шага с Apps Script)
# Если оставите как есть, запись в таблицу не сработает!
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
    """Получает токен доступа к GigaChat с правильным кодированием Base64"""
    if not GIGACHAT_CLIENT_ID or not GIGACHAT_CLIENT_SECRET:
        st.error("❌ Ошибка: Ключи API не найдены в настройках Railway!")
        st.info("Проверьте переменные GIGACHAT_CLIENT_ID и GIGACHAT_CLIENT_SECRET во вкладке Variables.")
        return None
    
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    # 1. Склеиваем ID и Secret через двоеточие: "ID:Secret"
    credentials = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
    
    # 2. Кодируем полученную строку в Base64 (как требует документация Сбера)
    try:
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    except Exception as e:
        st.error(f"Ошибка кодирования ключей: {e}")
        return None
    
    # 3. Формируем заголовок Authorization
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "RqUID": "00000000-0000-0000-0000-000000000000",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    data = {"scope": "GIGACHAT_API_PERS"}
    
    try:
        # Отправляем запрос (verify=False нужен для самоподписанных сертификатов Сбера)
        response = requests.post(url, headers=headers, data=data, verify=False)
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            # Показываем точную ошибку от Сбера
            error_text = response.text
            st.error(f"❌ Сбер отверг ключи (код {response.status_code}): {error_text}")
            st.warning("Проверьте, нет ли пробелов в ключах в настройках Railway и правильно ли выбраны ID/Secret.")
            return None
            
    except Exception as e:
        st.error(f"❌ Ошибка соединения с сервером Сбера: {e}")
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
        "Ты — Александр Андреевич Чацкий из комедии 'Горе от ума'. "
        "Ты строгий, но справедливый учитель литературы. "
        "Твоя задача: задавать вопросы по русской классике, проверять знания ученика и кратко комментировать ответы. "
        "Если ответ верный — похвали кратко (используй слова 'верно', 'браво', 'отлично'). "
        "Если нет — укажи на ошибку с иронией, но подскажи верный путь. "
        "Не пиши длинные тексты, общайся живо."
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
    if not GOOGLE_SCRIPT_URL or GOOGLE_SCRIPT_URL == "ВАША_ССЫЛКА_НА_GOOGLE_SCRIPT":
        st.warning("⚠️ Ссылка на Google Script не настроена в коде!")
        return False
        
    payload = {
        "nick": nick,
        "topic": topic,
        "status": 1
    }
    
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
        # Google Apps Script иногда возвращает редирект или специфичный ответ, считаем успехом любой 200
        if response.status_code == 200:
            return True
        else:
            st.error(f"Ошибка записи в таблицу: {response.text}")
            return False
    except Exception as e:
        st.error(f"Ошибка соединения с Google Таблицей: {e}")
        return False

# --- ИНТЕРФЕЙС STREAMLIT ---

st.set_page_config(page_title="Урок с Чацким", page_icon="🎩")

st.title("🎩 Литературный экзамен с Чацким")
st.markdown("*«Свежо предание, а верится с трудом...»*)")

# Инициализация состояния сессии
if "token" not in st.session_state:
    st.session_state.token = None
if "nick" not in st.session_state:
    st.session_state.nick = ""
if "current_topic_index" not in st.session_state:
    st.session_state.current_topic_index = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Шаг 1: Вход пользователя
if not st.session_state.nick:
    nick_input = st.text_input("Как вас зовут, сударь/сударыня?", placeholder="Введите ваш никнейм")
    if st.button("Начать экзамен"):
        if nick_input.strip():
            st.session_state.nick = nick_input.strip()
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": f"Ах, {nick_input}! Добро пожаловать. Я — Чацкий. Готовы ли вы продемонстрировать свои знания русской словесности? Начнем с первой темы."
            })
            st.rerun()
        else:
            st.warning("Назовитесь, прежде чем войти в класс!")

else:
    # Получение токена при первом запуске сессии
    if not st.session_state.token:
        with st.spinner("Чацкий связывается со Сбером..."):
            st.session_state.token = get_gigachat_token()
            if not st.session_state.token:
                st.stop() # Останавливаем выполнение, если токена нет

    # Отображение истории чата
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Поле ввода ответа
    if prompt := st.chat_input("Ваш ответ..."):
        # Добавляем сообщение пользователя
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Генерируем ответ Чацкого
        current_topic = TOPICS[st.session_state.current_topic_index]
        context = f"Текущая тема экзамена: {current_topic}. Если ученик ответил правильно на вопрос по этой теме, считай тему пройденной."
        
        with st.chat_message("assistant"):
            with st.spinner("Чацкий размышляет..."):
                response_text = ask_gigachat(st.session_state.token, prompt, context)
                st.write(response_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # Логика проверки: ищем ключевые слова похвалы в ответе ИИ
        positive_words = ["верно", "правильно", "браво", "отлично", "превосходно", "засчитано", "именно так", "совершенно верно"]
        if any(word in response_text.lower() for word in positive_words):
            success = send_to_google_sheet(st.session_state.nick, current_topic)
            if success:
                st.success(f"✅ Тема «{current_topic}» зачтена и записана в журнал!")
                
                # Переход к следующей теме
                st.session_state.current_topic_index += 1
                
                if st.session_state.current_topic_index < len(TOPICS):
                    next_topic = TOPICS[st.session_state.current_topic_index]
                    follow_up = f"Превосходно. Следующая тема: **{next_topic}**. Что вы можете о ней сказать?"
                else:
                    follow_up = "🎉 Поздравляю! Вы прошли весь курс. Можете быть свободны, сударь!"
                
                st.session_state.chat_history.append({"role": "assistant", "content": follow_up})
                st.rerun()
