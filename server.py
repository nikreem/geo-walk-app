from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import json

app = Flask(__name__)
# Разрешаем CORS, чтобы твой фронтенд с GitHub Pages мог общаться с этим сервером
CORS(app)

DB_PATH = "users.db"

def init_db():
    """Создает таблицу пользователей с игровым прогрессом, если её еще нет"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            photo_url TEXT,
            is_vip BOOLEAN DEFAULT 0,
            coins INTEGER DEFAULT 1000,
            energy INTEGER DEFAULT 100,
            last_free_spin INTEGER DEFAULT 0,
            unlocked TEXT DEFAULT '["default", "bright"]',
            active_char TEXT DEFAULT 'default',
            active_map TEXT DEFAULT 'bright'
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/api/user/auth', methods=['POST'])
def auth_user():
    """Авторизация: возвращает профиль и текущий игровой прогресс из БД"""
    data = request.json or {}
    tg_id = data.get('id')
    username = data.get('username', '').replace("@", "").lower().strip()
    first_name = data.get('first_name', 'Гость')
    photo_url = data.get('photo_url', '')

    if not tg_id:
        return jsonify({"error": "No TG ID provided"}), 400

    # Проверка на VIP (по ID или юзернейму)
    is_vip = 1 if (tg_id == 5434932796 or username == "kirushapross") else 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ищем пользователя в базе
    cursor.execute("SELECT coins, energy, last_free_spin, unlocked, active_char, active_map FROM users WHERE id = ?", (tg_id,))
    row = cursor.fetchone()

    if row is None:
        # Новый игрок — создаем запись с дефолтными значениями
        cursor.execute('''
            INSERT INTO users (id, username, first_name, photo_url, is_vip)
            VALUES (?, ?, ?, ?, ?)
        ''', (tg_id, username, first_name, photo_url, is_vip))
        conn.commit()
        
        user_stats = {
            "coins": 1000, 
            "energy": 100, 
            "last_free_spin": 0,
            "unlocked": ["default", "bright"], 
            "active_char": "default", 
            "active_map": "bright"
        }
    else:
        # Старый игрок — обновляем его ник/аватарку (если сменил в ТГ), но сохраняем прогресс
        cursor.execute('''
            UPDATE users SET username = ?, first_name = ?, photo_url = ?, is_vip = ? WHERE id = ?
        ''', (username, first_name, photo_url, is_vip, tg_id))
        conn.commit()
        
        user_stats = {
            "coins": row[0], 
            "energy": row[1], 
            "last_free_spin": row[2],
            "unlocked": json.loads(row[3]), 
            "active_char": row[4], 
            "active_map": row[5]
        }

    conn.close()
    
    return jsonify({
        "id": tg_id,
        "username": username,
        "is_vip": bool(is_vip),
        "stats": user_stats
    })

@app.route('/api/user/save', methods=['POST'])
def save_progress():
    """Сохранение текущего прогресса игрока в БД"""
    data = request.json or {}
    tg_id = data.get('id')
    stats = data.get('stats')

    if not tg_id or not stats:
        return jsonify({"error": "Invalid payload"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE users SET 
                coins = ?, 
                energy = ?, 
                last_free_spin = ?, 
                unlocked = ?, 
                active_char = ?, 
                active_map = ?
            WHERE id = ?
        ''', (
            stats.get('coins'),
            stats.get('energy'),
            stats.get('last_free_spin'),
            json.dumps(stats.get('unlocked')),
            stats.get('active_char'),
            stats.get('active_map'),
            tg_id
        ))
        conn.commit()
        status = "success"
    except Exception as e:
        status = f"error: {e}"
    finally:
        conn.close()

    return jsonify({"status": status})

@app.route('/api/admin/action', methods=['POST'])
def admin_action():
    """Админ-панель: изменение баланса любого игрока по его Username в БД"""
    data = request.json or {}
    target_username = data.get('target_username', '').replace("@", "").lower().strip()
    action_type = data.get('type')  # 'coins', 'energy', 'spin'
    value = int(data.get('value', 0))

    if not target_username:
        return jsonify({"error": "Target username is required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем, есть ли такой игрок в базе
    cursor.execute("SELECT id FROM users WHERE username = ?", (target_username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"error": f"Пользователь @{target_username} не найден на сервере!"}), 404

    target_id = user[0]

    if action_type == 'coins':
        cursor.execute("UPDATE users SET coins = coins + ? WHERE id = ?", (value, target_id))
    elif action_type == 'energy':
        cursor.execute("UPDATE users SET energy = MIN(100, energy + ?) WHERE id = ?", (value, target_id))
    elif action_type == 'spin':
        cursor.execute("UPDATE users SET last_free_spin = 0 WHERE id = ?", (target_id,))

    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": f"Успешно изменено ({action_type}: {value}) для @{target_username}"})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
