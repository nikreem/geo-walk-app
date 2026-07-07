from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
# Включаем CORS, чтобы фронтенд с GitHub Pages мог общаться с бэком на Render
CORS(app)

DB_PATH = "users.db"

def init_db():
    """Создает таблицу пользователей, если её еще нет"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            photo_url TEXT,
            is_vip BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/api/user', methods=['POST'])
def save_and_check_user():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    tg_id = data.get('id')
    username = data.get('username', '')
    first_name = data.get('first_name', 'Гость')
    photo_url = data.get('photo_url', '')

    # Если запроса от TG нет (зашли просто по прямой ссылке на API)
    if not tg_id:
        return jsonify({"is_vip": False, "status": "guest"})

    # Проверка условий на VIP (ID или Юзернейм)
    # Очищаем юзернейм от знака @ на случай, если он придет с ним
    clean_username = username.replace("@", "").lower()
    
    is_vip = 0
    if tg_id == 5434932796 or clean_username == "kirushapross":
        is_vip = 1

    # Запись или обновление данных в БД SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (id, username, first_name, photo_url, is_vip)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                photo_url = excluded.photo_url,
                is_vip = excluded.is_vip
        ''', (tg_id, username, first_name, photo_url, is_vip))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Ошибка БД: {e}")
        # Даже если база упала, вернем статус пользователю, чтобы интерфейс работал
        return jsonify({"id": tg_id, "is_vip": bool(is_vip), "db_error": True})

    return jsonify({
        "status": "success",
        "id": tg_id,
        "username": username,
        "is_vip": bool(is_vip)
    })

if __name__ == '__main__':
    init_db()
    # Render динамически назначает порт через переменную среды PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
