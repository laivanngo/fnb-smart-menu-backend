# Tệp: fnb-smart-menu-backend/wait-for-db.py (TẠO MỚI)

import os
import time
import psycopg2
from psycopg2 import OperationalError

# Lấy thông tin CSDL từ biến môi trường (giống models.py)
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "fnb_db")

def check_db_connection():
    try:
        # Thử kết nối
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.close() # Nếu thành công, đóng lại và trả về True
        return True
    except OperationalError as e:
        # Nếu lỗi (ví dụ: "Connection refused")
        print(f"Lỗi kết nối: {e}")
        return False

print("--- Đang chờ CSDL sẵn sàng ---")
max_retries = 30 # Thử 30 lần
retries = 0
while retries < max_retries:
    if check_db_connection():
        print("--- CSDL đã sẵn sàng! ---")
        break # Thoát khỏi vòng lặp
    
    retries += 1
    print(f"CSDL chưa sẵn sàng, đang thử lại... (Lần {retries}/{max_retries})")
    time.sleep(2) # Chờ 2 giây rồi thử lại
    
if retries == max_retries:
    print("Lỗi: Không thể kết nối CSDL sau 60 giây. Bỏ cuộc.")
    exit(1) # Dừng script với mã lỗi

# Nếu mọi thứ OK, thoát với mã 0
exit(0)