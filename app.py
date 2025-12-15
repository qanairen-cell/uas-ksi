from flask import Flask, render_template, request, redirect, session, flash, url_for # <<< TAMBAH: flash, url_for
from utils.auth import (
    register_user,
    check_login,
    check_login_by_id,
    get_all_users,
    # <<< FUNGSI BARU UNTUK LUPA KATA SANDI (Anda harus menambahkannya di utils/auth.py)
    generate_reset_token,
    validate_reset_token,
    reset_user_password
)
from utils.audit import log_login
from utils.otp import generate_otp, verify_otp
from utils.mailer import send_email
from utils.decorators import login_required, admin_required
import os
import secrets # <<< TAMBAH: untuk membuat token reset yang aman
from datetime import datetime, timedelta # <<< TAMBAH: untuk menampilkan sisa waktu lockout

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "development-secret")

@app.route("/")
def home():
    # Ini adalah halaman index utama
    return render_template("index.html")

# =======================
# LOGIN PAGE (Redirect ke /login)
# =======================
# Catatan: Route /login_page dihapus karena konflik routing di atas.
# Kita pakai /login untuk menampilkan form.

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
        flash("Registrasi berhasil. Silakan login.", "success")
        return redirect("/login")
    
    flash(message, "danger")
    return render_template("register.html"), 400


# =======================
# LOGIN (STEP 1) - MODIFIKASI BATAS 10 KALI
# =======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        # Halaman login akan menampilkan pesan flash dari redirect sebelumnya
        return render_template("login.html")

    # ========== POST ==========
    email = request.form["email"]
    password = request.form["password"]

    # check_login (di utils/auth) kini harus mengembalikan status
    # 1. Objek user (Sukses)
    # 2. None (Gagal / Password salah)
    # 3. Tuple ('LOCKED', datetime_object) (Akun terkunci)
    user_or_status = check_login(email, password)
    
    # 1. LOGIKA LOCKOUT (10 KALI PERCOBAAN)
    if isinstance(user_or_status, tuple) and user_or_status[0] == 'LOCKED':
        lockout_until = user_or_status[1]
        remaining_time = lockout_until - datetime.now()
        remaining_str = str(remaining_time).split('.')[0]
        
        flash(f"Akun terkunci karena terlalu banyak percobaan. Coba lagi dalam {remaining_str}.", "danger")
        return redirect("/login")
        
    # 2. LOGIKA GAGAL (Credential Mismatch)
    if not user_or_status:
        # check_login di utils/auth diasumsikan sudah menghitung percobaan gagal di DB
        flash("Email atau kata sandi salah.", "danger")
        return redirect("/login")

    # 3. LOGIKA SUKSES
    user = user_or_status 

    otp = generate_otp(user["id"])
    send_email(
        user["email"],
        "Kode OTP Login",
        f"Kode OTP kamu: {otp}"
    )

    session["otp_user"] = user["id"]
    flash("Kode OTP telah dikirim ke email Anda.", "success")
    return redirect("/otp")


# =======================
# OTP VERIFICATION (STEP 2)
# =======================
@app.route("/otp", methods=["GET", "POST"])
def otp_verify():
    if "otp_user" not in session:
        flash("Silakan login terlebih dahulu.", "warning")
        return redirect("/login") # Ubah redirect ke /login

    if request.method == "GET":
        return render_template("otp.html")

    user_id = session["otp_user"]
    otp_input = request.form["otp"]

    ip = request.remote_addr
    ua = request.headers.get("User-Agent")

    if verify_otp(user_id, otp_input):
        user = check_login_by_id(user_id) # Ambil data user lagi
        
        # Inisialisasi session user
        session["user_id"] = user["id"]
        session["email"] = user["email"]
        session["role"] = user["role"]

        session.pop("otp_user")
        log_login(user_id, ip, ua, "success")
        flash("Verifikasi berhasil. Selamat datang!", "success")
        return redirect("/dashboard")

    log_login(user_id, ip, ua, "failed")
    flash("OTP salah atau kadaluarsa.", "danger")
    return redirect("/otp")


# ==================================
# LUPA KATA SANDI (FITUR BARU)
# ==================================

# STEP 1: Permintaan Token Reset
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html") # <<< Template baru

    # ========== POST ==========
    email = request.form.get("email")

    # generate_reset_token (di utils/auth) akan membuat dan menyimpan token di DB
    token = generate_reset_token(email)
    
    if token:
        # Buat tautan reset eksternal
        reset_url = request.url_root.rstrip('/') + url_for('reset_password', token=token)
        
        # Kirim email dengan tautan reset
        send_email(
             email,
             "Permintaan Atur Ulang Kata Sandi",
             f"Silakan klik tautan ini untuk mengatur ulang kata sandi Anda: {reset_url}. Tautan berlaku 1 jam."
        )

    # Selalu berikan pesan yang sama untuk keamanan
    flash("Klik tautan yang dikirim ke email untuk mengatur ulang kata sandi", "info")
    return redirect("/login")


# STEP 2: Atur Ulang Kata Sandi
@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    # 1. Validasi Token (di utils/auth)
    user_id = validate_reset_token(token)

    if not user_id:
        flash("Tautan reset kata sandi tidak valid atau sudah kedaluwarsa.", "danger")
        return redirect("/forgot_password")

    if request.method == "GET":
        return render_template("reset_password.html", token=token) # <<< Template baru

    # ========== POST: Setel Kata Sandi Baru ==========
    new_password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if new_password != confirm_password:
        flash("Kata sandi baru dan konfirmasi tidak cocok.", "danger")
        return render_template("reset_password.html", token=token)
        
    # 2. Update password dan hapus token (di utils/auth)
    success = reset_user_password(user_id, token, new_password)

    if success:
        flash("Kata sandi Anda berhasil diatur ulang. Silakan login.", "success")
        return redirect("/login")
    else:
        flash("Terjadi kesalahan saat menyimpan kata sandi. Coba lagi.", "danger")
        return redirect("/forgot_password")


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
    flash("Anda telah berhasil logout.", "info")
    return redirect("/")
