# 🔒 Waymark Backend — Báo Cáo Rà Soát Bảo Mật Toàn Hệ Thống

> **Ngày**: 10/05/2026  
> **Phạm vi**: Toàn bộ source code backend (`app/`), Docker, Alembic, `.env`  
> **Mục tiêu**: Xác định các lỗ hổng bảo mật, vấn đề logic, rủi ro trước khi deploy production

---

## Tổng Quan Mức Độ Nghiêm Trọng

| Mức độ | Số lượng | Biểu tượng |
|--------|----------|------------|
| **NGHIÊM TRỌNG** (Critical) | 4 | 🔴 |
| **CAO** (High) | 5 | 🟠 |
| **TRUNG BÌNH** (Medium) | 5 | 🟡 |
| **THẤP** (Low/Info) | 4 | 🔵 |

---

## 🔴 MỨC ĐỘ NGHIÊM TRỌNG (Critical) — Cần sửa NGAY trước deploy

### C1. SECRET_KEY mặc định hardcode — Khóa JWT không an toàn
- **File**: `app/core/security.py` (dòng 10), `.env` (dòng 7)
- **Vấn đề**: `SECRET_KEY` trong `.env` đang là `supersecretkey_change_in_production`. Đây là giá trị mặc định trong code (fallback). Nếu production `.env` không set hoặc bị leak, bất kỳ ai cũng có thể forge JWT token để giả mạo bất kỳ user nào.
- **Hậu quả**: Toàn quyền truy cập vào tất cả tài khoản, bao gồm Admin.
- **Cách sửa**:

```diff
# .env (production)
-SECRET_KEY=supersecretkey_change_in_production
+SECRET_KEY=<chuỗi ngẫu nhiên 64 ký tự, ví dụ: openssl rand -hex 32>
```

```diff
# app/core/security.py — Bỏ fallback mặc định
-SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_change_in_production")
+SECRET_KEY = os.getenv("SECRET_KEY")
+if not SECRET_KEY:
+    raise RuntimeError("SECRET_KEY environment variable is required")
```

---

### C2. Token Google/Apple KHÔNG xác minh chữ ký (verify_signature = False)
- **File**: `app/api/auth.py` (dòng 92-94 cho Google, dòng 267-270 cho Apple)
- **Vấn đề**: Cả Google và Apple login đều dùng `verify_signature: False, verify_aud: False, verify_exp: False`. Điều này có nghĩa bất kỳ ai cũng có thể tự tạo một JWT token giả chứa email tùy ý và đăng nhập thành công vào bất kỳ tài khoản nào.
- **Hậu quả**: Chiếm quyền bất kỳ tài khoản nào bằng cách craft một JWT giả có `email` trùng.
- **Cách sửa**:

```python
# Sử dụng thư viện google-auth chính thức thay vì decode thủ công
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

payload = id_token.verify_oauth2_token(
    token, 
    google_requests.Request(), 
    GOOGLE_CLIENT_ID  # verify audience
)
```

---

### C3. Facebook mock token cho phép tạo tài khoản giả trong production
- **File**: `app/api/auth.py` (dòng 165-169)
- **Vấn đề**: Code kiểm tra `if token.startswith("mock_fb_")` cho phép bất kỳ ai gửi `mock_fb_anything` và tự động đăng ký + đăng nhập mà KHÔNG cần xác minh qua Facebook. Đây là code debug/test bị bỏ quên.
- **Hậu quả**: Tạo không giới hạn tài khoản giả, spam, DDoS hệ thống.
- **Cách sửa**:

```diff
-        if token.startswith("mock_fb_"):
-            fb_id = token.replace("mock_fb_", "")
-            email = f"fb_{fb_id}@facebook.com"
-            ...
+        # REMOVED: Mock Facebook token (development only)
```

Tương tự cần xóa Apple mock: `app/api/auth.py` (dòng 260-262)

---

### C4. Mật khẩu Admin mặc định lưu trong `.env`
- **File**: `.env` (dòng 19-21)
- **Vấn đề**: `ADMIN_PASSWORD=Admin@123456` — mật khẩu admin quá yếu và lưu rõ trong file. Nếu `.env` bị leak hoặc commit nhầm, hacker có toàn quyền Admin.
- **Cách sửa**: Đổi mật khẩu admin production thành mật khẩu mạnh (16+ ký tự, chữ hoa/thường/số/ký tự đặc biệt). Cân nhắc xóa biến này khỏi `.env` sau khi setup xong.

---

## 🟠 MỨC ĐỘ CAO (High) — Cần sửa trước deploy

### H1. ACCESS_TOKEN_EXPIRE_MINUTES = 3000 (50 giờ!)
- **File**: `.env` (dòng 9)
- **Vấn đề**: JWT token hết hạn sau 50 giờ, quá dài. Nếu token bị đánh cắp, hacker có quyền truy cập suốt 2 ngày.
- **Khuyến nghị**: Giảm xuống 30-60 phút. Implement Refresh Token mechanism cho mobile app.

```diff
-ACCESS_TOKEN_EXPIRE_MINUTES=3000
+ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

### H2. Không có Rate Limiting — Dễ bị brute-force và DDoS
- **File**: `app/main.py`
- **Vấn đề**: Không có middleware rate limiting nào. Các endpoint nhạy cảm (`/v1/auth/login/password`, `/v1/auth/signup/email`, `/v1/auth/google`) có thể bị brute-force mật khẩu hoặc spam đăng ký.
- **Khuyến nghị**: Sử dụng `slowapi` hoặc Nginx rate limiting.

```python
# Ví dụ với slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@router.post("/login/password")
@limiter.limit("5/minute")  
def login(...):
```

---

### H3. Không có CORS configuration — Rủi ro Cross-Origin attacks
- **File**: `app/main.py`
- **Vấn đề**: Không có `CORSMiddleware`. Nếu có web client, cần cấu hình CORS chặt chẽ. Nếu chỉ dùng mobile, nên disable CORS hoặc chỉ allow origin cụ thể.
- **Khuyến nghị**:

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # KHÔNG dùng "*" trong production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### H4. Cloudflare R2 credentials lưu rõ trong `.env` — Cần kiểm soát chặt
- **File**: `.env` (dòng 10-13)
- **Vấn đề**: `R2_ACCESS_KEY_ID` và `R2_SECRET_ACCESS_KEY` lưu plaintext. Nếu leak sẽ cho phép hacker đọc/ghi/xóa toàn bộ media storage.
- **Khuyến nghị**: Dùng secret manager (AWS Secrets Manager, Vault) hoặc ít nhất đảm bảo `.env` chỉ tồn tại trên production server và KHÔNG bao giờ commit vào git.
- ✅ **Xác nhận**: `.env` đã nằm trong `.gitignore` và KHÔNG bị tracked bởi git — Tốt!

---

### H5. Hardcoded R2 public URL placeholder chưa đổi
- **File**: `app/api/memories.py` (dòng 87), `app/api/media.py` (dòng 114), `app/api/social.py` (dòng 110), `app/api/profile.py` (dòng 167)
- **Vấn đề**: URL `https://pub-xxxxxx.r2.dev/...` là placeholder, chưa được thay bằng domain R2 thực tế. Mặc dù `get_r2_url()` sẽ generate presigned URL, nhưng giá trị lưu vào DB vẫn là URL sai → dữ liệu bẩn.
- **Khuyến nghị**: Đưa R2 public domain vào biến môi trường `R2_PUBLIC_URL` và sử dụng xuyên suốt.

```diff
+R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "https://your-bucket.r2.dev")
 ...
-public_url = f"https://pub-xxxxxx.r2.dev/{object_key}"
+public_url = f"{R2_PUBLIC_URL}/{object_key}"
```

---

## 🟡 MỨC ĐỘ TRUNG BÌNH (Medium) — Nên sửa trước hoặc ngay sau deploy

### M1. Không có File Upload Validation — Rủi ro upload malware
- **File**: `app/api/memories.py` (dòng 62-110), `app/api/social.py` (dòng 88-131)
- **Vấn đề**: Không giới hạn kích thước file upload, không kiểm tra loại file (có thể upload `.exe`, `.sh`). Content-type do client tự gửi, có thể giả mạo.
- **Khuyến nghị**:
  - Thêm giới hạn kích thước (ví dụ: 10MB cho ảnh)
  - Kiểm tra magic bytes của file (thay vì chỉ trust content-type)
  - Whitelist extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`

---

### M2. `visibility_expires_at` so sánh timezone naive vs aware
- **File**: `app/api/memories.py` (dòng 264), `app/api/map.py` (dòng 61), `app/api/profile.py` (dòng 301-305)
- **Vấn đề**: Một số nơi dùng `datetime.utcnow()` (naive, không có timezone) để so sánh với cột `visibility_expires_at` (timezone-aware). Trong PostgreSQL có thể hoạt động nhưng sẽ gây lỗi hoặc kết quả sai trong một số trường hợp.
- **Khuyến nghị**: Thống nhất dùng `datetime.now(timezone.utc)` ở mọi nơi.

---

### M3. Thiếu kiểm tra ownership khi tạo conversation
- **File**: `app/api/chat.py` (dòng 161-193)
- **Vấn đề**: Khi `create_conversation`, không kiểm tra `participant_user_ids` có tồn tại hay không, cũng không kiểm tra user có bị block hay không. Hacker có thể tạo conversation với UUID không tồn tại hoặc user đã block.
- **Khuyến nghị**: Validate tất cả participant IDs tồn tại và không bị block trước khi tạo.

---

### M4. Không có soft-delete cho Memory — Dữ liệu mất vĩnh viễn
- **File**: `app/api/memories.py` (dòng 360-391)
- **Vấn đề**: `delete_memory` thực hiện hard delete (xóa vĩnh viễn). Model có trường `deleted_at` nhưng không được sử dụng. Dữ liệu một khi xóa không thể khôi phục.
- **Khuyến nghị**: Dùng soft-delete (set `deleted_at`) thay vì `db.delete()`, và thêm filter `deleted_at.is_(None)` vào tất cả queries.

---

### M5. Debug print statement trong production code
- **File**: `app/api/map.py` (dòng 71)
- **Vấn đề**: `print(f"DEBUG: Found {len(memories_data)} pins...")` — Log debug sẽ xuất hiện trong production stdout/logs.
- **Khuyến nghị**: Xóa hoặc chuyển sang logging module với level DEBUG.

---

## 🔵 MỨC ĐỘ THẤP (Low/Info) — Cải thiện sau deploy

### L1. Không có HTTPS enforcement
- **File**: `docker-compose.prod.yml`
- **Vấn đề**: Uvicorn chạy trên port 8000 HTTP thuần. Cần reverse proxy (Nginx/Caddy) phía trước với SSL/TLS.

### L2. Không có Database Connection Pooling tối ưu cho production
- **File**: `app/database.py` (dòng 16-21)
- `pool_size=20, max_overflow=50` — có thể cần điều chỉnh dựa trên số lượng workers (4 workers × 20 pool = 80 connections). Kiểm tra `max_connections` của PostgreSQL.

### L3. N+1 Query problem trong nhiều endpoints
- **Files**: `app/api/social.py` (dòng 504-565), `app/api/map.py` (dòng 73-91)
- **Vấn đề**: Nhiều endpoint lặp query trong vòng lặp (query user → query profile → query avatar per item). Với dữ liệu lớn sẽ gây chậm nghiêm trọng.
- **Khuyến nghị**: Dùng `joinedload` hoặc batch queries.

### L4. Không có Swagger UI protection
- **File**: `app/main.py`
- Swagger UI (`/docs`) và ReDoc (`/redoc`) mở công khai, cho phép bất kỳ ai khám phá toàn bộ API structure.
- **Khuyến nghị**: Disable trong production hoặc đặt sau authentication.

```python
app = FastAPI(docs_url=None, redoc_url=None)  # Disable in production
```

---

## ✅ Các Điểm Đã Làm Tốt

| Mục | Trạng thái |
|-----|-----------|
| `.env` trong `.gitignore`, không tracked bởi git | ✅ Tốt |
| Mật khẩu hash bằng bcrypt (`passlib`) | ✅ Tốt |
| JWT authentication trên tất cả endpoint cần thiết | ✅ Tốt |
| Block user enforcement trên map, chat, profile | ✅ Tốt |
| Privacy level filtering (private/friends/public) | ✅ Tốt |
| Admin + Super Admin phân quyền rõ ràng | ✅ Tốt |
| PostgreSQL + Redis không expose port ra ngoài (prod yml) | ✅ Tốt |
| Image optimization trước khi upload | ✅ Tốt |
| Visibility expiration filtering trên tất cả endpoints | ✅ Tốt |
| Owner luôn nhìn thấy memory của mình dù đã hết hạn | ✅ Tốt |

---

## 📋 Checklist Hành Động Trước Deploy

| # | Hành động | Mức độ | File | Trạng thái |
|---|-----------|--------|------|------------|
| 1 | Đổi SECRET_KEY production thành chuỗi ngẫu nhiên 64 ký tự | 🔴 Critical | `.env`, `security.py` | ⬜ |
| 2 | Bật verify_signature cho Google/Apple token | 🔴 Critical | `auth.py` | ⬜ |
| 3 | Xóa mock Facebook/Apple token code | 🔴 Critical | `auth.py` | ⬜ |
| 4 | Đổi ADMIN_PASSWORD thành mật khẩu mạnh | 🔴 Critical | `.env` | ⬜ |
| 5 | Giảm ACCESS_TOKEN_EXPIRE_MINUTES xuống 60 | 🟠 High | `.env` | ⬜ |
| 6 | Thêm Rate Limiting (slowapi hoặc Nginx) | 🟠 High | `main.py` | ⬜ |
| 7 | Cấu hình CORS middleware | 🟠 High | `main.py` | ⬜ |
| 8 | Thay R2 public URL placeholder | 🟠 High | Nhiều files | ⬜ |
| 9 | Thêm file upload validation (size + type) | 🟡 Medium | `memories.py`, `social.py` | ⬜ |
| 10 | Thống nhất timezone-aware datetime | 🟡 Medium | Nhiều files | ⬜ |
| 11 | Validate participant IDs khi tạo conversation | 🟡 Medium | `chat.py` | ⬜ |
| 12 | Xóa debug print statements | 🟡 Medium | `map.py` | ⬜ |
| 13 | Disable Swagger UI trong production | 🔵 Low | `main.py` | ⬜ |
| 14 | Setup Nginx reverse proxy với SSL | 🔵 Low | Infra | ⬜ |
