# File: main.py (Đã thêm WebSocket)
# Mục đích: Backend API với WebSocket real-time

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
import shutil
import os
import uuid

import crud, models, schemas, security
from models import SessionLocal, engine, Base
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# IMPORT WEBSOCKET MANAGER
try:
    from websocket_manager import manager
    print("✅ WebSocket manager loaded successfully!")
except ImportError:
    print("⚠️ websocket_manager.py not found - WebSocket disabled!")
    manager = None

app = FastAPI(title="FNB Smart Menu - Backend API")

# Upload directory
UPLOAD_DIRECTORY = "uploads"
STATIC_PATH = "/static"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
app.mount(STATIC_PATH, StaticFiles(directory=UPLOAD_DIRECTORY), name="static")

# CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://biitea.com",
    "https://www.biitea.com",
    "https://admin.fnbsmartmenu.com",
    "https://api.fnbsmartmenu.com" 
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    print("Starting application...")
    models.create_tables()
    print("Database tables ready.")
    db = SessionLocal()
    admin = crud.get_admin_by_username(db, "admin")
    if not admin:
        print("Creating default admin (admin/admin)...")
        admin_in = schemas.AdminCreate(username="admin", password="admin")
        crud.create_admin(db, admin_in)
        print("Admin created!")
    else:
        print("Admin already exists.")
    db.close()
    print("Startup complete.")

# === PUBLIC ENDPOINTS ===

@app.get("/menu", response_model=List[schemas.PublicCategory])
def get_full_menu(db: Session = Depends(get_db)):
    """PUBLIC API: Get full menu"""
    return crud.get_public_menu(db)

@app.post("/orders/calculate", response_model=schemas.OrderCalculateResponse)
def calculate_order(
    order_data: schemas.OrderCalculateRequest,
    db: Session = Depends(get_db)
):
    """PUBLIC API: Calculate order total"""
    try:
        return crud.calculate_order_total(db, order_data)
    except HTTPException as e:
        if e.status_code < 500:
             raise e
        print(f"Error calculating order: {e.detail}")
        raise HTTPException(status_code=500, detail="System error calculating order.")
    except Exception as e:
        print(f"Unknown error calculating order: {e}")
        raise HTTPException(status_code=500, detail="Unknown system error calculating order.")

@app.post("/orders", response_model=schemas.PublicOrderResponse, status_code=status.HTTP_201_CREATED)
async def submit_new_order(  # IMPORTANT: async here!
    order_data: schemas.OrderCreate,
    db: Session = Depends(get_db)
):
    """PUBLIC API: Submit order + Send WebSocket notification"""
    try:
        # Step 1: Save order to database
        db_order = crud.create_order(db, order_data)
        
        # Step 2: Send WebSocket notification to admin
        if manager:
            notification_message = {
                "type": "new_order",
                "order_id": db_order.id,
                "customer_name": db_order.customer_name,
                "customer_phone": db_order.customer_phone,
                "total_amount": float(db_order.total_amount),
                "delivery_method": db_order.delivery_method_selected.value,
                "payment_method": db_order.payment_method.value,
                "timestamp": datetime.now().isoformat(),
                "status": "MOI"
            }
            await manager.broadcast(notification_message)
            print(f"📢 Sent notification for order #{db_order.id} to {len(manager.active_connections)} admins")
        
        return db_order
    except HTTPException as e:
        if e.status_code < 500:
            raise e
        print(f"Error creating order: {e.detail}")
        raise HTTPException(status_code=500, detail="System error creating order.")
    except Exception as e:
        print(f"Unknown error creating order: {e}")
        raise HTTPException(status_code=500, detail="Cannot process order due to system error.")

# === WEBSOCKET ENDPOINT ===

@app.websocket("/ws/admin/orders")
async def websocket_admin_orders(websocket: WebSocket):
    """
    WebSocket endpoint for admin real-time notifications
    
    URL: ws://localhost:8000/ws/admin/orders
    """
    if not manager:
        print("⚠️ WebSocket manager not available!")
        await websocket.close()
        return
    
    # Accept and save connection
    await manager.connect(websocket)
    print("🔌 Admin connected via WebSocket")
    
    try:
        # Keep connection open
        while True:
            # Receive data from client (if any)
            data = await websocket.receive_text()
            
            # Handle ping-pong for keep-alive
            if data == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        # Client disconnected
        manager.disconnect(websocket)
        print("🔌 Admin disconnected from WebSocket")
    except Exception as e:
        # Other errors
        print(f"⚠️ WebSocket error: {e}")
        manager.disconnect(websocket)

# === ADMIN ENDPOINTS ===

@app.post("/admin/token", response_model=schemas.Token)
async def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """ADMIN API: Login"""
    admin = crud.get_admin_by_username(db, form_data.username)
    if not admin or not security.verify_password(form_data.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(data={"sub": admin.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/admin/me", response_model=schemas.Admin)
async def read_admin_me(current_admin: models.Admin = Depends(security.get_current_admin)):
    """ADMIN API: Get current admin info"""
    return current_admin

@app.post("/admin/upload-image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...), 
    current_admin: models.Admin = Depends(security.get_current_admin)
):
    """ADMIN API: Upload image"""
    allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    public_url = f"{STATIC_PATH}/{unique_filename}"
    
    return {
        "message": "Image uploaded successfully",
        "filename": unique_filename,
        "url": public_url
    }

# Category endpoints
@app.post("/admin/categories/", response_model=schemas.Category, status_code=status.HTTP_201_CREATED)
def create_new_category(
    category: schemas.CategoryCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.create_category(db=db, category=category)

@app.get("/admin/categories/", response_model=List[schemas.Category])
def read_all_categories(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.get_categories(db, skip=skip, limit=limit)

@app.put("/admin/categories/{category_id}", response_model=schemas.Category)
def update_existing_category(
    category_id: int, category: schemas.CategoryUpdate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_category = crud.update_category(db, category_id, category)
    if db_category is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return db_category

@app.delete("/admin/categories/{category_id}", response_model=schemas.Category)
def delete_existing_category(
    category_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_category = crud.delete_category(db, category_id)
    if db_category is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return db_category

# Product endpoints
@app.post("/admin/products/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_new_product(
    product: schemas.ProductCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_category = crud.get_category(db, product.category_id)
    if not db_category: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category ID {product.category_id} not found.")
    return crud.create_product(db=db, product=product)

@app.get("/admin/products/", response_model=List[schemas.Product])
def read_all_products(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.get_products(db, skip=skip, limit=limit)

@app.get("/admin/products/{product_id}", response_model=schemas.Product)
def read_one_product(
    product_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_product = crud.get_product(db, product_id)
    if db_product is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return db_product

@app.put("/admin/products/{product_id}", response_model=schemas.Product)
def update_existing_product(
    product_id: int, product: schemas.ProductUpdate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    if product.category_id is not None:
        db_category = crud.get_category(db, product.category_id)
        if not db_category: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category ID {product.category_id} not found.")
    db_product = crud.update_product(db, product_id, product)
    if db_product is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return db_product

@app.delete("/admin/products/{product_id}", response_model=schemas.Product)
def delete_existing_product(
    product_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_product = crud.delete_product(db, product_id)
    if db_product is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return db_product

# Options endpoints
@app.post("/admin/options/", response_model=schemas.Option, status_code=status.HTTP_201_CREATED)
def create_new_option(
    option: schemas.OptionCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.create_option(db=db, option=option)

@app.get("/admin/options/", response_model=List[schemas.Option])
def read_all_options(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.get_options(db, skip=skip, limit=limit)

@app.delete("/admin/options/{option_id}", response_model=schemas.Option)
def delete_existing_option(
    option_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_option = crud.delete_option(db, option_id)
    if db_option is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option group not found")
    return db_option

@app.put("/admin/options/{option_id}", response_model=schemas.Option)
def update_existing_option(
    option_id: int, 
    option: schemas.OptionUpdate, 
    db: Session = Depends(get_db), 
    current_admin: models.Admin = Depends(security.get_current_admin)
):
    """ADMIN API: Update option group"""
    db_option = crud.update_option(db, option_id, option)
    if db_option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option group not found")
    return db_option

@app.post("/admin/options/{option_id}/values/", response_model=schemas.OptionValue, status_code=status.HTTP_201_CREATED)
def create_new_option_value(
    option_id: int, option_value: schemas.OptionValueCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_option = crud.get_option(db, option_id)
    if not db_option: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Option group ID {option_id} not found.")
    return crud.create_option_value(db=db, option_value=option_value, option_id=option_id)

@app.put("/admin/values/{value_id}", response_model=schemas.OptionValue)
def update_existing_option_value(
    value_id: int, 
    option_value: schemas.OptionValueUpdate, 
    db: Session = Depends(get_db), 
    current_admin: models.Admin = Depends(security.get_current_admin)
):
    """ADMIN API: Update option value"""
    db_value = crud.update_option_value(db, value_id, option_value)
    if db_value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option value not found")
    return db_value

@app.delete("/admin/values/{value_id}", response_model=schemas.OptionValue)
def delete_existing_option_value(
    value_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_value = crud.delete_option_value(db, value_id)
    if db_value is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option value not found")
    return db_value

@app.post("/admin/products/{product_id}/link_options", response_model=schemas.Product)
def link_options_to_product(
    product_id: int, link_request: schemas.ProductLinkOptionsRequest, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_product_check = crud.get_product(db, product_id)
    if not db_product_check: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    db_product = crud.link_product_to_options(db, product_id, link_request.option_ids)
    return db_product

# Voucher endpoints
@app.post("/admin/vouchers/", response_model=schemas.Voucher, status_code=status.HTTP_201_CREATED)
def create_new_voucher(
    voucher: schemas.VoucherCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    existing = db.query(models.Voucher).filter(models.Voucher.code == voucher.code).first()
    if existing: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Voucher code '{voucher.code}' already exists.")
    return crud.create_voucher(db=db, voucher=voucher)

@app.get("/admin/vouchers/", response_model=List[schemas.Voucher])
def read_all_vouchers(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
): return crud.get_vouchers(db, skip=skip, limit=limit)

@app.put("/admin/vouchers/{voucher_id}", response_model=schemas.Voucher)
def update_existing_voucher(
    voucher_id: int, voucher: schemas.VoucherCreate, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    existing_check = db.query(models.Voucher).filter(models.Voucher.code == voucher.code, models.Voucher.id != voucher_id).first()
    if existing_check: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Voucher code '{voucher.code}' already exists.")
    db_voucher = crud.update_voucher(db, voucher_id=voucher_id, voucher=voucher)
    if db_voucher is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found")
    return db_voucher

@app.delete("/admin/vouchers/{voucher_id}", response_model=schemas.Voucher)
def delete_existing_voucher(
    voucher_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_voucher = crud.delete_voucher(db, voucher_id=voucher_id)
    if db_voucher is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found")
    return db_voucher

# Order endpoints
@app.get("/admin/orders/", response_model=List[schemas.AdminOrderListResponse])
def read_all_orders(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    return crud.get_orders(db, skip=skip, limit=limit)

@app.get("/admin/orders/{order_id}", response_model=schemas.OrderDetail)
def read_order_details(
    order_id: int, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_order = crud.get_order_details(db, order_id=order_id)
    if db_order is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return db_order

@app.put("/admin/orders/{order_id}/status", response_model=schemas.AdminOrderListResponse)
def update_order_status(
    order_id: int, status: models.OrderStatus, db: Session = Depends(get_db), current_admin: models.Admin = Depends(security.get_current_admin)
):
    db_order = crud.update_order_status(db, order_id, status)
    if db_order is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return db_order