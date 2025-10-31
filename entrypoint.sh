#!/bin/sh
# Tệp: fnb-smart-menu-backend/entrypoint.sh
# Mục đích: Script chạy đầu tiên khi container backend khởi động

echo "--- Chạy Entrypoint ---"

# 1. Đảm bảo các bảng trong database (đang được mount) đã được tạo
echo "Đang tạo bảng (nếu chưa có)..."
python models.py

# 2. Chạy kịch bản nhập hàng mẫu (seed)
# File seed.py của chúng ta đủ thông minh để kiểm tra
# và chỉ thêm dữ liệu nếu database còn trống.
echo "Đang nhập hàng mẫu (nếu cần)..."
python seed.py

# 3. Khởi động "Bộ não" (Uvicorn)
echo "Khởi động Uvicorn server tại 0.0.0.0:8000..."
# "exec" sẽ thay thế tiến trình 'sh' bằng 'uvicorn'
# đây là cách làm chuẩn để Docker quản lý tiến trình chính
exec uvicorn main:app --host 0.0.0.0 --port 8000