import bcrypt
import psycopg2
import psycopg2.extras # Diperlukan untuk DictCursor
import secrets # Untuk token reset yang aman
from datetime import datetime, timedelta # Untuk pelacakan waktu kunci dan kedaluwarsa token

# Diasumsikan get_db berada di utils/db.py
from utils.db import get_db

# =========================
# HELPER: FUNGSI UTILITY
# =========================

def execute_query(sql, params=None, fetch_one=False, fetch_all=False, commit=False):
    """Fungsi pembantu untuk menjalankan query ke DB."""
    conn = get_db()
    if conn is None:
        return None if fetch_one or fetch_all else False

    # Menggunakan DictCursor untuk mempermudah akses kolom DB
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    result = None
    
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
        if fetch_one:
            result = cur.fetchone()
        elif fetch_all:
            result = cur.fetchall()
    except Exception as e:
        print(f"Database error: {e}")
        if commit:
            conn.rollback()
    finally:
        cur.close()
        conn.close()
    
    return result

# =========================
# REGISTER USER
# =========================
def register_user(email, password, role="user"):
    # ... (Fungsi register_user tetap sama) ...
    # Menggunakan kode Anda yang sudah ada
    # Anda mungkin perlu mengganti conn.cursor() biasa dengan DictCursor jika menggunakan execute_query
    
    if role not in ("user", "admin"):
        role = "user"

    if len(password) < 8:
        return False, "Password terlalu pendek"

    conn = get_db()
    if conn is None:
        return False, "Koneksi database gagal"

    cur = conn.cursor()

    try:
        # PENTING: Perhatikan nama kolom 'password_hash' di DB
        hashed = bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt()
        ).decode()

        cur.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
            (email, hashed, role)
        )

        conn.commit()
        return True, "Registrasi berhasil"

    except Exception:
        conn.rollback()
        return False, "Email sudah terdaftar"

    finally:
        cur.close()
        conn.close()


# =======================================================================
# LOGIN EMAIL + PASSWORD (MODIFIKASI: BATAS PERCOBAAN 10 KALI)
# =======================================================================
def check_login(email, password):
    # Menggunakan execute_query untuk mengambil semua data user termasuk kolom baru
    user = execute_query(
        "SELECT id, email, password_hash, role, failed_login_attempts, lockout_until FROM users WHERE email = %s",
        (email,),
        fetch_one=True
    )
    
    # 1. User tidak ditemukan
    if not user:
        return None

    user_id = user["id"]
    stored_hash = user["password_hash"]
    failed_attempts = user["failed_login_attempts"]
    lockout_time = user["lockout_until"]
    
    # 2. Cek Lockout (Kunci Akun)
    if lockout_time and lockout_time > datetime.now():
        # Akun terkunci, kembalikan status kunci dan waktu unlock
        return ('LOCKED', lockout_time) 

    # 3. Verifikasi Kata Sandi
    if bcrypt.checkpw(password.encode(), stored_hash.encode()):
        # LOGIN BERHASIL: Reset penghitung kegagalan
        execute_query(
            "UPDATE users SET failed_login_attempts = 0, lockout_until = NULL WHERE id = %s",
            (user_id,),
            commit=True
        )
        return {
            "id": user_id,
            "email": user["email"],
            "role": user["role"]
        }

    else:
        # 4. LOGIN GAGAL: Tingkatkan Counter
        new_attempts = failed_attempts + 1
        
        if new_attempts >= 10:
            # Terapkan Lockout selama 30 menit (atau sesuai kebutuhan Anda)
            lockout_until = datetime.now() + timedelta(minutes=30) 
            execute_query(
                "UPDATE users SET failed_login_attempts = %s, lockout_until = %s WHERE id = %s",
                (new_attempts, lockout_until, user_id),
                commit=True
            )
        else:
            # Hanya update jumlah percobaan gagal
            execute_query(
                "UPDATE users SET failed_login_attempts = %s WHERE id = %s",
                (new_attempts, user_id),
                commit=True
            )
        
        # Selalu return None jika login gagal, app.py yang akan menampilkan pesan flash
        return None

# =========================
# LOGIN BY ID (OTP VERIFY)
# =========================
def check_login_by_id(user_id):
    # Menggunakan DictCursor untuk mempermudah akses
    user = execute_query(
        "SELECT id, email, role FROM users WHERE id = %s",
        (user_id,),
        fetch_one=True
    )

    if not user:
        return None

    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"]
    }


# =======================================================================
# FITUR LUPA KATA SANDI (3 FUNGSI BARU)
# =======================================================================

def generate_reset_token(email):
    """Membuat dan menyimpan token reset password untuk user"""
    user = execute_query(
        "SELECT id, email FROM users WHERE email = %s",
        (email,),
        fetch_one=True
    )

    if not user:
        return None

    user_id = user["id"]
    token = secrets.token_urlsafe(32) 
    expires_at = datetime.now() + timedelta(hours=1) # Token berlaku 1 jam

    # Hapus token lama untuk user ini dan masukkan yang baru
    execute_query("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,), commit=True)
    
    execute_query(
        "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
        (user_id, token, expires_at),
        commit=True
    )
    
    return token

def validate_reset_token(token):
    """Memeriksa token, waktu kedaluwarsa, dan mengembalikan user_id jika valid"""
    reset_record = execute_query(
        "SELECT user_id, expires_at FROM password_reset_tokens WHERE token = %s",
        (token,),
        fetch_one=True
    )

    if not reset_record:
        return None # Token tidak ditemukan

    if reset_record['expires_at'] < datetime.now():
        return None # Token sudah kedaluwarsa

    return reset_record['user_id']

def reset_user_password(user_id, token, new_password):
    """Mengupdate password user dan menghapus token"""
    
    try:
        # 1. Hash Kata Sandi Baru
        hashed = bcrypt.hashpw(
            new_password.encode(),
            bcrypt.gensalt()
        ).decode()

        # 2. Update Password di tabel users
        execute_query(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hashed, user_id),
            commit=True
        )

        # 3. Hapus Token (Invalidasi)
        execute_query(
            "DELETE FROM password_reset_tokens WHERE token = %s",
            (token,),
            commit=True
        )
        
        return True
        
    except Exception as e:
        print(f"Error resetting password: {e}")
        return False


# =========================
# ADMIN: AMBIL SEMUA USER
# =========================
# Catatan: Terdapat dua fungsi get_all_users di file asli Anda, saya satukan yang terakhir
def get_all_users():
    rows = execute_query("""
        SELECT id, email, role
        FROM users
        WHERE role = 'user'
        ORDER BY id
    """, fetch_all=True)

    if rows is None:
        return []

    return [
        {"id": r["id"], "email": r["email"], "role": r["role"]}
        for r in rows
    ]
