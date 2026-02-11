"""
Configuration management for SQL_RAG.
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Try to import streamlit for cloud deployment
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False

# OpenAI Configuration
# Try Streamlit secrets first (for cloud deployment), then environment variables
if HAS_STREAMLIT:
    try:
        OPENAI_KEY = st.secrets.get("OPENAI_KEY", os.getenv("OPENAI_KEY", ""))
        OPENAI_MODEL = st.secrets.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    except:
        OPENAI_KEY = os.getenv("OPENAI_KEY", "")
        OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
else:
    OPENAI_KEY = os.getenv("OPENAI_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Database Configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "enterprise")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Construct connection string based on DB_TYPE
if DB_TYPE == "sqlite":
    DB_CONNECTION_STRING = f"sqlite:///{os.getenv('DB_PATH', 'enterprise.db')}"
elif DB_TYPE == "postgresql":
    DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_TYPE == "mysql":
    DB_CONNECTION_STRING = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    raise ValueError(f"Unsupported database type: {DB_TYPE}")

# ChromaDB Configuration
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./repo_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "sql_rag.log")

# Rate Limiting Configuration
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Query Configuration
MAX_QUESTION_LENGTH = int(os.getenv("MAX_QUESTION_LENGTH", "500"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
