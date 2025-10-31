# Tệp: schemas.py (Đã thêm is_out_of_stock)
# Mục đích: Định nghĩa các "biểu mẫu" (schemas) Pydantic

from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import models # Import models để dùng Enums

# --- Biểu mẫu cho Admin ---
class AdminBase(BaseModel):
    username: str

class AdminCreate(AdminBase):
    password: str

class Admin(AdminBase):
    id: int
    model_config = ConfigDict(from_attributes=True) # Sửa orm_mode

# --- Biểu mẫu cho Token (Đăng nhập) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Biểu mẫu cho Lựa chọn con (OptionValue) ---
class OptionValueBase(BaseModel):
    name: str
    price_adjustment: float

class OptionValueCreate(OptionValueBase):
    pass

class OptionValue(OptionValueBase):
    id: int
    option_id: int
    model_config = ConfigDict(from_attributes=True) # Sửa orm_mode

# --- Biểu mẫu cho Nhóm Tùy chọn (Option) ---
class OptionBase(BaseModel):
    name: str
    type: models.OptionType
    display_order: int = 0 # Thêm display_order

class OptionCreate(OptionBase):
    pass # Không cần display_order khi tạo

class Option(OptionBase):
    id: int
    values: List[OptionValue] = []
    model_config = ConfigDict(from_attributes=True) # Sửa orm_mode

# --- Biểu mẫu cho Sản phẩm (Product) ---
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    base_price: float
    image_url: Optional[str] = None
    is_best_seller: Optional[bool] = False
    is_out_of_stock: Optional[bool] = False # <-- THÊM DÒNG NÀY [cite: 416]

class ProductCreate(ProductBase):
    category_id: int

class Product(ProductBase):
    id: int
    category_id: int
    options: List[Option] = [] # Options được trả về đã được sắp xếp bởi CRUD
    model_config = ConfigDict(from_attributes=True) # Sửa orm_mode

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    image_url: Optional[str] = None
    is_best_seller: Optional[bool] = None
    category_id: Optional[int] = None
    is_out_of_stock: Optional[bool] = None # <-- THÊM DÒNG NÀY [cite: 428]

class ProductLinkOptionsRequest(BaseModel):
    option_ids: List[int]

# --- Biểu mẫu cho Danh mục (Category) ---
class CategoryBase(BaseModel):
    name: str
    display_order: Optional[int] = 0

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int
    # Không cần trả products ở đây cho API admin categories
    # products: List[Product] = []
    model_config = ConfigDict(from_attributes=True) # Sửa orm_mode

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    display_order: Optional[int] = None

# --- Biểu mẫu cho Voucher ---
class VoucherBase(BaseModel):
    code: str
    description: Optional[str] = None
    type: str # 'percentage' hoặc 'fixed'
    value: float
    min_order_value: float = 0
    max_discount: Optional[float] = None
    is_active: bool = True

class VoucherCreate(VoucherBase):
    pass

class Voucher(VoucherBase):
    id: int
    model_config = ConfigDict(from_attributes=True) # Sửa orm_mode

# --- Biểu mẫu Công khai (Public Schemas) ---
class PublicOptionValue(BaseModel):
    id: int
    name: str
    price_adjustment: float
    model_config = ConfigDict(from_attributes=True)

class PublicOption(BaseModel):
    id: int
    name: str
    type: models.OptionType
    display_order: int # Thêm thứ tự
    values: List[PublicOptionValue] = []
    model_config = ConfigDict(from_attributes=True)

class PublicProduct(BaseModel):
    id: int
    name: str
    description: Optional[str]
    base_price: float
    image_url: Optional[str]
    is_best_seller: bool
    is_out_of_stock: bool # <-- THÊM DÒNG NÀY [cite: 438]
    options: List[PublicOption] = [] # Đã được sắp xếp bởi CRUD
    model_config = ConfigDict(from_attributes=True)

class PublicCategory(BaseModel):
    id: int
    name: str
    display_order: int
    products: List[PublicProduct] = [] # Products đã chứa options sắp xếp
    model_config = ConfigDict(from_attributes=True)

# --- Biểu mẫu cho Luồng Đặt hàng (Công khai) ---
class OrderItemOptionCreate(BaseModel):
    option_value_id: int

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    note: Optional[str] = None
    options: List[int] # List of OptionValue IDs

class OrderCalculateRequest(BaseModel):
    items: List[OrderItemCreate]
    voucher_code: Optional[str] = None
    delivery_method: models.DeliveryMethod

class OrderCalculateResponse(BaseModel):
    sub_total: float
    delivery_fee: float
    discount_amount: float
    total_amount: float

class OrderCreate(OrderCalculateRequest):
    customer_name: str
    customer_phone: str
    customer_address: str
    customer_note: Optional[str] = None
    payment_method: models.PaymentMethod

class PublicOrderResponse(BaseModel): # Dùng cho xác nhận đặt hàng thành công
    id: int
    status: models.OrderStatus
    total_amount: float
    model_config = ConfigDict(from_attributes=True)

# --- Biểu mẫu Chi tiết Đơn hàng cho Admin ---
class OrderItemOptionDetail(BaseModel):
    option_name: str
    value_name: str
    added_price: float
    model_config = ConfigDict(from_attributes=True)

class OrderItemDetail(BaseModel):
    id: int
    product_name: str
    quantity: int
    item_price: float
    item_note: Optional[str] = None
    options_selected: List[OrderItemOptionDetail] = []
    model_config = ConfigDict(from_attributes=True)

class OrderDetail(BaseModel):
    id: int
    customer_name: str
    customer_phone: str
    customer_address: str
    customer_note: Optional[str] = None
    sub_total: float
    delivery_fee: float
    discount_amount: float
    total_amount: float
    status: models.OrderStatus
    payment_method: models.PaymentMethod
    delivery_method_selected: models.DeliveryMethod
    voucher_code: Optional[str] = None
    items: List[OrderItemDetail] = []
    model_config = ConfigDict(from_attributes=True)

# --- Biểu mẫu Danh sách Đơn hàng cho Admin (Thông tin cơ bản) ---
class AdminOrderListResponse(BaseModel):
    id: int
    total_amount: float
    status: models.OrderStatus
    # Có thể thêm created_at nếu cần
    model_config = ConfigDict(from_attributes=True)