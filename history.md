# Lịch sử phát triển dự án Waymark

## 2026-05-06
- Khởi tạo file `history.md` để theo dõi các thay đổi của dự án.
- **Worker**: Đã thiết lập `Celery` chạy với backend `Redis` (trong `app/worker.py`), bao gồm 2 task cơ bản: `process_media` và `send_notification`.
- Cấu hình `docker-compose.yml` để tự động khởi chạy `worker` song song với `web`.
- Cập nhật luồng tạo Memory (`app/api/memories.py`) để trigger `process_media` chạy ngầm.
- **Social Graph & Engagement**:
  - Tạo các models: `UserRelationship` (cho hệ thống Follow/Friend), `Like`, `Comment`.
  - Migration database thành công cho các bảng social.
  - Xây dựng file `app/api/social.py` gồm các API: Like/Unlike memory, Thêm comment vào memory, Follow user.
  - Tích hợp push notification ngầm (Celery) khi có người Like, Comment hoặc Follow.
- **Place & Geo Index**:
  - Thêm CRUD cơ bản cho địa điểm qua file `app/api/places.py`.
  - Cập nhật API Memory để hỗ trợ bind bài post với một `place_id` cụ thể.
  - Hỗ trợ lấy toàn bộ memories thuộc về một Place (`GET /v1/places/{place_id}/memories`).
- **News Feed / Discovery**:
  - Viết `app/api/discovery.py`.
  - Triển khai endpoint trending nearby (`GET /v1/discovery/trending/nearby`) để lọc các top memories public.
  - Triển khai endpoint giả lập phân cụm trên map (`GET /v1/discovery/clusters`) hỗ trợ zoom/bbox bounds của bản đồ.
- **Sửa lỗi Database Connection**:
  - Xung đột cổng 5432 và 5433 với PostgreSQL có sẵn trên Windows.
  - Cập nhật `docker-compose.yml` chuyển expose port của `postgres` sang **15432**.
- **Media Upload (Cloudflare R2)**:
  - Thêm bảng `Media` vào Database để lưu trữ video/ảnh.
  - Cài đặt `boto3` và tạo API `POST /v1/memories/{memory_id}/media/upload-url` sinh **Presigned URL** trực tiếp lên Cloudflare R2 (Giảm tải băng thông cho server).
- **Cải tiến Luồng tạo Memory & Upload ảnh trực tiếp**:
  - Chuyển API tạo Memory (`POST /v1/memories`) sang dùng `multipart/form-data` để hỗ trợ upload ảnh trực tiếp qua tham số `images`.
  - Tự động tải ảnh trực tiếp lên Cloudflare R2 (sử dụng thông tin khai báo trong `.env`) và lưu bản ghi vào bảng `Media` gắn với `Memory` vừa tạo.
  - Cập nhật schema `MemoryDetailResponse` và API lấy chi tiết Memory (`GET /v1/memories/{memory_id}`) để sinh **Presigned GET URL** trực tiếp từ Cloudflare R2 dựa trên thông tin cấu hình `.env`, giúp hiển thị ảnh trực tiếp từ Cloudflare R2 một cách bảo mật mà không cần cấu hình Bucket Public.
  - Sửa lỗi validate trường `place_id` (chuyển sang dạng `str` và phân tích UUID thủ công) giúp tránh lỗi crash 422 Unprocessable Entity của Pydantic/FastAPI khi người dùng nhập sai định dạng hoặc truyền chuỗi trống từ Swagger UI. Trả về thông báo lỗi chi tiết, dễ hiểu bằng Tiếng Việt.
- **Tương tác xã hội & Sửa lỗi bình luận (Comment)**:
  - Tích hợp động hiển thị `likes_count`, `comments_count` và trạng thái `is_liked` (người dùng hiện tại đã like hay chưa) vào tất cả các API trả về danh sách/chi tiết Memory.
  - Sửa lỗi crash 500 khi bình luận nhờ cơ chế tiền kiểm tra sự tồn tại của `memory_id` và `parent_comment_id` ngay từ Python. Nếu người dùng nhập sai/để mặc định giá trị ví dụ của Swagger ở `parent_comment_id` thay vì trả lỗi 500 DB IntegrityError, hệ thống giờ sẽ phản hồi lỗi 400 rõ ràng bằng Tiếng Việt hướng dẫn xóa trống hoặc đặt thành null đối với bình luận mới.

## 2026-05-07
- **Hồ sơ cá nhân (Profile)**: 
  - Thêm schema và API quản lý trang cá nhân `GET/PUT /v1/profile/me`.
  - Hỗ trợ lấy thông tin người dùng khác `GET /v1/profile/{user_id}` và danh sách bài đăng của họ `GET /v1/profile/{user_id}/memories`.
  - Bổ sung API `POST /v1/profile/me/avatar` cho phép tải trực tiếp ảnh đại diện lên Cloudflare R2 và tự động lưu vào UserProfile.
- **Hoàn thiện Core API**: 
  - Bổ sung API cập nhật/xóa bài đăng (PATCH/DELETE `/v1/memories/{memory_id}`) có đi kèm xóa cascade media, likes và comments liên quan.
  - Bổ sung chức năng hủy theo dõi (DELETE `/v1/users/{user_id}/follow`).
- **Tính năng Chat**: 
  - Tạo các model database `Conversation`, `ConversationParticipant`, `Message`.
  - Phát triển module `app/api/chat.py` hỗ trợ API tạo hội thoại, lấy danh sách hội thoại, gửi và xem tin nhắn.
  - Cấu hình API chat trả về URL ảnh (`media_url`) được sinh bảo mật trực tiếp từ Cloudflare R2.
- **Tính năng Collection (Bộ sưu tập)**:
  - Tạo các model `Collection`, `CollectionItem`.
  - Phát triển module `app/api/collections.py` hỗ trợ quản lý bộ sưu tập và lưu bài đăng (memories) vào album.
- **Tính năng bình luận (Comment) có ảnh**:
  - Nâng cấp model `Comment` hỗ trợ trường `media_id` và cập nhật API `POST /v1/memories/{id}/comments` sang định dạng Multipart hỗ trợ upload trực tiếp ảnh đi kèm bình luận lên R2.
- **Giao diện Client Thử nghiệm (Test SPA)**:
  - Xây dựng giao diện Single Page Application (SPA) tuyệt đẹp tại route gốc (`/`), sử dụng phong cách thiết kế Cyber-glassmorphism tối tân.
  - Tích hợp bản đồ **Leaflet** giao diện Dark-theme của CartoDB, hỗ trợ click/double-click lấy tọa độ, hiển thị ghim bài viết động có kèm ảnh nạp từ R2, nút Like tương tác thời gian thực, khung bình luận kèm upload ảnh và lựa chọn lưu bài viết vào bộ sưu tập.
  - Hỗ trợ đầy đủ bộ khung chat trực tiếp, cho phép tạo phòng chat theo User ID, gửi tin nhắn văn bản lẫn hình ảnh và tự động nạp tin nhắn mới liên tục (polling).
- **Database & Migration**:
  - Khắc phục lỗi `autogenerate` của Alembic khi dùng chung với hệ thống `postgis_tiger_geocoder`.
  - Deploy script migration mới và nâng cấp DB (tạo bảng Chat, Collection) thành công qua môi trường Docker (`alembic upgrade head`).

## 2026-05-21
- **Cập nhật hình ảnh (Media) cho các API hiển thị**:
  - Sửa API Map Pins (`GET /v1/map/pins`) để tự động kèm theo danh sách link ảnh/video (`media`) của mỗi bài đăng.
  - Sửa API Profile Memories (`GET /v1/profile/{user_id}/memories`) bổ sung mảng `media` chứa ảnh thực tế.
  - Sửa API Danh sách Collections (`GET /v1/collections`), bổ sung `cover_image_url` (tự động lấy ảnh mới nhất làm ảnh bìa) và `items_count`.
- **Cải tiến Authentication**:
  - Bổ sung trả về trường `user_id` kèm theo JWT Token trong tất cả các API đăng nhập/đăng ký (Password, Google, Facebook, Apple).
- **Sửa lỗi API & Database**:
  - Khắc phục lỗi **500 Internal Server Error** trên API Comments (`GET /v1/memories/{memory_id}/comments`) do truy vấn bảng `comment_likes` chưa được khởi tạo. Đã viết file Migration mới (`g1h2i3j4k5l6`) và áp dụng thành công.
  - Sửa lỗi crash Pydantic Model (Forward Reference của `MediaResponse`) bằng `model_rebuild()`.
  - Cập nhật các bộ lọc truy vấn: Loại bỏ các bản ghi đã bị xóa mềm (`deleted_at IS NOT NULL`) khỏi API danh sách Memories và Comments.

## 2026-05-22
- **Thêm Refresh Token**:
  - Thêm hàm `create_refresh_token()` vào `app/core/security.py` — tạo JWT dài hạn 7 ngày (cấu hình qua env `REFRESH_TOKEN_EXPIRE_DAYS`), phân biệt với access token bằng trường `type: "refresh"` trong payload.
  - Cập nhật schema `Token` trong `app/schemas.py`: thêm trường `refresh_token`. Thêm schema `RefreshTokenRequest`.
  - Cập nhật **tất cả 4 endpoint login** (`login/password`, `google`, `facebook`, `apple`) trong `app/api/auth.py` để trả về cả `access_token` lẫn `refresh_token`.
  - Thêm endpoint mới `POST /v1/auth/refresh`: nhận `refresh_token`, kiểm tra loại token và trạng thái user, trả về cặp token mới (token rotation). Không cần migration DB — token hoàn toàn stateless (JWT).
- **Sửa lỗi quyền riêng tư Memory**:
  - Khắc phục bug trong `GET /v1/memories/{memory_id}` (`app/api/memories.py`): thiếu kiểm tra `deleted_at` — kỷ niệm đã bị xóa mềm vẫn có thể truy cập bởi người khác.
  - Sắp xếp lại thứ tự kiểm tra quyền: `not found → deleted → blocked → private (level 1) → friends (level 2) → public expired (level 3)` cho logic rõ ràng và bảo mật hơn.
- **Cập nhật Tài liệu API** (`api_documentation.md`):
  - Section Auth: thêm tài liệu endpoint `POST /auth/refresh` chi tiết (request, response, bảng lỗi, quy trình đề xuất cho App). Cập nhật response mẫu login có `refresh_token`. Thêm response mẫu cho `GET /auth/me`.
  - Section Chat & WebSocket: viết lại hoàn toàn với mô tả kiến trúc REST + WebSocket, bảng hướng dẫn kết nối WebSocket, payload chi tiết với bảng mô tả từng trường, hướng dẫn reconnect, response mẫu đầy đủ cho từng endpoint (`GET /conversations`, `POST /conversations`, `GET /conversations/{id}/messages`, `POST /conversations/{id}/messages`), giải thích ý nghĩa `is_pending` (Message Request), bảng lỗi thường gặp.
- **Sửa lỗi 500 khi xem kỷ niệm của người khác** (`app/api/memories.py`):
  - Khắc phục `TypeError: can't compare offset-naive and offset-aware datetimes` tại `GET /v1/memories/{memory_id}` dòng 287.
  - Nguyên nhân: `datetime.utcnow()` trả về naive datetime (không có timezone), trong khi `memory.visibility_expires_at` từ DB là aware datetime (có timezone UTC) → Python không cho so sánh 2 loại này.
  - Fix: thay `from datetime import datetime` → `from datetime import datetime, timezone` và đổi `datetime.utcnow()` → `datetime.now(timezone.utc)`. Lưu ý `datetime.utcnow()` đã bị deprecated từ Python 3.12.

## 2026-06-26
- **FCM Push Notification (thật)**:
  - Thêm `firebase-admin==6.3.0` vào `requirements.txt`.
  - Lưu Firebase Service Account (`firebase_service_account.json`) tại thư mục gốc dự án.
  - Cập nhật `app/worker.py`: khởi tạo Firebase Admin SDK một lần tại module load. Task `send_notification` giờ thực hiện 2 bước: (1) lưu bản ghi vào DB như cũ, (2) query tất cả `DeviceToken` của user nhận rồi gửi FCM thật qua `firebase_admin.messaging.send()`. Token hết hạn (`UnregisteredError`) được tự động xoá khỏi DB.
- **API Đổi mật khẩu**:
  - Thêm `POST /v1/auth/change-password` (🔒 yêu cầu đăng nhập). Nhận `current_password` + `new_password`, kiểm tra MK cũ đúng trước khi lưu MK mới.
- **API Quên / Đặt lại mật khẩu**:
  - Thêm `POST /v1/auth/forgot-password` (🔓 không cần đăng nhập). Nhận `email`, tạo reset token ngẫu nhiên (`secrets.token_urlsafe(32)`) hiệu lực 30 phút, vô hiệu hoá token cũ chưa dùng. Hiện trả về `reset_token` trong response để test; production cần tích hợp gửi email.
  - Thêm `POST /v1/auth/reset-password` (🔓 không cần đăng nhập). Nhận `token` + `new_password`, validate hết hạn, đã dùng, sau đó đặt lại mật khẩu và đánh dấu token đã dùng.
  - Thêm model `PasswordResetToken` vào `app/models.py`.
- **API Lưu Device Token (FCM)**:
  - Thêm `POST /v1/auth/device-token` (🔒 yêu cầu đăng nhập). Nhận `token` (FCM registration token) + `platform` (`ios`/`android`/`web`). Upsert: nếu token đã tồn tại và thuộc thiết bị khác đăng nhập → cập nhật `user_id`. Cho phép một user có nhiều device token (nhiều thiết bị).
  - Thêm model `DeviceToken` vào `app/models.py`.
- **Map API hỗ trợ khách (chưa đăng nhập)**:
  - Sửa `GET /v1/map/pins`: chuyển từ `get_current_user` (bắt buộc) sang `get_optional_user` (tuỳ chọn).
  - Khách không có token → chỉ nhận pin `privacy_level=3` (công khai) còn trong hạn hiển thị 30 ngày.
  - Người dùng đã đăng nhập → giữ nguyên logic cũ: public + bạn bè, loại trừ blocked.
  - Thêm hàm `get_optional_user` vào `app/core/dependencies.py` (dùng `HTTPBearer(auto_error=False)`).
- **Database Migration**:
  - Migration `h7i8j9k0l1m2`: tạo bảng `device_tokens` (lưu FCM tokens) và `password_reset_tokens` (lưu token quên MK) với index phù hợp.

## 2026-06-29
- **Section 12 tài liệu FCM Push Notification** (`api_documentation.md`):
  - Viết toàn bộ Section 12 hướng dẫn tích hợp Firebase: đăng ký device token, bảng loại thông báo, phân trang, Flutter integration guide.
- **API Đăng xuất** (`app/api/auth.py`):
  - Thêm `POST /v1/auth/logout` (🔒): nhận `device_token`, xóa khỏi DB. Thiết bị đó ngừng nhận push notification sau khi logout.
- **Sửa lỗi Google OAuth 400** (`app/api/auth.py`):
  - python-jose ném lỗi khi ID Token chứa `at_hash` claim nhưng không có access_token đi kèm.
  - Fix: dùng `google.oauth2.id_token.verify_oauth2_token()` khi có `GOOGLE_CLIENT_ID` (xác minh chữ ký thật). Fallback sang `jwt.get_unverified_claims()` cho môi trường dev không có client ID.

## 2026-06-30
- **Backup dữ liệu lên Cloudflare R2** (`scripts/backup_r2.sh`, `scripts/restore_r2.sh`, `scripts/README.md`):
  - Script tự động: `pg_dump | gzip` → upload lên R2 bucket `waymark-media/backups/`.
  - Script restore: liệt kê backup có sẵn trên R2, tải về, restore (`DROP SCHEMA + CREATE SCHEMA + pg_restore`).
  - Hướng dẫn cài cron hàng ngày, quy trình chuyển server giữ nguyên dữ liệu, bảng lệnh nguy hiểm cần tránh.
- **Phân trang cursor-based** (`app/api/social.py`, `app/api/chat.py`):
  - Thông báo (`GET /notifications`): tham số `before_id` + `limit` (tối đa 50) thay vì OFFSET.
  - Tin nhắn (`GET /conversations/{id}/messages`): tham số `before_id` + `limit` (mặc định 30, tối đa 100) thay vì `skip`.
  - Cursor-based tránh data drift khi có real-time data mới.
- **Anti-spam — Rate Limiting** (`app/core/rate_limit.py`, `app/main.py`, `requirements.txt`):
  - Cài `fastapi-limiter==0.1.6` dùng Redis DB 1 (DB 0 là Celery).
  - IP-based: signup 5/giờ, login 10/phút, forgot-password 3/giờ.
  - User-based: like 200/giờ, comment 30/giờ, follow 50/giờ, message 30/phút, tạo memory 20/24 giờ.
  - Callback 429 trả lỗi tiếng Việt, dùng `X-Forwarded-For` cho real IP qua nginx.
- **Tối ưu N+1 queries — Batch Loading** (`app/api/map.py`, `app/api/social.py`, `app/api/profile.py`, `app/api/discovery.py`):
  - Viết hàm `_batch_enrich_memories()` trong `map.py`: load likes counts, comments counts, is_liked, media, author info bằng ~6 queries thay vì 5×N queries cũ.
  - `GET /map/pins`: dùng `_batch_enrich_memories()`.
  - `GET /users/{id}/memories` (`profile.py`): dùng `_batch_enrich_memories()`.
  - `GET /discovery/trending/nearby` (`discovery.py`): dùng `_batch_enrich_memories()`.
  - `GET /memories/{id}/comments` (`social.py`): batch load avatars + comment media + comment likes counts + liked_set — giảm từ 3N → 3 queries.
  - `GET /notifications` (`social.py`): batch load sender info (user + profile + avatar) — giảm từ 3N → 4 queries.
  - `GET /memories/{id}/likes` (`social.py`): dùng `_build_simple_user_list()` — giảm từ 3N → 3 queries.
  - Block check trong `map.py`: thay Python loop bằng SQL UNION subquery.
- **Bảo mật** (`app/core/security.py`, `app/api/auth.py`):
  - `SECRET_KEY`: in warning khi dùng default key lúc khởi động.
  - Password reset token: lưu SHA-256 hash vào DB thay vì plaintext.
  - `GET /followers`, `GET /following`, `GET /friends` (`social.py`): thêm kiểm tra target user tồn tại trước khi follow; thêm pagination `limit`/`offset`.
- **Validation & Upload** (`app/core/upload_validator.py`, `app/api/memories.py`, `app/schemas.py`):
  - Tạo `app/core/upload_validator.py`: kiểm tra content-type (JPEG/PNG/WebP/GIF/HEIC) và kích thước (≤50MB).
  - `POST /memories`: validate `privacy_level` phải là 1/2/3; giới hạn tối đa 10 ảnh/kỷ niệm; áp dụng upload validator cho từng ảnh.
  - `app/schemas.py`: thêm `Field` constraints — username 3–30 ký tự, password 6–128 ký tự, caption 1–2000 ký tự, display_name ≤50 ký tự.
- **Soft Delete bình luận** (`app/api/social.py`):
  - `DELETE /comments/{id}`: đổi từ hard delete sang soft delete (`deleted_at = utcnow()`). Comment bị ẩn khỏi API nhưng giữ trong DB.
- **Sửa bug** (`app/api/map.py`, `app/api/discovery.py`):
  - `map.py` dòng 79: `m_res.author_username` → `m_res.username` (field không tồn tại trong schema, gây mất data silently).
  - `discovery.py`: thiếu filter `deleted_at.is_(None)` → kỷ niệm đã xóa vẫn hiện trong trending.
- **Cập nhật tài liệu** (`api_documentation.md`):
  - Thêm bảng Rate Limiting và mã lỗi 429.
  - Cập nhật `POST /memories`: validation `privacy_level`, giới hạn ảnh, caption 1–2000 ký tự.
  - Cập nhật `DELETE /comments/{id}`: ghi rõ soft delete.
  - Cập nhật `GET /followers/following/friends`: thêm `limit`/`offset` params.
  - Thêm note bảo mật cho `POST /auth/google` (verify chữ ký) và `POST /auth/forgot-password` (SHA-256 hash).
  - Thêm bảng validation rules cho `POST /auth/signup/email`.

## 2026-05-27
- **Sửa lỗi trùng lặp cuộc hội thoại (Conversation Deduplication)**:
  - Nâng cấp API tạo cuộc hội thoại (`POST /v1/chat`). Đối với cuộc hội thoại trực tiếp (direct message 1-1), hệ thống tiến hành kiểm tra sự tồn tại trong DB.
  - Nếu đã tồn tại cuộc hội thoại trực tiếp giữa hai người dùng này trước đó, hệ thống sẽ trả về ngay cuộc hội thoại cũ kèm flag `is_existing: true` thay vì tạo mới trùng lặp.
  - Thêm thuộc tính `is_existing: bool = False` vào `ConversationResponse` trong `app/schemas.py` và khởi tạo trong `enrich_conversation` ở `app/api/chat.py`.
- **Cập nhật tài liệu dự án**:
  - Cập nhật chi tiết trường `is_existing` và logic kiểm tra trùng lặp trong [api_documentation.md](file:///d:/Duong/Waymark/waymark/api_documentation.md).

