import random
from datetime import datetime, timedelta
from utils.db import get_db

def generate_otp(user_id):
    otp = str(random.randint(100000, 999999))

    expires = datetime.utcnow() + timedelta(minutes=5)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO login_otp (user_id, otp_code, expires_at)
        VALUES (%s, %s, %s)
    """, (user_id, otp, expires))

    conn.commit()
    cur.close()
    conn.close()

    return otp


def verify_otp(user_id, otp_input):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id FROM login_otp
        WHERE user_id = %s
          AND otp_code = %s
          AND is_used = FALSE
          AND expires_at > NOW()
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id, otp_input))

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return False

    otp_id = row[0]

    cur.execute("""
        UPDATE login_otp
        SET is_used = TRUE
        WHERE id = %s
    """, (otp_id,))

    conn.commit()
    cur.close()
    conn.close()
    return True
