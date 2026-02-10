"""
Universal SQL Agent - Streamlit UI
Dynamic database connection with chat interface for natural language SQL queries.
"""
import streamlit as st
from sqlalchemy import create_engine, text
from src.core.generator2 import run_agent, answer_synthesis
from src.database.schema import get_database_schema
from src.database.indexer import sentence_transformer_ef
import chromadb
from src.utils.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="Universal SQL Agent",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONNECTION SETTINGS ---
with st.sidebar:
    st.header("🔌 Database Connection")
    
    db_type = st.selectbox(
        "Database Type",
        ["SQLite", "PostgreSQL", "MySQL"],
        help="Select your database type"
    )
    
    # Dynamic form based on database type
    if db_type == "SQLite":
        db_path = st.text_input(
            "Database File Path",
            value="enterprise.db",
            help="Path to your SQLite database file"
        )
        conn_string = f"sqlite:///{db_path}"
        
    else:  # PostgreSQL or MySQL
        col1, col2 = st.columns(2)
        with col1:
            host = st.text_input("Host", value="localhost")
            user = st.text_input("User", value="postgres" if db_type == "PostgreSQL" else "root")
        with col2:
            port = st.text_input("Port", value="5432" if db_type == "PostgreSQL" else "3306")
            password = st.text_input("Password", type="password", help="Your password is not stored")
        
        dbname = st.text_input("Database Name", value="enterprise")
        
        # Construct connection string
        if db_type == "PostgreSQL":
            conn_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        elif db_type == "MySQL":
            conn_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"
    
    # Connection button
    if st.button("🚀 Connect", type="primary"):
        try:
            with st.spinner("Testing connection..."):
                # Test the connection
                test_engine = create_engine(conn_string)
                with test_engine.connect() as conn:
                    # Test query based on database type
                    if db_type == "SQLite":
                        result = conn.execute(text("SELECT sqlite_version();"))
                    elif db_type == "PostgreSQL":
                        result = conn.execute(text("SELECT version();"))
                    else:  # MySQL
                        result = conn.execute(text("SELECT version();"))
                    
                    version = result.fetchone()[0]
                
                # Save to session
                st.session_state['db_engine'] = test_engine
                st.session_state['db_type'] = db_type
                st.session_state['conn_string'] = conn_string
                st.session_state['schema_indexed'] = False
                
                st.success(f"✅ Connected to {db_type}!")
                st.caption(f"Version: {version[:50]}...")
                logger.info("Connected to %s database", db_type)
                
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")
            logger.error("Connection failed: %s", str(e))
    
    # Show connection status
    if "db_engine" in st.session_state:
        st.divider()
        st.markdown("**Connection Status:**")
        st.markdown(f"🟢 Connected to **{st.session_state.get('db_type', 'Unknown')}**")
        
        # Schema indexing section
        st.divider()
        st.markdown("**Schema Indexing:**")
        
        if st.session_state.get('schema_indexed', False):
            st.success("✅ Schema indexed")
        else:
            st.warning("⚠️ Schema not indexed")
        
        if st.button("📊 Index Schema", help="Index database schema for vector search"):
            try:
                with st.spinner("Indexing schema..."):
                    # Get schema from database
                    engine = st.session_state['db_engine']
                    
                    # Extract schemas
                    with engine.connect() as conn:
                        if st.session_state['db_type'] == "SQLite":
                            result = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table';"))
                            schemas = [row[0] for row in result.fetchall() if row[0] is not None]
                        elif st.session_state['db_type'] == "PostgreSQL":
                            # Get table names
                            result = conn.execute(text("""
                                SELECT table_name
                                FROM information_schema.tables
                                WHERE table_schema = 'public'
                                AND table_type = 'BASE TABLE';
                            """))
                            tables = [row[0] for row in result.fetchall()]
                            
                            # Get CREATE TABLE statements
                            schemas = []
                            for table in tables:
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
                                schemas.append(result.fetchone()[0])
                        else:  # MySQL
                            result = conn.execute(text("SHOW TABLES;"))
                            tables = [row[0] for row in result.fetchall()]
                            schemas = []
                            for table in tables:
                                result = conn.execute(text(f"SHOW CREATE TABLE {table};"))
                                schemas.append(result.fetchone()[1])
                    
                    # Generate table IDs
                    import re
                    ids = []
                    for sql in schemas:
                        pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s\(]+)"
                        match = re.search(pattern, sql, re.IGNORECASE)
                        if match:
                            ids.append(match.group(1).strip('"'))
                        else:
                            ids.append(f"table_{len(ids)}")
                    
                    # Index into ChromaDB
                    chroma_client = chromadb.PersistentClient(path="./repo_db")
                    try:
                        chroma_client.delete_collection(name="schema_index")
                    except:
                        pass
                    
                    collection = chroma_client.get_or_create_collection(
                        name="schema_index",
                        embedding_function=sentence_transformer_ef
                    )
                    collection.add(documents=schemas, ids=ids)
                    
                    # Store collection in session state
                    st.session_state['chroma_collection'] = collection
                    st.session_state['schema_indexed'] = True
                    st.success(f"✅ Indexed {len(schemas)} tables: {', '.join(ids)}")
                    logger.info("Indexed %d tables", len(schemas))
                    
            except Exception as e:
                st.error(f"❌ Indexing failed: {str(e)}")
                logger.error("Indexing failed: %s", str(e))

# --- MAIN CHAT INTERFACE ---
st.title("🤖 Universal SQL Agent")
st.caption("Ask questions about your database in natural language")

# Check if connected
if "db_engine" not in st.session_state:
    st.info("👈 **Please connect to a database in the sidebar to start**")
    st.markdown("""
    ### How to use:
    1. Select your database type (SQLite, PostgreSQL, or MySQL)
    2. Enter your connection details
    3. Click **Connect**
    4. Click **Index Schema** to enable smart retrieval
    5. Start asking questions!
    
    ### Example questions:
    - "How many users are in the database?"
    - "What is the total revenue from all orders?"
    - "Which customer spent the most money?"
    - "Show me the top 5 products by sales"
    """)
    st.stop()

# Check if schema is indexed
if not st.session_state.get('schema_indexed', False):
    st.warning("⚠️ **Schema not indexed yet**. Click 'Index Schema' in the sidebar for better results.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "data" in message and message["data"]:
            st.dataframe(message["data"], use_container_width=True)

# User input
if prompt := st.chat_input("Ask a question about your database..."):
    # Add user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("🧠 Thinking..."):
            try:
                # Get collection from session state (if indexed)
                collection = st.session_state.get('chroma_collection', None)
                
                # Run agent with user's engine and collection
                result = run_agent(
                    prompt, 
                    st.session_state['db_engine'],
                    collection
                )
                
                if result and result.get("success"):
                    # Synthesize natural language answer
                    answer = answer_synthesis(prompt, result)
                    
                    # Display answer
                    st.markdown(f"**{answer}**")
                    
                    # Show data table
                    if result.get("data"):
                        st.dataframe(result["data"], use_container_width=True)
                    
                    # Store in history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "data": result.get("data")
                    })
                    
                    logger.info("Query succeeded: %s", prompt)
                    
                else:
                    error_msg = f"❌ Sorry, I couldn't answer that question.\n\n**Error:** {result.get('error', 'Unknown error')}"
                    st.markdown(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    logger.warning("Query failed: %s", result.get('error'))
                    
            except Exception as e:
                error_msg = f"❌ An error occurred: {str(e)}"
                st.markdown(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
                logger.error("Exception in chat: %s", str(e), exc_info=True)

# Footer
st.divider()
st.caption("💡 Tip: Be specific in your questions for better results. The agent uses smart retrieval with foreign key analysis.")
