from collections import defaultdict
from saleapp import db, app
from saleapp.models import *
from flask_login import current_user
from sqlalchemy import func, and_, or_
from datetime import datetime
from sqlalchemy.sql import extract
import json, os
from flask import render_template, request, redirect, url_for, flash, session

from saleapp import utils



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


# Hàm thống kê số lượng sản phẩm theo ngày tháng và từ khoa tìm kiếm

from sqlalchemy import func, and_, or_, select


def product_stats(kw=None, from_date=None, to_date=None):
    total_quantity_A = db.session.query(func.sum(ReceiptDetail.quantity)).scalar()
    total_quantity_B = db.session.query(func.sum(SaleBookDetail.quantity)).scalar()
    total_quantity_product = (total_quantity_A or 0) + (total_quantity_B or 0)

    receipt_query = select(
        ReceiptDetail.product_id,
        func.sum(ReceiptDetail.quantity).label('total_quantity')
    ).group_by(ReceiptDetail.product_id)

    sale_book_query = select(
        SaleBookDetail.product_id,
        func.sum(SaleBookDetail.quantity).label('total_quantity')
    ).group_by(SaleBookDetail.product_id)

    combined_query = receipt_query.union_all(sale_book_query).alias("combined")

    p = db.session.query(
        Product.id,
        Product.name,
        Category.name,
        func.sum(combined_query.c.total_quantity).label('total_quantity'),
        func.sum(combined_query.c.total_quantity) / total_quantity_product * 100
    ) \
    .join(combined_query, combined_query.c.product_id == Product.id) \
    .outerjoin(Category, Category.id == Product.category_id) \
    .group_by(Product.id, Product.name, Category.name)

    if kw:
        p = p.filter(Product.name.contains(kw))

    results = p.all()
    results_with_stt = [(index + 1, *result) for index, result in enumerate(results)]

    return results_with_stt





def revenue_by_product_category(month, year):
    return db.session.query(
        Category.name.label("category_name"),
        func.sum(
            func.coalesce(ReceiptDetail.quantity * ReceiptDetail.price, 0) +
            func.coalesce(SaleBookDetail.quantity * SaleBookDetail.price, 0)
        ).label("total_revenue"),
        func.sum(
            func.coalesce(ReceiptDetail.quantity, 0) +
            func.coalesce(SaleBookDetail.quantity, 0)
        ).label("total_quantity")  # Thêm tổng số lượt bán
    )\
    .join(Product, Product.category_id == Category.id)\
    .outerjoin(ReceiptDetail, ReceiptDetail.product_id == Product.id)\
    .outerjoin(Receipt, Receipt.id == ReceiptDetail.receipt_id)\
    .outerjoin(SaleBookDetail, SaleBookDetail.product_id == Product.id)\
    .outerjoin(SaleBook, SaleBook.id == SaleBookDetail.sale_book_id)\
    .filter(
        or_(
            extract('month', Receipt.create_date) == month,
            extract('month', SaleBook.created_date) == month
        ),
        or_(
            extract('year', Receipt.create_date) == year,
            extract('year', SaleBook.created_date) == year
        )
    )\
    .group_by(Category.name)\
    .all()



def book_sale_frequency(month, year):
    stats = db.session.query(
        Product.name.label("book_name"),
        Category.name.label("category_name"),  # Thêm tên thể loại
        db.func.sum(
            db.func.coalesce(ReceiptDetail.quantity, 0) +
            db.func.coalesce(SaleBookDetail.quantity, 0)
        ).label('total_sold')
    ).outerjoin(Category, Product.category_id == Category.id) \
     .outerjoin(SaleBookDetail, Product.id == SaleBookDetail.product_id) \
     .outerjoin(SaleBook, SaleBook.id == SaleBookDetail.sale_book_id) \
     .outerjoin(ReceiptDetail, Product.id == ReceiptDetail.product_id) \
     .outerjoin(Receipt, Receipt.id == ReceiptDetail.receipt_id) \
     .filter(
        or_(
            extract('month', SaleBook.created_date) == month,
            extract('month', Receipt.create_date) == month
        ),
        or_(
            extract('year', SaleBook.created_date) == year,
            extract('year', Receipt.create_date) == year
        )
     ) \
     .group_by(Product.name, Category.name).all()  # Nhóm theo tên sách và tên thể loại
    return stats

def total_revenue_all(month, year):
    # Tổng doanh thu từ ReceiptDetail
    total_receipt = db.session.query(
        func.coalesce(func.sum(ReceiptDetail.quantity * ReceiptDetail.price), 0)
    ).join(Receipt, ReceiptDetail.receipt_id == Receipt.id) \
     .filter(
         extract('month', Receipt.create_date) == month,
         extract('year', Receipt.create_date) == year
     ).scalar()

    # Tổng doanh thu từ SaleBookDetail
    total_sale_book = db.session.query(
        func.coalesce(func.sum(SaleBookDetail.quantity * SaleBookDetail.price), 0)
    ).join(SaleBook, SaleBookDetail.sale_book_id == SaleBook.id) \
     .filter(
         extract('month', SaleBook.created_date) == month,
         extract('year', SaleBook.created_date) == year
     ).scalar()

    # Tổng doanh thu
    return total_receipt + total_sale_book

def total_quantity(month, year):
    # Tổng số lượng từ bảng ReceiptDetail với điều kiện tháng và năm
    total_receipt = db.session.query(
        func.coalesce(func.sum(ReceiptDetail.quantity), 0)
    ).join(Receipt, ReceiptDetail.receipt_id == Receipt.id) \
     .filter(
         extract('month', Receipt.create_date) == month,
         extract('year', Receipt.create_date) == year
     ).scalar()

    # Tổng số lượng từ bảng SaleBookDetail với điều kiện tháng và năm
    total_sale_book = db.session.query(
        func.coalesce(func.sum(SaleBookDetail.quantity), 0)
    ).join(SaleBook, SaleBookDetail.sale_book_id == SaleBook.id) \
     .filter(
         extract('month', SaleBook.created_date) == month,
         extract('year', SaleBook.created_date) == year
     ).scalar()

    # Trả về tổng của hai bảng
    return total_receipt + total_sale_book




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


















































