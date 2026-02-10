"""
SQL_RAG Package Setup
"""
from setuptools import setup, find_packages

setup(
    name="sql_rag",
    version="1.0.0",
    description="Universal SQL Agent with RAG and multi-database support",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "sqlalchemy>=2.0.0",
        "chromadb>=0.4.0",
        "streamlit>=1.28.0",
        "sqlglot>=20.0.0",
        "sentence-transformers>=2.2.0",
        "python-dotenv>=1.0.0",
        "psycopg2-binary>=2.9.0",
        "pymysql>=1.1.0",
    ],
    python_requires=">=3.8",
)
