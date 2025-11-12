import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI
import bcrypt

# ========== CONFIGURATION ==========
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")  # from Render
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

MODELS = {
    "GPT-3.5 Turbo": {"provider": "openai", "model": "gpt-3.5-turbo", "icon": "🚀"},
    "Llama 3.1 8B": {"provider": "huggingface", "model": "meta-llama/Llama-3.1-8B-Instruct:novita", "icon": "🦙"},
    "DeepSeek V3.2": {"provider": "huggingface", "model": "deepseek-ai/DeepSeek-V3.2-Exp:novita", "icon": "🔍"},
    "Qwen Coder 30B": {"provider": "huggingface", "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct:nebius", "icon": "💻"},
    "SmolLM3 3B": {"provider": "huggingface", "model": "HuggingFaceTB/SmolLM3-3B:hf-inference", "icon": "⚡"},
    "GLM-4.6": {"provider": "huggingface", "model": "zai-org/GLM-4.6:novita", "icon": "🌟"}
}

# ========== DATABASE SETUP ==========
def get_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize database tables"""
    conn = get_connection()
    if conn is None:
        return
        
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                title TEXT,
                messages JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prompt_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                prompt TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    except Exception as e:
        st.error(f"Database initialization error: {e}")
    finally:
        conn.close()

def register_user(username, password):
    """Register a new user"""
    conn = get_connection()
    if conn is None:
        return False
        
    try:
        cur = conn.cursor()
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_pw))
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        return False
    except Exception as e:
        conn.rollback()
        st.error(f"Registration error: {e}")
        return False
    finally:
        conn.close()

def login_user(username, password):
    """Login user and return user data"""
    conn = get_connection()
    if conn is None:
        return None
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
            return user
        return None
    except Exception as e:
        st.error(f"Login error: {e}")
        return None
    finally:
        conn.close()

def save_chat(user_id, title, messages, model):
    """Save chat to database"""
    conn = get_connection()
    if conn is None:
        return
        
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chats (user_id, title, messages, model)
            VALUES (%s, %s, %s, %s)
        """, (user_id, title, json.dumps(messages), model))
        conn.commit()
    except Exception as e:
        st.error(f"Error saving chat: {e}")
        conn.rollback()
    finally:
        conn.close()

def load_chats(user_id):
    """Load user's chats from database"""
    conn = get_connection()
    if conn is None:
        return []
        
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, messages, timestamp, model 
            FROM chats 
            WHERE user_id = %s 
            ORDER BY timestamp DESC
        """, (user_id,))
        chats = cur.fetchall()
        return chats
    except Exception as e:
        st.error(f"Error loading chats: {e}")
        return []
    finally:
        conn.close()

def delete_chat(chat_id):
    """Delete a specific chat"""
    conn = get_connection()
    if conn is None:
        return
        
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM chats WHERE id = %s", (chat_id,))
        conn.commit()
    except Exception as e:
        st.error(f"Error deleting chat: {e}")
        conn.rollback()
    finally:
        conn.close()

def delete_all_chats(user_id):
    """Delete all chats for a user"""
    conn = get_connection()
    if conn is None:
        return
        
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM chats WHERE user_id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        st.error(f"Error deleting all chats: {e}")
        conn.rollback()
    finally:
        conn.close()

def save_prompt_to_history(user_id, prompt):
    """Save prompt to history"""
    conn = get_connection()
    if conn is None:
        return
        
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO prompt_history (user_id, prompt) VALUES (%s, %s)", (user_id, prompt))
        conn.commit()
    except Exception as e:
        st.error(f"Error saving prompt: {e}")
        conn.rollback()
    finally:
        conn.close()

def load_prompt_history(user_id, limit=20):
    """Load prompt history for a user"""
    conn = get_connection()
    if conn is None:
        return []
        
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT prompt FROM prompt_history 
            WHERE user_id = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """, (user_id, limit))
        prompts = [row['prompt'] for row in cur.fetchall()]
        return prompts
    except Exception as e:
        st.error(f"Error loading prompt history: {e}")
        return []
    finally:
        conn.close()

def delete_all_prompt_history(user_id):
    """Delete all prompt history for a user"""
    conn = get_connection()
    if conn is None:
        return
        
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM prompt_history WHERE user_id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        st.error(f"Error deleting prompt history: {e}")
        conn.rollback()
    finally:
        conn.close()

# ========== MODEL CALLS ==========
def call_huggingface(messages, model_name):
    try:
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"messages": messages, "model": MODELS[model_name]["model"], "max_tokens": 1000, "temperature": 0.7}
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {str(e)}"

def call_gpt(messages):
    try:
        response = openai_client.chat.completions.create(model="gpt-3.5-turbo", messages=messages, max_tokens=1000, temperature=0.7)
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def call_model(messages, model_name):
    if MODELS[model_name]["provider"] == "openai":
        return call_gpt(messages)
    else:
        return call_huggingface(messages, model_name)

def get_model_display_info(model_used):
    """Safely get model display information with error handling"""
    if not model_used:
        return "🤖", "Unknown"
   
    try:
        # Try to get from MODELS first
        if model_used in MODELS:
            return MODELS[model_used]["icon"], model_used.split()[0]
       
        # If model_used is a full model name from database, find matching key
        for model_key, model_info in MODELS.items():
            if model_info["model"] == model_used:
                return model_info["icon"], model_key.split()[0]
       
        # Fallback: try to extract first word safely
        if isinstance(model_used, str):
            return "🤖", model_used.split()[0] if model_used.split() else "Unknown"
        else:
            return "🤖", "Unknown"
           
    except (AttributeError, IndexError):
        return "🤖", "Unknown"

def handle_up_arrow():
    """Handle up arrow key press for navigating to previous prompts"""
    current_text = st.session_state.current_input
    if current_text and current_text.strip() and current_text not in st.session_state.prompt_history:
        st.session_state.temp_unsaved_text = current_text
   
    if st.session_state.current_history_index < len(st.session_state.prompt_history) - 1:
        st.session_state.current_history_index += 1
        st.session_state.current_input = st.session_state.prompt_history[st.session_state.current_history_index]
    elif st.session_state.current_history_index == -1:
        st.session_state.current_history_index = 0
        st.session_state.current_input = st.session_state.prompt_history[0]
   
    st.session_state.input_key += 1
    st.rerun()

def handle_down_arrow():
    """Handle down arrow key press for navigating to newer prompts"""
    if st.session_state.current_history_index > 0:
        st.session_state.current_history_index -= 1
        st.session_state.current_input = st.session_state.prompt_history[st.session_state.current_history_index]
    elif st.session_state.current_history_index == 0:
        st.session_state.current_history_index = -1
        st.session_state.current_input = getattr(st.session_state, 'temp_unsaved_text', '')
        if hasattr(st.session_state, 'temp_unsaved_text'):
            del st.session_state.temp_unsaved_text
   
    st.session_state.input_key += 1
    st.rerun()

# ========== MAIN APP ==========
def main():
    st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="wide")
   
    st.markdown("""
        <style>
        .main {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);}
        .stButton>button {border-radius: 0.75rem;}
        .chat-message {padding: 1.5rem; border-radius: 1rem; margin-bottom: 1rem;}
        .user-message {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;}
        .bot-message {background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white;}
        .sidebar-chat-item {padding: 0.5rem; border-radius: 0.5rem; margin-bottom: 0.25rem; cursor: pointer;}
        .sidebar-chat-item:hover {background-color: rgba(255,255,255,0.1);}
        .sidebar-chat-item.active {background-color: rgba(255,255,255,0.2); border-left: 3px solid #667eea;}
        .delete-btn {background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white; border: none; border-radius: 0.5rem; padding: 0.25rem 0.5rem; font-size: 0.75rem;}
        .clear-all-btn {background: linear-gradient(135deg, #ff6b6b 0%, #c23616 100%); color: white; border: none; border-radius: 0.5rem; padding: 0.5rem; margin-top: 1rem;}
       
        /* Hide the arrow buttons */
        .arrow-buttons {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    init_db()
   
    # Session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_model" not in st.session_state:
        st.session_state.current_model = "Llama 3.1 8B"
    if "user" not in st.session_state:
        st.session_state.user = None
    if "prompt_history" not in st.session_state:
        st.session_state.prompt_history = []
    if "current_history_index" not in st.session_state:
        st.session_state.current_history_index = -1
    if "current_input" not in st.session_state:
        st.session_state.current_input = ""
    if "input_key" not in st.session_state:
        st.session_state.input_key = 0
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
    if "sidebar_state" not in st.session_state:
        st.session_state.sidebar_state = "chats"
    if "show_clear_all_confirm" not in st.session_state:
        st.session_state.show_clear_all_confirm = False
    if "clear_all_type" not in st.session_state:
        st.session_state.clear_all_type = None

    # Login
    if not st.session_state.logged_in:
        st.title("🔐 Login")
        tab1, tab2 = st.tabs(["Login", "Register"])
       
        with tab1:
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if user := login_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.session_state.prompt_history = load_prompt_history(user["id"])
                    st.rerun()
                else:
                    st.error("Invalid credentials")
       
        with tab2:
            new_user = st.text_input("New Username")
            new_pass = st.text_input("New Password", type="password")
            if st.button("Register"):
                if register_user(new_user, new_pass):
                    st.success("Account created! Please login.")
                else:
                    st.error("Username exists")
        return

    # Main Chat Interface
    with st.sidebar:
        st.write(f"👋 Welcome, {st.session_state.user['username']}!")
       
        # Sidebar tabs for better organization
        sidebar_tab1, sidebar_tab2 = st.tabs(["💬 Chats", "📝 Prompts"])
       
        with sidebar_tab1:
            # New Chat Button
            if st.button("🆕 New Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.current_history_index = -1
                st.session_state.current_input = ""
                st.session_state.input_key += 1
                st.session_state.current_chat_id = None
                st.rerun()
           
            st.markdown("---")
           
            # Chat History Section with improved UI
            st.subheader("📚 Your Chats")
            chats = load_chats(st.session_state.user["id"])
           
            if not chats:
                st.info("No chat history yet. Start a new conversation!")
            else:
                for chat in chats:
                    chat_id, title, messages, timestamp, model_used = chat["id"], chat["title"], chat["messages"], chat["timestamp"], chat["model"]
                    col1, col2 = st.columns([4, 1])
                   
                    with col1:
                        # Highlight current active chat
                        is_active = st.session_state.current_chat_id == chat_id
                        active_class = "active" if is_active else ""
                       
                        # Safely get model icon and name
                        model_icon, model_name = get_model_display_info(model_used)
                       
                        chat_display = f"""
                        <div class="sidebar-chat-item {active_class}" onclick="this.closest('form').querySelector('button').click()">
                            <div style="font-weight: bold; font-size: 0.9rem;">{title}</div>
                            <div style="font-size: 0.7rem; opacity: 0.8;">
                                {timestamp.strftime('%Y-%m-%d') if timestamp else 'Unknown'} • {model_icon} {model_name}
                            </div>
                        </div>
                        """
                        st.markdown(chat_display, unsafe_allow_html=True)
                       
                        if st.button(f"Load {title}", key=f"load_{chat_id}", type="secondary", use_container_width=True):
                            st.session_state.messages = json.loads(messages)
                            st.session_state.current_chat_id = chat_id
                            st.rerun()
                   
                    with col2:
                        if st.button("🗑️", key=f"delete_{chat_id}", help="Delete this chat"):
                            delete_chat(chat_id)
                            if st.session_state.current_chat_id == chat_id:
                                st.session_state.messages = []
                                st.session_state.current_chat_id = None
                            st.rerun()
               
                # Clear All Chats Button
                st.markdown("---")
                if not st.session_state.show_clear_all_confirm or st.session_state.clear_all_type != "chats":
                    if st.button("🗑️ Clear All Chats", use_container_width=True, type="secondary"):
                        st.session_state.show_clear_all_confirm = True
                        st.session_state.clear_all_type = "chats"
                        st.rerun()
                else:
                    st.warning("Are you sure you want to delete ALL chats?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes", use_container_width=True):
                            delete_all_chats(st.session_state.user["id"])
                            st.session_state.messages = []
                            st.session_state.current_chat_id = None
                            st.session_state.show_clear_all_confirm = False
                            st.session_state.clear_all_type = None
                            st.success("All chats cleared!")
                            st.rerun()
                    with col2:
                        if st.button("❌ No", use_container_width=True):
                            st.session_state.show_clear_all_confirm = False
                            st.session_state.clear_all_type = None
                            st.rerun()
       
        with sidebar_tab2:
            st.subheader("📋 Recent Prompts")
            prompt_history = load_prompt_history(st.session_state.user["id"], limit=20)
           
            if not prompt_history:
                st.info("No prompt history yet.")
            else:
                for i, prompt in enumerate(prompt_history):
                    if st.button(f"💬 {prompt[:50]}...", key=f"prompt_{i}", use_container_width=True):
                        st.session_state.current_input = prompt
                        st.session_state.input_key += 1
                        st.rerun()
               
                # Clear All Prompts Button
                st.markdown("---")
                if not st.session_state.show_clear_all_confirm or st.session_state.clear_all_type != "prompts":
                    if st.button("🗑️ Clear All Prompts", use_container_width=True, type="secondary"):
                        st.session_state.show_clear_all_confirm = True
                        st.session_state.clear_all_type = "prompts"
                        st.rerun()
                else:
                    st.warning("Are you sure you want to delete ALL prompt history?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes", use_container_width=True):
                            delete_all_prompt_history(st.session_state.user["id"])
                            st.session_state.prompt_history = []
                            st.session_state.show_clear_all_confirm = False
                            st.session_state.clear_all_type = None
                            st.success("All prompt history cleared!")
                            st.rerun()
                    with col2:
                        if st.button("❌ No", use_container_width=True):
                            st.session_state.show_clear_all_confirm = False
                            st.session_state.clear_all_type = None
                            st.rerun()
       
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.session_state.messages = []
            st.session_state.prompt_history = []
            st.rerun()

    # Main chat area
    col_main1, col_main2 = st.columns([3, 1])
   
    with col_main1:
        st.subheader(f"{MODELS[st.session_state.current_model]['icon']} Chat with {st.session_state.current_model}")
   
    with col_main2:
        selected_model = st.selectbox(
            "Model:",
            list(MODELS.keys()),
            index=list(MODELS.keys()).index(st.session_state.current_model),
            key="model_selector",
            label_visibility="collapsed"
        )
       
        if selected_model != st.session_state.current_model:
            st.session_state.current_model = selected_model
            st.rerun()

    # Chat messages display
    if not st.session_state.messages:
        st.info("💡 Start a new conversation by typing a message below!")
    else:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-message user-message"><strong>You:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message bot-message"><strong>AI:</strong> {msg["content"]}</div>', unsafe_allow_html=True)

    # Input section
    st.markdown("---")
    col1, col2 = st.columns([4, 1])
   
    with col1:
        user_input = st.text_area(
            "Your message:",
            height=100,
            placeholder=f"Ask {st.session_state.current_model} anything... (Press ↑ for previous prompts)",
            value=st.session_state.current_input,
            key=f"user_input_{st.session_state.input_key}",
            label_visibility="collapsed"
        )
   
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        send_button = st.button("🚀 Send", use_container_width=True)
       
        # Clear chat button
        if st.session_state.messages:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.messages = []
                st.session_state.current_chat_id = None
                st.rerun()

    # Hidden arrow key buttons (invisible but functional)
    with st.container():
        st.markdown('<div class="arrow-buttons">', unsafe_allow_html=True)
        col_up, col_down = st.columns(2)
        with col_up:
            up_pressed = st.button("⬆️", key="up_arrow_btn")
        with col_down:
            down_pressed = st.button("⬇️", key="down_arrow_btn")
        st.markdown('</div>', unsafe_allow_html=True)

    # Handle arrow key navigation
    if up_pressed and st.session_state.prompt_history:
        handle_up_arrow()
   
    elif down_pressed and st.session_state.prompt_history and st.session_state.current_history_index >= 0:
        handle_down_arrow()

    # JavaScript to capture arrow keys and click the hidden buttons
    st.components.v1.html("""
    <script>
    document.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowUp' && document.activeElement.tagName === 'TEXTAREA') {
            e.preventDefault();
            const buttons = document.querySelectorAll('[data-testid="baseButton-secondary"]');
            if (buttons.length > 0) {
                buttons[0].click();
            }
        }
        else if (e.key === 'ArrowDown' && document.activeElement.tagName === 'TEXTAREA') {
            e.preventDefault();
            const buttons = document.querySelectorAll('[data-testid="baseButton-secondary"]');
            if (buttons.length > 1) {
                buttons[1].click();
            }
        }
    });
    </script>
    """, height=0)

    if send_button and user_input.strip():
        # Save prompt to history
        save_prompt_to_history(st.session_state.user["id"], user_input)
        st.session_state.prompt_history = load_prompt_history(st.session_state.user["id"])
        st.session_state.current_history_index = -1
        st.session_state.current_input = ""
        st.session_state.input_key += 1
       
        st.session_state.messages.append({"role": "user", "content": user_input})
       
        with st.spinner(f"{MODELS[st.session_state.current_model]['icon']} {st.session_state.current_model} is thinking..."):
            response = call_model([{"role": "system", "content": "You are a helpful assistant."}] + st.session_state.messages, st.session_state.current_model)
       
        st.session_state.messages.append({"role": "assistant", "content": response})
       
        # Save chat with improved title generation
        chat_title = user_input[:50] + "..." if len(user_input) > 50 else user_input
        if not chat_title.strip():
            chat_title = "New Chat"
           
        save_chat(st.session_state.user["id"], chat_title, st.session_state.messages, st.session_state.current_model)
        st.rerun()

if __name__ == "__main__":
    main()