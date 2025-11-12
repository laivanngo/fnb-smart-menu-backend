# Tệp: models.py (Bản vá 1.9.1 - Sửa logic Sắp xếp)
# Mục đích: Định nghĩa cấu trúc "Kho dữ liệu" (Database)

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, Enum as SAEnum, DateTime, func
from sqlalchemy.orm import relationship, sessionmaker, DeclarativeBase
import enum

# --- Cấu hình cơ bản ---

# === THAY ĐỔI PHẦN NÀY ===
# Đọc thông tin CSDL từ biến môi trường
# os.getenv("TEN_BIEN", "gia_tri_mac_dinh")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "db") # 'db' sẽ là tên service CSDL trong docker-compose
DB_NAME = os.getenv("POSTGRES_DB", "fnb_db")
DB_PORT = os.getenv("DB_PORT", "5432")

# Tạo chuỗi kết nối mới cho PostgreSQL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Dòng SQLite cũ, bây giờ có thể XÓA hoặc GHI CHÚ (comment) lại:
# DATABASE_URL = "sqlite:////app/database_data/trasua_express.db"
# ========================

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Định nghĩa các ENUM ---
class OptionType(enum.Enum):
    CHON_1 = "CHON_1"
    CHON_NHIEU = "CHON_NHIEU"
class OrderStatus(enum.Enum):
    MOI = "MOI"
    DA_XAC_NHAN = "DA_XAC_NHAN"
    DANG_THUC_HIEN = "DANG_THUC_HIEN"
    DANG_GIAO = "DANG_GIAO"
    HOAN_TAT = "HOAN_TAT"
    DA_HUY = "DA_HUY"
class PaymentMethod(enum.Enum):
    TIEN_MAT = "TIEN_MAT"
    CHUYEN_KHOAN = "CHUYEN_KHOAN"
    MOMO = "MOMO"
class DeliveryMethod(enum.Enum):
    TIEU_CHUAN = "TIEU_CHUAN"
    NHANH = "NHANH"
class DeliveryAssignment(enum.Enum):
    CHUA_PHAN_CONG = "CHUA_PHAN_CONG"
    TU_GIAO = "TU_GIAO"
    THUE_SHIP = "THUE_SHIP"

# --- Bảng Liên kết (Bảng phụ) ---
class ProductOptionAssociation(Base):
    __tablename__ = "product_option_association"
    product_id = Column(Integer, ForeignKey("products.id"), primary_key=True)
    option_id = Column(Integer, ForeignKey("options.id"), primary_key=True)

# --- Các Bảng Chính ---
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # === SỬA DÒNG NÀY (Bản vá 1.9.1) ===
    # Yêu cầu Móng nhà tự sắp xếp Product theo display_order
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan", order_by="Product.display_order")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    base_price = Column(Float, nullable=False)
    image_url = Column(String)
    is_best_seller = Column(Boolean, default=False)
    display_order = Column(Integer, default=0) # Đã thêm ở 1.9
    is_out_of_stock = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="products")
    options = relationship("Option", secondary="product_option_association", back_populates="products")

class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    type = Column(SAEnum(OptionType), nullable=False, default=OptionType.CHON_NHIEU)
    display_order = Column(Integer, default=0) 
    
    values = relationship("OptionValue", back_populates="option", cascade="all, delete-orphan")
    products = relationship("Product", secondary="product_option_association", back_populates="options")

class OptionValue(Base):
    __tablename__ = "option_values"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price_adjustment = Column(Float, nullable=False, default=0)
    is_out_of_stock = Column(Boolean, default=False, nullable=False) # Đã thêm ở 1.2
    option_id = Column(Integer, ForeignKey("options.id"))
    option = relationship("Option", back_populates="values")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    customer_address = Column(String, nullable=False)
    customer_note = Column(String)
    sub_total = Column(Float, nullable=False)
    delivery_fee = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    status = Column(SAEnum(OrderStatus), nullable=False, default=OrderStatus.MOI)
    payment_method = Column(SAEnum(PaymentMethod), nullable=False, default=PaymentMethod.TIEN_MAT)
    delivery_method_selected = Column(SAEnum(DeliveryMethod), nullable=False)
    delivery_assignment = Column(SAEnum(DeliveryAssignment), default=DeliveryAssignment.CHUA_PHAN_CONG)
    voucher_code = Column(String, nullable=True)
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    item_price = Column(Float, nullable=False)
    item_note = Column(String)
    order_id = Column(Integer, ForeignKey("orders.id"))
    order = relationship("Order", back_populates="items")
    product_name = Column(String, nullable=False)
    options_selected = relationship("OrderItemOption", back_populates="order_item", cascade="all, delete-orphan")

class OrderItemOption(Base):
    __tablename__ = "order_item_options"
    id = Column(Integer, primary_key=True, index=True)
    option_name = Column(String, nullable=False)
    value_name = Column(String, nullable=False)
    added_price = Column(Float, nullable=False)
    order_item_id = Column(Integer, ForeignKey("order_items.id"))
    order_item = relationship("OrderItem", back_populates="options_selected")

class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    type = Column(String, nullable=False) # "percentage" or "fixed"
    value = Column(Float, nullable=False)
    min_order_value = Column(Float, default=0)
    max_discount = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

def create_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print("Đang tạo nền móng (database tables)...")
    create_tables()
    print("Nền móng (database tables) đã được tạo thành công!")