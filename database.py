# database_module.py

import sqlite3
from sqlite3 import Error

def create_connection(db_file='tasks.db'):
    """Создание соединения с базой данных SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(f"Ошибка подключения к базе данных: {e}")
    return conn

def create_table():
    """Создание таблицы tasks, если она не существует."""
    conn = create_connection()
    if conn is not None:
        create_table_sql = '''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            due_time TEXT,
            priority TEXT,
            status TEXT,
            completed_at TEXT
        );
        '''
        try:
            c = conn.cursor()
            c.execute(create_table_sql)
            conn.commit()
        except Error as e:
            print(f"Ошибка создания таблицы: {e}")
        finally:
            conn.close()
    else:
        print("Ошибка! Не удалось создать соединение с базой данных.")
