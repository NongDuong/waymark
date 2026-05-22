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
