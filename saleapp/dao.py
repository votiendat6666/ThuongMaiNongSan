import json
import threading

from Demos.mmapfile_demo import page_size
from flask import jsonify, request
from itertools import product

from flask_login import current_user
from sqlalchemy import and_
from sqlalchemy.orm import joinedload, scoped_session, sessionmaker

from saleapp import db

from saleapp.models import *
from fuzzywuzzy import process
from unidecode import unidecode
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Thread
import time
from saleapp import app


# Các hàm này sẽ được sử dụng để thao tác với cơ sở dữ liệu
def load_categories():
    with open('data/categories.json', encoding='utf-8') as f:
        return json.load(f)

# Hàm này sẽ load danh sách voucher từ file JSON
def load_voucher(user_id=None):
    with open('data/voucher.json', encoding='utf-8') as f:
        vouchers = json.load(f)
        if user_id:
            vouchers = [v for v in vouchers if v.get("user_id") == user_id]
        return vouchers

# Hàm này sẽ load danh sách sản phẩm từ file JSON
def count_products():
    return db.session.query(func.count(Product.id)).scalar()

# Hàm này sẽ load danh sách sản phẩm từ cơ sở dữ liệu với phân trang
def load_products(q=None, cate_id=None, page=1):
    query = db.session.query(Product)

    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    if cate_id:
        query = query.filter(Product.category_id == cate_id)

    # Điều kiện phân trang theo yêu cầu:
    if page == 1:
        page_size = 50
    else:
        page_size = 100

    start = (page - 1) * page_size
    end = start + page_size

    products = query.slice(start, end).all()

    # Tính số sản phẩm tiếp theo để xác định có còn "Xem thêm" không
    next_product = query.slice(end, end + 1).first()  # Kiểm tra có thêm sản phẩm

    has_next = next_product is not None

    return products, has_next

# Hàm này sẽ load băm mât khẩu từ file JSON
def add_user(name, username, password, avatar, email, address, phone):
    password = generate_password_hash(password.strip())  # an toàn hơn MD5
    if avatar:
        u = User(name=name, username=username, password=password, avatar=avatar, email=email, address=address,
                     phone=phone)
    else:
        u = User(name=name, username=username, password=password, email=email, address=address, phone=phone)
    db.session.add(u)
    db.session.commit()


def add_staff(name, username, password, avatar, email, address, phone, role):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    u = None
    if avatar:
        u = User(name=name, username=username, password=password, avatar=avatar, email=email, address=address,
                  phone=phone, user_role=role)
    else:
        u = User(name=name, username=username, password=password, email=email, address=address, phone=phone,
                  user_role=role)
    db.session.add(u)
    db.session.commit()


def auth_user(username, password, role):
    user = User.query.filter_by(username=username, user_role=role).first()
    if user and check_password_hash(user.password, password):
        return user
    return None


def auth_staff(username, password, role):
    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())

    return User.query.filter(User.username.__eq__(username),
                              User.password.__eq__(password),
                              User.user_role.__eq__(role)).first()

# Hàm này sẽ load sản phẩm theo ID
def load_product_by_id(id):
    product = db.session.query(Product).filter(Product.id == id).first()
    if product:
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "image": product.image,
            "category_id": product.category_id,
            "author_id": product.author_id,
            "quantity": product.quantity
        }
    return None

# Hàm này sẽ load sản phẩm theo danh mục và các điều kiện khác
def load_products_by_category(category_id):
    categories = load_categories()
    child_ids = [c['id'] for c in categories if c['parent_id'] == category_id]

    if not child_ids:
        child_ids = [category_id]

    return Product.query.filter(Product.category_id.in_(child_ids)).all()

# Hàm này sẽ load sản phẩm theo tên
def get_user_by_id(user_id):
    user = User.query.get(user_id) or User.query.get(user_id)
    return user


# Update password
def update_password(user_id, raw_password):
    user = User.query.get(user_id)
    if user:
        user.password = generate_password_hash(raw_password.strip())
        db.session.commit()
        return True
    return False


# Gọi hàm này để lấy danh sách sản phẩm trong giỏ hàng của người dùng
def get_cart_items(user_id):
    return CartItem.query.filter_by(user_id=user_id).all()


# Xoa sản phẩm yêu thích
def delete_favorite(user_id, product_id):
    try:
        fav = FavoriteProduct.query.filter_by(user_id=user_id, product_id=product_id).first()
        if fav:
            db.session.delete(fav)
            db.session.commit()
            return True
    except:
        db.session.rollback()
    return False

# Sản phẩm Flash Sale: ưu tiên voucher cao nhất
def get_flash_sale_products(limit=20):
    return db.session.query(Product) \
        .order_by(Product.voucher.desc()) \
        .limit(limit).all()

 # Sản phẩm bán chạy toàn shop (đã bán nhiều nhất)
def get_best_seller_products(limit=20):
    return db.session.query(Product) \
        .order_by(Product.daban.desc()) \
        .limit(limit).all()

# Sản phẩm thuộc nhóm cha cụ thể, sắp xếp theo đã bán nhiều nhất
def get_category_products_by_daban(parent_id, limit=20):
    child_ids = [
        c.id for c in db.session.query(Category).filter(Category.parent_id == parent_id).all()
    ]

    return db.session.query(Product) \
        .filter(Product.category_id.in_(child_ids)) \
        .order_by(Product.price.desc()) \
        .limit(limit).all()

# Sản phẩm thuộc nhóm Sách, sắp xếp theo like nhiều nhất
def get_favorites_books_products(parent_books_id=10000, limit=20):
    child_ids = [
        c.id for c in db.session.query(Category).filter(Category.parent_id == parent_books_id).all()
    ]

    return db.session.query(Product) \
        .filter(Product.category_id.in_(child_ids)) \
        .order_by(Product.like.desc()) \
        .limit(limit).all()

# Tính tổng tiền hàng trong giỏ của người dùng user_id với điều kiện các mặt hàng đã được chọn (is_selected=True).
def get_order_total_amount(user_id):
    selected_cart_items = CartItem.query.filter_by(user_id=user_id, is_selected=True).all()
    return sum(item.quantity * item.product.price for item in selected_cart_items)



# Lay json dia chi
with open('data/tinh_tp.json', encoding='utf-8') as f:
    provinces = json.load(f)

with open('data/quan_huyen.json', encoding='utf-8') as f:
    districts = json.load(f)

with open('data/phuong_xa.json', encoding='utf-8') as f:
    wards = json.load(f)

# Hàm trả danh sách Tỉnh/Thành phố
def get_provinces():
    return list(provinces.values())

# Hàm trả Quận/Huyện theo Tỉnh
def get_districts_by_province(province_code):
    return [d for d in districts.values() if d['parent_code'] == province_code]

# Hàm trả Phường/Xã theo Huyện
def get_wards_by_district(district_code):
    return [w for w in wards.values() if w['parent_code'] == district_code]


# Hàm này sẽ lấy danh sách bình luận của sản phẩm và thống kê các thông tin liên quan
def get_comment_stats(product_id):
    # Lấy bình luận thuộc sản phẩm
    comments = Comment.query.join(ReceiptDetail).filter(
        ReceiptDetail.product_id == product_id
    ).options(joinedload(Comment.images)).all()

    stats = {
        5: 0,
        4: 0,
        3: 0,
        2: 0,
        1: 0,
        'with_comment': 0,
        'with_image': 0,
        'total': 0
    }

    for c in comments:
        if c.rating in stats:
            stats[c.rating] += 1
        if c.content and c.content.strip():
            stats['with_comment'] += 1
        if c.images and len(c.images) > 0:
            stats['with_image'] += 1

    stats['total'] = len(comments)

    return stats

# Hàm đếm số lượng đơn nhập kho đang có
def get_next_receipt_number():
    last = db.session.query(func.max(ImportReceipt.id)).scalar()
    return (last or 0) + 1

# Hàm set time out để xoá PendingPayment sau 10 phút
def set_timeout_to_delete_pending(momo_order_id):
    def delete_if_expired():
        time.sleep(600)
        with app.app_context():  # 👈 Gói trong context để dùng db được
            pending = PendingPayment.query.filter_by(momo_order_id=momo_order_id).first()
            if pending:
                db.session.delete(pending)
                db.session.commit()
                print(f"🗑 Đã xoá PendingPayment {momo_order_id} sau 10 giây.")

    Thread(target=delete_if_expired).start()

# Hàm cập nhật hoặc tạo mới trong ProductInventory
def update_or_create_product_inventory(product_id, quantity):
    inventory = ProductInventory.query.filter_by(product_id=product_id).first()
    if inventory:
        # ✅ Nếu đã tồn tại, cộng dồn số lượng và cập nhật trạng thái
        inventory.quantity += quantity
        inventory.status = 2  # Cập nhật thành hàng cũ
    else:
        # ✅ Nếu chưa có, tạo mới với trạng thái hàng mới (1)
        inventory = ProductInventory(
            product_id=product_id,
            quantity=quantity,
            status=1
        )
        db.session.add(inventory)

    db.session.commit()

def insert_default_settings():
    default_settings = {
        'min_quantity_per_item': ('10', 'Số lượng tối thiểu cho mỗi sản phẩm'),
        'max_quantity_per_item': ('100', 'Số lượng tối đa cho mỗi sản phẩm'),
        'min_total_quantity': ('50', 'Tổng số lượng tối thiểu mỗi phiếu nhập'),
        'max_total_quantity': ('300', 'Tổng số lượng tối đa mỗi phiếu nhập')
    }

    for key, (value, description) in default_settings.items():
        if not Setting.query.get(key):
            db.session.add(Setting(key=key, value=value, description=description))

    db.session.commit()


# Hàm này sẽ hủy đơn hàng chưa thanh toán sau một khoảng thời gian nhất định
def schedule_cancel_unpaid_momo(receipt_id, delay_seconds=600):
    def cancel_after_delay():
        time.sleep(delay_seconds)

        with app.app_context():  # ✅ Rất quan trọng khi dùng thread
            Session = scoped_session(sessionmaker(bind=db.engine))
            session = Session()

            try:
                receipt = session.get(Receipt, receipt_id)
                if receipt and receipt.status == 'Chờ thanh toán' and receipt.payment_method == 'MoMo':
                    receipt.status = 'Đã hủy'

                    # ✅ Hoàn lại xu nếu có
                    user = session.get(User, receipt.user_id)
                    if user:
                        user.coin = (user.coin or 0) - (receipt.coin_earned or 0) + (receipt.coin_used or 0)

                    # ✅ Hoàn tồn kho theo dòng đã trừ trong ReceiptInventoryDetail
                    restore_details = session.query(ReceiptInventoryDetail).filter_by(receipt_id=receipt.id).all()

                    for detail in restore_details:
                        inventory = session.get(ProductInventory, detail.inventory_id)
                        if inventory:
                            inventory.quantity += detail.quantity
                        else:
                            # Nếu inventory không còn, tìm fallback theo product_id và status = 2 (có thể là "Còn hàng")
                            fallback = session.query(ProductInventory).filter_by(
                                product_id=detail.product_id, status=2
                            ).first()
                            if fallback:
                                fallback.quantity += detail.quantity
                            else:
                                fallback = ProductInventory(
                                    product_id=detail.product_id,
                                    quantity=detail.quantity,
                                    status=2
                                )
                                session.add(fallback)

                    session.commit()
                    print(f"[HUỶ] Đơn #{receipt_id} đã bị huỷ sau {delay_seconds} giây.")
                else:
                    print(f"[BỎ QUA] Đơn #{receipt_id} không đủ điều kiện huỷ.")
            except Exception as e:
                print(f"[LỖI huỷ đơn]: {e}")
                session.rollback()
            finally:
                session.close()
                Session.remove()

    Thread(target=cancel_after_delay).start()





if __name__ == "__main__":
    print(load_products())

