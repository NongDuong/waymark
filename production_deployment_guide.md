# HƯỚNG DẪN DEPLOY PRODUCTION HỆ THỐNG WAYMARK (BẢN SẢN XUẤT)

Tài liệu này hướng dẫn chi tiết từng bước cách triển khai ứng dụng **Waymark** lên máy chủ Linux (Ubuntu Server) sử dụng Docker Compose, Nginx Reverse Proxy và chứng chỉ bảo mật SSL Let's Encrypt (bắt buộc cho đăng nhập Google, Facebook, Apple).

---

## 🔒 PHẦN 1: BẢN CHECKLIST BẢO MẬT TRƯỚC KHI DEPLOY

Trước khi deploy lên Server thật, anh **bắt buộc** phải thay đổi các thông số sau trong tệp `.env` để tránh bị hacker tấn công:

| Tên biến trong `.env` | Trạng thái hiện tại | Yêu cầu thay đổi trên Production |
| :--- | :--- | :--- |
| `SECRET_KEY` | `supersecretkey_change_in_production` | Đổi thành 1 chuỗi ngẫu nhiên, dài và bảo mật (VD: chạy `openssl rand -hex 32` để sinh khóa). |
| `POSTGRES_PASSWORD` | `waymark_password` | Đổi thành mật khẩu cực kỳ mạnh. |
| `ADMIN_PASSWORD` | `Admin@123456` | Đổi thành mật khẩu quản trị hệ thống khó đoán. |

---

## 📦 PHẦN 2: CẤU HÌNH DOCKER COMPOSE CHO SẢN XUẤT (`docker-compose.prod.yml`)

Khác với môi trường Local (Sử dụng volume mount và tự động tải lại code `--reload`), bản Production cần được tối ưu hiệu năng và bảo mật tối đa:
* Loại bỏ tính năng tự động reload code.
* Khóa toàn bộ các cổng kết nối Database (`5432`) và Redis (`6379`) ra môi trường ngoài (chỉ cho phép các container liên lạc nội bộ).
* Tự động khởi chạy lại khi Server bị mất nguồn (`restart: always`).

Anh hãy tạo một file mới tên là `docker-compose.prod.yml` trên Server với nội dung sau:

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    # Chạy 4 workers để xử lý hàng ngàn request cùng lúc, tắt tính năng --reload
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started

  postgres:
    image: postgis/postgis:16-3.4
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    # KHÔNG expose cổng 15432 ra ngoài internet để bảo mật tuyệt đối DB
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    # KHÔNG expose cổng 6379 ra ngoài internet
    volumes:
      - redis_prod_data:/data

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    command: celery -A app.worker.celery_app worker --loglevel=info
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_started
      postgres:
        condition: service_healthy

volumes:
  postgres_prod_data:
  redis_prod_data:
```

---

## 🌐 PHẦN 3: CẤU HÌNH NGINX REVERSE PROXY & SSL (HTTPS)

Google, Facebook và Apple yêu cầu bắt buộc trang web phải chạy trên giao thức **HTTPS (SSL)** thì mới cho phép đăng nhập. Chúng ta sẽ dùng **Nginx** trên máy chủ chính (Host) làm cổng chặn và cài SSL miễn phí thông qua **Let's Encrypt (Certbot)**.

### 1. Cài đặt Nginx & Certbot trên Ubuntu Server:
Chạy các lệnh sau trên Terminal của VPS Ubuntu:
```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y
```

### 2. Tạo cấu hình Nginx cho Waymark:
Tạo một file cấu hình Nginx mới:
```bash
sudo nano /etc/nginx/sites-available/waymark
```

Dán nội dung cấu hình sau vào (hãy thay thế `waymark.vn` bằng tên miền thật của anh):
```nginx
server {
    listen 80;
    server_name waymark.top www.waymark.top;

    # Cổng chuyển dữ liệu tới FastAPI Docker Container
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Hỗ trợ kết nối WebSocket cho tính năng CHAT thời gian thực
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

Kích hoạt cấu hình và khởi động lại Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/waymark /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. Cài đặt chứng chỉ SSL HTTPS tự động (Let's Encrypt):
Chạy lệnh sau, Certbot sẽ tự động cấu hình SSL và cập nhật file Nginx của anh thành HTTPS an toàn:
```bash
sudo certbot --nginx -d waymark.vn -d www.waymark.vn
```
*(Certbot sẽ hỏi email của anh và hỏi có tự động chuyển hướng HTTP sang HTTPS không, hãy chọn **2: Redirect**).*

---

## 🚀 PHẦN 4: THỰC THI DEPLOY TỪNG BƯỚC (STEP-BY-STEP)

Sau khi chuẩn bị xong các tệp cấu hình trên Server, anh thực hiện triển khai theo đúng trình tự sau:

### Bước 1: Sao chép mã nguồn lên Server
Anh có thể dùng Git để clone mã nguồn lên server, hoặc dùng công cụ SCP/SFTP để đẩy thư mục dự án lên VPS.

### Bước 2: Khởi chạy cụm Docker Containers Production
Chạy lệnh Build và Start hệ thống chạy ngầm dưới nền:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Bước 3: Chạy di trú Cơ sở dữ liệu (Alembic Migration)
Sau khi các Container khởi động thành công, anh cần nâng cấp cơ sở dữ liệu Postgres lên phiên bản mới nhất:
```bash
docker compose -f docker-compose.prod.yml exec web alembic upgrade head
```

### Bước 4: Khởi tạo Tài khoản Quản trị viên (Admin)
Chạy script tự động khởi tạo tài khoản Admin hệ thống dựa trên thông tin điền trong `.env`:
```bash
docker compose -f docker-compose.prod.yml exec web python setup_admin.py
```

### Bước 5: Kiểm tra trạng thái hoạt động
Anh có thể theo dõi xem các luồng xử lý API và Celery có chạy ổn định hay không bằng lệnh:
```bash
docker compose -f docker-compose.prod.yml logs -f --tail=100
```

---

*Chúc anh triển khai hệ thống Waymark lên Production thành công rực rỡ! Nếu trong quá trình deploy trên VPS gặp bất kỳ lỗi gì về quyền hạn, kết nối hay DNS, anh cứ gửi log lên đây tôi sẽ giải quyết siêu tốc cho anh!* 🚀
