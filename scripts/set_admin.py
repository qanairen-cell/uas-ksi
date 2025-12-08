import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_db


def make_admin(email):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET role = 'admin' WHERE email = %s",
        (email,)
    )

    if cur.rowcount == 0:
        print("❌ User tidak ditemukan")
    else:
        print("✅ User berhasil dijadikan ADMIN")

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    make_admin("mardiantikarim5@gmail.com")
