import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.db import get_db


def main():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id, email, role FROM users")
    users = cur.fetchall()

    print("=== DAFTAR USERS ===")
    for u in users:
        print(f"ID: {u[0]} | Email: {u[1]} | Role: {u[2]}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
