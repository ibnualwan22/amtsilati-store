# setup_database.py

import pymysql.cursors
import os
import sys
from werkzeug.security import generate_password_hash
from config import get_config

def get_connection():
    """Membuat koneksi ke database MySQL"""
    config = get_config()
    try:
        connection = pymysql.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            port=config.MYSQL_PORT,
            db=config.MYSQL_DB,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"Error connecting to MySQL: {e}")
        sys.exit(1)

def create_tables(cursor):
    """Membuat tabel dengan sintaks MySQL"""
    print("Executing CREATE TABLE statements for MySQL...")

    # Sintaks diubah untuk MySQL (AUTO_INCREMENT, DECIMAL, ENUM, dll)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(80) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL
    )
    """)
    print("✓ Table 'users' checked/created.")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(255) NOT NULL UNIQUE,
        price DECIMAL(10, 2) NOT NULL,
        availability VARCHAR(50) DEFAULT 'Tersedia',
        link_ig VARCHAR(255),
        link_wa VARCHAR(255),
        link_shopee VARCHAR(255),
        link_tiktok VARCHAR(255),
        image_filename VARCHAR(255)
    )
    """)
    print("✓ Table 'books' checked/created.")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offline_buyers (
        id INT PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(255) NOT NULL UNIQUE,
        address TEXT,
        dormitory VARCHAR(100)
    )
    """)
    print("✓ Table 'offline_buyers' checked/created.")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offline_sales (
        id INT PRIMARY KEY AUTO_INCREMENT,
        buyer_id INT NOT NULL,
        book_id INT NOT NULL,
        quantity INT NOT NULL,
        total_price DECIMAL(10, 2) NOT NULL,
        payment_status ENUM('Lunas', 'Belum Lunas') DEFAULT 'Lunas',
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES offline_buyers(id),
        FOREIGN KEY (book_id) REFERENCES books(id)
    )
    """)
    print("✓ Table 'offline_sales' checked/created.")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS online_sales (
        id INT PRIMARY KEY AUTO_INCREMENT,
        buyer_name VARCHAR(255) NOT NULL,
        buyer_address TEXT NOT NULL,
        book_id INT NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        shipping_cost DECIMAL(10, 2),
        total_price DECIMAL(10, 2) NOT NULL,
        transfer_date DATE,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (book_id) REFERENCES books(id)
    )
    """)
    print("✓ Table 'online_sales' checked/created.")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cash_records (
        id INT PRIMARY KEY AUTO_INCREMENT,
        type ENUM('debit', 'kredit') NOT NULL,
        description TEXT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        category VARCHAR(100),
        record_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("✓ Table 'cash_records' checked/created.")

def create_admin_user(cursor, username='admin', password='password123'):
    """Membuat user admin default"""
    password_hash = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, password_hash)
        )
        print(f"\\n✅ Admin user created: Username={username}, Password={password}")
    except pymysql.IntegrityError:
        print(f"\\n⚠️ Username '{username}' already exists.")

def main():
    """Fungsi utama untuk setup database MySQL"""
    # Set environment jika ada argumen
    if len(sys.argv) > 1:
        os.environ['FLASK_ENV'] = sys.argv[1]

    config = get_config()
    print(f"=== DATABASE SETUP FOR: {os.environ.get('FLASK_ENV', 'development')} ===")
    print(f"Target Database: {config.MYSQL_DB} on {config.MYSQL_HOST}")

    # Konfirmasi sebelum menjalankan
    response = input("This will create tables in the database. Continue? (y/n): ")
    if response.lower() != 'y':
        print("Setup cancelled.")
        return

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            create_tables(cursor)
            create_admin_user(cursor)
        connection.commit()
        print("\\n✅ Database setup completed successfully!")
    finally:
        connection.close()

if __name__ == '__main__':
    main()