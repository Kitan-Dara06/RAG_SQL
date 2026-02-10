"""
Test PostgreSQL connection and setup schema.
"""
from sqlalchemy import create_engine, text
from logger import get_logger

logger = get_logger(__name__)

def test_postgres_connection():
    """Test PostgreSQL connection."""
    connection_string = "postgresql://myuser:mypassword@localhost/enterprise"
    
    logger.info("Testing PostgreSQL connection...")
    logger.info("Connection string: %s", connection_string.replace("mypassword", "***"))
    
    try:
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info("✓ Connected to PostgreSQL!")
            logger.info("Version: %s", version[:50])
            
            # Check if any tables exist
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                logger.info("Existing tables: %s", tables)
            else:
                logger.info("No tables found - database is empty")
            
            return True, version, tables
            
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL: %s", str(e))
        return False, str(e), []


def setup_postgres_schema():
    """Create schema in PostgreSQL database."""
    connection_string = "postgresql://myuser:mypassword@localhost/enterprise"
    
    logger.info("Setting up PostgreSQL schema...")
    
    try:
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Drop existing tables if they exist
            logger.info("Dropping existing tables...")
            conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS orders CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS products CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
            conn.commit()
            
            # Create tables
            logger.info("Creating users table...")
            conn.execute(text("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            logger.info("Creating products table...")
            conn.execute(text("""
                CREATE TABLE products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    category VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            logger.info("Creating orders table...")
            conn.execute(text("""
                CREATE TABLE orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    total DECIMAL(10, 2),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            logger.info("Creating order_items table...")
            conn.execute(text("""
                CREATE TABLE order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER REFERENCES orders(id),
                    product_id INTEGER REFERENCES products(id),
                    quantity INTEGER NOT NULL,
                    price DECIMAL(10, 2) NOT NULL
                );
            """))
            
            # Insert test data
            logger.info("Inserting test data...")
            conn.execute(text("INSERT INTO users (name, email) VALUES ('Alice', 'alice@test.com'), ('Bob', 'bob@test.com');"))
            conn.execute(text("INSERT INTO products (name, price, category) VALUES ('Laptop', 1000.00, 'Electronics'), ('Mouse', 25.00, 'Electronics');"))
            conn.execute(text("INSERT INTO orders (user_id, total, status) VALUES (1, 1025.00, 'completed'), (2, 25.00, 'pending');"))
            conn.execute(text("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (1, 1, 1, 1000.00), (1, 2, 1, 25.00), (2, 2, 1, 25.00);"))
            
            conn.commit()
            
            logger.info("✓ Schema setup complete!")
            return True
            
    except Exception as e:
        logger.error("Failed to setup schema: %s", str(e), exc_info=True)
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PostgreSQL Connection Test")
    print("=" * 60)
    
    # Test connection
    success, info, tables = test_postgres_connection()
    
    if success:
        print(f"\n✓ Connection successful!")
        print(f"PostgreSQL version: {info[:50]}")
        
        if tables:
            print(f"Existing tables: {tables}")
            response = input("\nDrop and recreate schema? (y/n): ")
            if response.lower() == 'y':
                if setup_postgres_schema():
                    print("\n✓ Schema created successfully!")
                else:
                    print("\n✗ Schema creation failed. Check logs.")
        else:
            print("\nDatabase is empty. Creating schema...")
            if setup_postgres_schema():
                print("\n✓ Schema created successfully!")
            else:
                print("\n✗ Schema creation failed. Check logs.")
    else:
        print(f"\n✗ Connection failed: {info}")
        print("\nTroubleshooting:")
        print("1. Check if PostgreSQL is running: sudo systemctl status postgresql")
        print("2. Verify database exists: psql -U myuser -d enterprise")
        print("3. Check credentials in .env file")
