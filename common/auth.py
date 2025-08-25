import os
import sqlite3
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from werkzeug.security import generate_password_hash, check_password_hash

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
        key TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------------
# Auth / CRUD functions
# ---------------------
def create_user_with_jwt(db, username: str):
    key = os.urandom(4).hex()
    hkey = generate_password_hash(key)
    data = {"username": username, "key":key}
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    cursor = db.cursor()
    cursor.execute(f"INSERT INTO {USERS_TABLE} (username, key) VALUES (?, ?)", (username, hkey))
    db.commit()
    return token

def rotate_jwt(db, username: str):
    key = os.urandom(4).hex()
    new_hkey = generate_password_hash(key)
    data = {"username": username, 'key':key}
    new_token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    cursor = db.cursor()
    cursor.execute(f"UPDATE {USERS_TABLE} SET key=? WHERE username=?", (new_hkey, username))
    db.commit()
    return new_token

def get_token(db, username) :
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM {USERS_TABLE} WHERE username=?;", (username, ))
    user = cursor.fetchone()
    return None if user is None else user['key']

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security), db=Depends(get_db)):
    token = credentials.credentials
    try:
        data     = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = data.get("username")
        key      = data.get("key")
        hkey     = get_token(db, username)

        if (username is None) or (key is None):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        if (hkey is None) :
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or token invalid")
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    is_valid = check_password_hash(hkey, key)
    if is_valid :
        return username
    else :
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")