# WAYMARK API - TÀI LIỆU TÍCH HỢP CHI TIẾT

> **Base URL:** `https://<your-domain>/v1`  
> **Auth:** Tất cả API có 🔒 yêu cầu Header: `Authorization: Bearer <access_token>`

---

## MỤC LỤC
1. [Xác thực (Auth)](#1-xác-thực-auth)
2. [Hồ sơ người dùng (Profile)](#2-hồ-sơ-người-dùng-profile)
3. [Bản đồ (Map)](#3-bản-đồ-map)
4. [Kỷ niệm (Memories)](#4-kỷ-niệm-memories)
5. [Địa điểm (Places)](#5-địa-điểm-places)
6. [Khám phá (Discovery)](#6-khám-phá-discovery)
7. [Xã hội (Social)](#7-xã-hội-social)
8. [Chat & WebSocket](#8-chat--websocket)
9. [Đa phương tiện (Media)](#9-đa-phương-tiện-media)
10. [Bộ sưu tập (Collections)](#10-bộ-sưu-tập-collections)
11. [Báo cáo (Reports)](#11-báo-cáo-reports)

---

## 1. XÁC THỰC (AUTH)

### `POST /auth/signup/email` — Đăng ký bằng Email
Tạo tài khoản mới. Hệ thống tự động tạo hồ sơ cá nhân (UserProfile) ngay khi đăng ký thành công.

**Request Body (JSON):**
```json
{
  "email": "user@example.com",
  "username": "duongwaymark",
  "password": "SecurePassword123",
  "display_name": "Dương Waymark"
}
```
**Response 200:**
```json
{
  "id": "uuid",
  "username": "duongwaymark",
  "primary_email": "user@example.com"
}
```

---

### `POST /auth/login/password` — Đăng nhập bằng Email & Mật khẩu
Dùng `username` hoặc `email` đều được.

**Request:** `application/x-www-form-urlencoded`
```
username=duongwaymark&password=SecurePassword123
```
**Response 200:**
```json
{ "access_token": "eyJhbGci...", "token_type": "bearer" }
```

---

### `POST /auth/google` — Đăng nhập bằng Google 🔓
Gửi `credential` (ID Token) nhận được từ Google Sign-In SDK trên App.

**Request Body (JSON):**
```json
{ "credential": "<google_id_token>" }
```
**Response 200:** Trả về JWT token tương tự login thông thường.

> **Lưu ý:** Nếu email chưa tồn tại, hệ thống sẽ tự động tạo tài khoản mới và hồ sơ cá nhân kèm ảnh avatar từ Google.

---

### `POST /auth/facebook` — Đăng nhập bằng Facebook 🔓
Gửi `access_token` nhận được từ Facebook Login SDK.

**Request Body (JSON):**
```json
{ "access_token": "<facebook_access_token>" }
```

---

### `POST /auth/apple` — Đăng nhập bằng Apple 🔓
Gửi `id_token` từ Sign in with Apple SDK.

**Request Body (JSON):**
```json
{ "id_token": "<apple_id_token>", "display_name": "Tên hiển thị (chỉ lần đầu)" }
```

---

### `GET /auth/me` 🔒 — Lấy thông tin tài khoản hiện tại
Trả về thông tin User đang đăng nhập (không bao gồm thông tin hồ sơ chi tiết).

---

### `GET /auth/config` 🔓 — Lấy cấu hình đăng nhập mạng xã hội
Trả về Client ID của Google, Facebook, Apple để App khởi tạo SDK đúng cách.

**Response 200:**
```json
{
  "google_client_id": "xxxxxxx.apps.googleusercontent.com",
  "facebook_app_id": "7210xxxxx",
  "apple_client_id": "vn.waymark.app.signin"
}
```

---

## 2. HỒ SƠ NGƯỜI DÙNG (PROFILE)

### `GET /profile/me` 🔒 — Lấy hồ sơ của bản thân
Trả về toàn bộ thông tin hồ sơ cá nhân bao gồm số liệu thống kê thời gian thực (số người theo dõi, số kỷ niệm, tổng lượt thích nhận được...).

**Response 200:**
```json
{
  "user_id": "uuid",
  "username": "duongwaymark",
  "display_name": "Dương Waymark",
  "avatar_url": "https://pub-xxx.r2.dev/avatars/...",
  "bio": "Tôi yêu khám phá",
  "gender": "male",
  "home_city": "Hà Nội",
  "country_code": "VN",
  "followers_count": 120,
  "following_count": 85,
  "total_likes_received": 340,
  "memories_count": 42,
  "is_vip": false,
  "is_admin": false
}
```

---

### `PUT /profile/me` 🔒 — Cập nhật hồ sơ cá nhân
Chỉ cần gửi các trường muốn thay đổi (partial update).

**Request Body (JSON):**
```json
{
  "display_name": "Tên mới",
  "bio": "Mô tả mới",
  "gender": "female",
  "home_city": "TP. Hồ Chí Minh",
  "country_code": "VN"
}
```

---

### `POST /profile/me/avatar` 🔒 — Tải lên ảnh đại diện
Gửi file ảnh dạng `multipart/form-data`. Hệ thống tự động tối ưu ảnh về kích thước tối đa 400x400px và chuyển sang định dạng `.webp` trước khi lưu lên Cloudflare R2.

**Request:** `multipart/form-data`
| Field | Type | Mô tả |
|-------|------|-------|
| `avatar` | File | File ảnh (jpg, png, webp...) |

---

### `GET /profile/{user_id}` 🔒 — Xem hồ sơ người dùng khác
Trả về hồ sơ công khai của người dùng khác. Bao gồm trạng thái quan hệ: `is_following`, `is_blocked`.

---

### `GET /profile/{user_id}/memories` 🔒 — Xem kỷ niệm của người dùng khác
Trả về danh sách kỷ niệm theo quyền riêng tư:
- Nếu là **bạn bè** (follow chéo): Thấy được kỷ niệm chế độ bạn bè (level 2) + công khai (level 3).
- Nếu là **người lạ**: Chỉ thấy kỷ niệm công khai (level 3) còn hạn hiển thị.

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|---------|-------|
| `skip` | int | 0 | Bỏ qua N kỷ niệm đầu (phân trang) |
| `limit` | int | 20 | Số lượng trả về tối đa |

---

### `GET /profile/me/location-stats` 🔒 — Thống kê hành trình theo địa lý
Trả về tóm tắt "Tôi đã đi qua bao nhiêu tỉnh/thành, quận/huyện, quốc gia?".

**Response 200:**
```json
{
  "total_memories": 42,
  "total_countries": 3,
  "total_provinces": 12,
  "total_districts": 28,
  "total_communes": 45,
  "total_places": 37,
  "countries": ["Vietnam", "Thailand", "Japan"],
  "provinces": ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng"]
}
```

---

## 3. BẢN ĐỒ (MAP)

### `GET /map/pins` 🔒 — Lấy ghim kỷ niệm xung quanh (Bản đồ cá nhân hóa)
**Mục đích:** Dùng cho màn hình **Bản đồ chính** của App. Trả về tất cả kỷ niệm trong bán kính xung quanh vị trí người dùng, bao gồm cả kỷ niệm của bản thân, bạn bè và công khai. Tự động **lọc bỏ** kỷ niệm của người đã chặn nhau.

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|---------|-------|
| `lat` | float | **Bắt buộc** | Vĩ độ trung tâm |
| `lng` | float | **Bắt buộc** | Kinh độ trung tâm |
| `radius` | float | 1000 | Bán kính (mét) |

**Quy tắc hiển thị:**
- ✅ Kỷ niệm của **bản thân** (mọi chế độ riêng tư)
- ✅ Kỷ niệm của **bạn bè** (chế độ bạn bè + công khai)
- ✅ Kỷ niệm **công khai** của người lạ (còn hạn hiển thị 30 ngày)
- ❌ Kỷ niệm của người đã **chặn nhau**

**Trả về tối đa:** 100 ghim.

---

## 4. KỶ NIỆM (MEMORIES)

### `POST /memories` 🔒 — Tạo kỷ niệm mới
Dùng `multipart/form-data` vì có thể kèm theo ảnh.

**Request Fields:**
| Field | Type | Mô tả |
|-------|------|-------|
| `caption` | string | Nội dung kỷ niệm (bắt buộc) |
| `lat` | float | Vĩ độ (bắt buộc) |
| `lng` | float | Kinh độ (bắt buộc) |
| `privacy_level` | int | 1=Riêng tư, 2=Bạn bè, 3=Công khai (mặc định 3) |
| `mood_code` | string | Trạng thái cảm xúc (tùy chọn) |
| `place_id` | UUID | ID địa điểm từ hệ thống Places (tùy chọn) |
| `images` | File[] | Danh sách ảnh đính kèm (tùy chọn) |

> Sau khi tạo, hệ thống tự động kích hoạt 2 tác vụ nền: **xử lý media** và **reverse geocoding** (tự động điền tên tỉnh/thành, quận/huyện).

---

### `GET /memories/on-this-day` 🔒 — "Ngày này năm xưa"
Trả về kỷ niệm của người dùng vào đúng ngày này trong các năm trước — tương tự tính năng "On This Day" của Facebook.

**Query Parameters:**
| Param | Type | Mô tả |
|-------|------|-------|
| `years_ago` | int | (Tùy chọn) Lọc đúng N năm trước. Không truyền = lấy tất cả |

---

### `GET /memories/{memory_id}` 🔒 — Xem chi tiết kỷ niệm
Trả về thông tin đầy đủ của một kỷ niệm. Tự động kiểm tra quyền riêng tư và trạng thái chặn.

---

### `PATCH /memories/{memory_id}` 🔒 — Chỉnh sửa kỷ niệm
Chỉ chủ sở hữu hoặc Admin mới có quyền sửa. Chỉ cần gửi các trường muốn thay đổi.

---

### `DELETE /memories/{memory_id}` 🔒 — Xóa kỷ niệm
Xóa hoàn toàn kỷ niệm, toàn bộ ảnh, like và bình luận liên quan.

---

### `POST /memories/{memory_id}/extend` 🔒 — Gia hạn hiển thị kỷ niệm
Kỷ niệm công khai mặc định hiển thị 30 ngày. API này gia hạn thêm thời gian.

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|---------|-------|
| `days` | int | 30 | Số ngày gia hạn thêm |

---

## 5. ĐỊA ĐIỂM (PLACES)

### `POST /places` 🔒 — Đăng ký địa điểm mới
Lưu một địa điểm thực tế vào hệ thống. Nếu địa điểm đã tồn tại (dựa theo `provider_place_id`), hệ thống trả về thông tin sẵn có mà không tạo trùng.

**Request Body (JSON):**
```json
{
  "provider": "google",
  "provider_place_id": "ChIJ...",
  "name": "Cà phê Cộng Hà Nội",
  "address_text": "152 Triệu Việt Vương, Hà Nội",
  "country_code": "VN",
  "admin1": "Hà Nội",
  "admin2": "Quận Hai Bà Trưng",
  "location": { "lat": 21.0245, "lng": 105.8412 }
}
```

---

### `GET /places/{place_id}/memories` 🔒 — Kỷ niệm tại địa điểm
Trả về danh sách kỷ niệm được check-in tại địa điểm này, tự động kiểm tra quyền riêng tư và bạn bè. Trả về tối đa 50 kỷ niệm, sắp xếp mới nhất trước.

---

## 6. KHÁM PHÁ (DISCOVERY)

> **So sánh với `/map/pins`:** Discovery chỉ trả về bài đăng **công khai**, dùng cho tính năng **"Khám phá cộng đồng"**, không phải bản đồ cá nhân.

### `GET /discovery/trending/nearby` 🔒 — Kỷ niệm xu hướng xung quanh
Trả về tối đa 20 kỷ niệm công khai mới nhất trong bán kính chỉ định, kèm thông tin tác giả.

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|---------|-------|
| `lat` | float | **Bắt buộc** | Vĩ độ |
| `lng` | float | **Bắt buộc** | Kinh độ |
| `radius` | float | 5000 | Bán kính (mét) |

---

### `GET /discovery/clusters` 🔒 — Gom cụm ghim trên bản đồ
Khi người dùng zoom out bản đồ, gộp nhiều ghim gần nhau thành một cụm với số lượng. Nhận vùng bản đồ hiện tại (`bbox`) và mức zoom.

**Query Parameters:**
| Param | Type | Mô tả |
|-------|------|-------|
| `bbox` | string | Chuỗi `"minLng,minLat,maxLng,maxLat"` |
| `zoom` | int | Mức thu phóng bản đồ hiện tại |

**Response:**
```json
[{ "lat": 21.02, "lng": 105.84, "count": 47 }]
```

---

## 7. XÃ HỘI (SOCIAL)

### Like / Unlike kỷ niệm
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/memories/{memory_id}/likes` 🔒 | Thích kỷ niệm. Tự động gửi thông báo đẩy cho chủ bài. |
| `DELETE` | `/memories/{memory_id}/likes` 🔒 | Bỏ thích. |
| `GET` | `/memories/{memory_id}/likes` 🔒 | Danh sách người đã thích. |

---

### Bình luận
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/memories/{memory_id}/comments` 🔒 | Đăng bình luận (text hoặc ảnh, hỗ trợ reply). |
| `GET` | `/memories/{memory_id}/comments` 🔒 | Lấy tất cả bình luận (kèm avatar, likes). |
| `DELETE` | `/comments/{comment_id}` 🔒 | Xóa bình luận (chủ bình luận hoặc chủ bài đăng). |
| `POST` | `/comments/{comment_id}/likes` 🔒 | Thích bình luận. |
| `DELETE` | `/comments/{comment_id}/likes` 🔒 | Bỏ thích bình luận. |

**Đăng bình luận** dùng `multipart/form-data`:
| Field | Type | Mô tả |
|-------|------|-------|
| `content` | string | Nội dung text (tùy chọn nếu có ảnh) |
| `parent_comment_id` | UUID | ID bình luận cha nếu muốn reply (tùy chọn) |
| `image` | File | Ảnh đính kèm (tùy chọn) |

---

### Follow / Unfollow
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/users/follow` 🔒 | Follow người dùng. Tự động tăng bộ đếm followers/following. |
| `DELETE` | `/users/{user_id}/follow` 🔒 | Unfollow. Tự động giảm bộ đếm. |
| `GET` | `/followers` 🔒 | Danh sách người đang theo dõi mình. |
| `GET` | `/following` 🔒 | Danh sách người mình đang theo dõi. |
| `GET` | `/friends` 🔒 | Danh sách bạn bè (follow chéo lẫn nhau). |

**Body cho Follow:**
```json
{ "target_user_id": "uuid-của-người-muốn-follow" }
```

---

### Chặn / Bỏ chặn
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `POST` | `/users/{user_id}/block` 🔒 | Chặn người dùng. Tự động hủy follow hai chiều nếu có. |
| `DELETE` | `/users/{user_id}/block` 🔒 | Bỏ chặn. |

---

### Thông báo (Notifications)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/notifications` 🔒 | Lấy 50 thông báo gần nhất (kèm avatar người gửi). |
| `POST` | `/notifications/{id}/read` 🔒 | Đánh dấu một thông báo đã đọc. |
| `POST` | `/notifications/read-all` 🔒 | Đánh dấu tất cả thông báo đã đọc. |

---

## 8. CHAT & WEBSOCKET

### Kết nối WebSocket — Nhận tin nhắn thời gian thực
```
wss://<your-domain>/v1/conversations/ws/<access_token>
```
Kết nối một lần khi App khởi động. Khi có tin nhắn mới trong bất kỳ cuộc hội thoại nào, server sẽ **đẩy dữ liệu về tức thì** qua WebSocket, không cần App polling liên tục.

**Payload nhận được khi có tin nhắn mới:**
```json
{
  "type": "new_message",
  "conversation_id": "uuid",
  "message": { "id": "uuid", "text_content": "Xin chào!", "sender_user_id": "uuid", "sent_at": "..." }
}
```

---

### REST API Chat
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/conversations` 🔒 | Danh sách cuộc hội thoại (kèm tin nhắn cuối, avatar đối phương). |
| `POST` | `/conversations` 🔒 | Tạo cuộc hội thoại mới (trực tiếp hoặc nhóm). |
| `GET` | `/conversations/{id}/messages` 🔒 | Lấy lịch sử tin nhắn (hỗ trợ phân trang). |
| `POST` | `/conversations/{id}/messages` 🔒 | Gửi tin nhắn. Tự động đẩy WebSocket đến các thành viên. |

**Tạo cuộc hội thoại:**
```json
{
  "participant_user_ids": ["uuid-người-nhận"],
  "title": null
}
```
> Nếu `participant_user_ids` có 1 người → tạo chat **riêng tư (direct)**. Nhiều người → tạo **nhóm**.

**Gửi tin nhắn:**
```json
{
  "text_content": "Nội dung tin nhắn",
  "media_id": null,
  "reply_to_message_id": null
}
```

---

## 9. ĐA PHƯƠNG TIỆN (MEDIA)

Hệ thống có **2 cách tải ảnh lên** tùy mục đích:

### Cách 1: Tải trực tiếp (Dùng cho avatar, ảnh nhỏ)

#### `POST /media/upload` 🔒 — Tải file lên thẳng qua Backend
Gửi file ảnh, Backend tối ưu và đẩy lên Cloudflare R2, trả về URL công khai.

**Request:** `multipart/form-data` — field `file`

**Response:**
```json
{ "id": "uuid", "file_url": "https://pub-xxx.r2.dev/general/..." }
```

---

### Cách 2: Presigned URL (Dùng cho ảnh/video kỷ niệm lớn)
Điện thoại tải file **thẳng lên Cloudflare R2** mà không đi qua Backend — tiết kiệm băng thông Server.

**Bước 1 — Xin link tải:** `POST /memories/{memory_id}/media/upload-url` 🔒

```json
{ "filename": "photo.jpg", "content_type": "image/jpeg", "media_type": 1 }
```
**Response:**
```json
{
  "upload_url": "https://...r2.cloudflarestorage.com/...?X-Amz-Signature=...",
  "public_url": "https://pub-xxx.r2.dev/memories/.../uuid.jpg",
  "media_id": "uuid"
}
```

**Bước 2 — Tải file:** App dùng `PUT` request đến `upload_url` (không cần token), body là binary file.

**Bước 3 — Xác nhận:** `PUT /memories/media/{media_id}/confirm` 🔒 — Báo Backend tải xong.

---

## 10. BỘ SƯU TẬP (COLLECTIONS)

Tính năng **lưu kỷ niệm vào folder** do người dùng tự tổ chức (giống như Album ảnh).

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/collections` 🔒 | Lấy danh sách bộ sưu tập của bản thân. |
| `POST` | `/collections` 🔒 | Tạo bộ sưu tập mới. |
| `GET` | `/collections/{id}/items` 🔒 | Lấy danh sách kỷ niệm trong bộ sưu tập. |
| `POST` | `/collections/{id}/items` 🔒 | Thêm kỷ niệm vào bộ sưu tập. |

**Tạo bộ sưu tập:**
```json
{ "name": "Chuyến đi Đà Lạt 2025", "description": "Mô tả...", "is_public": true }
```

---

## 11. BÁO CÁO (REPORTS)

### `POST /reports` 🔒 — Báo cáo vi phạm
Báo cáo một kỷ niệm hoặc bình luận vi phạm cộng đồng. Báo cáo được lưu với trạng thái **Chờ xử lý** để Admin duyệt sau.

**Request Body (JSON):**
```json
{
  "target_id": "uuid-của-bài-viết-hoặc-bình-luận",
  "target_type": 1,
  "reason": "Nội dung không phù hợp",
  "details": "Mô tả chi tiết lý do báo cáo..."
}
```

> `target_type`: `1` = Kỷ niệm (Memory), `2` = Bình luận (Comment)

---

## PHỤ LỤC: MÃ TRẠNG THÁI HTTP

| Mã | Ý nghĩa |
|----|---------|
| 200 | Thành công |
| 201 | Tạo mới thành công |
| 204 | Xóa thành công (không có nội dung trả về) |
| 400 | Dữ liệu gửi lên không hợp lệ |
| 401 | Chưa đăng nhập hoặc Token hết hạn |
| 403 | Không có quyền truy cập |
| 404 | Không tìm thấy tài nguyên |
| 500 | Lỗi phía Server |

## PHỤ LỤC: MÃ QUYỀN RIÊNG TƯ KỶ NIỆM

| Mã | Ý nghĩa |
|----|---------|
| `1` | **Riêng tư (Private)** — Chỉ bản thân xem được |
| `2` | **Bạn bè (Friends)** — Chỉ người follow chéo nhau |
| `3` | **Công khai (Public)** — Mọi người xem được trong 30 ngày |
