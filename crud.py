# Tệp: crud.py (Bản HOÀN CHỈNH - Đã sửa lỗi create_option, thêm update/delete voucher, sắp xếp options)
# Mục đích: Chứa tất cả các hàm logic nghiệp vụ (CRUD)

from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy import asc # Import công cụ Sắp xếp
from fastapi import HTTPException
import models, schemas
import security
from typing import List

# --- Nghiệp vụ Admin ---
def get_admin_by_username(db: Session, username: str):
    """Tìm admin theo username"""
    return db.query(models.Admin).filter(models.Admin.username == username).first()

def create_admin(db: Session, admin: schemas.AdminCreate):
    """Tạo Admin mới với mật khẩu đã được "băm" (hash)"""
    hashed_password = security.get_password_hash(admin.password)
    db_admin = models.Admin(username=admin.username, hashed_password=hashed_password)
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

# --- Nghiệp vụ Danh mục (Category) ---
def get_category(db: Session, category_id: int):
    """Tìm 1 danh mục theo ID"""
    return db.query(models.Category).filter(models.Category.id == category_id).first()

def get_categories(db: Session):
    """Lấy danh sách tất cả danh mục, sắp xếp theo display_order"""
    return db.query(models.Category).order_by(models.Category.display_order).all()

def create_category(db: Session, category: schemas.CategoryCreate):
    """Tạo danh mục mới"""
    db_category = models.Category(name=category.name, display_order=category.display_order)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

def update_category(db: Session, category_id: int, category: schemas.CategoryUpdate):
    """Cập nhật thông tin danh mục"""
    db_category = get_category(db, category_id)
    if not db_category:
        return None
    update_data = category.model_dump(exclude_unset=True) # Dùng model_dump cho Pydantic V2
    for key, value in update_data.items():
        setattr(db_category, key, value)
    db.commit()
    db.refresh(db_category)
    return db_category

def delete_category(db: Session, category_id: int):
    """Xóa một danh mục"""
    db_category = get_category(db, category_id)
    if not db_category:
        return None
    db.delete(db_category)
    db.commit()
    return db_category

# --- Nghiệp vụ Sản phẩm (Product) ---
def get_product(db: Session, product_id: int):
    """Lấy 1 sản phẩm CỤ THỂ bằng ID, kèm tùy chọn đã sắp xếp"""
    product = db.query(models.Product).options(
        joinedload(models.Product.options).subqueryload(models.Option.values)
    ).filter(models.Product.id == product_id).first()

    # Sắp xếp options sau khi lấy ra
    if product and product.options:
        product.options.sort(key=lambda opt: opt.display_order if opt.display_order is not None else float('inf'))
        # Có thể sắp xếp values nếu cần
        # for opt in product.options:
        #     opt.values.sort(key=lambda val: val.name)

    return product


def get_products(db: Session):
    """Lấy danh sách TẤT CẢ sản phẩm, kèm tùy chọn"""
    products = db.query(models.Product).options(
        joinedload(models.Product.options) # Tải các Nhóm Tùy chọn
    ).all()

    # Sắp xếp options cho từng product
    for product in products:
        if product.options:
             product.options.sort(key=lambda opt: opt.display_order if opt.display_order is not None else float('inf'))

    return products

def create_product(db: Session, product: schemas.ProductCreate):
    """Tạo sản phẩm mới và gắn nó vào một danh mục"""
    db_product = models.Product(**product.model_dump()) # Dùng model_dump cho Pydantic V2
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product: schemas.ProductUpdate):
    """Cập nhật thông tin sản phẩm"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first() # Lấy object gốc để update
    if not db_product:
        return None
    update_data = product.model_dump(exclude_unset=True) # Dùng model_dump cho Pydantic V2
    for key, value in update_data.items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    # Lấy lại product với options đã load để trả về (để response_model khớp)
    return get_product(db, product_id)

def delete_product(db: Session, product_id: int):
    """Xóa một sản phẩm"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first() # Chỉ cần lấy product để xóa
    if not db_product:
        return None
    deleted_copy = schemas.Product.model_validate(db_product) # Tạo bản copy trước khi xóa để trả về
    db.delete(db_product)
    db.commit()
    return deleted_copy # Trả về bản copy

def link_product_to_options(db: Session, product_id: int, option_ids: List[int]):
    """Gắn các Nhóm Tùy chọn vào Sản phẩm"""
    db_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not db_product:
        return None

    # Lấy các đối tượng Option từ DB theo ID
    db_options = db.query(models.Option).filter(models.Option.id.in_(option_ids)).all()

    # Kiểm tra xem tất cả ID gửi lên có hợp lệ không (tùy chọn)
    # if len(db_options) != len(set(option_ids)):
    #     raise HTTPException(status_code=400, detail="Một hoặc nhiều Option ID không hợp lệ.")

    db_product.options = db_options # Gán trực tiếp list các object Option

    db.commit()
    # Lấy lại product với options đã load để trả về
    return get_product(db, product_id)

# --- Nghiệp vụ Nhóm Tùy chọn (Option) ---
def get_option(db: Session, option_id: int):
    """Tìm 1 Nhóm Tùy chọn theo ID"""
    return db.query(models.Option).filter(models.Option.id == option_id).first()

def create_option(db: Session, option: schemas.OptionCreate):
    """Tạo một Nhóm Tùy chọn mới (Vd: Topping)"""
    # display_order sẽ lấy default=0 từ model
    db_option = models.Option(name=option.name, type=option.type)
    db.add(db_option)
    db.commit()
    db.refresh(db_option)
    return db_option

def get_options(db: Session):
    """Lấy TẤT CẢ các nhóm tùy chọn, kèm lựa chọn con, sắp xếp theo display_order"""
    return db.query(models.Option).options(
        joinedload(models.Option.values) # Tải luôn các values
    ).order_by(models.Option.display_order).all() # Sắp xếp

def delete_option(db: Session, option_id: int):
    """Xóa một Nhóm Tùy chọn (và các lựa chọn con bên trong)"""
    db_option = get_option(db, option_id)
    if not db_option:
        return None
    deleted_copy = schemas.Option.model_validate(db_option) # Tạo bản copy trước khi xóa
    db.delete(db_option) # Cascade delete sẽ xóa cả values
    db.commit()
    return deleted_copy

# --- Nghiệp vụ Lựa chọn con (OptionValue) ---
def get_option_value(db: Session, value_id: int):
    """Tìm 1 Lựa chọn con theo ID"""
    return db.query(models.OptionValue).filter(models.OptionValue.id == value_id).first()

def create_option_value(db: Session, option_value: schemas.OptionValueCreate, option_id: int):
    """Tạo một Lựa chọn con (Vd: Trân châu) và gắn vào Nhóm (Vd: Topping)"""
    db_value = models.OptionValue(**option_value.model_dump(), option_id=option_id) # Dùng model_dump
    db.add(db_value)
    db.commit()
    db.refresh(db_value)
    return db_value

def delete_option_value(db: Session, value_id: int):
    """Xóa một Lựa chọn con"""
    db_value = get_option_value(db, value_id)
    if not db_value:
        return None
    deleted_copy = schemas.OptionValue.model_validate(db_value) # Tạo bản copy
    db.delete(db_value)
    db.commit()
    return deleted_copy

# --- Nghiệp vụ Voucher ---
def create_voucher(db: Session, voucher: schemas.VoucherCreate):
    """Tạo mã giảm giá mới"""
    db_voucher = models.Voucher(**voucher.model_dump()) # Dùng model_dump
    db.add(db_voucher)
    db.commit()
    db.refresh(db_voucher)
    return db_voucher

def get_vouchers(db: Session):
    """Lấy tất cả mã giảm giá"""
    return db.query(models.Voucher).all()

def get_voucher_by_code(db: Session, code: str):
    """Tìm mã giảm giá theo code (chỉ mã đang active)"""
    return db.query(models.Voucher).filter(models.Voucher.code == code, models.Voucher.is_active == True).first()

def get_voucher(db: Session, voucher_id: int):
    """Tìm voucher theo ID"""
    return db.query(models.Voucher).filter(models.Voucher.id == voucher_id).first()

def update_voucher(db: Session, voucher_id: int, voucher: schemas.VoucherCreate): # Tái sử dụng schema Create
    """Cập nhật thông tin voucher"""
    db_voucher = get_voucher(db, voucher_id)
    if not db_voucher:
        return None
    update_data = voucher.model_dump(exclude_unset=True) # Lấy các trường được gửi lên
    for key, value in update_data.items():
        setattr(db_voucher, key, value)
    db.commit()
    db.refresh(db_voucher)
    return db_voucher

def delete_voucher(db: Session, voucher_id: int):
     """Xóa một voucher"""
     db_voucher = get_voucher(db, voucher_id)
     if not db_voucher:
         return None
     deleted_copy = schemas.Voucher.model_validate(db_voucher) # Tạo bản copy
     db.delete(db_voucher)
     db.commit()
     return deleted_copy

# --- Nghiệp vụ Công khai (Public) ---
def get_public_menu(db: Session):
    """Lấy toàn bộ Menu công khai, đã sắp xếp"""
    categories = db.query(models.Category).options(
        subqueryload(models.Category.products). # Tải products
        subqueryload(models.Product.options).  # Tải options cho product
        joinedload(models.Option.values)       # Tải values cho option (dùng joinedload vì value đơn giản)
    ).order_by(models.Category.display_order).all()

    # Sắp xếp Options trong từng Product theo display_order
    for category in categories:
        for product in category.products:
            # Sắp xếp options dựa trên display_order của Option
            product.options.sort(key=lambda opt: opt.display_order if opt.display_order is not None else float('inf'))
            # Có thể cần sắp xếp values trong từng option nếu cần (ví dụ theo tên hoặc giá)
            # for option in product.options:
            #     option.values.sort(key=lambda val: val.name)

    return categories


# --- Logic "Quầy Thu ngân" ---
def _calculate_delivery_fee(method: models.DeliveryMethod, sub_total: float) -> float:
    """Hàm nội bộ tính phí ship"""
    base_fee = 25000.0 if method == models.DeliveryMethod.NHANH else 15000.0
    if method == models.DeliveryMethod.TIEU_CHUAN and sub_total >= 50000.0:
        return 0.0
    return base_fee

def _calculate_discount(voucher: models.Voucher, sub_total: float) -> float:
    """Hàm nội bộ tính giảm giá"""
    if not voucher or not voucher.is_active or sub_total < voucher.min_order_value:
        return 0.0

    discount = 0.0
    if voucher.type == "percentage":
        discount = sub_total * (voucher.value / 100.0)
        if voucher.max_discount is not None and discount > voucher.max_discount:
            discount = voucher.max_discount
    elif voucher.type == "fixed":
        discount = voucher.value

    # Đảm bảo giảm giá không âm và không lớn hơn tổng tiền
    discount = max(0, discount)
    return min(discount, sub_total)

def calculate_order_total(db: Session, order_data: schemas.OrderCalculateRequest):
    """Tính toán lại tổng tiền đơn hàng từ ID (Nguồn tin cậy)"""
    sub_total = 0.0

    product_ids = list(set([item.product_id for item in order_data.items])) # Lấy ID duy nhất
    option_value_ids = list(set([opt_id for item in order_data.items for opt_id in item.options])) # Lấy ID duy nhất

    # Truy vấn một lần để lấy tất cả product và option value cần thiết
    products_in_cart = {p.id: p for p in db.query(models.Product).filter(models.Product.id.in_(product_ids)).all()}
    option_values_in_cart = {ov.id: ov for ov in db.query(models.OptionValue).filter(models.OptionValue.id.in_(option_value_ids)).all()}

    for item in order_data.items:
        db_product = products_in_cart.get(item.product_id)
        if not db_product:
            raise HTTPException(status_code=400, detail=f"Sản phẩm ID {item.product_id} không hợp lệ hoặc không tồn tại.")

        item_price = db_product.base_price

        for option_value_id in item.options:
            db_option_value = option_values_in_cart.get(option_value_id)
            if db_option_value:
                item_price += db_option_value.price_adjustment
            else:
                 raise HTTPException(status_code=400, detail=f"Tùy chọn ID {option_value_id} không hợp lệ.")
                 # Hoặc bỏ qua nếu muốn linh hoạt hơn: pass

        sub_total += item_price * item.quantity

    delivery_fee = _calculate_delivery_fee(order_data.delivery_method, sub_total)

    discount_amount = 0.0
    db_voucher = None
    if order_data.voucher_code:
        db_voucher = get_voucher_by_code(db, order_data.voucher_code)
        if db_voucher:
            # Kiểm tra điều kiện voucher trước khi áp dụng
            if sub_total >= db_voucher.min_order_value:
                discount_amount = _calculate_discount(db_voucher, sub_total)
            else:
                 raise HTTPException(status_code=400, detail=f"Đơn hàng chưa đủ điều kiện tối thiểu ({db_voucher.min_order_value:,}đ) để áp dụng mã '{order_data.voucher_code}'.")
        else:
            # Ném lỗi nếu voucher không hợp lệ
             raise HTTPException(status_code=400, detail=f"Mã giảm giá '{order_data.voucher_code}' không hợp lệ hoặc đã hết hạn.")

    total_amount = sub_total + delivery_fee - discount_amount

    return schemas.OrderCalculateResponse(
        sub_total=round(sub_total), # Làm tròn tiền Việt
        delivery_fee=round(delivery_fee),
        discount_amount=round(discount_amount),
        total_amount=round(total_amount) if total_amount > 0 else 0
    )


def create_order(db: Session, order: schemas.OrderCreate):
    """Tạo Đơn hàng mới và lưu vào DB"""

    # 1. Tính toán lại tổng tiền lần cuối (Nguồn tin cậy duy nhất)
    try:
        calculated = calculate_order_total(db, order)
    except HTTPException as e:
        raise e # Ném lại lỗi nếu sản phẩm/voucher/option không hợp lệ

    # 2. Tạo bản ghi Order chính
    db_order = models.Order(
        customer_name=order.customer_name,
        customer_phone=order.customer_phone,
        customer_address=order.customer_address,
        customer_note=order.customer_note,
        payment_method=order.payment_method,
        delivery_method_selected=order.delivery_method,
        voucher_code=order.voucher_code if calculated.discount_amount > 0 else None, # Chỉ lưu nếu voucher hợp lệ
        sub_total=calculated.sub_total,
        delivery_fee=calculated.delivery_fee,
        discount_amount=calculated.discount_amount,
        total_amount=calculated.total_amount,
        status=models.OrderStatus.MOI
    )
    db.add(db_order)
    db.flush() # Flush để lấy được order_id mà không commit ngay

    # 3. Lưu các món và tùy chọn của đơn hàng (Tối ưu hóa truy vấn)
    product_ids = list(set([item.product_id for item in order.items]))
    option_value_ids = list(set([opt_id for item in order.items for opt_id in item.options]))
    products_in_order = {p.id: p for p in db.query(models.Product).filter(models.Product.id.in_(product_ids)).all()}
    option_values_in_order = {
        ov.id: ov for ov in db.query(models.OptionValue).options(joinedload(models.OptionValue.option)) # Tải luôn tên Nhóm
        .filter(models.OptionValue.id.in_(option_value_ids)).all()
    }

    order_items_to_add = []
    order_item_options_to_add = []
    temp_items_for_options = [] # Dùng list để lưu tạm item object trước khi flush lấy id

    for item in order.items:
        db_product = products_in_order.get(item.product_id)
        if not db_product: continue # Bỏ qua nếu sản phẩm không tìm thấy (đã check ở calculate)

        options_selected_objects = [option_values_in_order.get(opt_id) for opt_id in item.options if option_values_in_order.get(opt_id)]
        item_price_at_order = db_product.base_price + sum(opt.price_adjustment for opt in options_selected_objects)

        db_item = models.OrderItem(
            order_id=db_order.id,
            product_name=db_product.name,
            quantity=item.quantity,
            item_price=item_price_at_order,
            item_note=item.note
        )
        order_items_to_add.append(db_item)
        temp_items_for_options.append({"item_obj": db_item, "options": options_selected_objects})

    # Thêm tất cả item vào DB một lần
    db.add_all(order_items_to_add)
    db.flush() # Flush để tất cả item object có ID

    # Bây giờ mới tạo các bản ghi Lựa chọn con với item_id đúng
    for temp_item in temp_items_for_options:
        db_item_obj = temp_item["item_obj"]
        options_selected = temp_item["options"]
        for opt_val in options_selected:
            if opt_val and opt_val.option: # Check kỹ trước khi truy cập
                db_item_option = models.OrderItemOption(
                    order_item_id=db_item_obj.id, # Lấy ID đã có sau khi flush
                    option_name=opt_val.option.name, # Lấy tên Nhóm từ object đã tải
                    value_name=opt_val.name,
                    added_price=opt_val.price_adjustment
                )
                order_item_options_to_add.append(db_item_option)

    # Thêm tất cả option của item vào DB
    db.add_all(order_item_options_to_add)

    db.commit() # Commit tất cả thay đổi
    db.refresh(db_order)
    return db_order

# --- Nghiệp vụ Admin xem Order ---
def get_orders(db: Session):
    """Lấy danh sách đơn hàng (thông tin cơ bản), mới nhất lên đầu"""
    return db.query(models.Order).order_by(models.Order.id.desc()).all()

def get_order_details(db: Session, order_id: int):
    """Lấy chi tiết đầy đủ của 1 đơn hàng"""
    return db.query(models.Order).options(
        # Tải sẵn các item và option của item
        subqueryload(models.Order.items).
        subqueryload(models.OrderItem.options_selected)
    ).filter(models.Order.id == order_id).first()


def update_order_status(db: Session, order_id: int, status: models.OrderStatus):
    """Cập nhật trạng thái đơn hàng"""
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        return None
    db_order.status = status
    db.commit()
    db.refresh(db_order)
    return db_order