#!/bin/sh
# Tệp: fnb-smart-menu-backend/entrypoint.sh
# Mục đích: Script chạy đầu tiên khi container backend khởi động

echo "--- Chạy Entrypoint ---"

# 1. Chạy "Người gác cổng" để chờ CSDL
echo "Đang chờ CSDL sẵn sàng..."
python wait-for-db.py

# 2. Đảm bảo các bảng trong database đã được tạo
echo "Đang tạo bảng (nếu chưa có)..."
python models.py

# 3. Chạy kịch bản nhập hàng mẫu (seed)
echo "Đang nhập hàng mẫu (nếu cần)..."
python seed.py

# 4. Khởi động "Bộ não" (Uvicorn)
echo "Khởi động Uvicorn server tại 0.0.0.0:8000..."
exec uvicorn main:app --host 0.0.0.0 --port 8000