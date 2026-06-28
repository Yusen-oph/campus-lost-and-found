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