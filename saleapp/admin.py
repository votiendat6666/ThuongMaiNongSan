from math import trunc
from flask import redirect, flash, url_for
from sqlalchemy.exc import SQLAlchemyError
from urllib3 import request
from saleapp.models import *
from saleapp import db, app
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, logout_user
from flask_admin import BaseView, expose, AdminIndexView
import utils
from flask import request
from datetime import datetime
from flask_admin.form import rules
import dao
import cloudinary.uploader



# Hiển thị sản phẩm
class ProductAdminView(ModelView):
    column_searchable_list = ['name', 'price']
    column_filters = ['name', 'price']
    can_view_details = True
    can_export = True
    column_exclude_list = ['description', 'quantity']
    column_labels = {
        'name': 'Tên sản phẩm',
        'price': 'Giá',
        'category_id': 'Danh mục',
        'author_id': 'Tác giả',
        'image': 'Ảnh'
    }


# Đăng xuất
class LogoutView(BaseView):
    @expose('/')
    def index(self):
        logout_user()
        return redirect('/')

    def is_accessible(self):
        return current_user.is_authenticated


# Trang chủ admin
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html', stats=utils.category_stats())
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == Role.ADMIN



# Thống kê
class StatsView(BaseView):
    @expose('/')
    def index(self):
        # Mặc định sẽ hiển thị trang doanh thu
        return self.render('admin/stats.html',total_revenue_all=[], revenue_stats=[], stats=[])

    @expose('/revenue')
    def revenue_view(self):
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        revenue_stats = []
        if month and year:
            try:
                revenue_stats = utils.revenue_by_product_category(month, year)

            except Exception as e:
                print(f"Error fetching revenue stats: {e}")
        return self.render('admin/stats.html',total_revenue_all = utils.total_revenue_all(month, year), revenue_stats=revenue_stats, stats=[])

    @expose('/frequency')
    def frequency_view(self):
        month1 = request.args.get('month1', type=int)
        year1 = request.args.get('year1', type=int)
        stats = []
        if month1 and year1:
            try:
                stats = utils.book_sale_frequency(month1, year1)
            except Exception as e:
                print(f"Error fetching book sale stats: {e}")
        return self.render('admin/stats.html',total_revenue_all=[], total_quantity = utils.total_quantity(month1, year1), revenue_stats=[], stats=stats)

    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == Role.ADMIN


class ManageRuleView(BaseView):
    @expose('/', methods=['GET', 'POST'])
    def manage_view(self):
        rule = ManageRule.query.first()  # Lấy quy định đầu tiên (vì có thể chỉ cần một bản ghi)

        if request.method == 'POST':  # Nếu phương thức là POST, cập nhật quy định
            import_quantity_min = int(request.form.get('import_quantity_min', 0))
            quantity_min = int(request.form.get('quantity_min', 0))
            cancel_time = int(request.form.get('cancel_time', 0))

            if not rule:  # Nếu chưa tồn tại quy định, tạo mới
                rule = ManageRule(
                    import_quantity_min=import_quantity_min,
                    quantity_min=quantity_min,
                    cancel_time=cancel_time,
                    updated_date=datetime.now()
                )
                db.session.add(rule)
            else:  # Cập nhật quy định hiện có
                rule.import_quantity_min = import_quantity_min
                rule.quantity_min = quantity_min
                rule.cancel_time = cancel_time
                rule.updated_date = datetime.now()

            db.session.commit()
            flash("Cập nhật quy định thành công!", "success")
            # return self.render('admin/manage_rules.html')

        return self.render('admin/ManageRule.html', rule=rule)

class AddStaffView(BaseView):
    @expose('/', methods=['GET', 'POST'])
    def add_staff(self):
        err_msg = ''
        if request.method == 'POST':
            password = request.form.get('password')
            confirm = request.form.get('confirm')

            if password.__eq__(confirm):
                name = request.form.get('name')
                username = request.form.get('username')
                password = request.form.get('password')
                avatar = request.files.get('avatar')
                avatar_path = None
                email = request.form.get('email')
                address = request.form.get('address')
                phone = request.form.get('phone')
                role = request.form.get('user_role')
                if avatar:
                    res = cloudinary.uploader.upload(avatar)
                    avatar_path = res['secure_url']
                if role == 'STAFF':
                    dao.add_staff(name=name, username=username, password=password, avatar=avatar_path, email=email, phone = phone,
                                  address=address, role=Role.STAFF)
                else:
                    dao.add_staff(name=name, username=username, password=password, avatar=avatar_path, email=email, phone = phone,
                                  address=address, role=Role.MANAGER)
                err_msg = 'Thêm tài khoản thành công !!!'
            else:
                err_msg = 'Mật khẩu không khớp!'

        return self.render('admin/add_staff.html', err_msg=err_msg)




class ImportBooksView(BaseView):
    @expose('/', methods=['GET', 'POST'])
    def import_books(self):
        rule = ManageRule.query.first()
        current_datetime = datetime.now()
        db.session.refresh(rule)
        if request.method == 'POST':
            date_import = request.form.get('date_import', datetime.now().strftime('%Y-%m-%d'))
            books = request.form.getlist('book')
            categories = request.form.getlist('category')
            authors = request.form.getlist('author')
            quantities = request.form.getlist('quantity')
            prices = request.form.getlist('price')
            image = request.files.get('image')
            errors = []
            success = []

            try:
                date_imp = datetime.now()
                import_receipt = ImportReceipt(date_import=date_imp, staff_id=current_user.id)
                db.session.add(import_receipt)

                for book_name, category_name, author_name, quantity_str, price_str in zip(books, categories, authors, quantities, prices):
                    try:
                        quantity = int(quantity_str)
                        price = float(price_str) if price_str else None  # Convert price to float if not empty

                        if quantity < rule.import_quantity_min:
                            errors.append(f"Số lượng nhập cho sách '{book_name}' phải lớn hơn hoặc bằng {rule.import_quantity_min}!")
                            continue

                        category = Category.query.filter_by(name=category_name).first()
                        if not category:
                            category = Category(name=category_name)
                            db.session.add(category)
                            db.session.flush()

                        author = Author.query.filter_by(name=author_name).first()
                        if not author:
                            author = Author(name=author_name)
                            db.session.add(author)
                            db.session.flush()

                        book = Product.query.filter_by(name=book_name).first()
                        if not book:
                            if image:
                                res = cloudinary.uploader.upload(image)
                                image_url = res['secure_url']
                            else:
                                image_url = None
                            book = Product(name=book_name, category_id=category.id, author_id=author.id, quantity=0, price=price, image=image_url)
                            db.session.add(book)
                            db.session.flush()

                        if book.quantity > 300:
                            errors.append(f"Số lượng nhập sách '{book_name}' trong kho lớn hơn 300 cuốn!")
                            continue
                        else:
                            book.quantity += quantity
                            if price is not None:
                                book.price = price


                        receipt_detail = ImportReceiptDetail(quantity=quantity, product_id=book.id, import_receipt=import_receipt)
                        db.session.add(receipt_detail)

                        success.append(f"Nhập thành công sách '{book_name}' với số lượng {quantity} và giá {price}!")

                    except ValueError:
                        errors.append(f"Số lượng '{quantity_str}' hoặc giá '{price_str}' không hợp lệ cho sách '{book_name}'!")
                    except SQLAlchemyError as e:
                        errors.append(f"Lỗi cơ sở dữ liệu khi nhập sách '{book_name}': {str(e)}")

                db.session.commit()

                if success:
                    flash(" ".join(success), "success")
                if errors:
                    flash(" ".join(errors), "danger")

            except SQLAlchemyError as e:
                db.session.rollback()
                flash(f"Lỗi khi tạo hóa đơn nhập: {str(e)}", "danger")

            return redirect(url_for('importbooksview.import_books'))

        books = Product.query.all()
        books_data = [{
            "name": book.name,
            "category": {"name": book.category.name},
            "author": {"name": book.author.name}
        } for book in books]

        return self.render('admin/import_book.html', current_datetime=current_datetime, rule=rule, books=books, books_data=books_data)
class UserView(ModelView):
    column_list = ['name','username','user_role']
    column_searchable_list = ['name', 'user_role']
    can_view_details = True
    can_export = True
    column_labels = {
        'name': 'Tên',
        'username': 'Tên tài khoản',
        'user_role':'Quyền'
    }


class MyCategoryView(ModelView):
    column_list = ['name', 'book']


admin = Admin(app=app, name='Quản lý bán hàng', template_mode='bootstrap4', index_view=MyAdminIndexView())
admin.add_view(ModelView(Category, db.session, name="Danh mục"))
admin.add_view(ProductAdminView(Product, db.session, name="Sản phẩm"))
admin.add_view(StatsView(name='Thống kê', endpoint='stats'))
admin.add_view(ManageRuleView(name='Quy định'))
admin.add_view(UserView(Staff, db.session))
admin.add_view(AddStaffView(name='Thêm nhân viên'))
admin.add_view(ImportBooksView(name='Nhập sách'))

admin.add_view(LogoutView(name='Đăng xuất'))
