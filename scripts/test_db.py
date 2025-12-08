import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_db

conn = get_db()
if conn:
    print("✅ Koneksi database BERHASIL")
    conn.close()
else:
    print("❌ Koneksi database GAGAL")
