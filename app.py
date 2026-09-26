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
    email       = request.form.get('email', '').strip()
    password    = request.form.get('password', '')
    full_name   = request.form.get('full_name', '').strip()
    role        = request.form.get('role', '').strip()
    institution = request.form.get('institution', '').strip()
    user_id     = request.form.get('user_id', '').strip()

    if not email or not password or not full_name or not role:
        return jsonify({"error": "Please fill in all required fields."}), 400

    connection = get_connection()
    cursor = connection.cursor()

    existing = cursor.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    if existing:
        connection.close()
        return jsonify({"error": "That email is already taken."}), 409

    cursor.execute(
        """INSERT INTO users (full_name, email, password_hash, role, institution, user_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (full_name, email, generate_password_hash(password, method="pbkdf2:sha256"),
         role, institution, user_id)
    )
    connection.commit()
    new_id = cursor.lastrowid
    session["user_id"] = new_id
    session["email"]   = email
    session["full_name"] = full_name
    connection.close()

    return jsonify({"status": "ok", "email": email})

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    connection = get_connection()
    cursor = connection.cursor()
    user = cursor.execute(
        "SELECT id, full_name, email, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    connection.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session["user_id"]   = user["id"]
    session["email"]     = user["email"]
    session["full_name"] = user["full_name"]
    return jsonify({"status": "ok", "email": user["email"]})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "ok"})

@app.route('/api/me', methods=['GET'])
def me():
    if "user_id" in session:
        return jsonify({
            "logged_in":  True,
            "email":      session.get("email"),
            "full_name":  session.get("full_name"),
            "user_id":    session.get("user_id")
        })
    return jsonify({"logged_in": False})

@app.route('/api/items', methods=['GET'])
def get_items():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    query = """
        SELECT items.id, items.title, items.description, items.category,
               items.image_url, items.status, items.posted_by, users.full_name as posted_by_name,
               EXISTS(
                   SELECT 1 FROM claim_requests cr
                   WHERE cr.item_id = items.id AND cr.status = 'pending'
               ) AS has_pending_request
        FROM items
        LEFT JOIN users ON items.posted_by = users.id
    """
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

    query += """ ORDER BY
        CASE items.status WHEN 'available' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END ASC,
        items.id DESC
    """

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    connection.close()

    items = []
    for row in rows:
        item = dict(row)
        item["has_pending_request"] = bool(item["has_pending_request"])
        items.append(item)

    return jsonify(items)

@app.route('/items', methods=['POST'])
def handle_item_submission():
    title       = request.form.get('item-title')
    description = request.form.get('description')
    category    = request.form.get('category')
    image_url   = request.form.get('image_url')
    posted_by   = session.get("user_id")

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO items (title, description, category, image_url, posted_by) VALUES (?, ?, ?, ?, ?)",
        (title, description, category, image_url, posted_by)
    )
    connection.commit()
    new_id = cursor.lastrowid
    connection.close()

    return jsonify({"status": "success", "id": new_id, "message": "Item posted!"})

@app.route('/items/<int:id>', methods=['GET'])
def get_item(id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT items.*, users.full_name as posted_by_name, users.email as posted_by_email,
               users.availability as posted_by_availability
        FROM items
        LEFT JOIN users ON items.posted_by = users.id
        WHERE items.id = ?
    """, (id,))
    item = cursor.fetchone()

    if item is None:
        connection.close()
        return "Item not found", 404

    item = dict(item)
    current_user_id = session.get("user_id")
    is_owner = current_user_id is not None and current_user_id == item["posted_by"]

    claim_requests = []
    my_claim_status = None
    confirmed_claim = None

    cursor.execute(
        "SELECT 1 FROM claim_requests WHERE item_id = ? AND status = 'pending' LIMIT 1", (id,)
    )
    has_pending_request = cursor.fetchone() is not None

    if is_owner:
        cursor.execute("""
            SELECT claim_requests.id, claim_requests.status, claim_requests.created_at,
                   claim_requests.proof_details,
                   users.id as requester_id, users.full_name as requester_name
            FROM claim_requests
            JOIN users ON claim_requests.requested_by = users.id
            WHERE claim_requests.item_id = ? AND claim_requests.status IN ('pending', 'cancelled')
            ORDER BY claim_requests.id ASC
        """, (id,))
        claim_requests = [dict(row) for row in cursor.fetchall()]

    if item["status"] in ("pending", "claimed"):
        cursor.execute("""
            SELECT users.id as requester_id, users.full_name as requester_name,
                   users.email as requester_email, users.availability as requester_availability
            FROM claim_requests
            JOIN users ON claim_requests.requested_by = users.id
            WHERE claim_requests.item_id = ? AND claim_requests.status = 'confirmed'
            LIMIT 1
        """, (id,))
        row = cursor.fetchone()
        confirmed_claim = dict(row) if row else None

    if not is_owner and current_user_id is not None:
        cursor.execute("""
            SELECT status FROM claim_requests
            WHERE item_id = ? AND requested_by = ?
            ORDER BY id DESC LIMIT 1
        """, (id, current_user_id))
        row = cursor.fetchone()
        my_claim_status = row["status"] if row else None

    connection.close()

    return render_template(
        'item.html',
        item=item,
        is_owner=is_owner,
        claim_requests=claim_requests,
        my_claim_status=my_claim_status,
        confirmed_claim=confirmed_claim,
        has_pending_request=has_pending_request
    )

@app.route('/api/items/<int:id>/claim', methods=['POST'])
def create_claim_request(id):
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Please log in to claim an item."}), 401

    proof_details = request.form.get('proof_details', '').strip()
    if not proof_details:
        return jsonify({"error": "Please describe details that prove you're the true owner."}), 400

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, status, posted_by FROM items WHERE id = ?", (id,))
    item = cursor.fetchone()

    if item is None:
        connection.close()
        return "Item not found", 404

    if item["posted_by"] == user_id:
        connection.close()
        return jsonify({"error": "You can't claim your own item."}), 400

    if item["status"] == "claimed":
        connection.close()
        return jsonify({"error": "This item has already been claimed."}), 409

    if item["status"] == "pending":
        connection.close()
        return jsonify({"error": "This item's claim is already being finalized."}), 409

    existing = cursor.execute(
        "SELECT id, status FROM claim_requests WHERE item_id = ? AND requested_by = ? ORDER BY id DESC LIMIT 1",
        (id, user_id)
    ).fetchone()

    if existing and existing["status"] == "pending":
        connection.close()
        return jsonify({"status": "ok", "claim_status": "pending"})

    cursor.execute(
        "INSERT INTO claim_requests (item_id, requested_by, status, proof_details) VALUES (?, ?, 'pending', ?)",
        (id, user_id, proof_details)
    )
    connection.commit()
    connection.close()

    return jsonify({"status": "ok", "claim_status": "pending"})

@app.route('/api/items/<int:item_id>/claim-requests/<int:request_id>/confirm', methods=['POST'])
def confirm_claim_request(item_id, request_id):
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Please log in."}), 401

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, posted_by, status FROM items WHERE id = ?", (item_id,))
    item = cursor.fetchone()

    if item is None:
        connection.close()
        return "Item not found", 404

    if item["posted_by"] != user_id:
        connection.close()
        return jsonify({"error": "Not authorized."}), 403

    claim_request = cursor.execute(
        "SELECT id, status FROM claim_requests WHERE id = ? AND item_id = ?",
        (request_id, item_id)
    ).fetchone()

    if claim_request is None:
        connection.close()
        return jsonify({"error": "Claim request not found."}), 404

    if claim_request["status"] != "pending":
        connection.close()
        return jsonify({"error": "This claim request is no longer pending."}), 409

    cursor.execute("UPDATE claim_requests SET status = 'confirmed' WHERE id = ?", (request_id,))
    cursor.execute(
        "UPDATE claim_requests SET status = 'declined' WHERE item_id = ? AND id != ? AND status = 'pending'",
        (item_id, request_id)
    )
    cursor.execute("UPDATE items SET status = 'pending' WHERE id = ?", (item_id,))
    connection.commit()
    connection.close()

    return jsonify({"status": "ok"})

@app.route('/api/items/<int:id>/confirm-claimed', methods=['POST'])
def confirm_item_claimed(id):
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Please log in."}), 401

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, posted_by, status FROM items WHERE id = ?", (id,))
    item = cursor.fetchone()

    if item is None:
        connection.close()
        return "Item not found", 404

    if item["posted_by"] != user_id:
        connection.close()
        return jsonify({"error": "Not authorized."}), 403

    if item["status"] != "pending":
        connection.close()
        return jsonify({"error": "This item isn't awaiting a claim confirmation."}), 409

    cursor.execute("UPDATE items SET status = 'claimed' WHERE id = ?", (id,))
    connection.commit()
    connection.close()

    return jsonify({"status": "ok"})

@app.route('/api/items/<int:id>/claim/cancel', methods=['POST'])
def cancel_claim_request(id):
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Please log in."}), 401

    connection = get_connection()
    cursor = connection.cursor()

    claim_request = cursor.execute(
        "SELECT id, status FROM claim_requests WHERE item_id = ? AND requested_by = ? ORDER BY id DESC LIMIT 1",
        (id, user_id)
    ).fetchone()

    if claim_request is None or claim_request["status"] != "pending":
        connection.close()
        return jsonify({"error": "You don't have a pending request on this item."}), 409

    cursor.execute("UPDATE claim_requests SET status = 'cancelled' WHERE id = ?", (claim_request["id"],))
    connection.commit()
    connection.close()

    return jsonify({"status": "ok"})

@app.route('/users/<int:id>', methods=['GET'])
def get_user_profile(id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, full_name, email, role, institution, profile_photo, availability, created_at FROM users WHERE id = ?",
        (id,)
    )
    user = cursor.fetchone()

    if user is None:
        connection.close()
        return "User not found", 404

    cursor.execute(
        "SELECT id, title, category, image_url, status FROM items WHERE posted_by = ? ORDER BY id DESC",
        (id,)
    )
    items = cursor.fetchall()

    current_user_id = session.get("user_id")
    is_own_profile = current_user_id == id

    has_contact_access = is_own_profile
    if not has_contact_access and current_user_id is not None:
        cursor.execute("""
            SELECT 1 FROM claim_requests
            JOIN items ON claim_requests.item_id = items.id
            WHERE (items.posted_by = ? AND claim_requests.requested_by = ?)
               OR (items.posted_by = ? AND claim_requests.requested_by = ?)
            LIMIT 1
        """, (id, current_user_id, current_user_id, id))
        has_contact_access = cursor.fetchone() is not None

    connection.close()

    profile_user = dict(user)
    initials = "".join(part[0] for part in profile_user["full_name"].split() if part).upper()[:2]
    profile_user["initials"] = initials

    return render_template(
        'profile.html',
        profile_user=profile_user,
        items=[dict(row) for row in items],
        is_own_profile=is_own_profile,
        has_contact_access=has_contact_access
    )

@app.route('/api/users/<int:id>/availability', methods=['POST'])
def update_availability(id):
    if session.get("user_id") != id:
        return jsonify({"error": "Not authorized."}), 403

    availability = request.form.get('availability', '').strip()

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET availability = ? WHERE id = ?", (availability, id))
    connection.commit()
    connection.close()

    return jsonify({"status": "ok", "availability": availability})

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"incoming": [], "outgoing": []})

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT claim_requests.id, claim_requests.item_id, items.title AS item_title,
               users.full_name AS requester_name, claim_requests.status, claim_requests.created_at
        FROM claim_requests
        JOIN items ON claim_requests.item_id = items.id
        JOIN users ON claim_requests.requested_by = users.id
        WHERE items.posted_by = ? AND claim_requests.status IN ('pending', 'cancelled')
        ORDER BY claim_requests.id DESC
        LIMIT 20
    """, (user_id,))
    incoming = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT claim_requests.id, claim_requests.item_id, items.title AS item_title,
               claim_requests.status, claim_requests.created_at
        FROM claim_requests
        JOIN items ON claim_requests.item_id = items.id
        WHERE claim_requests.requested_by = ?
        ORDER BY claim_requests.id DESC
        LIMIT 20
    """, (user_id,))
    outgoing = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return jsonify({"incoming": incoming, "outgoing": outgoing})

if __name__ == '__main__':
 app.run(debug=True)