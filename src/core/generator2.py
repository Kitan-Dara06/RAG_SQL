"""
SQL_RAG Generator2 - Smart Retrieval with Foreign Key Analysis

This module implements an advanced RAG (Retrieval-Augmented Generation) pipeline:
1. **Smart Retrieval**: Analyzes foreign key relationships to include related tables
2. **AST Validation**: Uses sqlglot for syntax validation and security checks
3. **Query Critic**: Separate AI agent analyzes failures and provides feedback
4. **Dialect-Aware**: Automatically detects database type and adjusts prompts

Differences from generator.py:
- generator.py: Simple top-K retrieval (faster, less context-aware)
- generator2.py: Smart retrieval with foreign key analysis (slower, more accurate)

This is the MAIN production code for the SQL_RAG project.
"""
import re
import sqlite3

import chromadb
import sqlglot
from chromadb.utils import embedding_functions
from openai import OpenAI
from sqlalchemy import create_engine, text
from sqlglot import exp

from src.utils.config import (
    OPENAI_KEY,
    DB_CONNECTION_STRING,
    DB_TYPE,
    CHROMA_DB_PATH,
    OPENAI_MODEL,
    EMBEDDING_MODEL,
    MAX_RETRIES,
)
from src.utils.logger import get_logger
from src.utils.exceptions import SQLExecutionError, DatabaseConnectionError, SchemaExtractionError
from src.validation.validators import sanitize_error_message

# Initialize logger
logger = get_logger(__name__)

# Default database engine (for backward compatibility)
# For SaaS/multi-tenant use, pass engine directly to functions
_default_engine = None

def get_default_engine():
    """Get or create default engine from config."""
    global _default_engine
    if _default_engine is None:
        try:
            _default_engine = create_engine(DB_CONNECTION_STRING)
            logger.info("Default database engine initialized: %s", DB_TYPE)
        except Exception as e:
            logger.error("Failed to initialize default database engine: %s", str(e))
            raise DatabaseConnectionError(f"Failed to connect to {DB_TYPE} database", DB_TYPE)
    return _default_engine

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_KEY)

# Initialize ChromaDB with sentence transformer embeddings
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

def get_collection():
    """Get or create the schema_index collection."""
    try:
        return chroma_client.get_collection(
            name="schema_index",
            embedding_function=sentence_transformer_ef,
        )
    except Exception as e:
        logger.warning("Collection not found, creating new one: %s", str(e))
        return chroma_client.create_collection(
            name="schema_index",
            embedding_function=sentence_transformer_ef,
        )

logger.info("Generator2 initialized with model=%s, embedding=%s", 
           OPENAI_MODEL, EMBEDDING_MODEL)


def get_table_neighbours(table_name):
    """
    Find related tables via foreign key relationships.
    
    This enables smart retrieval by including tables that are referenced
    by or reference the given table, improving context for complex queries.
    
    Args:
        table_name: Name of the table to find neighbors for
    
    Returns:
        List of related table names
    """
    logger.debug("Finding neighbors for table: %s", table_name)
    
    try:
        # Note: This uses SQLite-specific PRAGMA. For other databases, use INFORMATION_SCHEMA
        conn = sqlite3.connect("enterprise.db")
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA foreign_key_list({table_name});")
        relations = cursor.fetchall()
        conn.close()
        
        # The 'table' column is index 2 in the result tuple
        related_tables = [r[2] for r in relations]
        logger.debug("Found %d neighbors for %s: %s", len(related_tables), table_name, related_tables)
        return related_tables
        
    except Exception as e:
        logger.error("Failed to get neighbors for %s: %s", table_name, str(e))
        return []


def smart_retrieval(question, collection=None):
    """
    Retrieve schemas using smart retrieval with foreign key expansion.
    
    Process:
    1. Vector search finds top-K most relevant tables
    2. For each table, find related tables via foreign keys
    3. Include all related tables in the context
    
    This provides better context for queries involving JOINs.
    
    Args:
        question: User's natural language question
        collection: ChromaDB collection (optional, uses default if not provided)
    
    Returns:
        List of relevant CREATE TABLE statements (expanded with related tables)
    """
    logger.debug("Smart retrieval for question: '%s'", question)
    
    # Use provided collection or get default
    if collection is None:
        collection = get_collection()
    
    # Initial vector search
    results = collection.query(query_texts=[question], n_results=2)
    found_tables = results["ids"][0]
    
    logger.info("Vector search found: %s", found_tables)
    final_tables = set(found_tables)
    
    # Expand with foreign key relationships
    for table in found_tables:
        neighbours = get_table_neighbours(table)
        if neighbours:
            logger.info("%s is linked to: %s", table, neighbours)
            final_tables.update(neighbours)
    
    if not final_tables:
        logger.warning("No tables found for question")
        return []
    
    # Retrieve full schemas
    final_data = collection.get(ids=list(final_tables))
    logger.info("Smart retrieval returned %d schemas", len(final_data["documents"]))
    return final_data["documents"]


def validate_sql_ast(sql_query):
    """
    Validate SQL using AST (Abstract Syntax Tree) parsing.
    
    This provides deeper security than string matching by analyzing
    the actual SQL structure. Detects modification commands even if
    they're obfuscated or use complex syntax.
    
    Args:
        sql_query: SQL query string
    
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    logger.debug("Validating SQL with AST: %s", sql_query[:100])
    
    try:
        # Parse into AST (Abstract Syntax Tree)
        parsed = sqlglot.parse_one(sql_query, read="sqlite")
        
        # Check for forbidden statement types
        forbidden_types = (exp.Drop, exp.Delete, exp.Insert, exp.Update, exp.Create)
        if parsed.find(forbidden_types):
            logger.warning("AST detected forbidden operation in SQL")
            return False, "Safety Violation: AST detected a modification command."
        
        logger.debug("SQL passed AST validation")
        return True, ""
        
    except Exception as e:
        logger.error("AST validation failed: %s", str(e))
        return False, f"Syntax Error: {str(e)}"


def execute_sql(sql_query, engine=None):
    """
    Execute SQL query with enhanced security and validation.
    
    Security Features:
    - Enhanced markdown cleanup (handles escaped newlines)
    - AST-based validation (deeper than string matching)
    - Sanitized error messages (no information leakage)
    - Dialect-aware execution
    
    Args:
        sql_query: SQL query string (may contain markdown)
        engine: SQLAlchemy engine (optional, uses default if not provided)
    
    Returns:
        dict with success status, columns, data, or error message
    """
    # Enhanced markdown cleanup using regex
    # First, handle escaped newlines (\n) by converting to actual newlines
    clean_sql = sql_query.replace('\\n', '\n')
    
    # Remove markdown code blocks with various formats
    clean_sql = re.sub(r'```(?:sql)?\s*\n?', '', clean_sql)
    clean_sql = re.sub(r'\n?```\s*', '', clean_sql)
    clean_sql = clean_sql.strip()
    
    logger.debug("Executing SQL (cleaned): %s", clean_sql[:100])
    
    # AST-based validation (more robust than string matching)
    is_valid, error_msg = validate_sql_ast(clean_sql)
    if not is_valid:
        logger.warning("SQL failed AST validation: %s", error_msg)
        return {"success": False, "error": error_msg}
    
    # Use provided engine or default
    if engine is None:
        engine = get_default_engine()
    
    # Execute query
    try:
        with engine.connect() as conn:
            result = conn.execute(text(clean_sql))
            rows = result.fetchall()
            column_names = list(result.keys())
            
        logger.info("SQL executed successfully, returned %d rows", len(rows))
        return {
            "success": True,
            "columns": column_names,
            "data": [tuple(row) for row in rows],
        }
        
    except Exception as e:
        # Log full error internally, return sanitized message
        logger.error("SQL execution failed: %s", str(e), exc_info=True)
        sanitized_msg = sanitize_error_message(e)
        return {
            "success": False,
            "error": sanitized_msg,
        }


def query_critic(question, failed_sql, error_message, schema_context, dialect="sqlite"):
    """
    AI-powered query critic that analyzes failures.
    
    This separate agent reviews failed queries and provides specific
    feedback on why they failed and how to fix them. This improves
    the retry success rate significantly.
    
    Args:
        question: Original user question
        failed_sql: The SQL that failed
        error_message: Error from execution
        schema_context: Schema that was provided
        dialect: Database dialect (sqlite, postgresql, mysql)
    
    Returns:
        Critic's analysis and suggested fix
    """
    logger.info("Query critic analyzing failure...")
    logger.debug("Failed SQL: %s", failed_sql[:100])
    logger.debug("Error: %s", error_message)
    
    prompt = f"""
    You are a Senior {dialect.upper()} Engineer reviewing a Junior's broken code.

    User Question: {question}
    The Broken SQL: {failed_sql}
    The Error Message: {error_message}
    The Schema: {schema_context}

    TASK:
    Explain WHY it failed in 1 sentence.
    Specifics only.
    Focus on {dialect.upper()}-specific syntax errors if applicable.
    Do not write SQL. Just explain the fix.
    """

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL, 
            messages=[{"role": "user", "content": prompt}]
        )
        critique = response.choices[0].message.content
        logger.info("Critic feedback: %s", critique[:100])
        return critique
        
    except Exception as e:
        logger.error("Query critic failed: %s", str(e))
        return "Unable to analyze error. Please review the error message."


def run_agent(question, engine=None, collection=None):
    """
    Main RAG agent with smart retrieval and query critic.
    
    Process:
    1. Smart retrieval (vector search + foreign key expansion)
    2. Generate SQL with dialect-aware prompts
    3. Validate with AST
    4. Execute query
    5. If error, use query critic for feedback and retry
    
    This is more sophisticated than generator.py's simple retry logic.
    
    Args:
        question: User's natural language question
        engine: SQLAlchemy engine (optional, uses default if not provided)
        collection: ChromaDB collection (optional, uses default if not provided)
    
    Returns:
        Execution result dict or None if all retries failed
    """
    logger.info("Agent starting for question: '%s'", question)
    
    # Use provided engine or default
    if engine is None:
        engine = get_default_engine()
    
    # Get dialect from engine
    dialect = engine.dialect.name
    logger.debug("Using database dialect: %s", dialect)
    
    # Smart retrieval with foreign key expansion
    schemas = smart_retrieval(question, collection)
    context_sql = "\n\n".join(schemas)
    
    # Dialect-aware system prompt
    messages = [
        {
            "role": "system",
            "content": f"""
            You are an expert {dialect.upper()} Data Analyst.

                Schema:
                {context_sql}

                Rules:
                1. Use ONLY the provided schema.
                2. Write valid {dialect.upper()} SQL.
                3. Return ONLY raw SQL. No markdown.
                """,
        },
        {"role": "user", "content": question},
    ]
    
    for attempt in range(MAX_RETRIES):
        logger.info("Attempt %d/%d", attempt + 1, MAX_RETRIES)
        
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL, messages=messages, temperature=0.1
            )
            sql = response.choices[0].message.content.strip()
            logger.debug("Generated SQL (attempt %d): %s", attempt + 1, sql[:100])
            
            result = execute_sql(sql, engine)
            if result["success"]:
                logger.info("Agent succeeded on attempt %d", attempt + 1)
                return result
            else:
                logger.warning("Attempt %d failed: %s", attempt + 1, result['error'])
                
                # Use query critic for better feedback
                critique = query_critic(question, sql, result["error"], context_sql, dialect)
                
                messages.append({"role": "assistant", "content": sql})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Your SQL failed.\nError: {result['error']}\nCritic's Advice: {critique}\nFix the SQL.",
                    }
                )
                
        except Exception as e:
            logger.error("Unexpected error in agent: %s", str(e), exc_info=True)
            return None
    
    logger.error("Agent failed after %d retries", MAX_RETRIES)
    return None


def answer_synthesis(question, result):
    """
    Synthesize natural language answer from query results.
    
    Takes the raw SQL results and generates a human-friendly answer
    that directly addresses the user's question.
    
    Args:
        question: Original user question
        result: Query execution result dict
    
    Returns:
        Natural language answer string
    """
    logger.info("Synthesizing answer for question: '%s'", question)
    
    if not result or not result.get("success"):
        logger.warning("Cannot synthesize answer from failed query")
        return "I couldn't retrieve the data to answer your question."
    
    columns = result["columns"]
    data = result["data"]
    
    # Format data as a readable table
    table_text = f"Columns: {', '.join(columns)}\n"
    for row in data[:10]:  # Limit to first 10 rows
        table_text += f"{row}\n"
    
    if len(data) > 10:
        table_text += f"... and {len(data) - 10} more rows\n"
    
    prompt = f"""
    The user asked: "{question}"
    
    Here is the query result:
    {table_text}
    
    Provide a clear, concise answer to their question based on this data.
    Be specific and use numbers from the data.
    Keep it under 3 sentences.
    """
    
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        answer = response.choices[0].message.content
        logger.info("Answer synthesized successfully")
        return answer
        
    except Exception as e:
        logger.error("Answer synthesis failed: %s", str(e))
        return f"I found {len(data)} results, but couldn't summarize them."



if __name__ == "__main__":
    q = "What is the full name of the user who bought the most expensive item?"
    output = run_agent(q)
    if output:
        print("\n FINAL DATA:")
        print(output["columns"])
        for row in output["data"]:
            print(row)

        print("HUMAN RESPONSE:")
        print(synthesize_answer(q, output["data"], output["columns"]))
