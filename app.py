import os
import re
import uuid
from datetime import timedelta
from functools import wraps
from flask import Flask, jsonify, render_template, request, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_connection
from init_db import create_dismissed_notifications_table

app = Flask(__name__)

# `python app.py` = development on your own computer. Anywhere else (e.g.
# PythonAnywhere, which imports this file instead) counts as running online.
IS_DEV = __name__ == "__main__"

# The secret key signs login cookies. The fallback is public on GitHub, so it's
# only allowed in development; online the app refuses to start without a real key.
app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    if not IS_DEV:
        raise RuntimeError("SECRET_KEY is not set. Set it before running the app online.")
    app.secret_key = "dev-secret-change-me"

# Basic protection against other websites submitting forms as a logged-in user:
# don't send the login cookie with requests that start on another site, and
# online (which uses HTTPS) only send it over HTTPS.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = not IS_DEV
# How long "Remember me" keeps someone logged in
app.permanent_session_lifetime = timedelta(days=30)

MIN_PASSWORD_LENGTH = 8
MAX_AVAILABILITY_LENGTH = 500

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB per request

# Add tables introduced after the database was first created
_connection = get_connection()
create_dismissed_notifications_table(_connection.cursor())
_connection.commit()
_connection.close()

@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "Image is too large. Maximum size is 5 MB."}), 413

def save_uploaded_image(file):
    """Save an uploaded image and return its public URL, or None if the file isn't an allowed image."""
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS or not (file.mimetype or "").startswith("image/"):
        return None
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return f"/static/uploads/{filename}"

# Each user may send at most this many claim requests for one item
# (cancelled and declined ones count too).
MAX_CLAIM_ATTEMPTS = 3

def is_locked(item):
    """A post can't be edited or deleted once a claimant is confirmed or it's claimed."""
    return item["status"] in ("pending", "claimed")

LOCKED_MESSAGE = "This post can't be changed once a claimant is confirmed."

def delete_uploaded_image(image_url):
    """Remove a previously uploaded image file. External image URLs are left alone."""
    prefix = "/static/uploads/"
    if not image_url or not image_url.startswith(prefix):
        return
    path = os.path.join(UPLOAD_FOLDER, os.path.basename(image_url))
    if os.path.isfile(path):
        os.remove(path)

@app.route('/')
def index():
    return render_template('index.html')

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
    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters."}), 400
    if password != request.form.get('confirm_password', ''):
        return jsonify({"error": "Passwords don't match."}), 400

    connection = get_connection()
    cursor = connection.cursor()

    existing = cursor.execute(
        "SELECT id FROM users WHERE email = ?", (email,)
    ).fetchone()
    if existing:
        connection.close()
        return jsonify({"error": "That email is already taken."}), 409

    # Optional profile photo, saved only once everything else is valid
    profile_photo = None
    photo_file = request.files.get('profile_photo')
    if photo_file and photo_file.filename:
        profile_photo = save_uploaded_image(photo_file)
        if profile_photo is None:
            connection.close()
            return jsonify({"error": "Please upload a PNG, JPG, GIF or WEBP image."}), 400

    cursor.execute(
        """INSERT INTO users (full_name, email, password_hash, role, institution, user_id, profile_photo)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (full_name, email, generate_password_hash(password, method="pbkdf2:sha256"),
         role, institution, user_id, profile_photo)
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
    # Ticked: keep the login for 30 days. Unticked: it ends when the browser closes.
    session.permanent = request.form.get('remember_me') == 'on'
    return jsonify({"status": "ok", "email": user["email"]})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "ok"})

@app.route('/api/me', methods=['GET'])
def me():
    if "user_id" in session:
        connection = get_connection()
        row = connection.execute(
            "SELECT profile_photo FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        connection.close()
        return jsonify({
            "logged_in":     True,
            "email":         session.get("email"),
            "full_name":     session.get("full_name"),
            "user_id":       session.get("user_id"),
            "profile_photo": row["profile_photo"] if row else None
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
    posted_by = session.get("user_id")
    if posted_by is None:
        return jsonify({"error": "Please log in to post an item."}), 401

    title       = request.form.get('item-title', '').strip()
    description = request.form.get('description', '').strip()
    category    = request.form.get('category', '').strip()
    image_file  = request.files.get('image')

    if not title or not description:
        return jsonify({"error": "Title and description are required."}), 400
    if category not in ('lost', 'found', 'trade'):
        return jsonify({"error": "Please select a valid category."}), 400

    image_url = None
    if image_file and image_file.filename:
        image_url = save_uploaded_image(image_file)
        if image_url is None:
            return jsonify({"error": "Please upload a PNG, JPG, GIF or WEBP image."}), 400

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

@app.route('/items/<int:id>/edit', methods=['GET'])
def edit_item_page(id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect('/login')

    connection = get_connection()
    item = connection.execute("SELECT * FROM items WHERE id = ?", (id,)).fetchone()
    connection.close()

    if item is None:
        return "Item not found", 404
    if item["posted_by"] != user_id:
        return "You can only edit your own posts.", 403
    if is_locked(item):
        return LOCKED_MESSAGE, 403

    return render_template('list-item-form.html', item=dict(item))

@app.route('/api/items/<int:id>/edit', methods=['POST'])
def update_item(id):
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Please log in."}), 401

    title        = request.form.get('item-title', '').strip()
    description  = request.form.get('description', '').strip()
    category     = request.form.get('category', '').strip()
    remove_image = request.form.get('remove_image') == '1'
    image_file   = request.files.get('image')

    if not title or not description:
        return jsonify({"error": "Title and description are required."}), 400
    if category not in ('lost', 'found', 'trade'):
        return jsonify({"error": "Please select a valid category."}), 400

    connection = get_connection()
    cursor = connection.cursor()
    item = cursor.execute("SELECT id, posted_by, image_url, status FROM items WHERE id = ?", (id,)).fetchone()

    if item is None:
        connection.close()
        return jsonify({"error": "Item not found."}), 404
    if item["posted_by"] != user_id:
        connection.close()
        return jsonify({"error": "Not authorized."}), 403
    if is_locked(item):
        connection.close()
        return jsonify({"error": LOCKED_MESSAGE}), 409

    old_image_url = item["image_url"]
    image_url = old_image_url
    if image_file and image_file.filename:
        image_url = save_uploaded_image(image_file)
        if image_url is None:
            connection.close()
            return jsonify({"error": "Please upload a PNG, JPG, GIF or WEBP image."}), 400
    elif remove_image:
        image_url = None

    cursor.execute(
        "UPDATE items SET title = ?, description = ?, category = ?, image_url = ? WHERE id = ?",
        (title, description, category, image_url, id)
    )
    connection.commit()
    connection.close()

    if image_url != old_image_url:
        delete_uploaded_image(old_image_url)

    return jsonify({"status": "success", "id": id, "message": "Item updated!"})

@app.route('/api/items/<int:id>/delete', methods=['POST'])
def delete_item(id):
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Please log in."}), 401

    connection = get_connection()
    cursor = connection.cursor()
    item = cursor.execute("SELECT id, posted_by, image_url, status FROM items WHERE id = ?", (id,)).fetchone()

    if item is None:
        connection.close()
        return jsonify({"error": "Item not found."}), 404
    if item["posted_by"] != user_id:
        connection.close()
        return jsonify({"error": "Not authorized."}), 403
    if is_locked(item):
        connection.close()
        return jsonify({"error": LOCKED_MESSAGE}), 409

    pending = cursor.execute(
        "SELECT 1 FROM claim_requests WHERE item_id = ? AND status = 'pending' LIMIT 1", (id,)
    ).fetchone()
    if pending:
        connection.close()
        return jsonify({"error": "Decline or wait for the pending claim requests before deleting this post."}), 409

    # Only cancelled/declined requests are left at this point
    cursor.execute("DELETE FROM claim_requests WHERE item_id = ?", (id,))
    cursor.execute("DELETE FROM items WHERE id = ?", (id,))
    connection.commit()
    connection.close()

    delete_uploaded_image(item["image_url"])

    return jsonify({"status": "ok"})

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
    attempts_used = 0

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

        cursor.execute(
            "SELECT COUNT(*) FROM claim_requests WHERE item_id = ? AND requested_by = ?",
            (id, current_user_id)
        )
        attempts_used = cursor.fetchone()[0]

    connection.close()

    return render_template(
        'item.html',
        item=item,
        is_owner=is_owner,
        claim_requests=claim_requests,
        my_claim_status=my_claim_status,
        confirmed_claim=confirmed_claim,
        has_pending_request=has_pending_request,
        is_locked=is_locked(item),
        attempts_used=attempts_used,
        attempts_left=max(MAX_CLAIM_ATTEMPTS - attempts_used, 0)
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

    attempts_used = cursor.execute(
        "SELECT COUNT(*) FROM claim_requests WHERE item_id = ? AND requested_by = ?",
        (id, user_id)
    ).fetchone()[0]
    if attempts_used >= MAX_CLAIM_ATTEMPTS:
        connection.close()
        return jsonify({"error": f"You've used all {MAX_CLAIM_ATTEMPTS} requests for this item."}), 403

    cursor.execute(
        "INSERT INTO claim_requests (item_id, requested_by, status, proof_details) VALUES (?, ?, 'pending', ?)",
        (id, user_id, proof_details)
    )
    connection.commit()
    connection.close()

    return jsonify({"status": "ok", "claim_status": "pending"})

@app.route('/api/items/<int:item_id>/claim-requests/<int:request_id>/decline', methods=['POST'])
def decline_claim_request(item_id, request_id):
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Please log in."}), 401

    connection = get_connection()
    cursor = connection.cursor()
    item = cursor.execute("SELECT id, posted_by FROM items WHERE id = ?", (item_id,)).fetchone()

    if item is None:
        connection.close()
        return jsonify({"error": "Item not found."}), 404
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

    # 'rejected' = turned down by the owner; 'declined' is used when someone
    # else's request was confirmed instead.
    cursor.execute("UPDATE claim_requests SET status = 'rejected' WHERE id = ?", (request_id,))
    connection.commit()
    connection.close()

    return jsonify({"status": "ok"})

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
    if len(availability) > MAX_AVAILABILITY_LENGTH:
        return jsonify({"error": f"Availability can't be longer than {MAX_AVAILABILITY_LENGTH} characters."}), 400

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET availability = ? WHERE id = ?", (availability, id))
    connection.commit()
    connection.close()

    return jsonify({"status": "ok", "availability": availability})

@app.route('/api/users/<int:id>/photo', methods=['POST'])
def update_profile_photo(id):
    if session.get("user_id") != id:
        return jsonify({"error": "Not authorized."}), 403

    photo_file = request.files.get('profile_photo')
    if not photo_file or not photo_file.filename:
        return jsonify({"error": "Please choose a photo."}), 400
    new_photo = save_uploaded_image(photo_file)
    if new_photo is None:
        return jsonify({"error": "Please upload a PNG, JPG, GIF or WEBP image."}), 400

    connection = get_connection()
    old_photo = connection.execute("SELECT profile_photo FROM users WHERE id = ?", (id,)).fetchone()["profile_photo"]
    connection.execute("UPDATE users SET profile_photo = ? WHERE id = ?", (new_photo, id))
    connection.commit()
    connection.close()

    delete_uploaded_image(old_photo)
    return jsonify({"status": "ok", "profile_photo": new_photo})

@app.route('/api/users/<int:id>/photo/delete', methods=['POST'])
def remove_profile_photo(id):
    if session.get("user_id") != id:
        return jsonify({"error": "Not authorized."}), 403

    connection = get_connection()
    old_photo = connection.execute("SELECT profile_photo FROM users WHERE id = ?", (id,)).fetchone()["profile_photo"]
    connection.execute("UPDATE users SET profile_photo = NULL WHERE id = ?", (id,))
    connection.commit()
    connection.close()

    delete_uploaded_image(old_photo)
    return jsonify({"status": "ok"})

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
          AND NOT EXISTS (
              SELECT 1 FROM dismissed_notifications d
              WHERE d.user_id = ?
                AND d.notif_id = 'incoming-' || claim_requests.id || '-' || claim_requests.status
          )
        ORDER BY claim_requests.id DESC
        LIMIT 20
    """, (user_id, user_id))
    incoming = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT claim_requests.id, claim_requests.item_id, items.title AS item_title,
               claim_requests.status, claim_requests.created_at
        FROM claim_requests
        JOIN items ON claim_requests.item_id = items.id
        WHERE claim_requests.requested_by = ?
          AND NOT EXISTS (
              SELECT 1 FROM dismissed_notifications d
              WHERE d.user_id = ?
                AND d.notif_id = 'outgoing-' || claim_requests.id || '-' || claim_requests.status
          )
        ORDER BY claim_requests.id DESC
        LIMIT 20
    """, (user_id, user_id))
    outgoing = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return jsonify({"incoming": incoming, "outgoing": outgoing})

@app.route('/api/notifications/dismiss', methods=['POST'])
def dismiss_notification():
    user_id = session.get("user_id")
    if user_id is None:
        return jsonify({"error": "Please log in."}), 401

    notif_id = request.form.get('notif_id', '').strip()
    if not re.fullmatch(r"(incoming|outgoing)-\d+-[a-z]+", notif_id):
        return jsonify({"error": "Invalid notification."}), 400

    connection = get_connection()
    connection.execute(
        "INSERT OR IGNORE INTO dismissed_notifications (user_id, notif_id) VALUES (?, ?)",
        (user_id, notif_id)
    )
    connection.commit()
    connection.close()

    return jsonify({"status": "ok"})

if __name__ == '__main__':
 app.run(debug=True)