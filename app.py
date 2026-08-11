from flask import Flask, jsonify, render_template, request

from db import get_connection
app = Flask(__name__)

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
def register():
    return render_template('register.html')

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

# TODO: Implement the POST routes for registration, login, and item submission
@app.route('/login', methods=['POST'])
def handle_login():
    return jsonify({"status": "success", "message": "Account logged in!"})

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