# Tệp: main.py (Bản HOÀN CHỈNH - Đã thêm Upload Image & Static Files)
# Mục đích: "Tổng hành dinh" của FastAPI, kết nối mọi thứ

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

# === THÊM IMPORT MỚI ===
from fastapi.staticfiles import StaticFiles # Để phục vụ file tĩnh
import shutil # Để lưu file
import os # Để tạo thư mục, lấy tên file
import uuid # Để tạo tên file duy nhất
# ========================

import crud, models, schemas, security
from models import SessionLocal, engine, Base
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FNB Smart Menu - Backend API")

# --- Cấu hình Thư mục Uploads ---
UPLOAD_DIRECTORY = "uploads" # Thư mục lưu ảnh (bên trong container)
STATIC_PATH = "/static" # Đường dẫn public để truy cập ảnh

# Tạo thư mục nếu chưa có
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# "Mở" thư mục uploads ra Internet qua đường dẫn /static
# Bất kỳ file nào trong UPLOAD_DIRECTORY sẽ truy cập được qua /static
# Quan trọng: Dòng này phải ở TRƯỚC các API router
app.mount(STATIC_PATH, StaticFiles(directory=UPLOAD_DIRECTORY), name="static")

# 2. Cấu hình CORS (Đã bao gồm tên miền production)
origins = [
    "http://localhost",
    "http://localhost:3000", # Frontend Khách hàng (local)
    "http://localhost:3001", # Frontend Admin (local)
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    
    # === TÊN MIỀN CÔNG KHAI ===
    "https://menu.fnbsmartmenu.com",
    "https://admin.fnbsmartmenu.com",
    "https://api.fnbsmartmenu.com" 
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Cho phép tất cả (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],
)


# 3. Hàm "trợ lý" để lấy "kho" (database)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Tạo Admin đầu tiên và Bảng khi khởi động
@app.on_event("startup")
def on_startup():
    print("Đang khởi động ứng dụng...")
    # Tạo bảng nếu chưa có
    models.create_tables()
    print("Kiểm tra/Tạo bảng hoàn tất.")
    # Tạo admin đầu tiên
    db = SessionLocal()
    admin = crud.get_admin_by_username(db, "admin")
    if not admin:
        print("Tạo tài khoản admin đầu tiên (admin/admin)...")
        admin_in = schemas.AdminCreate(username="admin", password="admin")
        crud.create_admin(db, admin_in)
        print("Tạo tài khoản admin thành công!")
    else:
        print("Tài khoản admin đã tồn tại.")
    db.close()
    print("Khởi động hoàn tất.")

# --- "CÁNH CỬA" CÔNG KHAI (KHÔNG cần "thẻ từ") ---

@app.get("/menu", response_model=List[schemas.PublicCategory])
def get_full_menu(db: Session = Depends(get_db)):
    """API CÔNG KHAI: Lấy toàn bộ Menu lồng nhau, đã sắp xếp"""
    return crud.get_public_menu(db)

@app.post("/orders/calculate", response_model=schemas.OrderCalculateResponse)
def calculate_order(
    order_data: schemas.OrderCalculateRequest,
    db: Session = Depends(get_db)
):
    """API CÔNG KHAI: Tính tiền giỏ hàng (kiểm tra SP, Option, Voucher)"""
    try:
        return crud.calculate_order_total(db, order_data)
    except HTTPException as e:
        # Nếu lỗi là do người dùng (400, 404), trả về lỗi đó
        if e.status_code < 500:
             raise e
        print(f"Lỗi khi tính toán đơn hàng: {e.detail}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi tính toán đơn hàng.")
    except Exception as e:
        print(f"Lỗi không xác định khi tính toán đơn hàng: {e}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống không xác định khi tính toán đơn hàng.")


@app.post("/orders", response_model=schemas.PublicOrderResponse, status_code=status.HTTP_201_CREATED)
def submit_new_order(
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db)
):
    """API CÔNG KHAI: Đặt hàng (tính tiền lại lần cuối và lưu)"""
    try:
        db_order = crud.create_order(db, order_data)
        return db_order
    except HTTPException as e:
        if e.status_code < 500:
            raise e
        print(f"Lỗi khi tạo đơn hàng: {e.detail}")
        raise HTTPException(status_code=500, detail="Lỗi hệ thống khi tạo đơn hàng.")
    except Exception as e:
        print(f"Lỗi không xác định khi tạo đơn hàng: {e}")
        raise HTTPException(status_code=500, detail="Không thể xử lý đơn hàng do lỗi hệ thống.")

# --- "CÁNH CỬA" QUẢN TRỊ (Bắt buộc phải có "thẻ từ") ---

# === Đăng nhập ===
@app.post("/admin/token", response_model=schemas.Token)
async def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """API ADMIN: Đăng nhập, lấy 'thẻ từ'"""
    admin = crud.get_admin_by_username(db, form_data.username)
    if not admin or not security.verify_password(form_data.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(data={"sub": admin.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/me", response_model=schemas.Admin)
async def read_admin_me(current_admin: models.Admin = Depends(security.get_current_admin)):
    """API ADMIN: Kiểm tra 'thẻ từ' và lấy thông tin user admin"""
    return current_admin

# === API UPLOAD ẢNH MỚI ===
@app.post("/admin/upload-image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...), 
    current_admin: models.Admin = Depends(security.get_current_admin)
):
    """
    API ADMIN: Nhận 1 file ảnh, lưu vào thư mục 'uploads'
    và trả về đường dẫn public (vd: /static/ten_file_duy_nhat.jpg)
    """
    # 1. Tạo tên file duy nhất
    file_extension = os.path.splitext(file.filename)[1] # Lấy đuôi file (vd: .jpg)
    if file_extension not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Định dạng file không hợp lệ. Chỉ chấp nhận .jpg, .png, .webp.")
        
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
    
    # 2. Lưu file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể lưu file: {e}")
    finally:
        file.file.close()
        
    # 3. Trả về đường dẫn public (bắt đầu bằng STATIC_PATH)
    public_url = os.path.join(STATIC_PATH, unique_filename)
    # Đảm bảo đường dẫn dùng dấu / (cho URL)
    public_url = public_url.replace("\\", "/") 
    
    return {"image_url": public_url}
# ==========================


# === Quản lý Danh mục (Category) ===
@app.post("/admin/categories/", response_model=schemas.Category, status_code=status.HTTP_201_CREATED)
def create_new_category(
    category: schemas.CategoryCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.create_category(db=db, category=category)

@app.get("/admin/categories/", response_model=List[schemas.Category])
def read_all_categories(
    db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.get_categories(db)

@app.put("/admin/categories/{category_id}", response_model=schemas.Category)
def update_existing_category(
    category_id: int, category: schemas.CategoryUpdate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_category = crud.update_category(db, category_id, category)
    if db_category is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy danh mục")
    return db_category

@app.delete("/admin/categories/{category_id}", response_model=schemas.Category)
def delete_existing_category(
    category_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_category = crud.delete_category(db, category_id)
    if db_category is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy danh mục")
    return db_category

# === Quản lý Sản phẩm (Product) ===
@app.post("/admin/products/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_new_product(
    product: schemas.ProductCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_category = crud.get_category(db, product.category_id)
    if not db_category: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Danh mục ID {product.category_id} không tồn tại.")
    return crud.create_product(db=db, product=product)

@app.get("/admin/products/", response_model=List[schemas.Product])
def read_all_products(
    db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.get_products(db)

@app.get("/admin/products/{product_id}", response_model=schemas.Product)
def read_one_product(
    product_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_product = crud.get_product(db, product_id)
    if db_product is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm")
    return db_product

@app.put("/admin/products/{product_id}", response_model=schemas.Product)
def update_existing_product(
    product_id: int, product: schemas.ProductUpdate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    if product.category_id is not None:
        db_category = crud.get_category(db, product.category_id)
        if not db_category: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Danh mục ID {product.category_id} không tồn tại.")
    db_product = crud.update_product(db, product_id, product)
    if db_product is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm")
    return db_product

@app.delete("/admin/products/{product_id}", response_model=schemas.Product)
def delete_existing_product(
    product_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_product = crud.delete_product(db, product_id)
    if db_product is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm")
    return db_product

# === Quản lý Tùy chọn (Options & Values) ===
@app.post("/admin/options/", response_model=schemas.Option, status_code=status.HTTP_201_CREATED)
def create_new_option(
    option: schemas.OptionCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.create_option(db=db, option=option)

@app.get("/admin/options/", response_model=List[schemas.Option])
def read_all_options(
    db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.get_options(db)

@app.delete("/admin/options/{option_id}", response_model=schemas.Option)
def delete_existing_option(
    option_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_option = crud.delete_option(db, option_id)
    if db_option is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Nhóm Tùy chọn")
    return db_option

@app.post("/admin/options/{option_id}/values/", response_model=schemas.OptionValue, status_code=status.HTTP_201_CREATED)
def create_new_option_value(
    option_id: int, option_value: schemas.OptionValueCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_option = crud.get_option(db, option_id)
    if not db_option: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Nhóm Tùy chọn ID {option_id} không tồn tại.")
    return crud.create_option_value(db=db, option_value=option_value, option_id=option_id)

@app.delete("/admin/values/{value_id}", response_model=schemas.OptionValue)
def delete_existing_option_value(
    value_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_value = crud.delete_option_value(db, value_id)
    if db_value is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Lựa chọn con")
    return db_value

@app.post("/admin/products/{product_id}/link_options", response_model=schemas.Product)
def link_options_to_product(
    product_id: int, link_request: schemas.ProductLinkOptionsRequest, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_product_check = crud.get_product(db, product_id)
    if not db_product_check: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm")
    db_product = crud.link_product_to_options(db, product_id, link_request.option_ids)
    return db_product

# === Quản lý Voucher ===
@app.post("/admin/vouchers/", response_model=schemas.Voucher, status_code=status.HTTP_201_CREATED)
def create_new_voucher(
    voucher: schemas.VoucherCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    existing = db.query(models.Voucher).filter(models.Voucher.code == voucher.code).first()
    if existing: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Mã voucher '{voucher.code}' đã tồn tại.")
    return crud.create_voucher(db=db, voucher=voucher)

@app.get("/admin/vouchers/", response_model=List[schemas.Voucher])
def read_all_vouchers(
    db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.get_vouchers(db)

@app.put("/admin/vouchers/{voucher_id}", response_model=schemas.Voucher)
def update_existing_voucher(
    voucher_id: int, voucher: schemas.VoucherCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    existing_check = db.query(models.Voucher).filter(models.Voucher.code == voucher.code, models.Voucher.id != voucher_id).first()
    if existing_check: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Mã voucher '{voucher.code}' đã tồn tại.")
    db_voucher = crud.update_voucher(db, voucher_id=voucher_id, voucher=voucher)
    if db_voucher is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy voucher")
    return db_voucher

@app.delete("/admin/vouchers/{voucher_id}", response_model=schemas.Voucher)
def delete_existing_voucher(
    voucher_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_voucher = crud.delete_voucher(db, voucher_id=voucher_id)
    if db_voucher is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy voucher")
    return db_voucher

# === Quản lý Đơn hàng (Admin) ===
@app.get("/admin/orders/", response_model=List[schemas.AdminOrderListResponse])
def read_all_orders(
    db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    return crud.get_orders(db)

@app.get("/admin/orders/{order_id}", response_model=schemas.OrderDetail)
def read_order_details(
    order_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_order = crud.get_order_details(db, order_id=order_id)
    if db_order is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng")
    return db_order

@app.put("/admin/orders/{order_id}/status", response_model=schemas.AdminOrderListResponse)
def update_order_status(
    order_id: int, status: models.OrderStatus, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_order = crud.update_order_status(db, order_id, status)
    if db_order is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng")
    return db_order