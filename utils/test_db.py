from db import get_db

conn = get_db()

if conn:
    print("Connected!")
    conn.close()
else:
    print("Failed!")
