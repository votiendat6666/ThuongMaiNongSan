from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import math
import secrets
import uuid
from datetime import timedelta, datetime
import json

from authlib.common.security import generate_token
from flask_mail import Message
from functools import wraps
from itertools import product
from statistics import quantiles
import utils
from flask_admin import BaseView, expose
from werkzeug.security import check_password_hash, generate_password_hash

from flask import render_template, request, redirect, abort, session, jsonify, url_for, make_response, flash, \
    current_app
import dao
from flask_login import login_user, logout_user, current_user, login_required, LoginManager
import cloudinary.uploader
from saleapp.models import *
import random
from saleapp.utils import count_cart, get_cart_stats
import requests, hmac, hashlib
import cloudinary
from sqlalchemy.orm import joinedload

from flask_login import current_user, logout_user
from saleapp.models import Role  # hoặc nơi bạn định nghĩa enum Role

from flask import render_template
from flask_login import login_required, current_user
from sqlalchemy import func



admin_staff_bp = Blueprint('admin_staff', __name__)


def login_staff_or_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('admin_staff.login_staff', next=request.path))

        if current_user.user_role not in [Role.STAFF, Role.ADMIN]:
            return redirect(url_for('admin_staff.login_staff', next=request.path))

        return f(*args, **kwargs)
    return decorated_function

# ✅ Đăng nhập nhân viên hoặc admin
@admin_staff_bp.route('/login-admin_staff', methods=['GET', 'POST'])
def login_staff():
    if current_user.is_authenticated and session.get('user_type') in ['admin_staff', 'admin']:
        return redirect(url_for('admin_staff.pos_ban_hang'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # ✅ Tìm user có role STAFF hoặc ADMIN
        user = User.query.filter(
            User.username == username,
            User.user_role.in_([Role.STAFF, Role.ADMIN])
        ).first()

        if user and check_password_hash(user.password, password.strip()):
            login_user(user)

            # ✅ Ghi session phân biệt loại user
            session['user_type'] = 'admin' if user.user_role == Role.ADMIN else 'admin_staff'

            return redirect(url_for('admin_staff.pos_ban_hang'))

        error = "Sai thông tin đăng nhập"

    return render_template('admin_staff/login_staff_admin.html', error=error)

def login_staff(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or session.get('user_type') != 'admin_staff':
            return redirect(url_for('admin_staff.login_staff', next=request.path))
        return f(*args, **kwargs)

    return decorated_function

# -----------------------------------------------------------------------------------------------------------------------
#                                                QUẢN TRỊ
# -----------------------------------------------------------------------------------------------------------------------

# Trang chính của nhân viên
@admin_staff_bp.route('/quantri', methods=['GET', 'POST'])
def staff():
    if not current_user.is_authenticated or current_user.user_role != Role.STAFF:
        return redirect(url_for('admin_staff.login_staff', next=request.path)
)  # 👈 redirect về login kèm ?next=/admin_staff

    return render_template('admin_staff/quantri.html')


# -----------------------------------------------------------------------------------------------------------------------
#                                               POS BÁN HÀNG
# -----------------------------------------------------------------------------------------------------------------------


@admin_staff_bp.route("/admin_staff/posBanHang")
@login_staff_or_admin
def pos_ban_hang():
    return render_template("admin_staff/posBanHang.html", path="/admin_staff/posBanHang")


# -----------------------------------------------------------------------------------------------------------------------
#                                               BẢNG ĐIỀU KHIỂN
# -----------------------------------------------------------------------------------------------------------------------

@admin_staff_bp.route("/admin_staff/bangDieuKhien")
@login_staff_or_admin
def bang_dieu_khien():
    total_customers = db.session.query(User).filter(User.user_role == Role.USER).count()
    total_products = db.session.query(Product).count()
    total_receipts = db.session.query(Receipt).count()

    recent_users = db.session.query(User) \
        .filter(User.user_role == Role.USER) \
        .order_by(User.joined_date.desc()) \
        .limit(5).all()

    recent_receipts = db.session.query(Receipt).order_by(Receipt.create_date.desc()).limit(5).all()

    # ✅ Đếm số sản phẩm có tồn kho > 10
    products_with_enough_stock = db.session.query(ProductInventory.product_id) \
        .group_by(ProductInventory.product_id) \
        .having(func.sum(ProductInventory.quantity) > 10).all()

    num_products_with_enough_stock = len(products_with_enough_stock)

    # ✅ Tổng sản phẩm còn lại = tổng sản phẩm - số sản phẩm có tồn kho > 10
    total_low_stock_products = total_products - num_products_with_enough_stock

    return render_template(
        "admin_staff/bangDieuKhien.html", path="/admin_staff/bangDieuKhien",
        total_customers=total_customers,
        total_products=total_products,
        total_receipts=total_receipts,
        recent_users=recent_users,
        recent_receipts=recent_receipts,
        total_low_stock_products=total_low_stock_products
    )

# -----------------------------------------------------------------------------------------------------------------------
#                                               QUẢN LÝ KHÁCH HÀNG
# -----------------------------------------------------------------------------------------------------------------------

@admin_staff_bp.route("/admin_staff/quanLyKhachHang")
@login_staff_or_admin
def quan_ly_khach_hang():
    users = User.query.filter(User.user_role == Role.USER).all()

    # Gắn thêm thuộc tính `total_spent` cho mỗi user
    for u in users:
        u.total_spent = sum(
            r.final_amount or 0
            for r in u.receipts
            if r.is_paid
        )

    return render_template("admin_staff/quanLyKhachHang.html", users=users, path="/admin_staff/quanLyKhachHang")

# Xoá người dùng
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Người dùng không tồn tại!'}), 404

    try:
        # ✅ Xoá phiếu nhập kho
        ImportReceipt.query.filter_by(user_id=user.id).delete()
        db.session.flush()

        # ✅ Xoá địa chỉ
        Address.query.filter_by(user_id=user.id).delete()
        db.session.flush()

        # ✅ Xoá sản phẩm yêu thích
        FavoriteProduct.query.filter_by(user_id=user.id).delete()
        db.session.flush()

        # ✅ Xoá hoá đơn & chi tiết & comment
        receipts = Receipt.query.filter_by(user_id=user.id).all()
        for receipt in receipts:
            receipt_details = ReceiptDetail.query.filter_by(receipt_id=receipt.id).all()
            for detail in receipt_details:
                Comment.query.filter_by(receipt_detail_id=detail.id).delete()
                db.session.flush()
            ReceiptDetail.query.filter_by(receipt_id=receipt.id).delete()
            db.session.flush()
        Receipt.query.filter_by(user_id=user.id).delete()
        db.session.flush()

        # ✅ Cuối cùng xoá user
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'Xóa người dùng thành công!'}), 200

    except Exception as e:
        db.session.rollback()
        print("❌ Lỗi khi xóa người dùng:", str(e))
        return jsonify({'error': 'Lỗi khi xóa người dùng!', 'details': str(e)}), 500


# Lấy danh sách đơn của người dùng
@app.route("/api/add-users", methods=["POST"])
def add_users():
    errors = []
    users_added = 0

    usernames_in_db = {u.username for u in User.query.all()}
    emails_in_db = {u.email for u in User.query.all()}
    phones_in_db = {u.phone for u in User.query.all() if u.phone}

    try:
        usernames = request.form.getlist("username[]")
        names = request.form.getlist("name[]")
        passwords = request.form.getlist("password[]")
        emails = request.form.getlist("email[]")
        genders = request.form.getlist("gender[]")
        phones = request.form.getlist("phone[]")
        birthdays = request.form.getlist("birthday[]")

        for i in range(len(usernames)):
            username = usernames[i].strip()
            name = names[i].strip()
            password = passwords[i].strip()
            email = emails[i].strip()
            gender = genders[i].strip()
            phone = phones[i].strip()
            birthday = birthdays[i].strip()

            # Check username/email/phone đã tồn tại
            if username in usernames_in_db:
                errors.append(f"Dòng {i + 1}: Username '{username}' đã tồn tại.")
                continue
            # Nếu ok thì thêm
            u = User(
                username=username,
                name=name,
                password=generate_password_hash(password),
                email=email,
                gender=Gender[gender] if gender else None,
                phone=phone if phone else None,
                birthday=birthday
            )
            db.session.add(u)
            usernames_in_db.add(username)
            emails_in_db.add(email)
            if phone:
                phones_in_db.add(phone)
            users_added += 1

        db.session.commit()

        return jsonify({
            "status": "success",
            "added": users_added,
            "errors": errors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# Lấy danh sách đơn hàng "Hoàn thành" của người dùng
@admin_staff_bp.route('/api/users/<int:user_id>/purchases')
def get_user_purchases(user_id):
    receipts = Receipt.query.filter_by(user_id=user_id, status='Hoàn thành').all()

    data = []
    for r in receipts:
        data.append({
            "receipt_id": r.id,
            "receiver_name": r.receiver_name,
            "receiver_phone": r.receiver_phone,
            "coin_used": r.coin_used or 0,
            "voucher_discount": r.voucher_discount or 0,
            "created_date": r.create_date.strftime('%d/%m/%Y %H:%M'),
            "delivery_method": r.delivery_method,
            "final_amount": r.final_amount
        })

    return jsonify(data)

# Lấy danh sách bình luận của người dùng
@app.route('/api/users/<int:user_id>/comments')
def get_user_comments(user_id):
    comments = Comment.query.filter_by(user_id=user_id).all()
    data = []

    for c in comments:
        receipt_detail = c.receipt_detail  # lấy receipt_detail
        product = receipt_detail.product if receipt_detail else None

        data.append({
            'product_id': product.id if product else None,
            'product_name': product.name if product else "Sản phẩm không tồn tại",
            'product_image': product.image if product else "",
            'content': c.content,
            'images': [img.image_url for img in c.images],
            'star': c.rating,
            'created_date': c.created_date.strftime('%H:%M:%S %d/%m/%Y')
        })

    return jsonify(data)

# Lấy danh sách sản phẩm yêu thích của người dùng
@app.route('/api/users/<int:user_id>/love-products')
def get_favorite_products(user_id):
    favorites = (
        FavoriteProduct.query
        .filter_by(user_id=user_id)
        .join(Product)
        .with_entities(Product.id, Product.name, Product.image)
        .all()
    )

    data = []
    for product_id, name, image in favorites:
        data.append({
            "product_id": product_id,
            "product_name": name,
            "product_image": image
        })

    return jsonify(data)

# -----------------------------------------------------------------------------------------------------------------------
#                                               QUẢN LÝ SẢN PHẨM
# -----------------------------------------------------------------------------------------------------------------------

# Trang quản lý sản phẩm
@admin_staff_bp.route("/admin_staff/quanLySanPham")
@login_staff_or_admin
def quan_ly_san_pham():
    # Truy vấn tất cả sản phẩm
    products = Product.query.filter_by(is_deleted=False).all()

    # Truy vấn tổng số lượng đã nhập cho từng product_id
    import_quantities = (
        db.session.query(ImportReceiptDetail.product_id, func.sum(ImportReceiptDetail.quantity))
        .group_by(ImportReceiptDetail.product_id)
        .all()
    )
    import_quantity_map = {pid: qty for pid, qty in import_quantities}

    # ✅ Truy vấn tồn kho hiện tại từ bảng ProductInventory
    inventory_quantities = (
        db.session.query(ProductInventory.product_id, func.sum(ProductInventory.quantity))
        .group_by(ProductInventory.product_id)
        .all()
    )
    inventory_quantity_map = {pid: qty for pid, qty in inventory_quantities}

    # Truyền vào template
    return render_template(
        "admin_staff/quanLySanPham.html", path="/admin_staff/quanLySanPham",
        products=products,
        import_quantity_map=import_quantity_map,
        inventory_quantity_map=inventory_quantity_map  # ✅ truyền vào template
    )

# Cập nhật thông tin sản phẩm - Lấy thông tin sản phẩm theo ID
@admin_staff_bp.route('/api/productsEdit/<int:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'error': 'Không tìm thấy sản phẩm'}), 404

    return jsonify({
        'id': product.id,
        'name': product.name,
        'price': product.price,
        'image': product.image,
        'category_id': product.category_id,
        'voucher': product.voucher,
        'daban': product.daban,
        'like': product.like,
        'donvitinh': product.donvitinh,
        'thuong_hieu': product.thuong_hieu,
        'xuat_xu': product.xuat_xu,
        'quy_cach_dong_goi': product.quy_cach_dong_goi,
        'bao_quan': product.bao_quan,
        'cach_dung': product.cach_dung,
        'mo_ta_san_pham': product.mo_ta_san_pham

    })

# Cập nhật thông tin sản phẩm - PUT request
@app.route('/api/productsEdit/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    try:
        data = request.get_json()

        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({'error': 'Không tìm thấy sản phẩm'}), 404

        product.name = data.get('name')
        product.price = data.get('price')
        product.image = data.get('image')
        product.category_id = data.get('category_id')
        product.voucher = data.get('voucher')
        product.daban = data.get('daban')
        product.like = data.get('like')
        product.donvitinh = data.get('donvitinh')
        product.thuong_hieu = data.get('thuong_hieu')
        product.xuat_xu = data.get('xuat_xu')
        product.quy_cach_dong_goi = data.get('quy_cach_dong_goi')
        product.bao_quan = data.get('bao_quan')
        product.cach_dung = data.get('cach_dung')
        product.mo_ta_san_pham = data.get('mo_ta_san_pham')

        db.session.commit()
        return jsonify({'message': 'Cập nhật thành công'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Xoá sản phẩm
@admin_staff_bp.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    try:
        product = db.session.get(Product, product_id)
        if not product:
            print("[DEBUG] Không tìm thấy sản phẩm với ID:", product_id)
            return jsonify({"error": "Không tìm thấy sản phẩm"}), 404

        product.is_deleted = True
        db.session.commit()
        return jsonify({"message": "Xoá thành công"})
    except Exception as e:
        db.session.rollback()
        print("[ERROR] Lỗi khi xoá sản phẩm:", e)
        return jsonify({"error": "Lỗi server", "detail": str(e)}), 500

# Lấy danh sách tồn kho của sản phẩm theo ID
@admin_staff_bp.route("/api/product-inventory/<int:product_id>")
def get_product_inventory(product_id):
    inventories = db.session.query(ProductInventory).join(Product).filter(ProductInventory.product_id == product_id).all()
    if inventories:
        data = []
        for inv in inventories:
            data.append({
                "id": inv.id,
                "name": inv.product.name,
                "image": inv.product.image,  # đảm bảo cột `image` có trong bảng Product
                "quantity": inv.quantity,
                "type": inv.status  # status: 1 = hàng mới, 2 = hàng cũ
            })
        return jsonify(data)
    return jsonify([])  # Trả về mảng rỗng nếu không có tồn kho


# Tạo sản phẩm mới
@app.route('/api/products/bulk-create', methods=['POST'])
def create_multiple_products():
    try:
        data = request.json  # Nhận danh sách sản phẩm

        for item in data:
            product = Product(
                name=item.get('name'),
                price=float(item.get('price')),
                image=item.get('image_url'),
                category_id=int(item.get('category_id')),
                donvitinh=item.get('unit'),

                # Các trường chữ để None, số để 0
                description=None,
                voucher=0,
                daban=0,
                like=0,
                thuong_hieu=None,
                xuat_xu=None,
                quy_cach_dong_goi=None,
                bao_quan=None,
                cach_dung=None,
                mo_ta_san_pham=None,
                is_deleted=False
            )

            db.session.add(product)

        db.session.commit()
        return jsonify({"message": "Tạo sản phẩm thành công."}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Tải ảnh lên Cloudinary
@admin_staff_bp.route("/api/upload-image", methods=["POST"])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    image_file = request.files['image']

    try:
        result = cloudinary.uploader.upload(image_file)
        return jsonify({'url': result['secure_url']})
    except Exception as e:
        print("Upload error:", e)
        return jsonify({'error': 'Upload failed'}), 500

# Lấy danh sách sản phẩm đã xoá
@admin_staff_bp.route('/api/deleted-products')
def get_deleted_products():
    deleted_products = Product.query.filter_by(is_deleted=True).all()
    result = []
    for idx, p in enumerate(deleted_products, start=1):
        result.append({
            'stt': idx,
            'id': p.id,
            'name': p.name,
            'image': p.image,
            'price': f"{p.price:,.0f} VNĐ",
            'deleted_by': 'Quản trị viên',
            'deleted_at': 'Chưa lưu',
        })
    return jsonify(result)

# Khôi phục sản phẩm đã xoá
@admin_staff_bp.route('/api/products/<int:product_id>/restore', methods=['POST'])
def restore_product(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({'message': 'Không tìm thấy sản phẩm'}), 404

    product.is_deleted = False
    db.session.commit()
    return jsonify({'message': 'Sản phẩm đã được khôi phục'})


# Lấy danh sách các danh mục sản phẩm
@app.route('/api/categories')
def get_categories():
    categories = Category.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'parent_id': c.parent_id
    } for c in categories])

# Lấy danh sách sản phẩm
@admin_staff_bp.route('/api/products')
def get_products():
    products = Product.query.all()
    data = []
    for p in products:
        data.append({
            'id': p.id,
            'name': p.name,
            'category': p.category.name,  # Giả sử đã khai báo quan hệ Product → Category
            "is_deleted": p.is_deleted
        })
    return jsonify(data)

# -----------------------------------------------------------------------------------------------------------------------
#                                               QUẢN LÝ ĐƠN HÀNG
# -----------------------------------------------------------------------------------------------------------------------

# Trang quản lý đơn hàng
@admin_staff_bp.route("/admin_staff/quanLyDonHang")
@login_staff_or_admin
def quan_ly_don_hang():
    receipts = db.session.query(Receipt, User.username, Voucher.name) \
        .join(User, Receipt.user_id == User.id) \
        .outerjoin(Voucher, Receipt.voucher_id == Voucher.id) \
        .order_by(Receipt.create_date.desc()).all()

    receipt_details_map = {}
    for r, _, _ in receipts:
        # lấy danh sách sản phẩm trong từng đơn
        details = ReceiptDetail.query.filter_by(receipt_id=r.id).all()
        receipt_details_map[r.id] = details

    return render_template("admin_staff/quanLyDonHang.html", receipts=receipts, receipt_details_map=receipt_details_map, path="/admin_staff/quanLyDonHang")


# Tạo đơn hàng mới từ nhân viên
@app.route('/api/staff/ordersReceipt/create', methods=['POST'])
@login_required
def staff_create_ordersReceipt():
    data = request.get_json()

    try:
        receiver_name = data.get('receiver_name')
        receiver_phone = data.get('receiver_phone')
        receiver_address = data.get('receiver_address')
        payment_method = data.get('payment_method')
        delivery_method = data.get('delivery_method')
        note_message = data.get('note_message')
        total_amount = data.get('total_amount')
        final_amount = data.get('final_amount')
        items = data.get('items', [])

        if not items:
            return jsonify({'status': 'error', 'message': 'Không có sản phẩm nào trong đơn hàng'}), 400

        # Tạo đơn hàng mới
        receipt = Receipt(
            user_id=current_user.id,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            receiver_address=receiver_address,
            payment_method=payment_method,
            delivery_method=delivery_method,
            note_message=note_message,
            total_amount=total_amount,
            final_amount=final_amount,
            status='Đang xử lý',
            create_date=datetime.now(),
            created_by_staff = True
        )
        db.session.add(receipt)
        db.session.flush()  # Lấy được receipt.id trước khi commit

        # Lưu chi tiết sản phẩm và trừ kho
        for item in items:
            product_id = item['product_id']
            quantity = item['quantity']
            price = item['price']

            # Lưu chi tiết đơn hàng
            detail = ReceiptDetail(
                receipt_id=receipt.id,
                product_id=product_id,
                quantity=quantity,
                price=price
            )
            db.session.add(detail)

            # Trừ kho từ các ProductInventory (ưu tiên status 2 trước)
            quantity_to_deduct = quantity
            inventories = ProductInventory.query \
                .filter(ProductInventory.product_id == product_id,
                        ProductInventory.status.in_([1, 2]),
                        ProductInventory.quantity > 0) \
                .order_by(ProductInventory.status.desc(), ProductInventory.id.asc()) \
                .all()

            for inventory in inventories:
                if quantity_to_deduct == 0:
                    break

                deduct = min(quantity_to_deduct, inventory.quantity)
                inventory.quantity -= deduct
                quantity_to_deduct -= deduct

                db.session.add(ReceiptInventoryDetail(
                    receipt_id=receipt.id,
                    product_id=product_id,
                    inventory_id=inventory.id,
                    quantity=deduct
                ))

            if quantity_to_deduct > 0:
                raise Exception(f"Sản phẩm ID {product_id} không đủ số lượng tồn kho!")

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Đơn hàng đã được tạo và cập nhật tồn kho thành công!'})

    except Exception as ex:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'Lỗi: {str(ex)}'}), 500


# Huỷ đơn hàng
@admin_staff_bp.route('/api/receipt/<int:receipt_id>/cancel', methods=['POST'])
@login_required
def staff_cancel_receipt(receipt_id):
    try:
        receipt = db.session.get(Receipt, receipt_id)
        if not receipt:
            return jsonify({'message': 'Không tìm thấy đơn hàng'}), 404

        if receipt.status not in ['Đang xử lý', 'Chờ thanh toán']:
            return jsonify({'message': 'Đơn hàng không thể huỷ!'}), 400

        # ✅ Cập nhật trạng thái đơn hàng
        receipt.status = 'Đã hủy'

        # ✅ Hoàn lại xu nếu có người dùng
        user = db.session.get(User, receipt.user_id)
        if user:
            user.coin = (user.coin or 0) + (receipt.coin_used or 0)

        # ✅ Hoàn tồn kho từ bảng ReceiptInventoryDetail
        restore_details = ReceiptInventoryDetail.query.filter_by(receipt_id=receipt.id).all()

        for detail in restore_details:
            inventory = db.session.get(ProductInventory, detail.inventory_id)
            if inventory:
                inventory.quantity += detail.quantity
            else:
                # Trường hợp inventory bị xóa hoặc không tồn tại
                fallback = ProductInventory.query.filter_by(product_id=detail.product_id, status=2).first()
                if fallback:
                    fallback.quantity += detail.quantity
                else:
                    fallback = ProductInventory(
                        product_id=detail.product_id,
                        quantity=detail.quantity,
                        status=2
                    )
                    db.session.add(fallback)

            # ✅ Xoá dòng đã hoàn tất từ ReceiptInventoryDetail
            db.session.delete(detail)

        db.session.commit()
        return jsonify({'message': 'Đơn hàng đã được huỷ thành công'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Lỗi: {str(e)}'}), 500

# Hoàn thành đơn hàng
@admin_staff_bp.route('/api/receipt/<int:receipt_id>/complete', methods=['POST'])
def complete_receipt(receipt_id):
    try:
        receipt = db.session.get(Receipt, receipt_id)
        if not receipt:
            return jsonify({'error': 'Không tìm thấy đơn hàng'}), 404

        if receipt.status == 'Hoàn thành':
            return jsonify({'message': 'Đơn hàng đã hoàn thành trước đó'}), 400

        # ✅ Cập nhật trạng thái
        receipt.status = 'Hoàn thành'

        # ✅ Cộng xu khi hoàn thành đơn
        if receipt.coin_earned and receipt.user_id:
            user = db.session.get(User, receipt.user_id)
            if user:
                user.coin = (user.coin or 0) + receipt.coin_earned

        # ✅ Xoá các dòng chi tiết đơn
        ReceiptInventoryDetail.query.filter_by(receipt_id=receipt.id).delete(synchronize_session=False)

        db.session.commit()  # ✅ Commit lần 1 để áp dụng xoá

        # ✅ Lúc này mới tạo subquery đúng (đã loại bỏ các dòng chi tiết cũ)
        subquery = db.session.query(ReceiptInventoryDetail.inventory_id).distinct()
        ProductInventory.query.filter(
            ProductInventory.quantity == 0,
            ~ProductInventory.id.in_(subquery)
        ).delete(synchronize_session=False)

        db.session.commit()  # ✅ Commit lần 2 để xoá tồn kho = 0

        return '', 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Lấy danh sách sản phẩm từ API cho bán hàng trực tiếp
@app.route("/api/staff/products")
def api_products():
    products = Product.query.with_entities(Product.id, Product.name, Product.price, Product.donvitinh).all()
    result = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "donvitinh": p.donvitinh
        }
        for p in products
    ]
    return jsonify(result)


# -----------------------------------------------------------------------------------------------------------------------
#                                               QUẢN LÝ NHẬP KHO
# -----------------------------------------------------------------------------------------------------------------------

# Trang quản lý nhập kho
@admin_staff_bp.route("/admin_staff/quanLyNhapKho")
@login_staff_or_admin  # Nếu bạn đã kiểm tra phân quyền trong decorator riêng
def quan_ly_nhap_kho():
    # from datetime import datetime
    current_date = datetime.now().strftime("%d/%m/%Y")
    next_receipt_number = dao.get_next_receipt_number()

    # ✅ Truy vấn tất cả phiếu nhập (có thể lọc theo người nhập nếu cần)
    receipts = (
        db.session.query(ImportReceipt)
        .order_by(ImportReceipt.created_date.desc())
        .all()
    )

    return render_template(
        "admin_staff/quanLyNhapKho.html", path="/admin_staff/quanLyNhapKho",
        receipt_date=current_date,
        receipt_number=next_receipt_number,
        staff_name=current_user.name,
        receipts=receipts
    )

# Lấy danh sách tồn kho sản phẩm inventory
@admin_staff_bp.route("/api/product_inventories")
def get_product_inventories():
    inventories = db.session.query(ProductInventory.product_id, db.func.sum(ProductInventory.quantity)) \
                    .group_by(ProductInventory.product_id).all()
    return jsonify({str(pid): float(qty) for pid, qty in inventories})

# Lấy danh sách cài đặt để nhập kho
@admin_staff_bp.route("/api/settings")
def get_settings():
    settings = Setting.query.all()
    return jsonify({s.key: float(s.value) for s in settings})

# Tạo phiếu nhập kho mới
@admin_staff_bp.route("/admin_staff/receipts/create", methods=["POST"])
def create_import_receipt():
    data = request.json
    products = data.get("products", [])
    note = data.get("note", "")

    try:
        total_products = sum([p["quantity"] for p in products])
        total_amount = sum([p["quantity"] * p["price_import"] for p in products])

        # Tạo phiếu nhập
        receipt = ImportReceipt(
            created_date=datetime.now(),
            user_id=current_user.id,
            note=note,
            total_products_import=total_products,
            total_amount_import=total_amount
        )
        db.session.add(receipt)
        db.session.flush()

        for p in products:
            product_id = p["product_id"]
            quantity = p["quantity"]
            price_import = p["price_import"]
            expiry_date = datetime.strptime(p["expiry_date"], "%Y-%m-%d") if p["expiry_date"] else None
            supplier = p["supplier"]

            # ❗ Cập nhật các dòng tồn kho cũ (status=1) của sản phẩm này => status=2
            ProductInventory.query.filter_by(product_id=product_id, status=1).update({"status": 2})

            # ✅ Thêm dòng tồn kho mới (status=1)
            inventory = ProductInventory(
                product_id=product_id,
                quantity=quantity,
                status=1
            )
            db.session.add(inventory)

            # ✅ Thêm chi tiết phiếu nhập
            detail = ImportReceiptDetail(
                import_receipt_id=receipt.id,
                product_id=product_id,
                quantity=quantity,
                price_import=price_import,
                expiry_date=expiry_date,
                supplier=supplier
            )
            db.session.add(detail)

        db.session.commit()
        return jsonify({"status": "success", "message": "Lưu phiếu nhập và cập nhật tồn kho thành công."})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# -----------------------------------------------------------------------------------------------------------------------
#                                               QUẢN LÝ BÁO CÁO DOANH THU
# -----------------------------------------------------------------------------------------------------------------------

# Báo cáo doanh thu
@admin_staff_bp.route("/admin_staff/baoCaoDoanhThu")
@login_staff_or_admin
def bao_cao_doanh_thu():
    return render_template("admin_staff/baoCaoDoanhThu.html", path="/admin_staff/baoCaoDoanhThu")