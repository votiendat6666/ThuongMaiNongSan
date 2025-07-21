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

from saleapp import app, login, db, mail, google, facebook
from flask import render_template, request, redirect, abort, session, jsonify, url_for, make_response, flash, \
    current_app
import dao
from flask_login import login_user, logout_user, current_user, login_required
from saleapp import admin
import cloudinary.uploader
from saleapp.models import *
import random
from saleapp.utils import count_cart, get_cart_stats

@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = dao.get_user_by_id(session['user_id'])

    cart = session.get('cart', {})
    total_quantity = sum(item['quantity'] for item in cart.values()) if cart else 0

    category_id = request.args.get('category_id')
    keyword = request.args.get('q')

    query = db.session.query(Product)

    selected_category_id = None
    selected_parent_id = None

    if category_id:
        try:
            category_id = int(category_id)
            selected_category = db.session.query(Category).get(category_id)

            if selected_category:
                selected_category_id = selected_category.id

                if selected_category.children:
                    # Nếu là danh mục cha
                    child_ids = [child.id for child in selected_category.children]
                    query = query.filter(Product.category_id.in_(child_ids))
                    selected_parent_id = selected_category.id
                else:
                    # Nếu là danh mục con
                    query = query.filter(Product.category_id == category_id)
                    selected_parent_id = selected_category.parent_id
        except:
            category_id = None

    if keyword:
        query = query.filter(Product.name.ilike(f"%{keyword}%"))

    products = query.limit(24).all()

    flash_sale_products = dao.get_flash_sale_products()
    best_seller_products = dao.get_best_seller_products()
    beauty_products = dao.get_category_products_by_daban(parent_id=30000)
    favorites_books_products = dao.get_favorites_books_products()
    pharma_products = dao.get_category_products_by_daban(parent_id=90000)
    foods_products = dao.get_category_products_by_daban(parent_id=100000)
    plays_products = dao.get_category_products_by_daban(parent_id=20000)

    return render_template(
        'index.html',
        products=products,
        flash_sale_products=flash_sale_products,
        best_seller_products=best_seller_products,
        beauty_products=beauty_products,
        favorites_books_products=favorites_books_products,
        pharma_products=pharma_products,
        foods_products=foods_products,
        plays_products=plays_products,
        user=user,
        cart_stats={'total_quantity': total_quantity},
        selected_category_id=selected_category_id,
        selected_parent_id=selected_parent_id,
        show_related_section=True,
        show_full_image = True

    )


# Xem danh sách thể loại
@app.route('/load-products')
def load_products():
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 24, type=int)
    category_id = request.args.get('category_id', type=int)
    keyword = request.args.get('q', '')

    query = Product.query

    if category_id:
        selected_category = Category.query.get(category_id)
        if selected_category:
            if selected_category.children:
                child_ids = [c.id for c in selected_category.children]
                query = query.filter(Product.category_id.in_(child_ids))
            else:
                query = query.filter(Product.category_id == category_id)

    if keyword:
        query = query.filter(Product.name.ilike(f"%{keyword}%"))

    products = query.offset(offset).limit(limit).all()

    if not products:
        return ''

    return render_template('product-items.html', products=products)



# Xem thống kê toàn bộ
@app.route('/stats')
def stats():
    total_revenue_value = utils.total_revenue_all()
    total_quantity = utils.total_quantity()
    return render_template('stats.html', total_revenue_all=total_revenue_value, total_quantity=total_quantity)

# Xem danh sách sản phẩm theo thể loại
@app.route('/category/<int:category_id>')
def category_page(category_id):
    categories = dao.load_categories()

    selected_parent_id = None
    for c in categories:
        if c['id'] == category_id:
            if c['parent_id'] is None:
                selected_parent_id = c['id']
            else:
                selected_parent_id = c['parent_id']
            break

    keyword = request.args.get('q')

    if category_id == 0:
        # Tìm kiếm chung, không theo category
        products = db.session.query(Product)
        if keyword:
            products = products.filter(Product.name.ilike(f"%{keyword}%"))
        products = products.all()
    else:
        # Lọc theo category
        products = dao.load_products_by_category(category_id)
        if keyword:
            products = [p for p in products if keyword.lower() in p.name.lower()]

    return render_template(
        'category.html',
        products=products,
        categories=categories,
        selected_category_id=category_id,
        selected_parent_id=selected_parent_id
    )



# Xem chi tiet san pham
@app.route('/products/<int:id>')
def details(id):
    products = Product.query.get(id)
    if products is None:
        abort(404)

    # Kiểm tra like
    is_liked = False
    if current_user.is_authenticated:
        like = FavoriteProduct.query.filter_by(
            customer_id=current_user.id, product_id=id
        ).first()
        is_liked = like is not None

    # ➜ Lấy sản phẩm liên quan (ví dụ: cùng category)
    related_products = Product.query.filter(
        Product.category_id == products.category_id,
        Product.id != products.id
    ).limit(20).all()

    random_pages = random.randint(150, 500)
    flash_sale_products = dao.get_flash_sale_products()
    best_seller_products = dao.get_best_seller_products()
    beauty_products = dao.get_category_products_by_daban(parent_id=30000)
    favorites_books_products = dao.get_favorites_books_products()
    pharma_products = dao.get_category_products_by_daban(parent_id=50000)
    foods_products = dao.get_category_products_by_daban(parent_id=100000)
    plays_products = dao.get_category_products_by_daban(parent_id=20000)


    return render_template(
        'product-details.html',
        flash_sale_products=flash_sale_products,
        best_seller_products=best_seller_products,
        beauty_products =beauty_products,
        favorites_books_products=favorites_books_products,
        pharma_products=pharma_products,
        foods_products=foods_products,
        plays_products=plays_products,
        products=products,
        is_liked=is_liked,
        related_products=related_products,  # ➜ Đẩy ra template
        random_pages=random_pages,
        show_related_section=False
    )



@app.route('/api/like-product/<int:product_id>', methods=['POST'])
@login_required
def like_product(product_id):
    favorite = FavoriteProduct.query.filter_by(customer_id=current_user.id, product_id=product_id).first()
    product = Product.query.get(product_id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    if favorite:
        # Unlike
        db.session.delete(favorite)
        product.like = max(0, product.like - 1)
        db.session.commit()
        return jsonify({"liked": False, "like_count": product.like})
    else:
        # Like
        new_fav = FavoriteProduct(customer_id=current_user.id, product_id=product_id)
        db.session.add(new_fav)
        product.like += 1
        db.session.commit()
        return jsonify({"liked": True, "like_count": product.like})



# Xem danh sách sách theo thể loại
@app.route('/api/books', methods=['GET'])
def get_books():
    books = Product.query.all()
    book_list = [{
        "id": book.id,
        "name": book.name,
        "category": book.category.name,
        "price": book.price
    } for book in books]
    return jsonify(book_list)


# Nhập hóa đơn bán hàng - hoá đơn bán lẻ
@app.route('/import_bill', methods=['POST'])
def import_bill():
    try:
        data = request.json
        customer_name = data.get("customerName")
        invoice_date = data.get("invoiceDate")
        staff_name = data.get("staffName")
        details = data.get("details")  # Dạng JSON chứa danh sách sách

        # Tạo một hóa đơn mới
        date_sale = datetime.now()
        new_bill = SaleBook(
            customer_name=customer_name,
            created_date=date_sale,
            staff_id=current_user.id  # Thay ID nhân viên xử lý hóa đơn tại đây
        )
        db.session.add(new_bill)
        db.session.flush()  # Đảm bảo `new_bill` có ID để dùng ở bước tiếp theo

        # Thêm chi tiết hóa đơn
        for detail in details:
            book = Product.query.get(detail.get("bookId"))
            if not book or book.quantity < int(detail.get("quantity")):
                return jsonify({"message": f"Sách {book.name if book else 'không xác định'} không đủ số lượng"}), 400

            book.quantity -= int(detail.get("quantity"))  # Cập nhật tồn kho
            db.session.add(book)

            bill_detail = SaleBookDetail(
                sale_book_id=new_bill.id,
                product_id=detail.get("bookId"),
                quantity=int(detail.get("quantity")),
                price=book.price
            )
            db.session.add(bill_detail)

        # Lưu thay đổi
        db.session.commit()

        return jsonify({"message": "Hóa đơn được lưu thành công!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Đã xảy ra lỗi: {str(e)}"}), 500



# Gửi email chào mừng người dùng mới
def send_welcome_email(to_email, username):
    msg = Message(
        subject="Chào mừng bạn!",
        recipients=[to_email]
    )
    msg.body = f"""
    Xin chào {username},

    Chào mừng bạn đã đăng ký tài khoản thành công trên hệ thống TD FOOD!

    Thân mến,
    Đội ngũ hỗ trợ.
    """
    mail.send(msg)

@app.route('/login', methods=['GET', 'POST'])
def login_my_user():
    err_msg = ""
    active_form = 'login'  # ✅ Mặc định

    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'GET':
        next_url = request.args.get('next')
        if next_url:
            session['next'] = next_url

        form_type = request.args.get('form')
        if form_type == 'register':
            active_form = 'register'

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # ✅ ---- XỬ LÝ ĐĂNG KÝ ----
        if form_type == 'register':
            active_form = 'register'
            name = request.form.get('name')
            username = request.form.get('username')
            password = request.form.get('password')
            confirm = request.form.get('confirm')
            email = request.form.get('email')

            if password != confirm:
                err_msg = "Mật khẩu không khớp!"
                return render_template('login.html', err_msg=err_msg, active_form=active_form)

            existing = Customer.query.filter_by(username=username).first()
            if existing:
                err_msg = "Tên đăng nhập đã tồn tại!"
                return render_template('login.html', err_msg=err_msg, active_form=active_form)

            try:
                hashed_pw = generate_password_hash(password)

                c = Customer(name=name, username=username, password=hashed_pw,
                             email=email, user_role=Role.USER, is_active=True)
                db.session.add(c)
                db.session.commit()

                # ✅ GỬI MAIL CHÀO MỪNG
                send_welcome_email(email, name)

                return redirect('/login')
            except Exception as e:
                db.session.rollback()
                err_msg = "Đăng ký thất bại: " + str(e)
                return render_template('login.html', err_msg=err_msg, active_form=active_form)

        # ✅ ---- XỬ LÝ ĐĂNG NHẬP ----
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        user = None
        if role == 'staff':
            role = Role.STAFF
            user = dao.auth_staff(username, password, role=role)
        elif role == 'admin':
            role = Role.ADMIN
            user = dao.auth_staff(username, password, role=role)
        elif role == 'manager':
            role = Role.MANAGER
            user = dao.auth_staff(username, password, role=role)
        else:
            role = Role.USER
            user = dao.auth_user(username, password, role=role)

        if user:
            login_user(user=user)
            session.modified = True

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify(success=True, role=role.name)

            next_page = session.pop('next', None)
            if role in [Role.ADMIN, Role.MANAGER]:
                return redirect('/admin')
            elif role == Role.STAFF:
                return redirect('/staff')
            return redirect(next_page or '/')
        else:
            err_msg = "*Sai tài khoản hoặc mật khẩu!"
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return make_response(err_msg, 401)

    return render_template('login.html', err_msg=err_msg, active_form=active_form)

@app.route('/login/google')
def login_google():
    session['next'] = request.args.get('next') or '/'
    nonce = generate_token(32)
    session['nonce'] = nonce

    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)

@app.route('/auth/google/callback')
def google_callback():
    token = google.authorize_access_token()
    nonce = session.pop('nonce', None)
    user_info = google.parse_id_token(token, nonce=nonce)

    email = user_info['email']
    name = user_info.get('name')

    user = Customer.query.filter_by(email=email).first()
    if not user:
        # ✅ Tạo pass ngẫu nhiên rồi hash
        random_pw = secrets.token_urlsafe(16)
        hashed_pw = generate_password_hash(random_pw)

        user = Customer(
            name=name,
            username=email.split('@')[0],
            email=email,
            password=hashed_pw,  # ✅ Không để None
            user_role=Role.USER,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect(session.pop('next', '/'))


@app.route('/login/facebook')
def facebook_login():
    redirect_uri = url_for('facebook_callback', _external=True)
    return facebook.authorize_redirect(redirect_uri)
@app.route('/auth/facebook/callback')
def facebook_callback():
    token = facebook.authorize_access_token()
    resp = facebook.get('me?fields=id,name,email')
    profile = resp.json()

    # 👉 Lấy thông tin user
    facebook_id = profile['id']
    name = profile['name']
    email = profile.get('email')

    # 👉 Kiểm tra user tồn tại chưa, nếu chưa thì tạo
    user = Customer.query.filter_by(email=email).first()
    if not user:
        random_pw = secrets.token_urlsafe(16)
        hashed_pw = generate_password_hash(random_pw)
        user = Customer(
            name=name,
            username=email.split('@')[0],
            email=email,
            password= hashed_pw,  # Vì login Facebook không có password
            user_role=Role.USER,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    return redirect('/')


# Đăng xuất
@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    session.pop('cart', None)          # Xóa giỏ hàng
    session.pop('voucher_id', None)    # Xóa voucher đã chọn
    return redirect('/')



# Thêm sản phẩm vào giỏ hàng
@app.route('/api/add-cart', methods=['POST'])
@login_required
def add_to_cart():
    data = request.json
    product_id = data.get('id')
    quantity = data.get('quantity', 1)

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()

    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_quantity = sum(item.quantity for item in items)
    total_items = len(items)  # ✅

    return jsonify({
        'total_quantity': total_quantity,
        'total_items': total_items  # ✅ Trả thêm
    })



# Cập nhật số lượng sản phẩm trong giỏ hàng cart
@app.route('/api/update-cart', methods=['PUT'])
@login_required
def update_cart():
    data = request.get_json()
    product_id = data.get('id')
    quantity = data.get('quantity', 1)

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity = quantity
        db.session.commit()

    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_quantity = sum(item.quantity for item in items)
    total_amount = sum(item.quantity * item.product.price for item in items)
    total_items = len(items)  # ✅

    return jsonify({
        'total_quantity': total_quantity,
        'total_amount': total_amount,
        'total_items': total_items  # ✅
    })


# Cập nhật sô lượng sản phẩm giỏ hàng header
@app.route('/api/cart-stats')
def api_cart_stats():
    if current_user.is_authenticated:
        stats = get_cart_stats(current_user)
        return jsonify(stats)
    else:
        return jsonify({'total_quantity': 0, 'total_amount': 0})


# Xóa sản phẩm khỏi giỏ hàng
@app.route('/api/delete-cart/<int:product_id>', methods=['DELETE'])
@login_required
def delete_cart(product_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()

    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_quantity = sum(item.quantity for item in items)
    total_amount = sum(item.quantity * item.product.price for item in items)
    total_items = len(items)  # ✅

    return jsonify({
        'total_quantity': total_quantity,
        'total_amount': total_amount,
        'total_items': total_items  # ✅
    })


@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    """
    Lấy thông tin giỏ hàng của người dùng hiện tại.
    """
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    cart_data = [{
        'product_id': item.product_id,
        'quantity': item.quantity,
        'product_name': item.product.name,
        'price': item.product.priceqs
    } for item in cart_items]

    total_quantity = sum(item.quantity for item in cart_items)
    total_amount = sum(item.quantity * item.product.price for item in cart_items)

    return jsonify({
        'cart_items': cart_data,
        'total_quantity': total_quantity,
        'total_amount': total_amount
    })

# Hiển thị thống kê giỏ hàng trong template
@app.context_processor
def inject_cart_stats():
    stats = get_cart_stats(current_user)
    print("Inject cart stats:", stats)
    return {'cart_stats': stats}

# Xem giỏ hàng
@app.route('/cart')
def cart():
    session.pop('voucher_id', None)
    session.pop('use_coin', None)
    session.pop('payment_method', None)
    cart_items = []
    stats = {'total_quantity': 0, 'total_amount': 0}
    all_selected = False  # mặc định ban đầu

    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

        total_quantity = sum(item.quantity for item in cart_items)
        total_amount = sum(item.quantity * item.product.price for item in cart_items)

        stats = {
            'total_quantity': total_quantity,
            'total_amount': total_amount
        }

        all_selected = all(c.is_selected for c in cart_items) if cart_items else False

    return render_template('cart.html',
                           cart_items=cart_items,
                           stats=stats,
                           all_selected=all_selected)

#Trang Thanh Toán - lấy dữu liệu từ giỏ hàng - load địa chỉ, coin, voucher
@app.route("/api/pay", methods=['POST', 'GET'])
@login_required
def pay():

    # 🛒 Lấy giỏ hàng đã tick
    addresses = Address.query.filter_by(customer_id=current_user.id).all()
    selected_cart_items = CartItem.query.filter_by(user_id=current_user.id, is_selected=True).all()

    order_total_product_selected = len(selected_cart_items)
    order_total_quantity_selected = sum(item.quantity for item in selected_cart_items)
    order_total_amount_selected = sum(item.quantity * item.product.price for item in selected_cart_items)

    # 📅 Ngày giao dự kiến
    delivery_date = datetime.now() + timedelta(days=5)
    formatted_date = delivery_date.strftime('%d Tháng %m Năm %Y')

    vouchers = dao.load_voucher()

    voucher_discount = 0
    session_voucher_code = ""
    session_voucher_price = 0
    session_voucher_min_order = 0

    # ✅ Nếu có voucher trong session → tính luôn
    if 'voucher_id' in session:
        voucher = db.session.get(Voucher, session['voucher_id'])
        if voucher:
            voucher_discount = voucher.price_voucher
            session_voucher_code = voucher.code
            session_voucher_price = voucher.price_voucher
            session_voucher_min_order = voucher.min_order_value

    payment_method = session.get('payment_method', 'COD')  # Mặc định COD

    # 🎯 Tổng sau voucher
    order_total_amount_after_discount = max(order_total_amount_selected - voucher_discount, 0)

    # ✅ Tính coin
    customer = db.session.get(Customer, current_user.id)
    coin_balance = customer.coin if customer else 0

    use_coin = session.get('use_coin', False)
    if use_coin:
        order_total_amount_after_discount = max(order_total_amount_after_discount - coin_balance, 0)

    return render_template(
        'oder.html',
        user=current_user,
        addresses=addresses,
        selected_cart_items=selected_cart_items,
        order_total_product_selected=order_total_product_selected,
        order_total_quantity_selected=order_total_quantity_selected,
        order_total_amount_selected=order_total_amount_selected,
        delivery_date=formatted_date,
        vouchers=vouchers,
        voucher_discount=voucher_discount,
        session_voucher_code=session_voucher_code,
        session_voucher_price=session_voucher_price,
        session_voucher_min_order=session_voucher_min_order,
        order_total_amount_after_discount=order_total_amount_after_discount,
        coin_balance=coin_balance,
        payment_method= payment_method
    )
#
# @app.route('/api/order', methods=['POST'])
# @login_required
# def create_order():
#     if session.get('order_processing'):
#         return jsonify({"message": "Đơn hàng đang xử lý, vui lòng đợi!"}), 429
#
#     session['order_processing'] = True
#
#     try:
#         # Lấy dữ liệu
#         data = request.get_json() or {}
#         note_message = data.get('note_message', session.get('note_message', '')).strip()
#         print(f"note_message received: '{note_message}'")  # Debug
#
#         # Kiểm tra giỏ hàng
#         cart_items = CartItem.query.filter_by(user_id=current_user.id, is_selected=True).all()
#         if not cart_items:
#             session.pop('order_processing', None)
#             return jsonify({"message": "Giỏ hàng trống."}), 400
#
#         # Kiểm tra địa chỉ
#         address = Address.query.filter_by(customer_id=current_user.id, is_default=True).first()
#         if not address:
#             session.pop('order_processing', None)
#             return jsonify({"message": "Bạn chưa có địa chỉ mặc định!"}), 400
#
#         # Tạo chuỗi địa chỉ
#         customer_address = f"{address.receiver_address_line}, {address.receiver_ward}, {address.receiver_district}, {address.receiver_province}"
#
#         # Phương thức thanh toán
#         payment_method = "MoMo" if session.get('payment_method') == 'MoMo' else "COD"
#         delivery_method = "Thanh toán Online" if payment_method == 'MoMo' else "Thanh toán khi nhận hàng"
#
#         # Tính toán tổng tiền
#         total_amount = sum(item.quantity * item.product.price for item in cart_items)
#         voucher_discount = 0
#         if voucher_id := session.get('voucher_id'):
#             if voucher := db.session.get(Voucher, voucher_id):
#                 voucher_discount = voucher.price_voucher
#
#         # Kiểm tra khách hàng và coin
#         customer = db.session.get(Customer, current_user.id)
#         if not customer:
#             session.pop('order_processing', None)
#             return jsonify({"message": "Không tìm thấy thông tin khách hàng!"}), 400
#
#         coin_used = customer.coin if session.get('use_coin', False) else 0
#         final_amount = max(total_amount - voucher_discount - coin_used, 0)
#
#         # Tạo đơn hàng
#         new_receipt = Receipt(
#             create_date=datetime.now(),
#             customer_id=current_user.id,
#             customer_phone=address.receiver_phone,
#             customer_address=customer_address,
#             delivery_method=delivery_method,
#             payment_method=payment_method,
#             total_amount=total_amount,
#             voucher_id=voucher_id,
#             voucher_discount=voucher_discount,
#             coin_used=coin_used,
#             final_amount=final_amount,
#             note_message=note_message
#         )
#
#         # Thêm chi tiết đơn hàng
#         for item in cart_items:
#             new_receipt.receipt_details.append(ReceiptDetail(
#                 product_id=item.product_id,
#                 quantity=item.quantity,
#                 price=item.product.price
#             ))
#
#         # Cập nhật coin
#         if coin_used > 0:
#             customer.coin = max(customer.coin - coin_used, 0)
#         customer.coin += sum(item.quantity for item in cart_items) * 100
#
#         # Xóa giỏ hàng
#         for item in cart_items:
#             db.session.delete(item)
#
#         # Lưu vào CSDL
#         db.session.add(new_receipt)
#         db.session.commit()
#
#         print(f"note_message saved: '{new_receipt.note_message}'")  # Debug
#         session.pop('order_processing', None)
#         session.pop('voucher_id', None)
#         session.pop('use_coin', None)
#         session.pop('note_message', None)
#
#         return jsonify({
#             "message": "Đặt hàng thành công!",
#             "receipt_id": new_receipt.id,
#             "bonus_coin": customer.coin
#         }), 200
#
#     except Exception as e:
#         db.session.rollback()
#         session.pop('order_processing', None)
#         return jsonify({"message": f"Lỗi: {str(e)}"}), 500



import requests, hmac, hashlib

@app.route('/api/order', methods=['POST'])
@login_required
def create_order():
    if session.get('order_processing'):
        return jsonify({"message": "Đơn hàng đang xử lý, vui lòng đợi!"}), 429

    session['order_processing'] = True

    try:
        data = request.get_json() or {}
        note_message = data.get('note_message', '').strip()

        cart_items = CartItem.query.filter_by(user_id=current_user.id, is_selected=True).all()
        if not cart_items:
            return _clear_processing({"message": "Giỏ hàng trống."}, 400)

        address = Address.query.filter_by(customer_id=current_user.id, is_default=True).first()
        if not address:
            return _clear_processing({"message": "Bạn chưa có địa chỉ mặc định!"}, 400)

        payment_method = "MoMo" if session.get('payment_method') == 'MoMo' else "COD"

        total_amount = sum(item.quantity * item.product.price for item in cart_items)

        voucher_discount = 0
        voucher_id = session.get('voucher_id')
        if voucher_id:
            voucher = db.session.get(Voucher, voucher_id)
            if voucher:
                voucher_discount = voucher.price_voucher

        customer = db.session.get(Customer, current_user.id)
        if not customer:
            return _clear_processing({"message": "Không tìm thấy thông tin khách hàng!"}, 400)

        coin_used = customer.coin if session.get('use_coin') else 0
        final_amount = max(total_amount - voucher_discount - coin_used, 0)

        customer_address = f"{address.receiver_address_line}, {address.receiver_ward}, {address.receiver_district}, {address.receiver_province}"

        # === Nếu là COD ===
        if payment_method == 'COD':
            new_receipt = Receipt(
                create_date=datetime.now(),
                customer_id=current_user.id,
                customer_phone=address.receiver_phone,
                customer_address=customer_address,
                delivery_method="Thanh toán khi nhận hàng",
                payment_method="COD",
                total_amount=total_amount,
                voucher_id=voucher_id,
                voucher_discount=voucher_discount,
                coin_used=coin_used,
                final_amount=final_amount,
                note_message=note_message,
                is_paid=True
            )
            for item in cart_items:
                new_receipt.receipt_details.append(ReceiptDetail(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.product.price
                ))

            if coin_used > 0:
                customer.coin = max(customer.coin - coin_used, 0)
            customer.coin += sum(item.quantity for item in cart_items) * 100

            for item in cart_items:
                db.session.delete(item)

            db.session.add(new_receipt)
            db.session.commit()

            return _clear_processing({
                "message": "Đặt hàng COD thành công!",
                "receipt_id": new_receipt.id,
                "redirect_url": "/MyReceipt"
            }, 200)

        # === Nếu là MoMo ===
        momo_order_id = str(uuid.uuid4())

        # ✅ TẠO PendingPayment TRONG DB
        pending = PendingPayment(
            momo_order_id = momo_order_id,
            customer_id = current_user.id,
            note_message = note_message,
            customer_phone = address.receiver_phone,
            customer_address = customer_address,
            voucher_id = voucher_id,
            voucher_discount = voucher_discount,
            coin_used = coin_used,
            final_amount = final_amount,
            cart_items = json.dumps([
                {"product_id": i.product_id, "quantity": i.quantity, "price": i.product.price}
                for i in cart_items
            ])
        )
        db.session.add(pending)
        db.session.commit()

        pay_url = _create_momo_payment(momo_order_id, final_amount)

        return _clear_processing({
            "message": "Vui lòng quét QR để thanh toán MoMo.",
            "payUrl": pay_url,
            "momo_order_id": momo_order_id
        }, 200)

    except Exception as e:
        db.session.rollback()
        return _clear_processing({"message": f"Lỗi: {str(e)}"}, 500)






def _clear_processing(payload, status):
    session.pop('order_processing', None)
    session.pop('voucher_id', None)
    session.pop('use_coin', None)
    session.pop('note_message', None)
    return jsonify(payload), status



def _create_momo_payment(momo_order_id, final_amount):
    import uuid

    partner_code = current_app.config['MOMO_PARTNER_CODE']
    access_key = current_app.config['MOMO_ACCESS_KEY']
    secret_key = current_app.config['MOMO_SECRET_KEY']
    endpoint = "https://test-payment.momo.vn/v2/gateway/api/create"

    order_id = momo_order_id  # Dùng momo_order_id đồng bộ
    request_id = str(uuid.uuid4())
    order_info = f"Thanh toán đơn hàng của user #{current_user.id}"
    redirect_url = "https://jolly-baboon-3.loca.lt/MyReceipt"
    ipn_url = "https://jolly-baboon-3.loca.lt/api/momo_ipn"
    extra_data = ""

    raw_signature = (
        f"accessKey={access_key}"
        f"&amount={int(final_amount)}"
        f"&extraData={extra_data}"
        f"&ipnUrl={ipn_url}"
        f"&orderId={order_id}"
        f"&orderInfo={order_info}"
        f"&partnerCode={partner_code}"
        f"&redirectUrl={redirect_url}"
        f"&requestId={request_id}"
        f"&requestType=captureWallet"
    )

    signature = hmac.new(secret_key.encode('utf-8'), raw_signature.encode('utf-8'), hashlib.sha256).hexdigest()

    payload = {
        "partnerCode": partner_code,
        "partnerName": "MoMo Payment",
        "storeId": "Test Store",
        "requestId": request_id,
        "amount": str(int(final_amount)),
        "orderId": order_id,
        "orderInfo": order_info,
        "redirectUrl": redirect_url,
        "ipnUrl": ipn_url,
        "lang": "vi",
        "extraData": extra_data,
        "requestType": "captureWallet",
        "signature": signature
    }

    print("====== MOMO CREATE REQUEST ======")
    print(payload)

    res = requests.post(endpoint, json=payload)
    print("====== MOMO RAW RESPONSE ======")
    print(res.text)
    res.raise_for_status()
    res_data = res.json()

    return res_data.get('payUrl')



@app.route('/api/check_paid')
@login_required
def check_paid():
    receipt_id = request.args.get('receipt_id')
    receipt = Receipt.query.get(receipt_id)
    if receipt and receipt.is_paid:
        return jsonify({'is_paid': True})
    return jsonify({'is_paid': False})


@app.route('/MOMO')
def momo_page():
    return render_template('MOMO.html')



@app.route('/api/momo_ipn', methods=['POST'])
def momo_ipn():
    data = request.get_json()
    print("=== MoMo IPN received ===")
    print(data)
    print(f"orderId: {data.get('orderId')}")
    print(f"resultCode: {data.get('resultCode')}")
    print("========================")

    order_id = data.get('orderId')
    result_code = data.get('resultCode')

    if result_code == 0:
        pending = PendingPayment.query.filter_by(momo_order_id=order_id).first()
        if not pending:
            return jsonify({'message': 'Không tìm thấy PendingPayment'}), 400

        customer = db.session.get(Customer, pending.customer_id)
        if not customer:
            return jsonify({'message': 'Không tìm thấy khách hàng'}), 400

        try:
            new_receipt = Receipt(
                create_date = datetime.now(),
                customer_id = pending.customer_id,
                customer_phone = pending.customer_phone,
                customer_address = pending.customer_address,
                delivery_method = "Giao hàng tận nơi",
                payment_method = "MoMo",
                total_amount = pending.final_amount,
                voucher_id = pending.voucher_id,
                voucher_discount = pending.voucher_discount,
                coin_used = pending.coin_used,
                final_amount = pending.final_amount,
                note_message = pending.note_message,
                is_paid = True,
                momo_order_id = order_id
            )

            items = json.loads(pending.cart_items)
            for item in items:
                new_receipt.receipt_details.append(ReceiptDetail(
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    price=item['price']
                ))

            if pending.coin_used > 0:
                customer.coin = max(customer.coin - pending.coin_used, 0)
            customer.coin += sum(i['quantity'] for i in items) * 100

            CartItem.query.filter_by(user_id=pending.customer_id).delete()

            db.session.add(new_receipt)
            db.session.delete(pending)
            db.session.commit()

            return jsonify({'message': 'IPN OK'}), 200

        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khi lưu Receipt: {e}")
            return jsonify({'message': f'Lỗi khi lưu Receipt: {str(e)}'}), 500

    return jsonify({'message': 'IPN FAILED'}), 400





@app.route('/api/check_payment')
@login_required
def check_payment():
    receipt_id = request.args.get('receipt_id')
    receipt = Receipt.query.get(receipt_id)
    if receipt:
        return jsonify({'is_paid': receipt.is_paid})
    else:
        return jsonify({'is_paid': False, 'message': 'Không tìm thấy đơn hàng'})





@app.route('/api/set_note_message', methods=['POST'])
@login_required
def set_note_message():
    data = request.get_json() or {}
    note_message = data.get('note_message', '').strip()
    session['note_message'] = note_message
    return jsonify({'message': 'Note saved to session'}), 200

@app.route('/api/get_note_message', methods=['GET'])
@login_required
def get_note_message():
    note_message = session.get('note_message', '')
    return jsonify({'note_message': note_message}), 200

# Chọn voucher
@app.route("/api/set_voucher", methods=['POST'])
@login_required
def set_voucher():
    data = request.get_json()
    code = data.get('code')

    if not code:
        session.pop('voucher_id', None)
        return jsonify({'code': 200, 'message': 'Đã huỷ voucher!'})

    voucher = Voucher.query.filter_by(code=code).first()
    if not voucher:
        return jsonify({'code': 400, 'message': 'Mã voucher không hợp lệ!'})

    session['voucher_id'] = voucher.id
    return jsonify({'code': 200, 'message': 'Đã lưu voucher!'})

# click chọn sử dụng coin
@app.route('/api/set_use_coin', methods=['POST'])
@login_required
def set_use_coin():
    data = request.get_json()
    use_coin = data.get('use_coin', False)
    session['use_coin'] = use_coin

    # Tính lại tổng tiền y chang bên /pay
    order_total = dao.get_order_total_amount(current_user.id)

    # Tính voucher nếu có
    voucher_discount = 0
    if 'voucher_id' in session:
        voucher = db.session.get(Voucher, session['voucher_id'])
        if voucher:
            voucher_discount = voucher.price_voucher

    customer = db.session.get(Customer, current_user.id)
    coin_balance = customer.coin if customer else 0

    if use_coin:
        total_after = max(order_total - voucher_discount - coin_balance, 0)
    else:
        total_after = max(order_total - voucher_discount, 0)

    return jsonify({
        'code': 200,
        'new_total': total_after
    })

# Chọn phương thức thanh toán giữa tiền mặt và online
@app.route('/api/set_payment_method', methods=['POST'])
@login_required
def set_payment_method():
    data = request.get_json()
    payment_method = data.get('payment_method', 'COD')
    session['payment_method'] = payment_method
    return jsonify({'code': 200})




# Hiển thị danh sách thể loại
@app.context_processor
def common_attributes():
    return {
        "categories": dao.load_categories()
    }


# Đăng nhập bằng Flask-Login
@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


@app.context_processor
def comment_respone():
    return {
        "cart_stats": utils.count_cart(session.get('cart'))
    }


# Trang quản trị
@app.route('/staff', methods=['GET', 'POST'])
def staff():
    return render_template('staff.html')


# Trang cá nhân của người dùng
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        ho = request.form.get('ho')
        ten = request.form.get('ten')
        current_user.name = f"{ho} {ten}".strip()

        current_user.phone = request.form.get('sdt')
        current_user.address = request.form.get('address')
        current_user.email = request.form.get('email')

        gender_str = request.form.get('gender')
        if gender_str:
            current_user.gender = Gender[gender_str]  # Gán Enum

        birthday_str = request.form.get('birthday')
        if birthday_str:
            current_user.birthday = datetime.strptime(birthday_str, '%Y-%m-%d').date()

        # Upload avatar nếu có
        avatar = request.files.get('avatar')
        if avatar:
            upload_result = cloudinary.uploader.upload(avatar)
            current_user.avatar = upload_result['secure_url']

        # Lưu vào database
        db.session.commit()

        # ✅ Thêm flash thông báo thành công
        flash('Cập nhật hồ sơ thành công!', 'success')

        return redirect('/profile')

    return render_template('user/profile.html', user=current_user)



# Upload avatar
@app.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    avatar = request.files.get('avatar')
    if not avatar:
        return jsonify({'success': False, 'message': 'No file uploaded'})

    try:
        upload_result = cloudinary.uploader.upload(avatar)
        current_user.avatar = upload_result['secure_url']
        db.session.commit()

        return jsonify({'success': True, 'avatar_url': current_user.avatar})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})



# Đổi mật khẩu
@app.route('/changePassword', methods=['GET', 'POST'])
@login_required
def change_password():
    error = None
    success = None

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Kiểm tra mật khẩu hiện tại đúng không
        if not check_password_hash(current_user.password, current_password):
            error = "Mật khẩu hiện tại không đúng!"
        elif new_password != confirm_password:
            error = "Mật khẩu mới và xác nhận mật khẩu không khớp!"
        else:
            if dao.update_password(current_user.id, new_password):
                success = "Đổi mật khẩu thành công!"
            else:
                error = "Có lỗi xảy ra khi đổi mật khẩu!"

    return render_template('user/changePassword.html', error=error, success=success)

#Uu đãi thành viên
@app.route('/uuDaiThanhVien')
@login_required
def uu_dai_thanh_vien():
    return render_template('user/uuDaiThanhVien.html')

@app.route('/MyReceipt')
@login_required
def order():
    status = request.args.get('status')
    if status:
        session['receipt_status'] = status
    else:
        status = session.get('receipt_status', 'all')

    query = Receipt.query.filter_by(customer_id=current_user.id)
    if status != 'all':
        query = query.filter_by(status=status)  # ⚡ Bạn cần cột status trong Receipt nhé!

    receipts = query.order_by(Receipt.create_date.desc()).all()

    details_by_receipt = []

    for r in receipts:
        one_receipt_details = []
        for d in r.receipt_details:
            one_receipt_details.append({
                'id': d.product.id,
                'name': d.product.name,
                'price': d.product.price,
                'quantity': d.quantity
            })
        details_by_receipt.append({
            'receipt_id': r.id,
            'details': one_receipt_details
        })

    return render_template(
        'user/MyReceipt.html',
        status=status,
        receipts=receipts,
        rebuy_by_receipt=details_by_receipt  # ✅ map theo receipt
    )
@app.route('/api/receipts')
@login_required
def api_receipts():
    status = request.args.get('status', 'all')

    query = Receipt.query.filter_by(customer_id=current_user.id)
    if status != 'all':
        query = query.filter_by(status=status)

    receipts = query.order_by(Receipt.create_date.desc()).all()

    # ✅ TẠO LẠI rebuy_by_receipt
    details_by_receipt = []
    for r in receipts:
        one_receipt_details = []
        for d in r.receipt_details:
            one_receipt_details.append({
                'id': d.product.id,
                'name': d.product.name,
                'price': d.product.price,
                'quantity': d.quantity
            })
        details_by_receipt.append({
            'receipt_id': r.id,
            'details': one_receipt_details
        })

    return render_template(
        'user/receipt_list.html',
        receipts=receipts,
        rebuy_by_receipt=details_by_receipt   # ✅ Đừng quên cái này!
    )




@app.route('/api/set_receipt_status', methods=['POST'])
@login_required
def set_receipt_status():
    status = request.json.get('status', 'all')
    session['receipt_status'] = status
    return jsonify({'message': 'OK'})

# Voucher
@app.route('/voucher')
@login_required
def voucher():
    vouchers = dao.load_voucher()

    selected_cart_items = CartItem.query.filter_by(user_id=current_user.id, is_selected=True).all()
    order_total_amount_selected = sum(item.quantity * item.product.price for item in selected_cart_items)


    session_voucher_code = ""
    if 'voucher_id' in session:
        voucher = Voucher.query.get(session['voucher_id'])
        if voucher:
            session_voucher_code = voucher.code


    return render_template(
        'user/voucher.html',
        voucher=vouchers,
        order_total_amount_selected=order_total_amount_selected,
        session_voucher_code=session_voucher_code,
    )

@app.route('/loveProduct')
@login_required
def love_product():
    liked_products = db.session.query(Product)\
        .join(FavoriteProduct, Product.id == FavoriteProduct.product_id)\
        .filter(FavoriteProduct.customer_id == current_user.id).all()

    return render_template('user/loveProduct.html', products=liked_products)


@app.route('/api/favorites/<int:product_id>', methods=['DELETE'])
@login_required
def delete_favorite(product_id):
    try:
        favorite = FavoriteProduct.query.filter_by(customer_id=current_user.id, product_id=product_id).first()
        if favorite:
            db.session.delete(favorite)

            # ✅ Trừ like_count nếu có cột này
            product = Product.query.get(product_id)
            if product and product.like > 0:
                product.like -= 1  # hoặc like_count nếu tên cột vậy

            db.session.commit()
            return jsonify({'status': 'success', 'like_count': product.like})
        return jsonify({'status': 'not_found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/myAddress')
@login_required
def my_address():
    addresses = Address.query.filter_by(customer_id=current_user.id).all()
    default_address = next((addr for addr in addresses if addr.is_default), None)

    return render_template('user/myAddress.html', addresses=addresses, default_address=default_address)



#Chọn từng sản phẩm trong giỏ hàng
@app.route('/api/toggle-select-cart-item', methods=['PUT'])
@login_required
def toggle_select_cart_item():
    data = request.json
    cart_item = db.session.get(CartItem, data['cart_id'])

    if cart_item and cart_item.user_id == current_user.id:
        cart_item.is_selected = data['is_selected']
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'success': False}), 400


#Chọn all sản phẩm trong giỏ hàng
@app.route('/api/toggle-select-all-cart-items', methods=['PUT'])
@login_required
def toggle_select_all_cart_items():
    data = request.json
    cart_ids = data.get('cart_ids', [])
    is_selected = data.get('is_selected', False)

    try:
        cart_items = CartItem.query.filter(
            CartItem.user_id == current_user.id,
            CartItem.id.in_(cart_ids)
        ).all()

        for item in cart_items:
            item.is_selected = is_selected

        db.session.commit()
        return jsonify({'success': True})
    except Exception as ex:
        print('Lỗi toggle-select-all:', ex)
        return jsonify({'success': False}), 500


# API lấy tất cả Tỉnh/Thành phố
@app.route('/api/provinces')
def api_get_provinces():
    return jsonify(dao.get_provinces())

# API lấy Quận/Huyện theo Tỉnh
@app.route('/api/districts/<province_code>')
def api_get_districts(province_code):
    return jsonify(dao.get_districts_by_province(province_code))

# API lấy Phường/Xã theo Quận/Huyện
@app.route('/api/wards/<district_code>')
def api_get_wards(district_code):
    return jsonify(dao.get_wards_by_district(district_code))

# API lấy địa chỉ của người dùng mặc dịnh hiện tại
@app.route('/api/set-default-address', methods=['POST'])
def set_default_address():
    data = request.get_json()
    address_id = data.get('address_id')

    if not address_id:
        return jsonify(success=False, error='Thiếu ID')

    try:
        # 🔑 Tìm địa chỉ đang set
        address = Address.query.filter_by(id=address_id, customer_id=current_user.id).first()

        if not address:
            return jsonify(success=False, error='Địa chỉ không tồn tại')

        # 🔑 Reset tất cả địa chỉ của user về is_default = False
        Address.query.filter_by(customer_id=current_user.id).update({'is_default': False})

        # 🔑 Set địa chỉ được chọn thành mặc định
        address.is_default = True

        db.session.commit()
        return jsonify(success=True)

    except Exception as e:
        db.session.rollback()
        print('Lỗi:', e)
        return jsonify(success=False, error=str(e))

# Lưu địa chỉ mới
@app.route('/api/save-address', methods=['POST'])
def save_address():
    data = request.json

    # Lấy user hiện tại
    user_id = current_user.id

    # Kiểm tra xem user này đã có địa chỉ chưa
    has_address = Address.query.filter_by(customer_id=user_id).count() > 0

    new_address = Address(
        customer_id=user_id,
        receiver_name=data['receiver_name'],
        receiver_phone=data['receiver_phone'],
        receiver_province=data['receiver_province'],
        receiver_district=data['receiver_district'],
        receiver_ward=data['receiver_ward'],
        receiver_address_line=data['receiver_address_line'],
        is_default=not has_address  # Nếu chưa có thì set True
    )

    try:
        db.session.add(new_address)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/update-address', methods=['POST'])
def update_address():
    data = request.json

    address_id = data.get('id')
    if not address_id:
        return jsonify({'success': False, 'error': 'Missing ID'})

    address = Address.query.filter_by(id=address_id, customer_id=current_user.id).first()
    if not address:
        return jsonify({'success': False, 'error': 'Address not found'})

    # Cập nhật field
    address.receiver_name = data['receiver_name']
    address.receiver_phone = data['receiver_phone']
    address.receiver_province = data['receiver_province']
    address.receiver_district = data['receiver_district']
    address.receiver_ward = data['receiver_ward']
    address.receiver_address_line = data['receiver_address_line']

    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete-address', methods=['POST'])
def delete_address():
    data = request.json
    address_id = data.get('id')

    if not address_id:
        return jsonify({'success': False, 'error': 'Thiếu ID địa chỉ!'})

    try:
        # Tìm địa chỉ
        address = Address.query.filter_by(id=address_id, customer_id=current_user.id).first()
        if not address:
            return jsonify({'success': False, 'error': 'Không tìm thấy địa chỉ!'})

        # Lưu trạng thái trước khi xoá
        was_default = address.is_default

        # Xoá địa chỉ
        db.session.delete(address)
        db.session.commit()

        # Nếu địa chỉ vừa xoá là mặc định ➜ gán địa chỉ còn lại làm mặc định
        if was_default:
            another = Address.query.filter_by(customer_id=current_user.id).first()
            if another:
                another.is_default = True
                db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == "__main__":
    with app.app_context():
        app.run(
            debug=True,
            port=5000,
            host='0.0.0.0'
        )