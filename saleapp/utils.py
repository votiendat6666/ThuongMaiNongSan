from collections import defaultdict
from saleapp import db, app, mail
from saleapp.models import *
from flask_login import current_user
from sqlalchemy import func, and_, or_
from datetime import datetime
from sqlalchemy.sql import extract
import json, os
from flask import render_template, request, redirect, url_for, flash, session, current_app

from saleapp import utils
from sqlalchemy import func, and_, or_, select
from itsdangerous import URLSafeTimedSerializer


# Hàm đếm số lượng và tổng tiền trong giỏ hàng
def count_cart(cart):
    total_quantity, total_amount = 0, 0
    if cart:
        for p in cart.values():
            total_quantity += p['quantity']
            total_amount += p['quantity'] * p['price']
    return {'total_quantity': total_quantity, 'total_amount': total_amount}

# Hàm thêm hóa đơn vào cơ sở dữ liệu
def add_receipt(cart):
    receipt = Receipt(customer=current_user)
    db.session.add(receipt)
    for c in cart.values():
        d = ReceiptDetail(product_id=c['id'],
                          quantity=c['quantity'],
                          price=c['price'],
                          receipt=receipt)
        db.session.add(d)
    db.session.commit()


# Hàm thống kê số lượng sản phẩm theo danh mục
def category_stats():
    return db.session.query(Category.id, Category.name, func.count(Product.id)) \
        .join(Product,Category.id.__eq__(Product.category_id),isouter=True)  \
        .group_by(Category.id, Category.name).all()



# Hàm thêm sản phẩm vào giỏ hàng trong cơ sở dữ liệu
def add_to_cart_db(user_id, product_id, quantity=1):
    item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(user_id=user_id, product_id=product_id, quantity=quantity)
        db.session.add(item)
    db.session.commit()



# Hàm lấy thông tin giỏ hàng của người dùng
def get_cart_stats(user):
    total_quantity = 0
    total_amount = 0
    total_items = 0

    if user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        total_items = len(cart_items)  # ✅ Đếm số mặt hàng khác nhau
        for item in cart_items:
            total_quantity += item.quantity
            total_amount += item.quantity * item.product.price

    return {
        'total_quantity': total_quantity,
        'total_amount': total_amount,
        'total_items': total_items  # ✅ Trả thêm
    }













































