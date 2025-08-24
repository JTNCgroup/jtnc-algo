import os
import sqlite3
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import secrets

# ---------------------
# Config
# ---------------------
DATABASE   = os.getenv("DATABASE") #"database.db"
USERS_TABLE = os.getenv("USERS_TABLE") #users
SECRET_KEY = os.getenv("SECRET_KEY") #"UiBsYyW2p5x_0eJH6AS8Sdb_9njYTivhVky4jFJXc6M"
ALGORITHM = os.getenv("ALGORITHM") #"HS256"

security = HTTPBearer()

# ---------------------
# Schemas
# ---------------------
class UserCreate(BaseModel):
    username: str

class Token(BaseModel):
    access_token: str

# ---------------------
# DB helper
# ---------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        token TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------------
# Auth / CRUD functions
# ---------------------
def create_user_with_jwt(db, username: str):
    payload = {"sub": username}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    cursor = db.cursor()
    cursor.execute(f"INSERT INTO {USERS_TABLE} (username, token) VALUES (?, ?)", (username, token))
    db.commit()
    cursor.execute(f"SELECT * FROM {USERS_TABLE} WHERE username=?", (username,))
    return cursor.fetchone()

def rotate_jwt(db, username: str):
    payload = {"sub": username}
    new_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    cursor = db.cursor()
    cursor.execute(f"UPDATE {USERS_TABLE} SET token=? WHERE username=?", (new_token, username))
    db.commit()
    return new_token

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), db=Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM {USERS_TABLE} WHERE username=? AND token=?", (username, token))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or token invalid")
    return user