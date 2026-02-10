"""
Setup script for creating test databases in PostgreSQL and MySQL.
Creates identical schemas and populates with test data.
"""
import sys
import time
from sqlalchemy import create_engine, text
from logger import get_logger

logger = get_logger(__name__)


def setup_postgres():
    """Setup PostgreSQL test database."""
    logger.info("Setting up PostgreSQL test database...")
    
    try:
        engine = create_engine("postgresql://testuser:testpass123@localhost:5432/test_enterprise")
        
        with engine.connect() as conn:
            # Drop existing tables if they exist
            conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS orders CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS products CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
            conn.commit()
            
            # Create tables
            conn.execute(text("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    category VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    total DECIMAL(10, 2),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
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
            conn.execute(text("INSERT INTO users (name, email) VALUES ('Alice', 'alice@test.com'), ('Bob', 'bob@test.com');"))
            conn.execute(text("INSERT INTO products (name, price, category) VALUES ('Laptop', 1000.00, 'Electronics'), ('Mouse', 25.00, 'Electronics');"))
            conn.execute(text("INSERT INTO orders (user_id, total, status) VALUES (1, 1025.00, 'completed'), (2, 25.00, 'pending');"))
            conn.execute(text("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (1, 1, 1, 1000.00), (1, 2, 1, 25.00), (2, 2, 1, 25.00);"))
            
            conn.commit()
        
        logger.info("✓ PostgreSQL setup complete")
        return True
        
    except Exception as e:
        logger.error("Failed to setup PostgreSQL: %s", str(e))
        return False


def setup_mysql():
    """Setup MySQL test database."""
    logger.info("Setting up MySQL test database...")
    
    try:
        engine = create_engine("mysql+pymysql://testuser:testpass123@localhost:3306/test_enterprise")
        
        with engine.connect() as conn:
            # Drop existing tables if they exist
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            conn.execute(text("DROP TABLE IF EXISTS order_items;"))
            conn.execute(text("DROP TABLE IF EXISTS orders;"))
            conn.execute(text("DROP TABLE IF EXISTS products;"))
            conn.execute(text("DROP TABLE IF EXISTS users;"))
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            conn.commit()
            
            # Create tables
            conn.execute(text("""
                CREATE TABLE users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    category VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    total DECIMAL(10, 2),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """))
            
            conn.execute(text("""
                CREATE TABLE order_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT,
                    product_id INT,
                    quantity INT NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (product_id) REFERENCES products(id)
                );
            """))
            
            # Insert test data
            conn.execute(text("INSERT INTO users (name, email) VALUES ('Alice', 'alice@test.com'), ('Bob', 'bob@test.com');"))
            conn.execute(text("INSERT INTO products (name, price, category) VALUES ('Laptop', 1000.00, 'Electronics'), ('Mouse', 25.00, 'Electronics');"))
            conn.execute(text("INSERT INTO orders (user_id, total, status) VALUES (1, 1025.00, 'completed'), (2, 25.00, 'pending');"))
            conn.execute(text("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (1, 1, 1, 1000.00), (1, 2, 1, 25.00), (2, 2, 1, 25.00);"))
            
            conn.commit()
        
        logger.info("✓ MySQL setup complete")
        return True
        
    except Exception as e:
        logger.error("Failed to setup MySQL: %s", str(e))
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("SQL_RAG Multi-Database Test Setup")
    print("=" * 60)
    
    print("\nWaiting for databases to be ready...")
    time.sleep(5)  # Give containers time to start
    
    results = {}
    
    # Setup PostgreSQL
    print("\n[1/2] Setting up PostgreSQL...")
    results['postgres'] = setup_postgres()
    
    # Setup MySQL
    print("\n[2/2] Setting up MySQL...")
    results['mysql'] = setup_mysql()
    
    # Summary
    print("\n" + "=" * 60)
    print("Setup Summary:")
    print("=" * 60)
    print(f"PostgreSQL: {'✓ SUCCESS' if results['postgres'] else '✗ FAILED'}")
    print(f"MySQL:      {'✓ SUCCESS' if results['mysql'] else '✗ FAILED'}")
    print("=" * 60)
    
    if all(results.values()):
        print("\n✓ All databases setup successfully!")
        return 0
    else:
        print("\n✗ Some databases failed to setup. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
