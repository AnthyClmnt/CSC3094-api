# database.py
import sqlite3
from fastapi import HTTPException
import models
from utils import encryptToken, decrypt_token
from datetime import datetime

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
                forename TEXT
            )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS githubTokens (
                user_id INTEGER UNIQUE,
                token TEXT                
            )
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repoLastAnalysed (
                repo_owner TEXT,
                repo_name TEXT,
                last_updated DATETIME,
                PRIMARY KEY (repo_owner, repo_name)
            )
        """)

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commitFileAnalysis (
            repo_owner TEXT,
            repo_name TEXT,
            commit_sha TEXT,
            author TEXT,
            filename TEXT,
            complexity INTEGER,
            maintain_index FLOAT,
            ltc_ratio FLOAT,
            commit_date DATETIME,
            PRIMARY KEY (commit_sha, filename, repo_owner, repo_name)
        )
    ''')

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
        cursor.execute("INSERT INTO users (email, password, forename) VALUES (?, ?, ?)",
                       (user.email.lower(), user.password, user.forename))
        cursor.execute("SELECT id FROM users WHERE email=?", (user.email.lower(),))
        user_id = cursor.fetchone()

        close_db(conn)
        return user_id[0]
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
    cursor.execute("SELECT id, email, forename FROM users WHERE id=?", (user_id,))
    db_user = cursor.fetchone()

    close_db(conn)
    return db_user


def storeGitToken(token: str, user_id: str):
    encrypted_token = encryptToken(token)
    try:
        conn, cursor = connect_db()
        cursor.execute("INSERT INTO githubTokens (user_id, token) VALUES  (?, ?)", (user_id, encrypted_token))
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

        if token:
            return decrypt_token(token[0])
        else:
            return None
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to find Github access token")


def removeGitHubToken(user_id: str):
    try:
        conn, cursor = connect_db()
        cursor.execute("DELETE FROM githubTokens WHERE user_id=?", (user_id,))

        close_db(conn)
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to remove Github access token")


def getRepoLastAnalysedTime(repoName: str, repoOwner: str):
    conn, cursor = connect_db()
    cursor.execute("SELECT last_updated FROM repoLastAnalysed WHERE repo_name=? AND repo_owner=?",
                   (repoName, repoOwner))
    lastUpdated = cursor.fetchone()

    close_db(conn)

    if lastUpdated:
        return lastUpdated[0]
    return None


def setLastAnalysedTime(repoOwner: str, repoName: str):
    conn, cursor = connect_db()
    cursor.execute(
        "INSERT INTO repoLastAnalysed (repo_owner, repo_name, last_updated) VALUES (?, ?, ?) ON CONFLICT(repo_owner, "
        "repo_name) DO UPDATE SET last_updated = ?",
        (repoOwner, repoName, datetime.now(), datetime.now()))

    close_db(conn)


def getRepoAnalysis(repo_owner, repo_name, orderBy='complexity'):
    try:
        conn, cursor = connect_db()
        query = f"SELECT * FROM commitFileAnalysis WHERE repo_name=? AND repo_owner=? ORDER BY {orderBy} DESC"
        cursor.execute(query, (repo_name, repo_owner))
        analysis = cursor.fetchall()

        close_db(conn)

        if analysis:
            return analysis
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def insert_commit_complexity(repo_owner,
                             repo_name,
                             commit_sha,
                             author,
                             filename,
                             complexity,
                             maintain_index,
                             ltc_ratio,
                             commit_date):
    try:
        conn, cursor = connect_db()
        cursor.execute("INSERT INTO commitFileAnalysis (repo_owner, repo_name, commit_sha, author, filename, "
                       "complexity, maintain_index, ltc_ratio, commit_date) VALUES  (?, ?, ?, ?, ?, ?, ?, ?, ?)", (repo_owner, repo_name, commit_sha, author,
                                                                 filename, complexity, maintain_index, ltc_ratio, commit_date))

        close_db(conn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_repo_contributors(repoOwner: str, repoName: str):
    try:
        conn, cursor = connect_db()
        cursor.execute("SELECT DISTINCT author FROM commitFileAnalysis WHERE repo_name=? AND repo_owner=?",
                       (repoName, repoOwner))
        contributors = cursor.fetchall()

        close_db(conn)
        return contributors
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_repo_contributor_data(repoOwner: str, repoName: str, contributor: str):
    try:
        conn, cursor = connect_db()
        cursor.execute("SELECT DATE(commit_date) as commit_date, COUNT(DISTINCT commit_sha) AS commit_count FROM commitFileAnalysis WHERE repo_name=? AND repo_owner=? AND author=? GROUP BY DATE(commit_date) ORDER BY commit_date ASC",
                       (repoName, repoOwner, contributor))
        contributor_data = cursor.fetchall()

        close_db(conn)
        return contributor_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_repo_contributor_analysis(repo_owner: str, repo_name: str, author: str):
    try:
        conn, cursor = connect_db()
        cursor.execute("""
            SELECT 
                DATE(commit_date) as commit_date,
                AVG(maintain_index) AS avg_maintain_index,
                AVG(ltc_ratio) AS avg_ltc_ratio,
                AVG(complexity) AS avg_complexity
            FROM 
                commitFileAnalysis
            WHERE 
                repo_name = ? 
                AND repo_owner = ? 
                AND author = ?
            GROUP BY 
                strftime('%Y-%m', commit_date)
            ORDER BY 
                commit_date ASC
        """, (repo_name, repo_owner, author))
        contributor_data = cursor.fetchall()

        close_db(conn)
        return contributor_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))