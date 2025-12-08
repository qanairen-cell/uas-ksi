import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.db import get_db

conn = get_db()
cur = conn.cursor()

cur.execute("""
    SELECT user_id, ip_address, user_agent, status, created_at
    FROM login_audit
    ORDER BY created_at DESC
    LIMIT 20
""")

rows = cur.fetchall()

print("\n=== LOGIN LOGS (TERBARU) ===")
for r in rows:
    print(
        f"UserID: {r[0]} | "
        f"IP: {r[1]} | "
        f"Status: {r[3]} | "
        f"Waktu: {r[4]}"
    )

cur.close()
conn.close()
