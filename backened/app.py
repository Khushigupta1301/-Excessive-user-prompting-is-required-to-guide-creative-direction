from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()
MONGO_URI = "mongodb+srv://akankshag826_db_user:akankkhushhim3@miniproject-cluster.ohfbkdo.mongodb.net/?appName=miniproject-cluster"

client = MongoClient(MONGO_URI)

db = client["miniproject"]

users_collection = db["users"]
demo_collection = db["demo_requests"]
sales_collection = db["sales_contacts"]
newsletter_collection = db["newsletter"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET")

CORS(app)

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

limiter = Limiter(get_remote_address, app=app)

demo_requests = []
sales_contacts = []
newsletter_subscriptions = []

# -----------------------
# AUTH APIs
# -----------------------

@app.route("/api/v1/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"message": "Name, email and password are required"}), 400

    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters"}), 400

    # Check if user already exists
    existing_user = users_collection.find_one({"email": email})

    if existing_user:
        return jsonify({"message": "User already exists"}), 400

    # Hash password
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Insert into MongoDB
    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password
    })

    return jsonify({"message": "User created successfully"}), 201


@app.route("/api/v1/auth/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password required"}), 400

    user = users_collection.find_one({"email": email})

    if not user:
        return jsonify({"message": "User not found"}), 404

    if not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid password"}), 401

    # Create JWT token
    access_token = create_access_token(identity=email)

    return jsonify({
        "message": "Login successful",
        "token": access_token
    }), 200


@app.route("/api/v1/auth/forgot-password", methods=["POST"])
def forgot_password():

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"message": "email is required"}), 400

    user = users_collection.find_one({"email": email})

    # still return same message for security
    return jsonify({"message": "If an account exists, reset instructions were sent"})


@app.route("/api/v1/auth/reset-password", methods=["POST"])
def reset_password():

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    new_password = data.get("new_password") or ""

    if not email or not new_password:
        return jsonify({"message": "email and new_password are required"}), 400

    if len(new_password) < 8:
        return jsonify({"message": "Password must be at least 8 characters"}), 400

    user = users_collection.find_one({"email": email})

    if not user:
        return jsonify({"message": "User not found"}), 404

    hashed_password = bcrypt.generate_password_hash(new_password).decode("utf-8")

    users_collection.update_one(
        {"email": email},
        {"$set": {"password": hashed_password}}
    )

    return jsonify({"message": "Password reset successful"})


@app.route("/api/v1/auth/me")
@jwt_required()
def me():

    email = get_jwt_identity()

    user = users_collection.find_one({"email": email})

    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({
        "name": user["name"],
        "email": user["email"]
    })


# -----------------------
# USER APIs
# -----------------------

@app.route("/api/v1/users/profile")
@jwt_required()
def profile():

    email = get_jwt_identity()

    user = users_collection.find_one({"email": email})

    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({
        "name": user["name"],
        "email": user["email"]
    })

@app.route("/api/v1/users/profile", methods=["PATCH"])
@jwt_required()
def update_profile():

    email = get_jwt_identity()
    data = request.get_json(silent=True) or {}

    update_data = {}

    if "name" in data:
        update_data["name"] = data["name"]

    if not update_data:
        return jsonify({"message": "Nothing to update"}), 400

    users_collection.update_one(
        {"email": email},
        {"$set": update_data}
    )

    return jsonify({"message": "Profile updated"})


# -----------------------
# FORM APIs
# -----------------------
@app.route("/api/v1/forms/book-demo", methods=["POST"])
def book_demo():

    data = request.get_json(silent=True) or {}

    if not data.get("email"):
        return jsonify({"message": "email is required"}), 400

    demo_collection.insert_one(data)

    return jsonify({"message": "Demo request submitted"})


@app.route("/api/v1/forms/contact-sales", methods=["POST"])
def contact_sales():

    data = request.get_json(silent=True) or {}

    if not data.get("email"):
        return jsonify({"message": "email is required"}), 400

    sales_collection.insert_one(data)

    return jsonify({"message": "Sales request submitted"})

@app.route("/api/v1/forms/newsletter", methods=["POST"])
def newsletter():

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"message": "email is required"}), 400

    existing = newsletter_collection.find_one({"email": email})

    if not existing:
        newsletter_collection.insert_one({"email": email})

    return jsonify({"message": "Subscribed successfully"})

# -----------------------
# DASHBOARD APIs
# -----------------------

@app.route("/api/v1/dashboard/summary")
def dashboard_summary():

    total_users = users_collection.count_documents({})
    demo_requests = demo_collection.count_documents({})
    sales_contacts = sales_collection.count_documents({})

    return jsonify({
        "total_users": total_users,
        "demo_requests": demo_requests,
        "sales_contacts": sales_contacts
    })


@app.route("/api/v1/dashboard/activity")
def dashboard_activity():

    return jsonify({
        "activity": "No activity yet"
    })


@app.route("/api/v1/dashboard/subscription")
def dashboard_subscription():

    return jsonify({
        "plan": "Free",
        "status": "Active"
    })


# -----------------------

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "homepage.html")


@app.route("/<path:filename>")
def serve_frontend_file(filename):
    file_path = os.path.join(FRONTEND_DIR, filename)

    if not os.path.isfile(file_path):
        abort(404)

    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug)