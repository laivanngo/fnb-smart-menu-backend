# Tệp: seed.py (ĐÃ CẬP NHẬT THỨ TỰ)
# Mục đích: "Nhập hàng mẫu" (Seed) vào database để kiểm tra.

from sqlalchemy.orm import Session
from models import (
    SessionLocal, 
    Category, 
    Product, 
    Option, 
    OptionValue, 
    OptionType, 
    create_tables
)
from crud import link_product_to_options

def seed_data():
    db: Session = SessionLocal()
    
    try:
        print("Đang kiểm tra dữ liệu mẫu...")
        
        category = db.query(Category).filter(Category.name == "Trà Sữa").first()
        if category:
            print("Dữ liệu mẫu đã tồn tại. Bỏ qua.")
            return

        print("Đang thêm dữ liệu mẫu...")
        
        # 3. TẠO DANH MỤC
        cat_tra_sua = Category(name="Trà Sữa", display_order=1)
        cat_ca_phe = Category(name="Cà Phê", display_order=2)
        db.add_all([cat_tra_sua, cat_ca_phe])
        db.commit()

        # 4. TẠO SẢN PHẨM
        prod_matcha = Product(
            name="Trà Sữa Matcha",
            description="Trà xanh Nhật Bản",
            base_price=35000,
            image_url="🍵",
            is_best_seller=True,
            category_id=cat_tra_sua.id
        )
        prod_cafe_den = Product(
            name="Cà Phê Đen",
            description="Cà phê phin",
            base_price=20000,
            image_url="☕",
            is_best_seller=False,
            category_id=cat_ca_phe.id
        )
        db.add_all([prod_matcha, prod_cafe_den])
        db.commit()

        # 5. TẠO "THƯ VIỆN TÙY CHỌN" (VỚI THỨ TỰ)
        
        # --- Nhóm "Độ ngọt" (Ưu tiên 1) ---
        opt_duong = Option(name="Độ ngọt", type=OptionType.CHON_1, display_order=1)
        db.add(opt_duong)
        db.commit() 
        val_duong_100 = OptionValue(name="100% đường", price_adjustment=0, option_id=opt_duong.id)
        val_duong_50 = OptionValue(name="50% đường", price_adjustment=0, option_id=opt_duong.id)
        db.add_all([val_duong_100, val_duong_50])

        # --- Nhóm "Size" (Ưu tiên 2) ---
        opt_size = Option(name="Kích cỡ", type=OptionType.CHON_1, display_order=2)
        db.add(opt_size)
        db.commit()
        val_size_m = OptionValue(name="Size Vừa (M)", price_adjustment=0, option_id=opt_size.id)
        val_size_l = OptionValue(name="Size Lớn (L)", price_adjustment=5000, option_id=opt_size.id)
        db.add_all([val_size_m, val_size_l])
        
        # --- Nhóm "Topping" (Ưu tiên 3) ---
        opt_topping = Option(name="Topping", type=OptionType.CHON_NHIEU, display_order=3)
        db.add(opt_topping)
        db.commit()
        val_thach_dua = OptionValue(name="Thạch dừa", price_adjustment=5000, option_id=opt_topping.id)
        val_tran_chau = OptionValue(name="Trân châu đen", price_adjustment=7000, option_id=opt_topping.id)
        db.add_all([val_thach_dua, val_tran_chau])
        
        db.commit()

        # 6. "GẮN" TÙY CHỌN VÀO SẢN PHẨM
        # (Thứ tự ID ở đây không còn quan trọng, vì "Bộ não" sẽ tự sắp xếp)
        link_product_to_options(
            db, 
            product_id=prod_matcha.id, 
            option_ids=[opt_size.id, opt_topping.id, opt_duong.id]
        )
        
        link_product_to_options(
            db, 
            product_id=prod_cafe_den.id, 
            option_ids=[opt_duong.id]
        )
        
        print("Đã thêm dữ liệu mẫu thành công!")

    except Exception as e:
        print(f"Lỗi khi thêm dữ liệu mẫu: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_tables() 
    seed_data()