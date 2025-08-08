# saleapp/models.py
import hashlib

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Enum, DateTime, Sequence, func, text, Date
from sqlalchemy.orm import relationship
from flask_login import UserMixin
import enum
from datetime import datetime

from werkzeug.security import generate_password_hash

from saleapp import db, app
from sqlalchemy.dialects.mysql import JSON
from enum import Enum as PyEnum
import json


class Payment_Method(enum.Enum):
    CASH = "Cash"
    CREDIT_CARD = "Credit Card"
    BANK_TRANSFER = "Bank Transfer"


class Gender(PyEnum):
    MALE = "Nam"
    FEMALE = "Nữ"
    OTHER = "Khác"


class Role(enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    USER = "USER"

class User(db.Model, UserMixin):
    __tablename__ = 'User'
    id = Column(Integer, primary_key=True, autoincrement=True)
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


    import_receipts = db.relationship('ImportReceipt', backref='user', lazy=True)
    addresses = db.relationship('Address', backref='user', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='user', lazy=True)
    receipts = db.relationship('Receipt', backref='user', foreign_keys='Receipt.user_id', lazy=True)

class Address(db.Model):
    __tablename__ = 'Address'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    receiver_name = Column(String(255), nullable=False)  # Họ tên người nhận
    receiver_phone = Column(String(50), nullable=False)  # SĐT người nhận
    receiver_province = Column(String(255), nullable=False)  # Tỉnh/Thành phố
    receiver_district = Column(String(255), nullable=False)  # Quận/Huyện
    receiver_ward = Column(String(255), nullable=False)  # Phường/Xã
    receiver_address_line = Column(String(255), nullable=False)  # Địa chỉ cụ thể (số nhà, ấp, đường...)
    is_default = Column(Boolean, default=False)  # Mặc định


    def __str__(self):
        return f"{self.receiver_name} - {self.receiver_phone} - {self.receiver_address_line}, {self.receiver_ward}, {self.receiver_district}, {self.receiver_province}"


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


class ProductInventory(db.Model):
    __tablename__ = 'ProductInventory'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('Product.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.Integer, nullable=False, default=1)

    # product = db.relationship('Product', backref=db.backref('inventory', uselist=False))
    product = db.relationship('Product', backref=db.backref('inventories'))


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

    thuong_hieu = db.Column(db.String(255))
    xuat_xu = db.Column(db.String(255))
    quy_cach_dong_goi = db.Column(db.String(255))
    bao_quan = db.Column(db.Text)
    cach_dung = db.Column(db.Text)
    mo_ta_san_pham = db.Column(db.Text)
    is_deleted = db.Column(db.Boolean, default=False)

    # Quan hệ với bảng ReceiptDetail
    receipt_details = db.relationship('ReceiptDetail', backref='product', lazy=True)

    def __str__(self):
        return self.name

class ProductExtraInfo(db.Model):
    __tablename__ = 'ProductExtraInfo'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('Product.id'), nullable=False, unique=True)

    thuong_hieu = db.Column(db.String(255))
    xuat_xu = db.Column(db.String(255))
    quy_cach_dong_goi = db.Column(db.String(255))
    bao_quan = db.Column(db.Text)
    cach_dung = db.Column(db.Text)
    mo_ta_san_pham = db.Column(db.Text)

    # Quan hệ 1-1 với Product
    product = db.relationship('Product', backref=db.backref('extra_info_obj', uselist=False))

class Setting(db.Model):
    __tablename__ = 'setting'

    key = Column(String(100), primary_key=True)
    value = Column(String(255), nullable=False)
    description = Column(String(255))

# Comment gắn với ReceiptDetail, không gắn product trực tiếp nữa
class Comment(db.Model):
    __tablename__ = 'Comment'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
    receipt_detail_id = db.Column(db.Integer, db.ForeignKey('ReceiptDetail.id'), nullable=False)
    can_edit = db.Column(db.Boolean, default=True)  # ✅ Chỉ được sửa 1 lần
    created_date = db.Column(db.DateTime, default=datetime.now)


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
    create_date = Column(db.DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    receiver_name = db.Column(db.String(100), nullable=False)
    receiver_phone = Column(String(255), nullable=False)
    receiver_address = Column(String(255), nullable=False)
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
    pay_url = db.Column(db.String(2000))  # ✅ thêm dòng này để lưu link MoMo


    receipt_details = db.relationship('ReceiptDetail', backref='receipt', lazy=True)
    # user = db.relationship('User', backref='receipts', lazy=True)
    created_by_staff = db.Column(db.Boolean, default=False)


class ReceiptDetail(db.Model):  # Tạo bảng ReceiptDetail
    __tablename__ = 'ReceiptDetail'
    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey(Receipt.id), nullable=False)
    product_id = Column(Integer, ForeignKey(Product.id), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    price = Column(Float, default=0, nullable=False)


    comment = db.relationship('Comment', backref='receipt_detail', uselist=False)

class ReceiptInventoryDetail(db.Model):
    __tablename__ = 'Receipt_inventory_detail'

    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey('Receipt.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('Product.id'))
    inventory_id = db.Column(db.Integer, db.ForeignKey('ProductInventory.id'))
    quantity = db.Column(db.Integer)

    # Relationships nếu cần
    inventory = db.relationship('ProductInventory')

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


# class PendingPayment(db.Model):
#     __tablename__ = 'pending_payment'
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     momo_order_id = db.Column(db.String(255), unique=True, nullable=False)
#     user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
#     receiver_name = db.Column(db.String(100), nullable=False)
#     note_message = db.Column(db.String(255))
#     receipt_phone = db.Column(db.String(50))
#     receipt_address = db.Column(db.String(255))
#     voucher_id = db.Column(db.Integer, db.ForeignKey(Voucher.id))
#     voucher_discount = db.Column(db.Float, default=0)
#     coin_used = db.Column(db.Float, default=0)
#     coin_earned = db.Column(db.Integer, default=0)
#
#     final_amount = db.Column(db.Float, nullable=False)
#     cart_items = db.Column(db.Text, nullable=False)  # JSON string
#     created_at = db.Column(db.DateTime, default=datetime.now())


#✅ Tạo bảng ImportReceipt và ImportReceiptDetail để quản lý phiếu nhập kho
class ImportReceipt(db.Model):
    __tablename__ = 'ImportReceipt'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_date = Column(DateTime, nullable=False, default=func.now())  # Ngày nhập
    user_id = Column(Integer, ForeignKey(User.id))  # Người nhập (admin)
    total_products_import = Column(Integer, nullable=False, default=0)  # Tổng số sản phẩm nhập
    total_amount_import = Column(Float, nullable=False, default=0)  # Tổng tiền nhập
    note = Column(String(255))  # Ghi chú


    # Quan hệ 1-n với bảng chi tiết nhập
    details = relationship('ImportReceiptDetail', backref='import_receipt', lazy=True)

    def __str__(self):
        return f'Phiếu nhập #{self.id} - Ngày: {self.created_date.strftime("%d/%m/%Y")}'


class ImportReceiptDetail(db.Model):
    __tablename__ = 'ImportReceiptDetail'

    id = Column(Integer, primary_key=True, autoincrement=True)
    import_receipt_id = Column(Integer, ForeignKey('ImportReceipt.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('Product.id'), nullable=False)

    quantity = Column(Float, nullable=False)  # Số lượng nhập
    price_import = Column(Float, nullable=False)  # Giá nhập
    # import_date = Column(DateTime, nullable=False, default=func.now())  # Ngày nhập
    expiry_date = Column(Date)  # Ngày hết hạn (tuỳ chọn)
    supplier = Column(String(255))  # Tên nhà cung cấp (tuỳ chọn)

    # Liên kết về sản phẩm
    product = db.relationship('Product', backref='import_details')

    def __str__(self):
        return f'{self.product.name} - SL: {self.quantity}'



# Tạo bảng CartItem luu trữ sản phẩm đang có trong giỏ hàng người dùng
class CartItem(db.Model):
    __tablename__ = 'CartItem'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey(Product.id), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)

    # ✅ Thêm cột để lưu trạng thái checkbox
    is_selected = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('User', backref='cart_items')
    product = db.relationship('Product')


# Tạo bảng FavoriteProduct lưu trữ sản phẩm yêu thích của người dùng
class FavoriteProduct(db.Model):
    __tablename__ = 'FavoriteProduct'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    user_id = db.Column(db.Integer, db.ForeignKey('User.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('Product.id'), nullable=False)
    liked_at = db.Column(db.DateTime, default=datetime.now)

    # Ràng buộc: mỗi khách chỉ được like mỗi sản phẩm 1 lần
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='_customer_product_uc'),)

    # Quan hệ ngược (nếu cần)
    User = db.relationship('User', backref='favorites', lazy=True)
    product = db.relationship('Product', backref='liked_by', lazy=True)



def __tr__(self):
    return self.name


if __name__ == "__main__":
    with (app.app_context()):


        db.drop_all()  # Drop all table

        db.create_all()  # Create all table
        # Đặt sau khi db.create_all() xong
        with app.app_context():
            if not Setting.query.first():  # Chỉ thêm khi bảng chưa có dòng nào
                default_settings =[
                    Setting(key='max_quantity_per_item', value='100',
                            description='Tổng số lượng tối đa của mỗi sản phẩm sau khi nhập không được vượt quá 100'),
                    Setting(key='max_inventory_allowed', value='10',
                            description='Chỉ cho phép nhập nếu tồn kho hiện tại của sản phẩm nhỏ hơn hoặc bằng 10'),
                    Setting(key='min_quantity_per_item', value='50',
                            description='Số lượng nhập mỗi sản phẩm trong một dòng phải lớn hơn hoặc bằng 50'),
                    Setting(key='min_total_quantity', value='300',
                            description='Tổng số lượng tất cả sản phẩm trong phiếu nhập phải từ 300 trở lên'),
                    Setting(key='max_total_quantity', value='1000',
                            description='Tổng số lượng tất cả sản phẩm trong phiếu nhập không được vượt quá 1000'),

                ]

                db.session.add_all(default_settings)
                db.session.commit()
                print("✅ Đã thêm setting mặc định.")
            else:
                print("⚠️ Bảng Setting đã có dữ liệu, không thêm lại.")



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
                        donvitinh=p.get('donvitinh', 'Cái').strip(),  # Thêm đơn vị tính
                        thuong_hieu=p.get('thuong_hieu', '').strip(),
                        xuat_xu=p.get('xuat_xu', '').strip(),
                        quy_cach_dong_goi=p.get('quy_cach_dong_goi', '').strip(),
                        bao_quan=p.get('bao_quan', '').strip(),
                        cach_dung=p.get('cach_dung', '').strip(),
                        mo_ta_san_pham=p.get('mo_ta_san_pham', '').strip()

                    )
                    db.session.add(prod)
                db.session.commit()




        admin = User(
            name="Admin Dat", username="admin", email="admin@example.com",
            phone="0123456789",
            password=generate_password_hash('1'),
            user_role=Role.ADMIN,
            avatar="https://cdn.pixabay.com/photo/2022/04/08/09/17/frog-7119104_960_720.png"
        )

        staff = User(
            name="Staff Dat", username="staff", email="admin_staff@example.com",
            phone="0123456789",
            password= generate_password_hash('1'),
            user_role=Role.STAFF,
            avatar="https://cdn.pixabay.com/photo/2022/04/08/09/17/frog-7119104_960_720.png"
        )



        db.session.add_all([admin, staff])
        db.session.commit()
