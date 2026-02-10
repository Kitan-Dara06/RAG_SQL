# SQL_RAG - Universal SQL Agent

A production-ready SQL query generator using Retrieval-Augmented Generation (RAG) with smart schema retrieval and multi-database support.

## Features

- 🤖 **Natural Language to SQL**: Ask questions in plain English
- 🔌 **Multi-Database Support**: SQLite, PostgreSQL, MySQL
- 🧠 **Smart Retrieval**: Foreign key analysis for better context
- 🎯 **High Accuracy**: AST validation and query critic
- 🌐 **Web UI**: Streamlit interface for easy access
- 🔒 **Secure**: Session-isolated, AST validation, error sanitization

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up Environment
```bash
cp .env.example .env
# Edit .env and add your OPENAI_KEY
```

### 3. Run the Web UI
```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### 4. Connect & Query
1. Select your database type (SQLite/PostgreSQL/MySQL)
2. Enter connection details
3. Click "Connect"
4. Click "Index Schema"
5. Start asking questions!

## Example Questions

- "How many users are in the database?"
- "What is the total revenue from all orders?"
- "Which customer spent the most money?"
- "Show me the top 5 products by sales"

## Architecture

```
User Question
    ↓
Smart Retrieval (Vector Search + Foreign Keys)
    ↓
SQL Generation (GPT-4o-mini)
    ↓
AST Validation (sqlglot)
    ↓
Query Execution
    ↓
Answer Synthesis
```

## Project Structure

```
SQL_RAG/
├── app.py                 # Streamlit web UI
├── generator2.py          # Main RAG agent (production)
├── generator.py           # Simple RAG agent (baseline)
├── config.py             # Configuration management
├── logger.py             # Logging system
├── sql_rag.py            # Schema extraction
├── indexer.py            # Schema indexing
├── validators.py         # SQL validation
├── exceptions.py         # Custom exceptions
├── rate_limiter.py       # API rate limiting
├── tests/                # Test files
└── requirements.txt      # Dependencies
```

## Configuration

Edit `.env` file:

```bash
# OpenAI
OPENAI_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini

# Database (example for PostgreSQL)
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database
DB_USER=your_user
DB_PASSWORD=your_password

# ChromaDB
CHROMA_DB_PATH=./repo_db
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Logging
LOG_LEVEL=INFO
LOG_FILE=sql_rag.log
```

## API Usage

```python
from sqlalchemy import create_engine
from generator2 import run_agent

# Create database engine
engine = create_engine("postgresql://user:pass@localhost/db")

# Ask a question
result = run_agent("How many users?", engine)

if result and result['success']:
    print(result['data'])
```

## Development

### Run Tests
```bash
cd tests
python test_sql_rag.py
python test_postgres.py
```

### Index Schema
```bash
python indexer.py
```

## Security Features

- **AST Validation**: Blocks modification operations (INSERT, UPDATE, DELETE)
- **Error Sanitization**: Prevents information leakage
- **Session Isolation**: Multi-tenant capable
- **Rate Limiting**: Prevents API abuse

## Technologies

- **OpenAI GPT-4o-mini**: SQL generation
- **ChromaDB**: Vector database for schema search
- **SQLAlchemy**: Database abstraction
- **sqlglot**: SQL parsing and validation
- **Streamlit**: Web UI
- **Sentence Transformers**: Text embeddings

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
