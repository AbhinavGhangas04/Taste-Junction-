import mysql.connector
import os


def _db_settings():
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME", "taste_junction")

    if not password:
        raise RuntimeError(
            "DB_PASSWORD is not set. Please set DB_PASSWORD in environment variables."
        )

    return host, user, password, database


def get_server_conn():
    host, user, password, _ = _db_settings()
    return mysql.connector.connect(host=host, user=user, password=password)


def get_db_conn():
    host, user, password, database = _db_settings()
    return mysql.connector.connect(
        host=host, user=user, password=password, database=database
    )


def init_db():
    _, _, _, db_name = _db_settings()
    # 1. Create database if not exists
    conn = get_server_conn()
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
    cursor.close()
    conn.close()

    # 2. Connect to database
    conn = get_db_conn()
    cursor = conn.cursor()

    # 3. USERS table (IMPORTANT)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            password_hash VARCHAR(255),
            role VARCHAR(20)
        )
    """
    )

    # 4. ORDERS table (IMPORTANT)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255),
            food VARCHAR(255),
            total INT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) DEFAULT 'PENDING',
            payment_method VARCHAR(20) DEFAULT NULL
        )
    """
    )

    # Ensure 'food' column is wide enough for cart summaries
    try:
        cursor.execute("ALTER TABLE orders MODIFY COLUMN food VARCHAR(255)")
    except mysql.connector.Error:
        # If the column is already large enough or ALTER fails, ignore
        pass

    # Ensure payment_method column exists and after status
    try:
        cursor.execute(
            "ALTER TABLE orders ADD COLUMN payment_method VARCHAR(20) DEFAULT NULL AFTER status"
        )
    except mysql.connector.Error:
        # Column already exists -> ignore
        pass

    # Migrate old status values (if any) to new naming
    try:
        cursor.execute("UPDATE orders SET status='PENDING' WHERE status='ORDERED'")
        cursor.execute("UPDATE orders SET status='PREPARING' WHERE status='PROCESSING'")
        cursor.execute("UPDATE orders SET status='PACKED' WHERE status='READY'")
    except mysql.connector.Error:
        pass

    conn.commit()
    cursor.close()
    conn.close()

    print("Database initialized successfully")
