from flask import Flask, render_template, request, redirect, session
from utils.auth import (
    register_user,
    check_login,
    check_login_by_id,
    get_all_users
)
from utils.audit import log_login
from utils.otp import generate_otp, verify_otp
from utils.mailer import send_email
from utils.decorators import login_required, admin_required
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "development-secret")

@app.route("/")
def home():
    return render_template("index.html")


# =======================
# LOGIN PAGE
# =======================
@app.route("/")
def login_page():
    return render_template("login.html")


# =======================
# REGISTER
# =======================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    email = request.form["email"]
    password = request.form["password"]

    success, message = register_user(email, password)

    if success:
        return redirect("/")
    return message, 400


# =======================
# LOGIN (STEP 1)
# =======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    # ========== POST ==========
    email = request.form["email"]
    password = request.form["password"]

    user = check_login(email, password)

    if not user:
        return "Login gagal", 401

    otp = generate_otp(user["id"])
    send_email(
        user["email"],
        "Kode OTP Login",
        f"Kode OTP kamu: {otp}"
    )

    session["otp_user"] = user["id"]
    return redirect("/otp")



# =======================
# OTP VERIFICATION (STEP 2)
# =======================
@app.route("/otp", methods=["GET", "POST"])
def otp_verify():
    if "otp_user" not in session:
        return redirect("/")

    if request.method == "GET":
        return render_template("otp.html")

    user_id = session["otp_user"]
    otp_input = request.form["otp"]

    ip = request.remote_addr
    ua = request.headers.get("User-Agent")

    if verify_otp(user_id, otp_input):
        user = check_login_by_id(user_id)

        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["role"] = user["role"]

        session.pop("otp_user")
        log_login(user_id, ip, ua, "success")

        return redirect("/dashboard")

    log_login(user_id, ip, ua, "failed")
    return "OTP salah atau kadaluarsa", 401


# =======================
# DASHBOARD (ROLE AWARE)
# =======================
@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") == "admin":
        return render_template("dashboard_admin.html")
    return render_template("dashboard_user.html")


# =======================
# ADMIN PANEL - LIST USERS
# =======================
from utils.auth import get_all_users

@app.route("/admin/users")
@admin_required
def admin_users():
    users = get_all_users()
    return render_template("admin_users.html", users=users)



# =======================
# LOGOUT
# =======================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =======================
# MAIN
# =======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
