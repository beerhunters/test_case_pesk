from flask import Flask, request, jsonify, send_from_directory
import jwt
import redis
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__, static_folder="static")

# Настройки
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key")
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

# Подключение к Redis с обработкой ошибок
try:
    redis_client = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
    )
    redis_client.ping()
    print("Connected to Redis successfully.")
except redis.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    raise e

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "users.db")


# Инициализация базы данных SQLite
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS Users
                     (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)"""
        )
        c.execute(
            "INSERT OR IGNORE INTO Users (id, username, password, role) VALUES (?, ?, ?, ?)",
            (1, "user1", "pass1", "role_editor"),
        )
        c.execute(
            "INSERT OR IGNORE INTO Users (id, username, password, role) VALUES (?, ?, ?, ?)",
            (2, "user2", "pass2", "role_viewer"),
        )
        conn.commit()
        print("Database initialized successfully.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


# Вызываем init_db() при импорте модуля
init_db()


# Функция для создания JWT-токена
def create_token(user_id, role):
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


# Проверка токена
def verify_token(token):
    try:
        if redis_client.sismember("blacklist", token):
            return None, "Token is blacklisted"
        if not redis_client.sismember("whitelist", token):
            return None, "Token not found in whitelist"
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"


# Маршрут для главной страницы
@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


# Маршрут для авторизации
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, role FROM Users WHERE username = ? AND password = ?",
            (username, password),
        )
        user = c.fetchone()
        conn.close()

        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        user_id, role = user
        token = create_token(user_id, role)

        redis_client.sadd("whitelist", token)

        return jsonify({"token": token})
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


# Маршрут для выхода
@app.route("/api/logout", methods=["POST"])
def logout():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Token is required"}), 401

    token = (
        auth_header.replace("Bearer ", "")
        if auth_header.startswith("Bearer ")
        else auth_header
    )

    redis_client.srem("whitelist", token)
    redis_client.sadd("blacklist", token)

    return jsonify({"message": "Logged out successfully"})


# Защищенный маршрут с демонстрацией общего и специфичного контента
@app.route("/api/content", methods=["GET"])
def content():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Token is required"}), 401

    token = (
        auth_header.replace("Bearer ", "")
        if auth_header.startswith("Bearer ")
        else auth_header
    )

    payload, error = verify_token(token)
    if error:
        return jsonify({"error": error}), 401

    role = payload["role"]
    content_data = {
        "shared": "This content is accessible to all authenticated users.",
        "role_editor": "This content is exclusive to editors.",
        "role_viewer": "This content is specific to viewers.",
    }

    response_content = {"message": content_data.get("shared")}
    if role in content_data:
        response_content["role_specific"] = content_data.get(role)

    return jsonify(response_content)


# Очистка устаревших токенов
@app.route("/api/cleanup", methods=["POST"])
def cleanup():
    tokens = redis_client.smembers("whitelist")
    for token in tokens:
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            redis_client.srem("whitelist", token)
            redis_client.sadd("blacklist", token)

    return jsonify({"message": "Cleanup completed"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
