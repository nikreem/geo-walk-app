from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
# Разрешаем запросы со всех адресов, чтобы Telegram WebApp мог достучаться до сервера
CORS(app, resources={r"/*": {"origins": "*"}})

DB_FILE = 'database.json'

# Функция загрузки базы данных
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

# Функция сохранения базы данных
def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 1. Получить данные игрока (вызывается при старте игры)
@app.route('/get_player', methods=['GET'])
def get_player():
    username = request.args.get('username', '').lower()
    if not username:
        return jsonify({'error': 'No username provided'}), 400
    
    db = load_db()
    
    # Если игрока еще нет в базе, создаем его с начальными настройками
    if username not in db:
        db[username] = {
            "username": request.args.get('username'),
            "role": "User",
            "energy": 1000,
            "maxEnergy": 1000
        }
        save_db(db)
        
    return jsonify(db[username])

# 2. Обновить данные игрока (вызывается, когда админ выдает VIP или тратится энергия)
@app.route('/update_player', methods=['POST'])
def update_player():
    data = request.json
    username = data.get('username', '').lower()
    if not username:
        return jsonify({'error': 'No username provided'}), 400
    
    db = load_db()
    
    # Записываем обновленные данные
    db[username] = {
        "username": data.get('username'),
        "role": data.get('role', 'User'),
        "energy": data.get('energy', 1000),
        "maxEnergy": data.get('maxEnergy', 1000)
    }
    
    save_db(db)
    return jsonify({'status': 'success', 'player': db[username]})

if __name__ == '__main__':
    # Обязательно используем порт, который выдает хостинг Render (через os.environ)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
