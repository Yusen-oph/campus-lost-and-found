from functools import wraps
from flask import Flask, jsonify, render_template, request, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/hello')
def hello():
 return jsonify({'message': 'Hello from Flask!'})

@app.route('/post-item', methods=['GET'])
def list_items():
    return render_template('list-item-form.html')

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/api/register', methods=['POST'])
def register():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    connection = get_connection()
    cursor = connection.cursor()

    existing = cursor.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    if existing:
        connection.close()
        return jsonify({"error": "That email is already taken."}), 409

    cursor.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, generate_password_hash(password, method="pbkdf2:sha256")),
    )
    connection.commit()
    user_id = cursor.lastrowid
    connection.close()

    session["email"] = email
    return jsonify({"status": "ok", "email": email})

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    connection = get_connection()
    cursor = connection.cursor()
    user = cursor.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    connection.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session["email"] = user["email"]
    return jsonify({"status": "ok", "email": user["email"]})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "ok"})

@app.route('/api/me', methods=['GET'])
def me():
    if "user_id" in session:
        return jsonify({"logged_in": True, "email": session.get("email")})
    return jsonify({"logged_in": False})

@app.route('/api/items', methods=['GET'])
def get_items():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    query = "SELECT id, title, description, category, image_url, status FROM items"
    conditions = []
    params = []

    if search:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    if category:
        conditions.append("category = ?")
        params.append(category)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY id DESC"

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    connection.close()

    return jsonify([dict(row) for row in rows])

@app.route('/items', methods=['POST'])
def handle_item_submission():
    title       = request.form.get('item-title')
    description = request.form.get('description')
    category    = request.form.get('category')
    image_url   = request.form.get('image_url')

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO items (title, description, category, image_url) VALUES (?, ?, ?, ?)",
        (title, description, category, image_url)
    )
    connection.commit()
    new_id = cursor.lastrowid
    connection.close()

    return jsonify({"status": "success", "id": new_id, "message": "Item posted!"})

@app.route('/items/<int:id>', methods=['GET'])
def get_item(id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM items WHERE id = ?", (id,))
    item = cursor.fetchone()
    connection.close()

    if item is None:
        return "Item not found", 404

    return render_template('item.html', item=dict(item))

if __name__ == '__main__':
 app.run(debug=True)