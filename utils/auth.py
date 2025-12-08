from utils.db import get_db
import bcrypt

# =========================
# REGISTER USER
# =========================
def register_user(email, password, role="user"):
    # Validasi role
    if role not in ("user", "admin"):
        role = "user"

    # Validasi password
    if len(password) < 8:
        return False, "Password terlalu pendek"

    conn = get_db()
    if conn is None:
        return False, "Koneksi database gagal"

    cur = conn.cursor()

    try:
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


# =========================
# LOGIN EMAIL + PASSWORD
# =========================
def check_login(email, password):
    conn = get_db()
    if conn is None:
        return None

    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, password_hash, role FROM users WHERE email = %s",
        (email,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    user_id, email_db, stored_hash, role = row

    if bcrypt.checkpw(password.encode(), stored_hash.encode()):
        return {
            "id": user_id,
            "email": email_db,
            "role": role
        }

    return None


# =========================
# LOGIN BY ID (OTP VERIFY)
# =========================
def check_login_by_id(user_id):
    conn = get_db()
    if conn is None:
        return None

    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, role FROM users WHERE id = %s",
        (user_id,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "role": row[2]
    }


# =========================
# ✅ ADMIN: AMBIL SEMUA USER
# =========================
def get_all_users():
    conn = get_db()
    if conn is None:
        return []

    cur = conn.cursor()
    cur.execute(
        "SELECT id, email, role, created_at FROM users ORDER BY id"
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows


def get_all_users():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, email, role
        FROM users
        WHERE role = 'user'
        ORDER BY id
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"id": r[0], "email": r[1], "role": r[2]}
        for r in rows
    ]

