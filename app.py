from flask import Flask, jsonify, render_template
app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/api/hello')
def hello():
 return jsonify({'message': 'Hello from Flask!'})
if __name__ == '__main__':
 app.run(debug=True)