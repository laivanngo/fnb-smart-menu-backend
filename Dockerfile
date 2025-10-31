# Tệp: fnb-smart-menu-backend/Dockerfile
# Mục đích: Bản thiết kế "hộp" Backend FastAPI
# ĐÃ SỬA LỖI: Dùng Entrypoint để seed data

# 1. Chọn hệ điều hành và phiên bản Python
FROM python:3.10-slim

# 2. Đặt thư mục làm việc bên trong "hộp"
WORKDIR /app

# 3. Sao chép file danh sách vật liệu
COPY requirements.txt requirements.txt

# 4. Cài đặt "vật liệu"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Sao chép toàn bộ code của "Bộ não" vào "hộp"
COPY . .

# 6. Sao chép script khởi động (đã được cấp quyền +x)
COPY entrypoint.sh .

# 7. Mở "cổng" 8000 bên trong "hộp"
EXPOSE 8000

# 8. Lệnh để khởi động "hộp"
# Sẽ chạy script entrypoint.sh của chúng ta
ENTRYPOINT ["/app/entrypoint.sh"]

# Dòng CMD cũ (bị ENTRYPOINT ghi đè, nên ta xóa đi)
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]