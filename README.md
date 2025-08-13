# Thương mại nông sản
1) Công nghệ sử dụng
  Front-end: HTML5, CSS3, Bootstrap 5, JavaScript (ES6), AJAX (Fetch/axios).
  Back-end: Python 3.x, Flask (Blueprints, Jinja2, Flask-Login, Flask-WTF, Flask-Mail, Flask-SocketIO).
  Database: MySQL + SQLAlchemy ORM (migrations: Alembic).
  Thanh toán: Tích hợp MoMo (Sandbox) hoặc mô phỏng thanh toán online.
  AI Chatbot: API LLM (có thể nội bộ/3rd), logic fallback Q&A.
  Triển khai: Gunicorn/uwsgi + Nginx, .env cho secrets, Docker (tùy chọn).
  Chat với nhân viên cửa hàng.

3) Nhóm chức năng người dùng (User)
*Tài khoản
  Đăng ký, đăng nhập, đăng xuất (Flask-Login).
  Xác thực email (Flask-Mail + token).
  Quên mật khẩu / đặt lại mật khẩu qua email (JWT/itsdangerous).
  Đổi mật khẩu trong trang cá nhân.
  Cập nhật thông tin hồ sơ (avatar, tên, SĐT, địa chỉ).

*Tương tác & Nội dung
  Bình luận/đánh giá sản phẩm (CRUD, phân trang, chống spam).
  Sản phẩm yêu thích (wishlist/like).
  Xu thưởng/điểm tích lũy: tích điểm theo đơn hàng, đổi quà/phiếu giảm giá.
  Mua sắm
  Giỏ hàng (thêm/sửa/xóa), mã giảm giá, phí ship.
  Thanh toán online MoMo (Sandbox): tạo order, redirect, IPN callback; hoặc mô phỏng trạng thái thanh toán (success/fail/pending).
  Lịch sử đơn hàng, theo dõi trạng thái (processing/shipped/completed/cancelled).

*Chat
  Chat với AI: trả lời tự động FAQs, gợi ý SP, tra cứu đơn.
  Chat với Staff: mở ticket/pending → gán nhân viên → trò chuyện realtime (SocketIO).
  Thông báo

3) Nhóm chức năng Quản trị (Admin)
  Quản lý sản phẩm: danh mục/thương hiệu/thuộc tính biến thể, tồn kho, giá, hình ảnh.
  Quản lý người dùng: role (Customer/Staff/Admin), khóa/mở, nhật ký hoạt động.
  Quản lý nhập kho: phiếu nhập, chi tiết, nhà cung cấp, ràng buộc tồn.
  Quản lý đơn hàng: xem/duyệt/cập nhật trạng thái, hoàn tiền, xuất hóa đơn.
  Quản lý chat: hàng chờ (pending), gán staff, theo dõi cuộc trò chuyện, SLA.
  Quy định & cấu hình: điều khoản, chính sách, phí ship, cấu hình cổng thanh toán, email server.
  Báo cáo – Thống kê: doanh thu, top sản phẩm, tồn kho thấp, người dùng mới, kênh thanh toán.
