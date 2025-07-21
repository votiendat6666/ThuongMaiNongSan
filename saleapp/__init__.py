import socketio
from flask import Flask, render_template, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_mail import Mail  # ✅ Thêm Flask-Mail
from urllib.parse import quote
import secrets
import cloudinary
from authlib.integrations.flask_client import OAuth

# Khởi tạo Flask app
app = Flask(__name__)

# Secret key
app.secret_key = "project12345@@"

# Cấu hình database
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/qlbs?charset=utf8mb4" % quote('123456')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["PAGE_SIZE"] = 1000

# ✅ Cấu hình MAIL (dùng Gmail SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'votiendat842004@gmail.com'  # Thay bằng email thật
app.config['MAIL_PASSWORD'] = 'femqmemmnjtzypwh'     # Thay bằng mật khẩu ứng dụng Gmail
app.config['MAIL_DEFAULT_SENDER'] = 'votiendat842004@gmail.com'


# Cầu hình google OAuth
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id='986857020803-ume1cije674e422jd7ijq739do7dtl01.apps.googleusercontent.com',
    client_secret='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',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# ✅ MoMo config

app.config['MOMO_PARTNER_CODE'] = 'MOMODMJ120250721_TEST'
app.config['MOMO_ACCESS_KEY']   = 'Csil0yiSO0r7Ete4'
app.config['MOMO_SECRET_KEY']   = 'YY3r7SE6ZjBEvf6DuZGfKQQwYFbP7W6t'
app.config['MOMO_ENDPOINT'] = 'https://test-payment.momo.vn/v2/gateway/api/create'

# Cấu hình Facebook OAuth
facebook = oauth.register(
    name='facebook',
    client_id='1817485285833438',
    client_secret='3fdbf260fd00a4b7bc0d933162c59925',
    access_token_url='https://graph.facebook.com/oauth/access_token',
    access_token_params=None,
    authorize_url='https://www.facebook.com/dialog/oauth',
    authorize_params=None,
    api_base_url='https://graph.facebook.com/',
    client_kwargs={'scope': 'email'},
)



# Khởi tạo các extension
db = SQLAlchemy(app=app)
login = LoginManager(app)
mail = Mail(app)  # ✅ Thêm Mail

# Cloudinary config
cloudinary.config(
    cloud_name='dulpttl26',
    api_key='918116311519748',
    api_secret='XrRTrrc0G5u823Ehmkzh8iuWVOU'
)

# Filter định dạng VND
@app.template_filter('format_vnd')
def format_vnd(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except ValueError:
        return value

