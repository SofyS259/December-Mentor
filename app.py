import streamlit as st
import requests
import os
import base64

# --- НАСТРОЙКИ ---
# ВСТАВЬТЕ СЮДА ВАШУ ССЫЛКУ НА GOOGLE SCRIPT (с https:// и /exec)
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

def ask_gigachat(token, user_message, current_topic, is_correct_guess=False):
    """
    Генерирует ответ Чацкого.
    Если is_correct_guess=True, мы говорим ему, что ответ верный, чтобы он просто похвалил.
    """
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Промпт изменен: Чацкий ТОЛЬКО реагирует на текущий ответ.
    # Ему ЗАПРЕЩЕНО предлагать следующую тему или прощаться.
    system_prompt = (
        f"Ты — Александр Андреевич Чацкий из Горе от ума. Ты должен скопировать манеру речи Чацкого. Тема экзамена: '{current_topic}'. "
        "Твоя задача: оценить ответ ученика. "
        "1. Если ответ ВЕРНЫЙ: Похвали эмоционально ('Браво!', 'Отлично!', 'Именно так!', 'Верно!'). "
        "   НЕ предлагай следующую тему. НЕ пиши 'переходим дальше'. Просто вырази одобрение и закончи фразу. "
        "2. Если ответ НЕВЕРНЫЙ или слишком короткий: Покритикуй с иронией, укажи на ошибку и ПОПРОСИ ответить еще раз по этой же теме. "
        "Будь краток, жив и эмоционален."
    )
    
    # Если код уже решил, что ответ верный, мы даем это знать Чацкому, чтобы он точно похвалил
    user_context = ""
    if is_correct_guess:
        user_context = "(Система подсказывает: ответ ученика верный, но ты об этом не знай, просто оцени его содержание)."

    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_context} Ученик говорит: {user_message}"}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Ошибка: {response.text}"
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

st.set_page_config(page_title="Урок с Чацким", page_icon="🎩")
st.title("🎩 Литературный экзамен с Чацким")
st.markdown("*«Свежо предание, а верится с трудом...»*)")

if "token" not in st.session_state:
    st.session_state.token = None
if "nick" not in st.session_state:
    st.session_state.nick = ""
if "current_topic_index" not in st.session_state:
    st.session_state.current_topic_index = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "waiting_for_next" not in st.session_state:
    st.session_state.waiting_for_next = False # Флаг: ждем ли мы команду "дальше"

# Вход
if not st.session_state.nick:
    nick_input = st.text_input("Как вас зовут?", placeholder="Никнейм")
    if st.button("Начать"):
        if nick_input.strip():
            st.session_state.nick = nick_input.strip()
            st.session_state.chat_history.append({"role": "assistant", "content": f"Ах, {nick_input}! Я — Чацкий. Готовы к экзамену? Первая тема: **{TOPICS[0]}**. Что скажете?"})
            st.rerun()
else:
    if not st.session_state.token:
        with st.spinner("Связь со Сбером..."):
            st.session_state.token = get_gigachat_token()
            if not st.session_state.token:
                st.stop()

    # Отображение чата
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Логика ввода
    # Если мы ждем команду "дальше", подсказываем это в поле ввода
    placeholder_text = "Напишите 'дальше' или ответ по новой теме..." if st.session_state.waiting_for_next else "Ваш ответ..."
    
    if prompt := st.chat_input(placeholder_text):
        # Если мы в режиме ожидания следующей темы
        if st.session_state.waiting_for_next:
            # Проверяем, хочет ли пользователь идти дальше
            lower_prompt = prompt.lower()
            if any(x in lower_prompt for x in ["дальше", "следующ", "продолж", "ок", "готов", "да"]):
                # Переходим к следующей теме официально
                st.session_state.current_topic_index += 1
                st.session_state.waiting_for_next = False
                
                if st.session_state.current_topic_index < len(TOPICS):
                    next_topic = TOPICS[st.session_state.current_topic_index]
                    msg = f"Отлично. Следующая тема: **{next_topic}**. Что вы о ней знаете?"
                    st.session_state.chat_history.append({"role": "assistant", "content": msg})
                    st.rerun()
                else:
                    st.session_state.chat_history.append({"role": "assistant", "content": "🎉 Поздравляю! Вы прошли весь курс. Экзамен окончен."})
                    st.rerun()
            else:
                # Если написал что-то другое, пока игнорируем или просим подтвердить
                st.session_state.chat_history.append({"role": "assistant", "content": "Вы написали что-то непонятное. Напишите 'дальше', если готовы к следующей теме, или задайте свой вопрос."})
                st.rerun()
        
        else:
            # Обычный режим: отвечаем на вопрос по текущей теме
            current_topic = TOPICS[st.session_state.current_topic_index]
            
            # 1. Сначала добавляем сообщение пользователя
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)

            # 2. Анализируем ответ САМИ (без помощи ИИ для решения)
            # Ключевые слова для зачета (можно расширять)
            positive_words = ["браво", "отлично", "верно", "правильно", "превосходно", "засчитано", "именно так", "согласен", "хорошо"]
            
            # Хитрость: Мы попросим ИИ оценить ответ, но не будем слепо верить его тексту перехода.
            # Мы сами решим, был ли ответ хорошим, основываясь на ТОНЕ ответа ИИ.
            # Но чтобы не усложнять, давайте использовать простой триггер:
            # Если в ответе ИИ есть явная похвала И нет вопроса в конце -> считаем верным.
            
            # Получаем ответ от Чацкого
            with st.chat_message("assistant"):
                with st.spinner("Чацкий думает..."):
                    response_text = ask_gigachat(st.session_state.token, prompt, current_topic)
                    st.write(response_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response_text})

            # 3. ПРИНИМАЕМ РЕШЕНИЕ КОДОМ
            lower_response = response_text.lower()
            
            # Условия зачета:
            # 1. Есть слово похвалы.
            # 2. НЕТ вопросительного знака (значит, это не вопрос "Верно ли?").
            # 3. НЕТ слов "попробуй еще", "неверно", "ошибка".
            
            has_praise = any(word in lower_response for word in positive_words)
            has_question_mark = "?" in response_text
            has_negative = any(word in lower_response for word in ["неверно", "ошибка", "попробуй еще", "снова", "не совсем", "нет"])

            if has_praise and not has_question_mark and not has_negative:
                # ЗАЧЕТ!
                success = send_to_google_sheet(st.session_state.nick, current_topic)
                if success:
                    st.success(f"✅ Тема «{current_topic}» записана в журнал!")
                
                # Включаем режим ожидания
                st.session_state.waiting_for_next = True
                
                # Добавляем системную подсказку в чат (невидимую для ИИ, видимую пользователю как контекст)
                st.info("💡 Тема пройдена! Напишите **«дальше»** в поле ниже, чтобы перейти к следующей книге.")
                # Примечание: st.info не сохраняется в истории чата навсегда, но видно сейчас. 
                # Чтобы закрепить мысль, можно дописать сообщение от ассистента, но аккуратно.
                # Лучше просто оставить флаг waiting_for_next=True, который изменит подсказку в поле ввода.
                
                st.rerun()
            # Если не зачет - ничего не делаем, чат ждет нового ответа по той же теме.
