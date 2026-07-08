from flask import Flask, jsonify, render_template, request
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

@app.route('/items', methods=['GET'])
def get_items():
    ITEMS = [
        {"id": 1, "name": "Blue Water Bottle", "location": "Library, 2nd floor"},
        {"id": 2, "name": "Black Umbrella", "location": "Main Hall entrance"},
        {"id": 3, "name": "Calculator (Casio)", "location": "Maths block, Room 4"},
    ]
    return jsonify(ITEMS)

@app.route('/items', methods=['POST'])
def handle_item_submission():
    # Capture form data (or handle file upload)
    title = request.form.get('item-title')
    description = request.form.get('description')
    category = request.form.get('category')
    image_url = request.form.get('image_url')

    return jsonify({"status": "success", "message": "Item received!"})

if __name__ == '__main__':
 app.run(debug=True)