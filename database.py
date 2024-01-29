# database.py
import sqlite3
from fastapi import HTTPException
import models

DB_PATH = "example.db"


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    return conn, cursor


def close_db(conn):
    conn.commit()
    conn.close()


def create_db():
    conn, cursor = connect_db()

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                forename TEXT,
                githubConnected INTEGER NOT NULL 
            )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS githubTokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                token TEXT                
            )
        """)

    close_db(conn)


def register(user: models.UserRegistration):
    conn, cursor = connect_db()
    cursor.execute("SELECT id FROM users WHERE email=?", (user.email.lower(),))
    existing_user = cursor.fetchone()

    if existing_user:
        close_db(conn)
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        # Insert the new user
        cursor.execute("INSERT INTO users (email, password, forename, githubConnected) VALUES (?, ?, ?, 0)",
                       (user.email.lower(), user.password, user.forename))
        cursor.execute("SELECT id FROM users WHERE email=?", (user.email.lower(),))
        user_id = cursor.fetchone()

        close_db(conn)
        return user_id
    except sqlite3.IntegrityError:
        close_db(conn)


def login(user: models.UserLogin):
    conn, cursor = connect_db()
    cursor.execute("SELECT * FROM users WHERE email=?", (user.email.lower(),))
    db_user = cursor.fetchone()

    close_db(conn)
    return db_user


def getUser(user_id: int):
    conn, cursor = connect_db()
    cursor.execute("SELECT id, email, forename, githubConnected FROM users WHERE id=?", (user_id,))
    db_user = cursor.fetchone()

    close_db(conn)
    return db_user


def storeGitToken(token: str, user_id: str):
    try:
        conn, cursor = connect_db()
        cursor.execute("INSERT INTO githubTokens (user_id, token) VALUES  (?, ?)", (user_id, token))
        close_db(conn)

        return True
    except Exception:
        return False


def getGitToken(user_id: str):
    try:
        conn, cursor = connect_db()
        cursor.execute("SELECT token FROM githubTokens WHERE user_id=?", (user_id,))
        token = cursor.fetchone()

        close_db(conn)

        return token
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to find Github access token")
