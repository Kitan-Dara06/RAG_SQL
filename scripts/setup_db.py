import datetime
import random
import sqlite3

DB_NAME = "enterprise.db"


def create_connection():
    return sqlite3.connect(DB_NAME)


def setup_schema(cursor):
    print("🔨 Creating Tables...")

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        signup_date DATE
    );
    """)

    # 2. Products Table (Category is important for RAG testing)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock_level INTEGER
    );
    """)

    # 3. Orders Table (Links to Users)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_date DATE,
        status TEXT DEFAULT 'pending', -- pending, shipped, delivered, cancelled
        total_amount REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    # 4. Order Items (The Join Table - Links Orders to Products)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price REAL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)


def populate_data(cursor):
    print("🌱 Seeding Data...")

    # --- Users ---
    names = [
        "Kitan Oladapo",
        "Amina Yusuf",
        "Emeka Okonkwo",
        "Sarah Johnson",
        "David Chen",
    ]
    for name in names:
        email = f"{name.lower().replace(' ', '.')}@example.com"
        cursor.execute(
            "INSERT OR IGNORE INTO users (name, email, signup_date) VALUES (?, ?, ?)",
            (
                name,
                email,
                datetime.date(2023, random.randint(1, 12), random.randint(1, 28)),
            ),
        )

    # --- Products ---
    products = [
        ("Laptop Pro X", "Electronics", 1200.00),
        ("Wireless Mouse", "Electronics", 25.50),
        ("Ergonomic Chair", "Furniture", 350.00),
        ("Python for AI", "Books", 45.00),
        ("Noise Cancelling Headphones", "Electronics", 299.99),
        ("Standing Desk", "Furniture", 450.00),
    ]
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock_level) VALUES (?, ?, ?, 100)",
        products,
    )

    # --- Orders & Items ---
    # Create 20 random orders
    for _ in range(20):
        user_id = random.randint(1, len(names))
        # Random date in last 30 days
        order_date = datetime.date.today() - datetime.timedelta(
            days=random.randint(0, 30)
        )

        cursor.execute(
            "INSERT INTO orders (user_id, order_date, status, total_amount) VALUES (?, ?, ?, 0)",
            (user_id, order_date, random.choice(["shipped", "delivered", "pending"])),
        )

        order_id = cursor.lastrowid

        # Add 1-3 items to this order
        order_total = 0
        for _ in range(random.randint(1, 3)):
            prod_id = random.randint(1, len(products))
            # Get product price
            price = cursor.execute(
                "SELECT price FROM products WHERE id = ?", (prod_id,)
            ).fetchone()[0]
            qty = random.randint(1, 2)

            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                (order_id, prod_id, qty, price),
            )
            order_total += price * qty

        # Update total amount
        cursor.execute(
            "UPDATE orders SET total_amount = ? WHERE id = ?", (order_total, order_id)
        )


def main():
    conn = create_connection()
    cursor = conn.cursor()

    # Reset (Drop tables to ensure clean state)
    cursor.executescript(
        "DROP TABLE IF EXISTS order_items; DROP TABLE IF EXISTS orders; DROP TABLE IF EXISTS products; DROP TABLE IF EXISTS users;"
    )

    setup_schema(cursor)
    populate_data(cursor)

    conn.commit()
    print("✅ Database 'enterprise.db' created successfully with relations!")
    conn.close()


if __name__ == "__main__":
    main()
