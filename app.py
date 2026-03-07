import streamlit as st
import requests
import os
import base64

# --- НАСТРОЙКИ ---
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
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    system_prompt = (
        f"Ты — декабрьский наставник. Тема экзамена: '{current_topic}'. "
        "Твоя задача: оценить ответ ученика. "
        "1. Если ответ ВЕРНЫЙ: Похвали эмоционально ('Браво!', 'Отлично!', 'Именно так!', 'Верно!'). "
        "   НЕ предлагай следующую тему. НЕ пиши 'переходим дальше'. Просто вырази одобрение и закончи фразу. "
        "2. Если ответ НЕВЕРНЫЙ или слишком короткий: Укажи на ошибку мягко и ПОПРОСИ ответить еще раз по этой же теме. "
        "Будь краток, мудр и поддерживающ."
    )
    
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

# --- ИНИЦИАЛИЗАЦИЯ СЕССИИ ---
def init_session():
    defaults = {
        "token": None,
        "nick": "",
        "completed_topics": [],
        "current_topic": None,
        "chat_history": [],
        "waiting_for_next": False,
        "topic_scores": {},
        "total_score": 0,
        "target_score": 5,
        "exam_finished": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- ВИЗУАЛЬНЫЕ КОМПОНЕНТЫ ---

def render_topic_button(topic, status, score=0):
    """Кнопка темы с цветовой индикацией и баллами"""
    colors = {
        "completed": ("#28a745", "✅", "white"),
        "active": ("#007bff", "🎯", "white"),
        "locked": ("#6c757d", "⚪", "white"),
        "failed": ("#dc3545", "🔴", "white")
    }
    bg, emoji, text_color = colors.get(status, colors["locked"])
    score_text = f" <small style='opacity:0.8'>({score} бал.)</small>" if score > 0 else ""
    
    return f"""
    <div style="
        background: {bg};
        color: {text_color};
        padding: 10px 15px;
        border-radius: 8px;
        margin: 4px 0;
        font-weight: 500;
        border: 2px solid transparent;
        transition: all 0.2s;
    " onmouseover="this.style.borderColor='#fff'" onmouseout="this.style.borderColor='transparent'">
        {emoji} {topic}{score_text}
    </div>
    """

# --- ИНТЕРФЕЙС ---

st.set_page_config(page_title="Декабрьский наставник", page_icon="📚", layout="wide")

# Кастомные стили
st.markdown("""
<style>
    .success-box {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 10px 15px;
        border-radius: 4px;
        margin: 10px 0;
    }
    .error-box {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 10px 15px;
        border-radius: 4px;
        margin: 10px 0;
    }
    .score-banner {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .login-container {
        max-width: 400px;
        margin: 50px auto;
        padding: 30px;
        background: #f8f9fa;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .stTextInput > div > div > input {
        border-radius: 10px;
    }
    .stButton > button {
        border-radius: 10px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# === ЗАГОЛОВОК ===
st.title("📚 Декабрьский наставник")
st.markdown("*«Ученье — свет, а неученье — тьма...»*")

init_session()

# === ВХОД (вертикально: никнейм → кнопка) ===
if not st.session_state.nick:
    st.markdown("""
    <div class="login-container">
        <h3 style="text-align: center; margin-bottom: 20px;">👋 Добро пожаловать!</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col = st.columns(1)[0]
    with col:
        nick_input = st.text_input("Как вас зовут?", placeholder="Введите ваш никнейм", key="nick_input", label_visibility="visible")
        start_button = st.button("Начать экзамен 🚀", use_container_width=True, type="primary")
        
        if start_button:
            if nick_input.strip():
                st.session_state.nick = nick_input.strip()
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": f"Здравствуйте, {nick_input}! Я — ваш декабрьский наставник. Наберите **5 баллов** за правильные ответы, чтобы успешно сдать экзамен! Выберите тему в панели слева."
                })
                st.rerun()
            else:
                st.warning("⚠️ Пожалуйста, введите ваше имя!")
    st.stop()

# === ПОЛУЧЕНИЕ ТОКЕНА ===
if not st.session_state.token:
    with st.spinner("🔐 Устанавливаю связь..."):
        st.session_state.token = get_gigachat_token()
        if not st.session_state.token:
            st.stop()

# === БОКОВАЯ ПАНЕЛЬ ===
with st.sidebar:
    # 🎯 БАННЕР СЧЁТА
    st.markdown(f"""
    <div class="score-banner">
        ⭐ Ваш счёт: {st.session_state.total_score}/{st.session_state.target_score}
    </div>
    """, unsafe_allow_html=True)
    
    progress = min(st.session_state.total_score / st.session_state.target_score, 1.0)
    st.progress(progress)
    
    if st.session_state.total_score >= st.session_state.target_score:
        st.success("🏆 Экзамен сдан! Браво!")
    
    st.divider()
    st.subheader("📚 Темы")
    st.markdown(f"**Ученик:** {st.session_state.nick}")
    
    for i, topic in enumerate(TOPICS, 1):
        score = st.session_state.topic_scores.get(topic, 0)
        
        if topic in st.session_state.completed_topics:
            status = "completed"
        elif topic == st.session_state.current_topic:
            status = "active"
        elif score > 0:
            status = "failed"
        else:
            status = "locked"
        
        st.markdown(render_topic_button(topic, status, score), unsafe_allow_html=True)
        
        if st.button(f"{'✅' if status=='completed' else '🎯' if status=='active' else '📖'} {topic}", 
                    key=f"btn_{i}", 
                    use_container_width=True,
                    disabled=(status=="completed" and st.session_state.exam_finished)):
            if topic != st.session_state.current_topic:
                st.session_state.current_topic = topic
                st.session_state.waiting_for_next = False
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"«{topic}» — отличная тема! Что вы можете сказать об этом произведении?"
                })
                st.rerun()

    st.divider()
    
    if st.session_state.topic_scores:
        st.markdown("### 📊 Статистика:")
        for topic in TOPICS:
            score = st.session_state.topic_scores.get(topic, 0)
            if score > 0:
                status_icon = "✅" if topic in st.session_state.completed_topics else "🔄"
                st.markdown(f"{status_icon} **{topic}**: {score} балл.")

# === ОСНОВНОЙ ЧАТ ===
if st.session_state.exam_finished:
    st.balloons()
    st.success(f"""
    ## 🎉 Поздравляю, {st.session_state.nick}!
    
    Вы набрали **{st.session_state.total_score} баллов** и блестяще сдали экзамен!
    
    > *«Познание — путь к мудрости...»*
    
    Хочется начать заново? Обновите страницу! 🔄
    """)
    st.stop()

if not st.session_state.current_topic:
    st.info("👈 **Выберите тему в панели слева**, чтобы начать диалог с наставником!")
    
    st.markdown(f"""
    <div class="success-box">
        <strong>🎯 Как набрать баллы:</strong><br>
        • +1 балл за каждый верный ответ<br>
        • Нужно 5 баллов для "победы" в экзамене
    </div>
    
    <div class="error-box">
        <strong>💡 Подсказка:</strong><br>
        • Отвечайте подробно, наставник ценит развёрнутые ответы!<br>
        • Если ответ неверный — он подскажет, но балл не начислит
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🎨 Легенда:")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown("🟢 Пройдено")
    with col2: st.markdown("🔵 Активна")
    with col3: st.markdown("🔴 Были ошибки")
    with col4: st.markdown("⚪ Не начата")
    
else:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    current_topic = st.session_state.current_topic
    current_score = st.session_state.topic_scores.get(current_topic, 0)
    
    if current_score > 0:
        st.caption(f"📊 По этой теме у вас: {current_score} балл. Нужно набрать 5 для зачёта.")
    
    placeholder_text = (
        "Напишите 'дальше' для выбора новой темы..." 
        if st.session_state.waiting_for_next 
        else f"Ваш ответ по теме «{current_topic}»..."
    )
    
    if prompt := st.chat_input(placeholder_text):
        if st.session_state.waiting_for_next:
            lower_prompt = prompt.lower()
            if any(x in lower_prompt for x in ["дальше", "следующ", "продолж", "ок", "готов", "да", "новый"]):
                st.session_state.waiting_for_next = False
                st.session_state.current_topic = None
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "Превосходно! Выберите следующую тему в панели слева — и продолжим!"
                })
                st.rerun()
            else:
                st.session_state.waiting_for_next = False
        
        if not st.session_state.waiting_for_next:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("🎭 Наставник размышляет..."):
                    response_text = ask_gigachat(st.session_state.token, prompt, current_topic)
                    st.write(response_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response_text})

            lower_response = response_text.lower()
            positive_words = ["браво", "отлично", "верно", "правильно", "превосходно", "засчитано", "именно так", "согласен", "хорошо", "прекрасно"]
            
            has_praise = any(word in lower_response for word in positive_words)
            has_question_mark = "?" in response_text
            has_negative = any(word in lower_response for word in ["неверно", "ошибка", "попробуй еще", "снова", "не совсем", "нет", "увы", "ошибаетесь"])

            if has_praise and not has_question_mark and not has_negative:
                old_score = st.session_state.topic_scores.get(current_topic, 0)
                new_score = old_score + 1
                st.session_state.topic_scores[current_topic] = new_score
                st.session_state.total_score += 1
                
                if new_score >= 5 and current_topic not in st.session_state.completed_topics:
                    st.session_state.completed_topics.append(current_topic)
                    send_to_google_sheet(st.session_state.nick, current_topic)
                    st.markdown(f"""
                    <div class="success-box">
                        <strong>🎉 Тема «{current_topic}» пройдена!</strong><br>
                        Вы набрали 5 баллов и тема записана в журнал!
                    </div>
                    """, unsafe_allow_html=True)
                
                if st.session_state.total_score >= st.session_state.target_score:
                    st.session_state.exam_finished = True
                    st.markdown(f"""
                    <div class="success-box">
                        <strong>🏆 Экзамен сдан!</strong><br>
                        Вы набрали {st.session_state.total_score} баллов!
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.success(f"✅ +1 балл! Ваш счёт: {st.session_state.total_score}/{st.session_state.target_score}")
                
                st.session_state.waiting_for_next = True
                st.rerun()
            
            elif has_negative or has_question_mark:
                st.markdown(f"""
                <div class="error-box">
                    <strong>💡 Наставник рекомендует...</strong><br>
                    Попробуйте ответить ещё раз — балл будет начислен за верный ответ!
                </div>
                """, unsafe_allow_html=True)
