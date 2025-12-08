from utils.db import get_db
from datetime import datetime

def log_login(user_id, ip_address, user_agent, status):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO login_audit
        (user_id, ip_address, user_agent, status, created_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, ip_address, user_agent, status, datetime.utcnow())
    )

    conn.commit()
    cur.close()
    conn.close()
