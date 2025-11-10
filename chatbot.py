import streamlit as st
import sqlite3
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import requests
from openai import OpenAI

# ========== LOAD ENVIRONMENT VARIABLES ==========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
# Initialize clients
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT,
                    messages TEXT,
                    timestamp TEXT,
                    model TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Check if model column exists, if not add it
    try:
        c.execute("SELECT model FROM chats LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE chats ADD COLUMN model TEXT")
    
    conn.commit()
    conn.close()

# ========== AUTH ==========
def login_user(username, password):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user

def register_user(username, password):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# ========== CHAT HISTORY ==========
def save_chat(user_id, title, messages, model):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("INSERT INTO chats (user_id, title, messages, timestamp, model) VALUES (?, ?, ?, ?, ?)",
              (user_id, title, json.dumps(messages), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), model))
    conn.commit()
    conn.close()

def load_chats(user_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    
    # Check if model column exists
    c.execute("PRAGMA table_info(chats)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'model' in columns:
        c.execute("SELECT id, title, messages, timestamp, model FROM chats WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
    else:
        # If model column doesn't exist, use default value
        c.execute("SELECT id, title, messages, timestamp, 'GPT-3.5' as model FROM chats WHERE user_id=? ORDER BY timestamp DESC", (user_id,))
    
    chats = c.fetchall()
    conn.close()
    return chats

def delete_chat(chat_id):
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("DELETE FROM chats WHERE id=?", (chat_id,))
    conn.commit()
    conn.close()

# ========== MODEL CALLS ==========
def call_gpt(messages):
    if not OPENAI_API_KEY:
        return "⚠️ OpenAI API key not configured"
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ GPT Error: {str(e)}"

def call_deepseek_free(messages):
    """DeepSeek via OpenRouter (Free)"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.app",
                "X-Title": "AI Chatbot"
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }),
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            error_msg = f"OpenRouter API Error: {response.status_code}"
            try:
                error_detail = response.json().get('error', {}).get('message', response.text)
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            return error_msg
           
    except Exception as e:
        return f"⚠️ DeepSeek Free error: {str(e)}"

def call_qwen(messages):
    """Qwen AI via OpenRouter"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {QWEN_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.app",
                "X-Title": "AI Chatbot"
            },
            data=json.dumps({
                "model": "qwen/qwen-2.5-coder-32b-instruct",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }),
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            error_msg = f"Qwen API Error: {response.status_code}"
            try:
                error_detail = response.json().get('error', {}).get('message', response.text)
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            return error_msg
           
    except Exception as e:
        return f"⚠️ Qwen AI error: {str(e)}"

def call_llama(messages):
    """Meta Llama 3.3 70B Instruct via OpenRouter"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {LLAMA_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.app",
                "X-Title": "AI Chatbot"
            },
            data=json.dumps({
                "model": "meta-llama/llama-3.3-70b-instruct",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }),
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            error_msg = f"Llama API Error: {response.status_code}"
            try:
                error_detail = response.json().get('error', {}).get('message', response.text)
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            return error_msg
           
    except Exception as e:
        return f"⚠️ Llama 3.3 error: {str(e)}"

def call_mistral(messages):
    """Mistral 7B Instruct via OpenRouter"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.app",
                "X-Title": "AI Chatbot"
            },
            data=json.dumps({
                "model": "mistralai/mistral-7b-instruct",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }),
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            error_msg = f"Mistral API Error: {response.status_code}"
            try:
                error_detail = response.json().get('error', {}).get('message', response.text)
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            return error_msg
           
    except Exception as e:
        return f"⚠️ Mistral error: {str(e)}"

def call_gemma(messages):
    """Google Gemma 3 27B via OpenRouter"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GEMMA_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://streamlit.app",
                "X-Title": "AI Chatbot"
            },
            data=json.dumps({
                "model": "google/gemma-3-27b-it",
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }),
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            error_msg = f"Gemma API Error: {response.status_code}"
            try:
                error_detail = response.json().get('error', {}).get('message', response.text)
                error_msg += f" - {error_detail}"
            except:
                error_msg += f" - {response.text}"
            return error_msg
           
    except Exception as e:
        return f"⚠️ Gemma error: {str(e)}"

# ========== UTILITIES ==========
def generate_chat_title(first_message):
    if not first_message:
        return "New Chat"
    msg = first_message.strip()
    return msg[:30] + ("..." if len(msg) > 30 else "")

def get_first_user_message(messages):
    """Extract the first user message for title generation"""
    for msg in messages:
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""

# ========== MAIN APP ==========
def main():
    st.set_page_config(
        page_title="AI Chatbot Pro", 
        page_icon="🤖", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Beautiful Custom CSS
    st.markdown("""
        <style>
        /* Main background */
        .main {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        /* Header styling */
        .main-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 1rem;
            color: white;
            text-align: center;
            margin-bottom: 2rem;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        /* Chat messages */
        .chat-message {
            padding: 1.5rem;
            border-radius: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            border: none;
            backdrop-filter: blur(10px);
        }
        
        .user-message {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-left: 6px solid #4F46E5;
        }
        
        .bot-message {
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            border-left: 6px solid #10B981;
        }
        
        /* Model badges */
        .model-badge {
            background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 0.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .free-badge {
            background: linear-gradient(135deg, #00B4DB 0%, #0083B0 100%);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 0.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .qwen-badge {
            background: linear-gradient(135deg, #9C27B0 0%, #673AB7 100%);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 0.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .llama-badge {
            background: linear-gradient(135deg, #FF9800 0%, #FF5722 100%);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 0.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .mistral-badge {
            background: linear-gradient(135deg, #FF4081 0%, #F50057 100%);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 0.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .gemma-badge {
            background: linear-gradient(135deg, #4285F4 0%, #34A853 100%);
            color: white;
            padding: 0.4rem 1rem;
            border-radius: 1rem;
            font-size: 0.8rem;
            font-weight: bold;
            margin-left: 0.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        /* Sidebar styling */
        .sidebar .sidebar-content {
            background: linear-gradient(180deg, #1a202c 0%, #2d3748 100%);
            color: white;
        }
        
        /* Buttons */
        .stButton>button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 0.75rem;
            padding: 0.75rem 1.5rem;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .stButton>button:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        }
        
        /* Input fields */
        .stTextInput>div>div>input, .stTextArea>div>div>textarea {
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid #E2E8F0;
            border-radius: 1rem;
            padding: 1rem;
            font-size: 1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }
        
        .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Select box */
        .stSelectbox>div>div>div {
            background: rgba(255, 255, 255, 0.95);
            border: 2px solid #E2E8F0;
            border-radius: 1rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }
        
        /* API test results */
        .api-test {
            padding: 1.2rem;
            border-radius: 1rem;
            margin: 0.5rem 0;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .api-success {
            background: linear-gradient(135deg, #D4EDDA 0%, #C3E6CB 100%);
            color: #155724;
            border: 2px solid #C3E6CB;
        }
        
        .api-error {
            background: linear-gradient(135deg, #F8D7DA 0%, #F5C6CB 100%);
            color: #721C24;
            border: 2px solid #F5C6CB;
        }
        
        /* Chat history items */
        .history-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            margin: 0.75rem 0;
            border-radius: 1rem;
            border-left: 5px solid #667eea;
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .history-item:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateX(8px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }
        
        .active-chat {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-left: 5px solid #FFD700;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
        }
        
        /* Model cards */
        .model-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
            padding: 1.5rem;
            border-radius: 1.5rem;
            border: 1px solid rgba(255,255,255,0.2);
            text-align: center;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            height: 180px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .model-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 35px rgba(0,0,0,0.15);
        }
        
        /* Welcome section */
        .welcome-section {
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
            padding: 3rem;
            border-radius: 2rem;
            border: 2px dashed rgba(102, 126, 234, 0.5);
            text-align: center;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        /* Grid layout for model cards */
        .model-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Header Section
    st.markdown("""
        <div class="main-header">
            <h1>🚀 Ultimate AI Chatbot</h1>
            <h3>Choose from 6 powerful AI assistants!</h3>
            <p>Premium GPT • Free DeepSeek • Advanced Qwen • Meta Llama • Mistral • Google Gemma</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialize database first
    init_db()
    
    # API Status with beautiful cards in 3x2 grid
    st.subheader("🎯 Model Status")
    
    # Create a 3x2 grid using columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
            <div class="model-card">
                <h3>🤖 GPT-3.5</h3>
                <p>Premium AI</p>
                <small>OpenAI</small>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Test GPT", key="test_gpt", use_container_width=True):
            test_result = call_gpt([{"role": "user", "content": "Say 'Hello' in one word."}])
            if "Error" not in test_result:
                st.markdown(f'<div class="api-test api-success">✅ GPT-3.5: Working! 🎉</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="api-test api-error">❌ GPT-3.5: {test_result}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="model-card">
                <h3>🐉 DeepSeek</h3>
                <p>Free & Powerful</p>
                <small>OpenRouter</small>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Test DeepSeek", key="test_deepseek", use_container_width=True):
            test_result = call_deepseek_free([{"role": "user", "content": "Say 'Hello' in one word."}])
            if "Error" not in test_result:
                st.markdown(f'<div class="api-test api-success">✅ DeepSeek: Working! 🎉</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="api-test api-error">❌ DeepSeek: {test_result}</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
            <div class="model-card">
                <h3>🚀 Qwen AI</h3>
                <p>Coding Specialist</p>
                <small>Alibaba</small>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Test Qwen", key="test_qwen", use_container_width=True):
            test_result = call_qwen([{"role": "user", "content": "Say 'Hello' in one word."}])
            if "Error" not in test_result:
                st.markdown(f'<div class="api-test api-success">✅ Qwen: Working! 🎉</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="api-test api-error">❌ Qwen: {test_result}</div>', unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    
    with col4:
        st.markdown("""
            <div class="model-card">
                <h3>🦙 Llama 3.3</h3>
                <p>70B Instruct</p>
                <small>Meta AI</small>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Test Llama", key="test_llama", use_container_width=True):
            test_result = call_llama([{"role": "user", "content": "Say 'Hello' in one word."}])
            if "Error" not in test_result:
                st.markdown(f'<div class="api-test api-success">✅ Llama: Working! 🎉</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="api-test api-error">❌ Llama: {test_result}</div>', unsafe_allow_html=True)
    
    with col5:
        st.markdown("""
            <div class="model-card">
                <h3>💨 Mistral</h3>
                <p>7B Instruct</p>
                <small>Mistral AI</small>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Test Mistral", key="test_mistral", use_container_width=True):
            test_result = call_mistral([{"role": "user", "content": "Say 'Hello' in one word."}])
            if "Error" not in test_result:
                st.markdown(f'<div class="api-test api-success">✅ Mistral: Working! 🎉</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="api-test api-error">❌ Mistral: {test_result}</div>', unsafe_allow_html=True)
    
    with col6:
        st.markdown("""
            <div class="model-card">
                <h3>💎 Gemma 3</h3>
                <p>27B Model</p>
                <small>Google</small>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Test Gemma", key="test_gemma", use_container_width=True):
            test_result = call_gemma([{"role": "user", "content": "Say 'Hello' in one word."}])
            if "Error" not in test_result:
                st.markdown(f'<div class="api-test api-success">✅ Gemma: Working! 🎉</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="api-test api-error">❌ Gemma: {test_result}</div>', unsafe_allow_html=True)

    # State management
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_model" not in st.session_state:
        st.session_state.current_model = "GPT-3.5"
    if "user" not in st.session_state:
        st.session_state.user = None
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None

    # --- Login Section ---
    if not st.session_state.logged_in:
        st.markdown("---")
        st.subheader("🔐 Login to Your Account")
        
        tab1, tab2 = st.tabs(["🚪 Login", "📝 Register"])
        
        with tab1:
            login_username = st.text_input("👤 Username", key="login_username")
            login_password = st.text_input("🔒 Password", type="password", key="login_password")
            
            if st.button("🎯 Login", key="login_btn", use_container_width=True):
                if login_username and login_password:
                    user = login_user(login_username, login_password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user = user
                        st.session_state.messages = []
                        st.success(f"✅ Welcome back, {login_username}! 🎉")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.error("⚠️ Please enter both username and password")
        
        with tab2:
            reg_username = st.text_input("👤 Choose Username", key="reg_username")
            reg_password = st.text_input("🔒 Choose Password", type="password", key="reg_password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password", key="confirm_password")
            
            if st.button("✨ Create Account", key="reg_btn", use_container_width=True):
                if reg_username and reg_password:
                    if reg_password == confirm_password:
                        if len(reg_password) >= 6:
                            if register_user(reg_username, reg_password):
                                st.success("🎉 Account created successfully! Please login.")
                            else:
                                st.error("❌ Username already exists")
                        else:
                            st.error("⚠️ Password must be at least 6 characters")
                    else:
                        st.error("❌ Passwords do not match")
                else:
                    st.error("⚠️ Please fill all fields")
        return

    # --- Main Chat UI ---
    with st.sidebar:
        st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       border-radius: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 8px 25px rgba(0,0,0,0.1);'>
                <h3>👋 Welcome, {st.session_state.user[1]}!</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # Action Buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆕 New Chat", use_container_width=True):
                # Save current chat if it has messages
                if st.session_state.messages:
                    first_message = get_first_user_message(st.session_state.messages)
                    chat_title = generate_chat_title(first_message)
                    save_chat(
                        st.session_state.user[0],
                        chat_title,
                        st.session_state.messages,
                        st.session_state.current_model
                    )
                # Reset for new chat
                st.session_state.messages = []
                st.session_state.current_chat_id = None
                st.rerun()
        
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                # Save current chat before logout
                if st.session_state.messages:
                    first_message = get_first_user_message(st.session_state.messages)
                    chat_title = generate_chat_title(first_message)
                    save_chat(
                        st.session_state.user[0],
                        chat_title,
                        st.session_state.messages,
                        st.session_state.current_model
                    )
                st.session_state.logged_in = False
                st.session_state.messages = []
                st.session_state.user = None
                st.rerun()
        
        st.markdown("---")
        st.subheader("📚 Chat History")
        
        chats = load_chats(st.session_state.user[0])
        
        if chats:
            for chat_id, title, messages, timestamp, model_used in chats:
                # Create a container for the chat item
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        # Determine if this is the active chat
                        is_active = st.session_state.current_chat_id == chat_id
                        chat_class = "history-item active-chat" if is_active else "history-item"
                        
                        st.markdown(f"""
                            <div class="{chat_class}">
                                <strong>{'📍' if is_active else '💬'} {title}</strong><br>
                                <small>{model_used} • {timestamp[:16]}</small>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("Load Chat", key=f"load_{chat_id}"):
                            st.session_state.messages = json.loads(messages)
                            st.session_state.current_model = model_used
                            st.session_state.current_chat_id = chat_id
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️", key=f"delete_{chat_id}"):
                            delete_chat(chat_id)
                            if st.session_state.current_chat_id == chat_id:
                                st.session_state.messages = []
                                st.session_state.current_chat_id = None
                            st.rerun()
        else:
            st.info("🌟 No chat history yet. Start a conversation!")
        
        # Clear all chats
        if chats and st.button("🗑️ Clear All History", use_container_width=True):
            for chat_id, _, _, _, _ in chats:
                delete_chat(chat_id)
            st.session_state.messages = []
            st.session_state.current_chat_id = None
            st.rerun()

    # --- Chat Window ---
    st.subheader("💬 Chat Conversation")
    
    # Current model indicator
    current_model = st.session_state.current_model
    if current_model == "GPT-3.5":
        badge_class = "model-badge"
        badge_text = "Premium"
    elif current_model == "DeepSeek Free":
        badge_class = "free-badge"
        badge_text = "Free"
    elif current_model == "Qwen AI":
        badge_class = "qwen-badge"
        badge_text = "Coding"
    elif current_model == "Llama 3.3":
        badge_class = "llama-badge"
        badge_text = "70B Instruct"
    elif current_model == "Mistral 7B":
        badge_class = "mistral-badge"
        badge_text = "7B Instruct"
    else:  # Gemma 3
        badge_class = "gemma-badge"
        badge_text = "27B Model"
    
    st.markdown(f"""
        <div style='display: flex; align-items: center; margin-bottom: 1.5rem;'>
            <h4 style='margin: 0;'>Active Model: </h4>
            <span class='{badge_class}'>{current_model} ({badge_text})</span>
        </div>
    """, unsafe_allow_html=True)
    
    # Display messages
    chat_container = st.container()
    with chat_container:
        if st.session_state.messages:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    st.markdown(
                        f"""
                        <div class="chat-message user-message">
                            <strong>🧑 You:</strong><br>
                            {msg['content']}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="chat-message bot-message">
                            <strong>🤖 Assistant:</strong><br>
                            {msg['content']}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
        else:
            st.markdown("""
                <div class="welcome-section">
                    <h3>🌟 Welcome to Ultimate AI Chatbot! 🎉</h3>
                    <p>Start a conversation by typing a message below!</p>
                    <p>💡 <strong>Choose from 6 powerful AI models:</strong></p>
                    <p>• 🤖 GPT-3.5 (Premium OpenAI)</p>
                    <p>• 🐉 DeepSeek (Free & Powerful)</p>
                    <p>• 🚀 Qwen AI (Advanced Coding)</p>
                    <p>• 🦙 Llama 3.3 (70B Instruct)</p>
                    <p>• 💨 Mistral (7B Instruct)</p>
                    <p>• 💎 Gemma 3 (Google 27B)</p>
                </div>
            """, unsafe_allow_html=True)

    # --- Input Section ---
    st.markdown("---")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        user_input = st.text_area(
            "💭 Your message:",
            placeholder="Type your message here... Ask me anything!",
            key="user_input",
            height=120
        )
    
    with col2:
        model_choice = st.selectbox(
            "🤖 Choose AI:",
            ["GPT-3.5", "DeepSeek Free", "Qwen AI", "Llama 3.3", "Mistral 7B", "Gemma 3"],
            index=0
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        send_button = st.button("🚀 Send Message", use_container_width=True, type="primary")

    if send_button and user_input.strip():
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})
        
        # Prepare messages for API (include conversation history)
        api_messages = [{"role": "system", "content": "You are a helpful and intelligent assistant. Provide clear, accurate, and engaging responses."}]
        api_messages.extend(st.session_state.messages)
        
        # Call appropriate model
        with st.spinner(f"🤖 {model_choice} is thinking..."):
            if model_choice == "GPT-3.5":
                bot_reply = call_gpt(api_messages)
            elif model_choice == "DeepSeek Free":
                bot_reply = call_deepseek_free(api_messages)
            elif model_choice == "Qwen AI":
                bot_reply = call_qwen(api_messages)
            elif model_choice == "Llama 3.3":
                bot_reply = call_llama(api_messages)
            elif model_choice == "Mistral 7B":
                bot_reply = call_mistral(api_messages)
            else:  # Gemma 3
                bot_reply = call_gemma(api_messages)
        
        # Add bot response
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        
        # Update current model
        st.session_state.current_model = model_choice
        
        # Save chat (only save when we have a complete exchange)
        if len(st.session_state.messages) >= 2:
            first_message = get_first_user_message(st.session_state.messages)
            chat_title = generate_chat_title(first_message)
            save_chat(
                st.session_state.user[0],
                chat_title,
                st.session_state.messages,
                model_choice
            )
        
        st.rerun()

if __name__ == "__main__":
    main()