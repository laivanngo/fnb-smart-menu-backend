# File: websocket_manager.py
# Mục đích: Quản lý các kết nối WebSocket với admin

from fastapi import WebSocket
from typing import List
import json
from datetime import datetime

class ConnectionManager:
    """
    Quản lý các kết nối WebSocket
    
    Giải thích:
    - active_connections: Danh sách các admin đang kết nối
    - connect(): Thêm admin mới vào danh sách
    - disconnect(): Xóa admin ra khỏi danh sách
    - broadcast(): Gửi thông báo đến TẤT CẢ admin đang online
    """
    
    def __init__(self):
        # Danh sách lưu các kết nối WebSocket đang active
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """
        Khi admin mở trang, function này được gọi
        
        Bước thực hiện:
        1. Accept (chấp nhận) kết nối từ admin
        2. Thêm vào danh sách active_connections
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ Admin mới kết nối! Tổng: {len(self.active_connections)} admin đang online")
    
    def disconnect(self, websocket: WebSocket):
        """
        Khi admin đóng trang, function này được gọi
        
        Bước thực hiện:
        1. Xóa khỏi danh sách active_connections
        """
        self.active_connections.remove(websocket)
        print(f"❌ Admin ngắt kết nối! Còn: {len(self.active_connections)} admin đang online")
    
    async def broadcast(self, message: dict):
        """
        Gửi thông báo đến TẤT CẢ admin đang online
        
        Tham số:
        - message: Dictionary chứa thông tin cần gửi
        
        Ví dụ message:
        {
            "type": "new_order",
            "order_id": 123,
            "customer_name": "Nguyễn Văn A",
            "total_amount": 50000,
            "timestamp": "2025-11-13T10:30:00"
        }
        """
        # Danh sách admin bị lỗi kết nối
        disconnected = []
        
        # Gửi đến từng admin
        for connection in self.active_connections:
            try:
                # Gửi dữ liệu dạng JSON
                await connection.send_json(message)
                print(f"📤 Đã gửi thông báo: {message['type']}")
            except Exception as e:
                # Nếu gửi lỗi (admin đã offline), đánh dấu để xóa
                print(f"⚠️ Lỗi gửi đến admin: {e}")
                disconnected.append(connection)
        
        # Xóa các kết nối lỗi
        for connection in disconnected:
            try:
                self.active_connections.remove(connection)
            except:
                pass

# Tạo instance duy nhất (singleton pattern)
# Instance này sẽ được dùng chung trong toàn bộ app
manager = ConnectionManager()