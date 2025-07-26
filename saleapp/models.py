# saleapp/models.py
import hashlib

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Enum, DateTime, Sequence, func, text, Date
from sqlalchemy.orm import relationship
from flask_login import UserMixin
import enum
from datetime import datetime
from saleapp import db, app
from sqlalchemy.dialects.mysql import JSON
from enum import Enum as PyEnum


class Role(enum.Enum):
    ADMIN = "Admin"
    STAFF = "Staff"
    USER = "User"
    MANAGER = "Manager"


class Payment_Method(enum.Enum):
    CASH = "Cash"
    CREDIT_CARD = "Credit Card"
    BANK_TRANSFER = "Bank Transfer"


class Gender(PyEnum):
    MALE = "Nam"
    FEMALE = "Nữ"
    OTHER = "Khác"


class User(db.Model, UserMixin):
    __abstract__ = True
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(255), nullable=True)
    user_role = Column(Enum(Role), default=Role.USER)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    avatar = Column(String(255), default=None)
    joined_date = Column(String(255), default=func.now())
    is_active = Column(Boolean, default=True)

    # THÊM 3 trường mới:
    gender = Column(Enum(Gender), nullable=True)  # có thể null nếu chưa chọn
    birthday = Column(Date, nullable=True)
    coin = Column(Integer, default=100)


class Customer(User):  # Tạo bảng Customer
    __tablename__ = 'Customer'
    id = Column(Integer, Sequence('customer_id_seq', start=2000), primary_key=True, autoincrement=True)
    receipts = db.relationship('Receipt', backref='customer', lazy=True)

    def __str__(self):
        return self.name

    @property
    def is_authenticated(self):
        return True

    def get_id(self):
        return self.id


class Address(db.Model):
    __tablename__ = 'Address'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('Customer.id'), nullable=False)
    receiver_name = Column(String(255), nullable=False)  # Họ tên người nhận
    receiver_phone = Column(String(50), nullable=False)  # SĐT người nhận
    receiver_province = Column(String(255), nullable=False)  # Tỉnh/Thành phố
    receiver_district = Column(String(255), nullable=False)  # Quận/Huyện
    receiver_ward = Column(String(255), nullable=False)  # Phường/Xã
    receiver_address_line = Column(String(255), nullable=False)  # Địa chỉ cụ thể (số nhà, ấp, đường...)
    is_default = Column(Boolean, default=False)  # Mặc định

    customer = db.relationship('Customer', backref='addresses')

    def __str__(self):
        return f"{self.receiver_name} - {self.receiver_phone} - {self.receiver_address_line}, {self.receiver_ward}, {self.receiver_district}, {self.receiver_province}"


class Staff(User):  # Tạo bảng Staff
    __tablename__ = 'Staff'

    id = Column(Integer, Sequence('staff_id_seq', start=1), primary_key=True, autoincrement=True)
    address = Column(String(255), nullable=True)  # ✅ Thêm lại nếu staff có địa chỉ riêng
    import_receipts = db.relationship('ImportReceipt', backref='staff', lazy=True)
    salebooks = db.relationship('SaleBook', backref='staff', lazy=True)

    def __str__(self):
        return self.name

    @property
    def is_authenticated(self):
        return True

    def get_id(self):
        return self.id


class Category(db.Model):
    __tablename__ = 'Category'

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(100), nullable=False)

    # 🔸 Thêm cột parent_id để xác định danh mục cha
    parent_id = Column(Integer, ForeignKey('Category.id'), nullable=True)

    # 🔸 Quan hệ đệ quy: cha → con
    parent = relationship('Category', remote_side=[id], backref='children')

    # 🔸 Quan hệ với Product
    products = relationship('Product', backref='category', lazy=True)

    def __str__(self):
        return self.name


class Product(db.Model):  # Tạo bảng Product
    __tablename__ = 'Product'  # ✅ THÊM DÒNG NÀY

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255))
    price = db.Column(db.Float, default=0)
    image = db.Column(db.String(255))
    category_id = db.Column(db.Integer, db.ForeignKey('Category.id'), nullable=False)
    voucher = db.Column(db.Float, default=0)
    daban = db.Column(db.Float, default=0)
    like = db.Column(db.Integer, default=0)
    donvitinh = db.Column(db.String(50))  # ✅ Thêm đơn vị tính
    # 🔶 Thêm cột JSON để lưu các thông tin mở rộng
    extra_info = db.Column(JSON, nullable=True)

    # Quan hệ với bảng ReceiptDetail
    receipt_details = db.relationship('ReceiptDetail', backref='product', lazy=True)

    def __str__(self):
        return self.name


# Comment gắn với ReceiptDetail, không gắn product trực tiếp nữa
class Comment(db.Model):
    __tablename__ = 'Comment'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('Customer.id'), nullable=False)
    receipt_detail_id = db.Column(db.Integer, db.ForeignKey('ReceiptDetail.id'), nullable=False)
    can_edit = db.Column(db.Boolean, default=True)  # ✅ Chỉ được sửa 1 lần
    created_date = db.Column(db.DateTime, default=datetime.now)

    customer = db.relationship('Customer', backref='comments')




# Tạo bảng CommentImage để lưu trữ hình ảnh liên quan đến bình luận
class CommentImage(db.Model):
    __tablename__ = 'CommentImage'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    image_url = db.Column(db.String(255), nullable=False)

    # Liên kết với Comment
    comment_id = db.Column(db.Integer, db.ForeignKey('Comment.id'), nullable=False)
    comment = db.relationship('Comment', backref='images')

class Receipt(db.Model):
    __tablename__ = 'Receipt'
    id = Column(Integer, primary_key=True, autoincrement=True)
    create_date = Column(db.DateTime, default=datetime.now())
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)
    customer_phone = Column(String(255), nullable=False)
    customer_address = Column(String(255), nullable=False)
    delivery_method = Column(String(255), nullable=False)
    payment_method = Column(String(255), nullable=False)
    is_paid = db.Column(db.Boolean, default=False)  # ✅ Thêm cột này
    momo_order_id = db.Column(db.String(255))  # ✅ PHẢI THÊM DÒNG NÀY!!!

    note_message = Column(String(255), nullable=True)

    # ✅ Tổng tiền hàng trước giảm
    total_amount = Column(Float, nullable=False, default=0)

    # ✅ Voucher
    voucher_id = Column(Integer, ForeignKey('Voucher.id'), nullable=True)
    voucher_discount = Column(Float, nullable=False, default=0)

    # ✅ Coin
    coin_used = Column(Float, nullable=False, default=0)
    coin_earned = db.Column(db.Integer, default=0)

    # ✅ Tổng thanh toán sau giảm
    final_amount = Column(Float, nullable=False, default=0)
    # ✅ Trạng thái đơn hàng
    status = Column(String(50), nullable=False, default='Đang xử lý')

    receipt_details = db.relationship('ReceiptDetail', backref='receipt', lazy=True)

class ReceiptDetail(db.Model):  # Tạo bảng ReceiptDetail
    __tablename__ = 'ReceiptDetail'
    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey(Receipt.id), nullable=False)
    product_id = Column(Integer, ForeignKey(Product.id), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    price = Column(Float, default=0, nullable=False)

    comment = db.relationship('Comment', backref='receipt_detail', uselist=False)




class Voucher(db.Model):
    __tablename__ = 'Voucher'

    id = Column(Integer, primary_key=True, autoincrement=True)  # ID
    name = Column(String(255), nullable=False)  # Tên voucher
    code = Column(String(50), unique=True, nullable=False)  # Mã code
    description = Column(String(255), nullable=True)  # Mô tả
    hsd = Column(String(255), nullable=False)  # Hạn sử dụng (hsd)
    price_voucher = Column(Float, nullable=False)  # Số tiền giảm
    min_order_value = Column(Float, nullable=False, default=0)  # Đơn tối thiểu

    def __repr__(self):
        return f"<Voucher {self.code} - {self.price_voucher}>"


class PendingPayment(db.Model):
    __tablename__ = 'pending_payment'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    momo_order_id = db.Column(db.String(255), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey(Customer.id), nullable=False)
    note_message = db.Column(db.String(255))
    customer_phone = db.Column(db.String(50))
    customer_address = db.Column(db.String(255))
    voucher_id = db.Column(db.Integer, db.ForeignKey(Voucher.id))
    voucher_discount = db.Column(db.Float, default=0)
    coin_used = db.Column(db.Float, default=0)
    coin_earned = db.Column(db.Integer, default=0)  # ✅ THÊM CỘT NÀY

    final_amount = db.Column(db.Float, nullable=False)
    cart_items = db.Column(db.Text, nullable=False)  # JSON string



class ImportReceipt(db.Model):  # Tạo bảng ImportReceipt
    __tablename__ = 'ImportReceipt'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date_import = Column(db.DateTime, default=datetime.now())
    staff_id = Column(Integer, ForeignKey(Staff.id), nullable=False)
    import_receipt_details = db.relationship('ImportReceiptDetail', backref='import_receipt', lazy=True)


class ImportReceiptDetail(db.Model):  # Tạo bảng ImportReceiptDetail
    __tablename__ = 'ImportReceiptDetail'
    id = Column(Integer, primary_key=True, autoincrement=True)
    import_receipt_id = Column(Integer, ForeignKey(ImportReceipt.id), nullable=False)
    product_id = Column(Integer, ForeignKey(Product.id), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    price = Column(Float, default=0, nullable=False)
    description = Column(String(255))


class SaleBook(db.Model):  # Tạo bảng SaleBook
    __tablename__ = 'SaleBook'
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_date = Column(db.DateTime, default=datetime.now())
    customer_name = Column(String(255), nullable=False)
    staff_id = Column(Integer, ForeignKey(Staff.id), nullable=False)


class SaleBookDetail(db.Model):  # Tạo bảng SaleBookDetail
    __tablename__ = 'SaleBookDetail'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_book_id = Column(Integer, ForeignKey(SaleBook.id), nullable=False)
    product_id = Column(Integer, ForeignKey(Product.id), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    price = Column(Float, default=0, nullable=False)


class ManageRule(db.Model):
    __tablename__ = 'ManageRule'
    id = Column(Integer, primary_key=True, autoincrement=True)
    import_quantity_min = Column(Integer, nullable=False, default=150)
    quantity_min = Column(Integer, nullable=False, default=300)
    cancel_time = Column(Integer, nullable=False, default=48)
    updated_date = Column(DateTime, default=datetime.now())


# Tạo bảng CartItem luu trữ sản phẩm đang có trong giỏ hàng người dùng
class CartItem(db.Model):
    __tablename__ = 'CartItem'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey(Customer.id), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey(Product.id), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)

    # ✅ Thêm cột để lưu trạng thái checkbox
    is_selected = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('Customer', backref='cart_items')
    product = db.relationship('Product')


# Tạo bảng FavoriteProduct lưu trữ sản phẩm yêu thích của người dùng
class FavoriteProduct(db.Model):
    __tablename__ = 'FavoriteProduct'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    customer_id = db.Column(db.Integer, db.ForeignKey('Customer.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('Product.id'), nullable=False)
    liked_at = db.Column(db.DateTime, default=datetime.now)

    # Ràng buộc: mỗi khách chỉ được like mỗi sản phẩm 1 lần
    __table_args__ = (db.UniqueConstraint('customer_id', 'product_id', name='_customer_product_uc'),)

    # Quan hệ ngược (nếu cần)
    customer = db.relationship('Customer', backref='favorites', lazy=True)
    product = db.relationship('Product', backref='liked_by', lazy=True)


def __tr__(self):
    return self.name


if __name__ == "__main__":
    with app.app_context():


        db.drop_all()  # Drop all table

        db.create_all()  # Create all table
        m = ManageRule()
        db.session.add(m)
        db.session.commit()

        # Thiết lập lại AUTO_INCREMENT cho Customer và Staff
        db.session.execute(text("ALTER TABLE Customer AUTO_INCREMENT = 2000;"))
        db.session.execute(text("ALTER TABLE Staff AUTO_INCREMENT = 1;"))
        db.session.commit()

        import json

        with open('data/voucher.json', 'r', encoding='utf-8') as file:
            vouchers = json.load(file)
            for v in vouchers:
                voucher = Voucher(
                    name=v['name'],
                    code=v['code'],
                    description=v.get('description', ''),
                    hsd=v.get('hsd', ''),
                    price_voucher=float(v['price_voucher']),
                    min_order_value=float(v['min_order_value'])
                )
                db.session.add(voucher)
            db.session.commit()

        # Them du lieu vao bang Category tu file category.json
        with open('data/categories.json', 'r', encoding='utf-8') as file:
            raw_categories = json.load(file)

        # Bước 1: Thêm tất cả danh mục không có parent_id trước (cha)
        category_dict = {}

        for cate in raw_categories:
            if cate.get('parent_id') is None:
                obj = Category(id=cate['id'], name=cate['name'])
                db.session.add(obj)
                category_dict[cate['id']] = obj

        db.session.commit()

        # Bước 2: Thêm danh mục con (có parent_id)
        for cate in raw_categories:
            if cate.get('parent_id') is not None:
                parent = category_dict.get(cate['parent_id'])
                if parent:
                    obj = Category(id=cate['id'], name=cate['name'], parent=parent)
                    db.session.add(obj)
                    category_dict[cate['id']] = obj

        db.session.commit()

        # Them du lieu vao bang Product tu file products.json
        with app.app_context():
            with open(r'data\products.json', 'r', encoding='utf-8') as file:
                products = json.load(file)
                for p in products:
                    # Tách phần dữ liệu chung và phần mở rộng
                    extra_info = p.get('extra_info', {})

                    prod = Product(
                        name=p['name'].strip(),
                        price=float(p['price'].replace('.', '').replace('đ', '').strip()),
                        image=p['image'].strip(),
                        category_id=p['category_id'],
                        voucher=float(str(p.get('voucher', 0)).replace('%', '').replace('-', '').strip()),
                        daban=float(str(p.get('daban', 0)).replace('.', '').replace('đ', '').strip()),
                        like=int(p.get('like', 0)),
                        donvitinh=(p.get('donvitinh') or '').strip(),
                         extra_info=extra_info  # 👈 Lưu nguyên dict vào cột JSON
                    )
                    db.session.add(prod)
                db.session.commit()

        c = Staff(name="dat", email='dat@gamil.com', phone='0775186531', address='Nhà bè', username='admin',
                  password=str(hashlib.md5('1'.strip().encode('utf-8')).hexdigest()), user_role=Role.ADMIN,
                  avatar='https://cdn.pixabay.com/photo/2022/04/08/09/17/frog-7119104_960_720.png')
        db.session.add(c)
        db.session.commit()

        s = Staff(name="dat2", email='dat@gamil.com', phone='0775186531', address='Nhà bè', username='staff',
                  password=str(hashlib.md5('1'.strip().encode('utf-8')).hexdigest()), user_role=Role.STAFF,
                  avatar='https://cdn.pixabay.com/photo/2022/04/08/09/17/frog-7119104_960_720.png')
        db.session.add(s)
        db.session.commit()

        m = Staff(name="dat1", email='dat@gamil.com', phone='0775186531', address='Nhà bè', username='manager',
                  password=str(hashlib.md5('1'.strip().encode('utf-8')).hexdigest()), user_role=Role.MANAGER,
                  avatar='https://cdn.pixabay.com/photo/2022/04/08/09/17/frog-7119104_960_720.png')
        db.session.add(m)
        db.session.commit()
