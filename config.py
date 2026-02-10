"""
Centralized configuration management for SQL_RAG project.
Loads all settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================
# Required Configuration
# ============================================
OPENAI_KEY = os.getenv("OPENAI_KEY")
if not OPENAI_KEY:
    raise ValueError("OPENAI_KEY environment variable is required. Please set it in your .env file.")

# ============================================
# Database Configuration
# ============================================
DB_PATH = os.getenv("DB_PATH", "enterprise.db")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./repo_db")

# For SQLAlchemy connection string
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "sqlite":
    DB_CONNECTION_STRING = f"sqlite:///{DB_PATH}"
elif DB_TYPE == "postgresql":
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "test_enterprise")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_TYPE == "mysql":
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "test_enterprise")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_CONNECTION_STRING = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    raise ValueError(f"Unsupported DB_TYPE: {DB_TYPE}. Use 'sqlite', 'postgresql', or 'mysql'.")

# ============================================
# Model Configuration
# ============================================
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ============================================
# Rate Limiting
# ============================================
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))

# ============================================
# Logging Configuration
# ============================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "sql_rag.log")

# Validate log level
VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
if LOG_LEVEL not in VALID_LOG_LEVELS:
    raise ValueError(f"Invalid LOG_LEVEL: {LOG_LEVEL}. Must be one of {VALID_LOG_LEVELS}")

# ============================================
# Security & Validation
# ============================================
MAX_QUESTION_LENGTH = int(os.getenv("MAX_QUESTION_LENGTH", "500"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# ============================================
# Export all configuration
# ============================================
__all__ = [
    "OPENAI_KEY",
    "DB_PATH",
    "CHROMA_DB_PATH",
    "DB_TYPE",
    "DB_CONNECTION_STRING",
    "OPENAI_MODEL",
    "EMBEDDING_MODEL",
    "RATE_LIMIT_PER_MINUTE",
    "LOG_LEVEL",
    "LOG_FILE",
    "MAX_QUESTION_LENGTH",
    "MAX_RETRIES",
]


def get_config_summary():
    """Return a summary of current configuration (safe for logging)."""
    return {
        "db_type": DB_TYPE,
        "db_path": DB_PATH if DB_TYPE == "sqlite" else f"{DB_TYPE} database",
        "openai_model": OPENAI_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "rate_limit": RATE_LIMIT_PER_MINUTE,
        "log_level": LOG_LEVEL,
        "max_retries": MAX_RETRIES,
    }


if __name__ == "__main__":
    # Test configuration loading
    print("Configuration loaded successfully!")
    print("\nConfiguration Summary:")
    for key, value in get_config_summary().items():
        print(f"  {key}: {value}")
