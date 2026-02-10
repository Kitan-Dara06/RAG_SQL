"""
SQL_RAG Generator - Basic Top-K Retrieval Approach

This module implements a simple RAG (Retrieval-Augmented Generation) pipeline for SQL generation:
1. **Top-K Vector Search**: Uses ChromaDB to find the K most relevant table schemas
2. **Simple Context**: Passes top-K schemas directly to the LLM without relationship analysis
3. **Basic Retry**: Retries failed queries up to MAX_RETRIES times with error feedback

Differences from generator2.py:
- generator.py: Simple top-K retrieval (faster, less context-aware)
- generator2.py: Smart retrieval with foreign key analysis (slower, more accurate)
"""
import re
import sqlite3

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

from src.utils.config import (
    OPENAI_KEY,
    DB_PATH,
    CHROMA_DB_PATH,
    OPENAI_MODEL,
    EMBEDDING_MODEL,
    MAX_RETRIES,
)
from src.utils.logger import get_logger
from src.utils.exceptions import SQLExecutionError, InvalidInputError

# Initialize logger
logger = get_logger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_KEY)

# Initialize ChromaDB with sentence transformer embeddings
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = chroma_client.get_collection(
    name="schema_index", embedding_function=sentence_transformer_ef
)

logger.info("Generator initialized with model=%s, db=%s", OPENAI_MODEL, DB_PATH)


def get_relevant_schema(question):
    """
    Retrieve top-K most relevant table schemas using vector similarity search.
    
    This uses a simple top-K approach without considering table relationships.
    
    Args:
        question: User's natural language question
    
    Returns:
        List of relevant CREATE TABLE statements
    """
    logger.debug("Looking up schema for question: '%s'", question)
    results = collection.query(query_texts=[question], n_results=3)
    schemas = results["documents"][0]
    logger.info("Retrieved %d relevant schemas", len(schemas))
    return schemas


def generate_sql(question, schemas):
    """
    Generate SQL query using OpenAI with provided schema context.
    
    Args:
        question: User's natural language question
        schemas: List of relevant CREATE TABLE statements
    
    Returns:
        Generated SQL query string
    """
    context_sql = "\n\n".join(schemas)

    logger.debug("Generating SQL with %d schemas in context", len(schemas))
    system_prompt = f"""
    You are an expert SQLite Data Analyst.
    Your task is to generate a valid SQL query to answer the user's question.

        ### INSTRUCTIONS
        1. Use ONLY the provided schema. Do not assume other tables exist.
        2. The database is SQLite. Use compatible syntax (e.g., standard JOINs).
        3. Return ONLY the raw SQL query.
           - NO markdown formatting (like ```sql).
           - NO explanation.

        ### SCHEMA CONTEXT
        {context_sql}
    """
    user_prompt = f"Question: {question}"
    response = client.chat.completions.create(
        model=OPENAI_MODEL, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0.1
    )
    sql = response.choices[0].message.content.strip()
    logger.debug("Generated SQL: %s", sql[:100])
    return sql


def execute_sql(sql_query):
    """
    Execute SQL query with safety checks and markdown cleanup.
    
    Security Features:
    - Blocks all modification operations (DROP, DELETE, UPDATE, INSERT)
    - Cleans markdown code block formatting
    - Returns sanitized error messages
    
    Args:
        sql_query: SQL query string (may contain markdown)
    
    Returns:
        dict with success status, columns, data, or error message
    """
    # Enhanced markdown cleanup using regex
    # First, handle escaped newlines (\\n) by converting to actual newlines
    clean_sql = sql_query.replace('\\n', '\n')
    
    # Remove markdown code blocks with various formats:
    # - ```sql\nSELECT...\n```
    # - ```\nSELECT...\n```
    # - ```sql SELECT...```
    clean_sql = re.sub(r'```(?:sql)?\s*\n?', '', clean_sql)  # Remove opening ```sql or ```
    clean_sql = re.sub(r'\n?```\s*', '', clean_sql)  # Remove closing ```
    clean_sql = clean_sql.strip()
    
    logger.debug("Executing SQL (cleaned): %s", clean_sql[:100])
    
    # Security: Block forbidden operations
    forbidden_words = ["DROP", "DELETE", "UPDATE", "INSERT"]
    if any(word in clean_sql.upper() for word in forbidden_words):
        error_msg = "Safety Alert: Modification operations are not allowed. Only SELECT queries permitted."
        logger.warning("Blocked forbidden operation in SQL: %s", clean_sql[:50])
        return {
            "success": False,
            "error": error_msg,
        }
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(clean_sql)
        rows = cursor.fetchall()

        column_names = [description[0] for description in cursor.description]
        conn.close()
        logger.info("SQL executed successfully, returned %d rows", len(rows))
        return {"success": True, "columns": column_names, "data": rows}

    except Exception as e:
        conn.close()
        # Log full error internally, return sanitized message
        logger.error("SQL execution failed: %s", str(e), exc_info=True)
        return {
            "success": False,
            "error": "Query execution failed. Please check your query syntax.",
        }


def run_agent(question):
    """
    Main RAG agent with retry logic.
    
    Process:
    1. Retrieve relevant schemas (top-K vector search)
    2. Generate SQL query
    3. Execute and validate
    4. If error, retry with error feedback (up to MAX_RETRIES)
    
    Args:
        question: User's natural language question
    
    Returns:
        Execution result dict or None if all retries failed
    """
    logger.info("Agent starting for question: '%s'", question)
    schemas = get_relevant_schema(question)
    context_sql = "\n\n".join(schemas)

    messages = [
        {
            "role": "system",
            "content": f"""
             You are a SQL Expert.
             Schema:
             {context_sql}

             Rules:
             1. Use ONLY the provided schema.
             2. SQLite syntax.
             3. Return ONLY raw SQL. No markdown.
             """,
        },
        {"role": "user", "content": question},
    ]
    
    for attempt in range(MAX_RETRIES):
        logger.info("Attempt %d/%d", attempt + 1, MAX_RETRIES)

        response = client.chat.completions.create(
            model=OPENAI_MODEL, messages=messages, temperature=0.1
        )
        sql = response.choices[0].message.content.strip()
        logger.debug("Generated SQL (attempt %d): %s", attempt + 1, sql[:100])
        
        result = execute_sql(sql)
        if result["success"]:
            logger.info("Agent succeeded on attempt %d", attempt + 1)
            return result
        else:
            logger.warning("Attempt %d failed: %s", attempt + 1, result['error'])
            messages.append({"role": "assistant", "content": sql})
            messages.append(
                {
                    "role": "user",
                    "content": f"That SQL failed with error: {result['error']}. Fix it.",
                }
            )
    
    logger.error("Agent failed after %d retries", MAX_RETRIES)
    return None


if __name__ == "__main__":
    # Run the Agent
    output = run_agent(
        "What is the full name of the user who bought the most expensive item?"
    )

    if output:
        print("\n FINAL DATA:")
        print(output["columns"])
        for row in output["data"]:
            print(row)
