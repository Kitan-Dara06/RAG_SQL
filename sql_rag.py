"""
Database schema extraction for SQL_RAG.
Supports SQLite, PostgreSQL, and MySQL.
"""
import sqlite3
from sqlalchemy import create_engine, text
from config import DB_TYPE, DB_CONNECTION_STRING
from logger import get_logger

logger = get_logger(__name__)


def get_database_schema():
    """
    Extract CREATE TABLE statements from the database.
    
    Supports:
    - SQLite: Uses sqlite_master
    - PostgreSQL: Uses INFORMATION_SCHEMA
    - MySQL: Uses INFORMATION_SCHEMA
    
    Returns:
        List of CREATE TABLE statements
    """
    logger.info("Extracting schema from %s database", DB_TYPE)
    
    if DB_TYPE == "sqlite":
        return _get_sqlite_schema()
    elif DB_TYPE == "postgresql":
        return _get_postgresql_schema()
    elif DB_TYPE == "mysql":
        return _get_mysql_schema()
    else:
        raise ValueError(f"Unsupported database type: {DB_TYPE}")


def _get_sqlite_schema():
    """Extract schema from SQLite database."""
    # Extract database path from connection string
    db_path = DB_CONNECTION_STRING.replace("sqlite:///", "")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()
    
    schema_docs = [table[0] for table in tables if table[0] is not None]
    logger.info("Extracted %d tables from SQLite", len(schema_docs))
    return schema_docs


def _get_postgresql_schema():
    """Extract schema from PostgreSQL database."""
    engine = create_engine(DB_CONNECTION_STRING)
    
    with engine.connect() as conn:
        # Get all tables in public schema
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';
        """))
        tables = [row[0] for row in result.fetchall()]
        
        schema_docs = []
        for table in tables:
            # Get CREATE TABLE statement
            result = conn.execute(text(f"""
                SELECT 
                    'CREATE TABLE ' || :table_name || ' (' || 
                    string_agg(
                        column_name || ' ' || 
                        CASE 
                            WHEN data_type = 'character varying' THEN 'VARCHAR(' || character_maximum_length || ')'
                            WHEN data_type = 'numeric' THEN 'DECIMAL(' || numeric_precision || ',' || numeric_scale || ')'
                            WHEN data_type = 'integer' THEN 'INTEGER'
                            WHEN data_type = 'timestamp without time zone' THEN 'TIMESTAMP'
                            ELSE UPPER(data_type)
                        END ||
                        CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                        ', '
                    ) || ');' AS create_statement
                FROM information_schema.columns
                WHERE table_name = :table_name
                AND table_schema = 'public';
            """), {"table_name": table})
            
            create_stmt = result.fetchone()[0]
            schema_docs.append(create_stmt)
    
    logger.info("Extracted %d tables from PostgreSQL", len(schema_docs))
    return schema_docs


def _get_mysql_schema():
    """Extract schema from MySQL database."""
    engine = create_engine(DB_CONNECTION_STRING)
    
    with engine.connect() as conn:
        # Get all tables
        result = conn.execute(text("SHOW TABLES;"))
        tables = [row[0] for row in result.fetchall()]
        
        schema_docs = []
        for table in tables:
            # Get CREATE TABLE statement
            result = conn.execute(text(f"SHOW CREATE TABLE {table};"))
            create_stmt = result.fetchone()[1]
            schema_docs.append(create_stmt)
    
    logger.info("Extracted %d tables from MySQL", len(schema_docs))
    return schema_docs


if __name__ == "__main__":
    print(f"Extracting schema from {DB_TYPE} database...")
    schemas = get_database_schema()
    print(f"\nFound {len(schemas)} tables:\n")
    for s in schemas:
        print(f" Table:\n{s}\n")
