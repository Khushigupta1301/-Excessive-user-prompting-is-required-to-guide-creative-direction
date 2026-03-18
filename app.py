from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET")

CORS(app)

bcrypt = Bcrypt(app)
jwt = JWTManager(app)

limiter = Limiter(get_remote_address, app=app)

# fake storage (since you said you don't create database)
users = {}
demo_requests = []
sales_contacts = []

# -----------------------
# AUTH APIs
# -----------------------

@app.route("/api/v1/auth/signup", methods=["POST"])
def signup():

    data = request.json

    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if email in users:
        return jsonify({"message": "User already exists"}), 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    users[email] = {
        "name": name,
        "email": email,
        "password": hashed
    }

    return jsonify({"message": "User created successfully"})


@app.route("/api/v1/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():

    data = request.json

    email = data.get("email")
    password = data.get("password")

    user = users.get(email)

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"message": "Invalid credentials"}), 401

    token = create_access_token(identity=email)

    return jsonify({"token": token})


@app.route("/api/v1/auth/me")
@jwt_required()
def me():

    email = get_jwt_identity()
    user = users.get(email)

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
    user = users.get(email)

    return jsonify(user)


@app.route("/api/v1/users/profile", methods=["PATCH"])
@jwt_required()
def update_profile():

    email = get_jwt_identity()
    data = request.json

    user = users[email]

    if "name" in data:
        user["name"] = data["name"]

    return jsonify({"message": "Profile updated"})


@app.route("/api/v1/users/password", methods=["PATCH"])
@jwt_required()
def change_password():

    email = get_jwt_identity()
    data = request.json

    new_password = data.get("new_password")

    users[email]["password"] = bcrypt.generate_password_hash(new_password).decode("utf-8")

    return jsonify({"message": "Password updated"})


# -----------------------
# FORM APIs
# -----------------------

@app.route("/api/v1/forms/book-demo", methods=["POST"])
def book_demo():

    data = request.json
    demo_requests.append(data)

    return jsonify({"message": "Demo request submitted"})


@app.route("/api/v1/forms/contact-sales", methods=["POST"])
def contact_sales():

    data = request.json
    sales_contacts.append(data)

    return jsonify({"message": "Sales request submitted"})


@app.route("/api/v1/forms/newsletter", methods=["POST"])
def newsletter():

    data = request.json

    return jsonify({"message": "Subscribed successfully"})


# -----------------------
# DASHBOARD APIs
# -----------------------

@app.route("/api/v1/dashboard/summary")
def dashboard_summary():

    return jsonify({
        "total_users": len(users),
        "demo_requests": len(demo_requests),
        "sales_contacts": len(sales_contacts)
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
    return {"message": "Backend is running"}

if __name__ == "__main__":
    app.run(debug=True)