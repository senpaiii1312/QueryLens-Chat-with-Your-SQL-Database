import streamlit as st
from pathlib import Path
from langchain_classic.agents import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_classic.agents.agent_types import AgentType
from langchain_classic.callbacks import StreamlitCallbackHandler
from langchain_classic.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq

st.set_page_config(page_title="QueryLens | Chat with SQL", page_icon="🗃️", layout="wide")

# UI styling only
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #f7f9fc 0%, #eef3f9 100%);
    }
    .block-container {
        max-width: 1100px;
        padding-top: 2.2rem;
        padding-bottom: 2.5rem;
    }
    .hero {
        padding: 1.5rem 1.7rem;
        border: 1px solid #e0e7f0;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.92);
        box-shadow: 0 8px 24px rgba(35, 55, 80, 0.06);
        margin-bottom: 1.2rem;
    }
    .hero-kicker {
        color: #55749a;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .hero-title {
        color: #172b4d;
        font-size: 2rem;
        font-weight: 750;
        line-height: 1.2;
        margin: 0;
    }
    .hero-subtitle {
        color: #62748a;
        font-size: 1rem;
        margin-top: 0.55rem;
        margin-bottom: 0;
    }
    [data-testid="stSidebar"] {
        background: #f0f4f9;
        border-right: 1px solid #e0e7f0;
    }
    [data-testid="stSidebar"] .block-container {
        padding-top: 1.8rem;
    }
    div[data-testid="stChatMessage"] {
        border: 1px solid #e3eaf3;
        border-radius: 14px;
        padding: 0.75rem 1rem;
        background: rgba(255, 255, 255, 0.8);
        margin-bottom: 0.65rem;
    }
    .stChatInput textarea {
        border-radius: 12px;
    }
    div[data-testid="stButton"] > button {
        border-radius: 10px;
        border: 1px solid #d6e0ec;
        font-weight: 600;
    }
    .small-note {
        color: #73839a;
        font-size: 0.82rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="hero-kicker">Database assistant</div>
    <p class="hero-title">🗃️ QueryLens</p>
    <p class="hero-subtitle">Ask questions in plain English and explore your SQL database through chat.</p>
</div>
""", unsafe_allow_html=True)

LOCALDB = "USE_LOCALDB"
MYSQL = "USE_MYSQL"

radio_opt = ["Use SQLLite 3 Database- Student.db", "Connect to you MySQL Database"]

st.sidebar.title("⚙️ Connection settings")
st.sidebar.caption("Choose a database and enter the required credentials.")
selected_opt = st.sidebar.radio(label="Database source", options=radio_opt)

if radio_opt.index(selected_opt) == 1:
    db_uri = MYSQL
    mysql_host = st.sidebar.text_input("MySQL host")
    mysql_user = st.sidebar.text_input("MySQL user")
    mysql_password = st.sidebar.text_input("MySQL password", type="password")
    mysql_db = st.sidebar.text_input("MySQL database")
else:
    db_uri = LOCALDB
    st.sidebar.info("Using the local student.db file.")

st.sidebar.divider()
st.sidebar.subheader("🔑 API access")
api_key = st.sidebar.text_input(label="Groq API key", type="password")
st.sidebar.markdown(
    '<p class="small-note">Your API key is used to connect to the language model.</p>',
    unsafe_allow_html=True
)

if not db_uri:
    st.info("Please enter the database info and URI")

if not api_key:
    st.info("Please provide the Groq API Key")

llm = ChatGroq(groq_api_key=api_key, model_name='qwen/qwen3.8-27b', streaming=True)

@st.cache_resource(ttl="2h")
def configure_db(db_uri, mysql_host=None, mysql_user=None, mysql_password=None, mysql_db=None):
    if db_uri == LOCALDB:
        dbfilepath = (Path(__file__).parent / "student.db").absolute()
        print(dbfilepath)
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri == MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MySQL connection details.")
            st.stop()
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))

if db_uri == MYSQL:
    db = configure_db(db_uri, mysql_host, mysql_user, mysql_password, mysql_db)
else:
    db = configure_db(db_uri)

# Toolkit
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

if "messages" not in st.session_state or st.sidebar.button("Clear chat history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "Hi! Ask me a question about your database."}]

st.markdown("### 💬 Chat with your database")
st.caption("Try questions like “Show all students” or “Which student has the highest marks?”")

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_query = st.chat_input(placeholder="Ask a question about your database...")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback = StreamlitCallbackHandler(st.container())
        response = agent.run(user_query, callbacks=[streamlit_callback])
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.write(response)
