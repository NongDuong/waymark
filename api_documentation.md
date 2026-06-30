# WAYMARK API - TÀI LIỆU TÍCH HỢP CHI TIẾT

> **Base URL:** `https://<your-domain>/v1`  
> **Auth:** Tất cả API có 🔒 yêu cầu Header: `Authorization: Bearer <access_token>`  
> **Rate Limiting:** Hệ thống giới hạn số lượng request để chống spam. Vượt quá giới hạn sẽ nhận mã lỗi `429 Too Many Requests`.

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
12. [Thông báo & Push Notification (Firebase)](#12-thông-báo--push-notification-firebase)

> **Ký hiệu:** 🔒 = Cần Bearer Token | 🔓 = Không cần Token

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

| Field | Ràng buộc |
|-------|----------|
| `email` | Định dạng email hợp lệ, bắt buộc |
| `username` | 3–30 ký tự, bắt buộc |
| `password` | 6–128 ký tự, bắt buộc |
| `display_name` | Tối đa 50 ký tự, tùy chọn |

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
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "user_id": "uuid"
}
```

> **Lưu ý:** Từ phiên bản này, tất cả endpoint login đều trả về thêm `refresh_token` (JWT dài hạn 7 ngày). Xem mục **Làm mới Token** bên dưới.

---

### `POST /auth/google` — Đăng nhập bằng Google 🔓
Gửi `credential` (ID Token) nhận được từ Google Sign-In SDK trên App.

**Request Body (JSON):**
```json
{ "credential": "<google_id_token>" }
```
**Response 200:** Trả về JWT token tương tự login thông thường (bao gồm `access_token`, `refresh_token`, `token_type`, `user_id`).

> **Lưu ý:** Nếu email chưa tồn tại, hệ thống sẽ tự động tạo tài khoản mới và hồ sơ cá nhân kèm ảnh avatar từ Google.  
> **Bảo mật:** Khi biến môi trường `GOOGLE_CLIENT_ID` được cấu hình, server tự động xác minh chữ ký ID Token với Google. Nếu không cấu hình, token được decode mà không verify (chỉ dùng cho môi trường phát triển).

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

### `POST /auth/refresh` — Làm mới Token (Refresh)
Khi `access_token` hết hạn, gửi `refresh_token` để nhận cặp token mới mà không cần đăng nhập lại. Hệ thống áp dụng **token rotation**: mỗi lần refresh đều trả về cả `access_token` mới lẫn `refresh_token` mới.

**Request Body (JSON):**
```json
{
  "refresh_token": "eyJhbGci...<refresh_token_cũ>"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGci...<access_token_mới>",
  "refresh_token": "eyJhbGci...<refresh_token_mới>",
  "token_type": "bearer",
  "user_id": "uuid"
}
```

**Lỗi thường gặp:**
| Mã | Chi tiết |
|----|---------|
| 401 | `Refresh token expired or invalid` — Token đã hết hạn hoặc sai định dạng |
| 401 | `Invalid refresh token` — Token không phải loại refresh hoặc thiếu user ID |
| 401 | `User not found` — Tài khoản đã bị xóa |
| 400 | `Inactive user` — Tài khoản bị khóa |

> **Quy trình đề xuất cho App:**
> 1. Lưu cả `access_token` và `refresh_token` khi đăng nhập.
> 2. Khi gọi API nhận `401`, gửi `POST /auth/refresh` với `refresh_token`.
> 3. Nếu refresh thành công → cập nhật cả 2 token → gọi lại API ban đầu.
> 4. Nếu refresh thất bại (401) → chuyển về màn hình đăng nhập.

---

### `GET /auth/me` 🔒 — Lấy thông tin tài khoản hiện tại
Trả về thông tin User đang đăng nhập (không bao gồm thông tin hồ sơ chi tiết).

**Response 200:**
```json
{
  "id": "uuid",
  "username": "duongwaymark",
  "primary_email": "user@example.com",
  "is_admin": false,
  "is_vip": false,
  "created_at": "2026-01-15T08:30:00Z"
}
```

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

### `POST /auth/change-password` 🔒 — Đổi mật khẩu
Đổi mật khẩu cho tài khoản đang đăng nhập. Không áp dụng cho tài khoản đăng nhập bằng Google/Facebook/Apple (không có mật khẩu).

**Request Body (JSON):**
```json
{
  "current_password": "OldPassword123",
  "new_password": "NewPassword456"
}
```

**Response 200:**
```json
{ "message": "Đổi mật khẩu thành công." }
```

**Lỗi thường gặp:**
| Mã | Chi tiết |
|----|---------|
| 400 | `Mật khẩu hiện tại không đúng.` |
| 400 | `Mật khẩu mới phải có ít nhất 6 ký tự.` |
| 400 | `Tài khoản không sử dụng mật khẩu (đăng nhập mạng xã hội).` |

---

### `POST /auth/forgot-password` 🔓 — Quên mật khẩu
Tạo token đặt lại mật khẩu cho email đã đăng ký. Hiện tại token được trả về trực tiếp trong response để tiện tích hợp (production sẽ gửi qua email).

**Request Body (JSON):**
```json
{ "email": "user@example.com" }
```

**Response 200:**
```json
{
  "message": "Token đặt lại mật khẩu đã được tạo.",
  "reset_token": "abc123xyz...",
  "expires_in_minutes": 30
}
```

> **Lưu ý:** Nếu email không tồn tại, response vẫn trả về `200` với thông báo chung — để tránh tiết lộ email nào đã đăng ký.  
> Token có hiệu lực **30 phút** và chỉ dùng được **một lần**.  
> **Bảo mật:** Token được lưu dưới dạng hash SHA-256 trong DB, không lưu plaintext — an toàn ngay cả khi DB bị lộ.

---

### `POST /auth/reset-password` 🔓 — Đặt lại mật khẩu
Sử dụng token nhận từ `forgot-password` để đặt mật khẩu mới.

**Request Body (JSON):**
```json
{
  "token": "abc123xyz...",
  "new_password": "NewPassword789"
}
```

**Response 200:**
```json
{ "message": "Đặt lại mật khẩu thành công." }
```

**Lỗi thường gặp:**
| Mã | Chi tiết |
|----|---------|
| 400 | `Token không hợp lệ.` |
| 400 | `Token đã được sử dụng.` |
| 400 | `Token đã hết hạn.` |
| 400 | `Mật khẩu mới phải có ít nhất 6 ký tự.` |

---

### `POST /auth/device-token` 🔒 — Lưu FCM Device Token
Lưu FCM registration token của thiết bị để nhận push notification. Gọi API này ngay sau khi đăng nhập thành công và mỗi khi FCM SDK cấp token mới. Một user có thể có nhiều token (nhiều thiết bị).

**Request Body (JSON):**
```json
{
  "token": "fMtY8k3Ps0c:APA91bH...",
  "platform": "android"
}
```

| Field | Type | Mô tả |
|-------|------|-------|
| `token` | string | FCM registration token từ Firebase SDK (bắt buộc) |
| `platform` | string | `ios` / `android` / `web` (tùy chọn) |

**Response 200:**
```json
{ "message": "Device token đã được lưu." }
```

> **Quy trình đề xuất:**
> 1. Lấy FCM token từ Firebase SDK (`getToken()`).
> 2. Gọi `POST /auth/device-token` ngay sau đăng nhập.
> 3. Lắng nghe sự kiện `onTokenRefresh` của Firebase SDK → gọi lại API khi token thay đổi.
> 4. Khi logout, gọi `POST /auth/logout` với `device_token` để xóa thiết bị khỏi danh sách nhận thông báo.

---

### `POST /auth/logout` 🔒 — Đăng xuất

Xóa FCM device token của thiết bị hiện tại khỏi DB. Sau khi gọi API này, thiết bị đó sẽ không nhận push notification nữa.

**Request Body (JSON):**
```json
{
  "device_token": "fMtY8k3Ps0c:APA91bH..."
}
```

| Field | Bắt buộc | Mô tả |
|-------|----------|-------|
| `device_token` | ❌ | FCM token của thiết bị muốn xóa. Nếu không truyền, chỉ logout phiên làm việc, không xóa token nào. |

**Response 200:**
```json
{ "message": "Đăng xuất thành công." }
```

> **Lưu ý:** JWT access token vẫn tồn tại đến khi hết hạn (server không có blacklist JWT). Client cần tự xóa token khỏi bộ nhớ cục bộ.

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

### `GET /map/pins` 🔓🔒 — Lấy ghim kỷ niệm xung quanh
**Mục đích:** Dùng cho màn hình **Bản đồ chính** của App. Hỗ trợ cả khách chưa đăng nhập lẫn người dùng đã đăng nhập.

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|---------|-------|
| `lat` | float | **Bắt buộc** | Vĩ độ trung tâm |
| `lng` | float | **Bắt buộc** | Kinh độ trung tâm |
| `radius` | float | 1000 | Bán kính (mét) |

**Quy tắc hiển thị — Chưa đăng nhập (không gửi token):**
- ✅ Kỷ niệm **công khai** (`privacy_level=3`) còn trong hạn hiển thị 30 ngày

**Quy tắc hiển thị — Đã đăng nhập (gửi Bearer token):**
- ✅ Kỷ niệm của **bạn bè** (chế độ bạn bè + công khai)
- ✅ Kỷ niệm **công khai** của người lạ (còn hạn hiển thị 30 ngày)
- ❌ Kỷ niệm của người đã **chặn nhau**
- ❌ Kỷ niệm của chính user (lấy riêng qua Profile API)

**Trả về tối đa:** 100 ghim.

---

## 4. KỶ NIỆM (MEMORIES)

### `POST /memories` 🔒 — Tạo kỷ niệm mới
Dùng `multipart/form-data` vì có thể kèm theo ảnh.

**Request Fields:**
| Field | Type | Mô tả |
|-------|------|-------|
| `caption` | string | Nội dung kỷ niệm, 1–2000 ký tự (bắt buộc) |
| `lat` | float | Vĩ độ (bắt buộc) |
| `lng` | float | Kinh độ (bắt buộc) |
| `privacy_level` | int | **1**=Riêng tư, **2**=Bạn bè, **3**=Công khai (mặc định 3). Chỉ chấp nhận 1, 2, hoặc 3 — giá trị khác trả về 400. |
| `mood_code` | string | Trạng thái cảm xúc (tùy chọn) |
| `place_id` | UUID | ID địa điểm từ hệ thống Places (tùy chọn) |
| `images` | File[] | Danh sách ảnh đính kèm, tối đa 10 ảnh (tùy chọn). Xem giới hạn bên dưới. |

**Giới hạn ảnh đính kèm:**
- **Số lượng:** Tối đa **10 ảnh** mỗi kỷ niệm — quá giới hạn → `400`
- **Định dạng hỗ trợ:** JPEG, JPG, PNG, WebP, GIF, HEIC, HEIF — sai định dạng → `400`
- **Kích thước tối đa mỗi file:** 50MB — quá lớn → `413`

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
| `DELETE` | `/comments/{comment_id}` 🔒 | Xóa bình luận (chủ bình luận hoặc chủ bài đăng). Áp dụng **soft delete** — bình luận bị ẩn, không xóa vật lý khỏi DB. |
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
| `GET` | `/followers` 🔒 | Danh sách người đang theo dõi mình (có phân trang). |
| `GET` | `/following` 🔒 | Danh sách người mình đang theo dõi (có phân trang). |
| `GET` | `/friends` 🔒 | Danh sách bạn bè (follow chéo lẫn nhau, có phân trang). |

**Body cho Follow:**
```json
{ "target_user_id": "uuid-của-người-muốn-follow" }
```

**Query Parameters cho GET /followers, /following, /friends:**
| Param | Type | Mặc định | Mô tả |
|-------|------|---------|-------|
| `limit` | int | 50 | Số lượng trả về (tối đa 100) |
| `offset` | int | 0 | Bỏ qua N bản ghi đầu (phân trang offset) |

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

### 8.1 Tổng quan Kiến trúc Chat

Hệ thống chat sử dụng kiến trúc **kết hợp REST + WebSocket**:
- **REST API** để tạo cuộc hội thoại, gửi tin nhắn, lấy lịch sử → đảm bảo logic nghiệp vụ tập trung.
- **WebSocket** để nhận tin nhắn thời gian thực → App không cần polling.

**Luồng hoạt động cơ bản:**
1. App kết nối WebSocket khi khởi động (dùng `access_token`).
2. Khi user gửi tin nhắn, App gọi `POST /conversations/{id}/messages`.
3. Server lưu tin nhắn vào DB → đẩy payload qua WebSocket đến **tất cả thành viên** (kể cả người gửi trên thiết bị khác).
4. App nhận payload WebSocket → hiển thị tin nhắn mới ngay lập tức.

> Hệ thống hỗ trợ **multi-device**: Cùng một user có thể kết nối WebSocket từ nhiều thiết bị, tất cả đều nhận tin.

---

### 8.2 Kết nối WebSocket — Nhận tin nhắn thời gian thực

**URL kết nối:**
```
wss://<your-domain>/v1/conversations/ws/<access_token>
```

**Hướng dẫn chi tiết:**

| Bước | Mô tả |
|------|-------|
| 1. Kết nối | Gửi WebSocket handshake đến URL trên. Server sẽ verify JWT token từ URL path. |
| 2. Xác thực | Nếu token hợp lệ → server accept kết nối. Nếu không → server đóng kết nối với code `1008 (Policy Violation)`. |
| 3. Lắng nghe | Sau khi kết nối, App chỉ cần **lắng nghe** (receive). Không cần gửi gì qua WebSocket. |
| 4. Xử lý ngắt | Khi mất kết nối, App nên tự động reconnect sau 2-5 giây (exponential backoff). |

**Payload nhận được khi có tin nhắn mới:**
```json
{
  "type": "new_message",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": {
    "id": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",
    "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "sender_user_id": "11111111-2222-3333-4444-555555555555",
    "message_type": 1,
    "text_content": "Xin chào bạn!",
    "media_id": null,
    "media_url": null,
    "reply_to_message_id": null,
    "sent_at": "2026-05-22T10:30:00Z"
  }
}
```

**Các trường trong `message`:**
| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | UUID | ID duy nhất của tin nhắn |
| `conversation_id` | UUID | Cuộc hội thoại chứa tin nhắn |
| `sender_user_id` | UUID | Người gửi |
| `message_type` | int | `1` = Văn bản, `2` = Hình ảnh |
| `text_content` | string\|null | Nội dung text (null nếu là ảnh) |
| `media_id` | UUID\|null | ID media đính kèm |
| `media_url` | string\|null | URL trực tiếp tới media (đã signed) |
| `reply_to_message_id` | UUID\|null | ID tin nhắn đang reply (null nếu không reply) |
| `sent_at` | datetime | Thời điểm gửi (UTC) |

> **Xử lý reconnect khuyến nghị:** Khi WebSocket bị ngắt, App nên:
> 1. Reconnect với backoff: 2s → 4s → 8s → 16s (tối đa 30s).
> 2. Sau khi reconnect, gọi `GET /conversations` để kiểm tra tin nhắn bị lỡ.
> 3. So sánh `last_message_id` của mỗi cuộc hội thoại với tin nhắn cuối cùng App đã nhận.

---

### 8.3 `GET /conversations` 🔒 — Danh sách cuộc hội thoại

Trả về tất cả cuộc hội thoại mà user đang tham gia, sắp xếp theo thời gian cập nhật mới nhất. Tự động **ẩn** cuộc hội thoại với người đã chặn.

**Response 200:**
```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "conversation_type": 1,
    "created_by": "uuid",
    "title": "Dương Waymark",
    "last_message_id": "uuid",
    "created_at": "2026-05-20T08:00:00Z",
    "updated_at": "2026-05-22T10:30:00Z",
    "is_pending": false,
    "is_existing": false,
    "other_user_id": "uuid-đối-phương",
    "other_user_username": "duongwaymark",
    "other_user_display_name": "Dương Waymark",
    "other_user_avatar_url": "https://pub-xxx.r2.dev/avatars/...",
    "last_message_text": "Xin chào bạn!",
    "last_message_sender_id": "uuid-người-gửi-cuối"
  }
]
```

**Giải thích các trường quan trọng:**
| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `conversation_type` | int | `1` = Chat riêng tư (direct, 2 người), `2` = Nhóm (group) |
| `is_pending` | bool | `true` nếu đây là cuộc hội thoại direct mà hai người **chưa follow chéo nhau** (giống "Message Request" của Instagram). App có thể hiển thị riêng tab "Tin nhắn chờ". |
| `is_existing` | bool | `true` nếu cuộc hội thoại này đã tồn tại trước đó khi gọi API tạo cuộc hội thoại (chỉ có ý nghĩa khi gọi `POST /conversations`). |
| `other_user_*` | | Thông tin đối phương (chỉ có ở chat direct `conversation_type=1`). Bao gồm ID, username, tên hiển thị, avatar. |
| `title` | string\|null | Với chat direct: tự động lấy tên đối phương. Với chat nhóm: tiêu đề do người tạo đặt. |
| `last_message_text` | string\|null | Nội dung tin nhắn cuối cùng. Nếu là ảnh → hiển thị `"[Hình ảnh]"`. |
| `last_message_sender_id` | UUID\|null | ID người gửi tin nhắn cuối — App dùng để hiển thị "Bạn: ..." hay tên người khác. |

---

### 8.4 `POST /conversations` 🔒 — Tạo cuộc hội thoại mới

Tạo cuộc hội thoại riêng tư hoặc nhóm. Người tạo tự động được thêm làm thành viên.

> **Lưu ý kiểm tra trùng lặp (Deduplication):**
> Đối với cuộc hội thoại trực tiếp (`conversation_type = 1`), hệ thống sẽ kiểm tra xem đã tồn tại cuộc hội thoại trực tiếp nào giữa hai người dùng này chưa trước khi tạo bản ghi mới.
> - Nếu **đã tồn tại**, API trả về thông tin cuộc hội thoại cũ kèm trường `"is_existing": true` trong response body.
> - Nếu **chưa tồn tại**, hệ thống sẽ tạo cuộc hội thoại mới và trả về với `"is_existing": false`.

**Request Body (JSON):**
```json
{
  "participant_user_ids": ["uuid-người-nhận"],
  "title": null,
  "conversation_type": 1
}
```

**Quy tắc:**
| Điều kiện | Kết quả |
|-----------|---------|
| `participant_user_ids` có **1 người** | Tạo/lấy chat **riêng tư (direct)**, `conversation_type` tự động = `1` |
| `participant_user_ids` có **nhiều người** | Tạo chat **nhóm (group)**, `conversation_type` tự động = `2` |
| `title` | Tùy chọn. Chỉ có ý nghĩa với chat nhóm. Chat direct tự lấy tên đối phương. |

**Response 201:** Trả về object `ConversationResponse` tương tự như `GET /conversations` (1 phần tử).

```json
{
  "id": "uuid-mới-hoặc-đã-có",
  "conversation_type": 1,
  "created_by": "uuid-người-tạo",
  "title": "Dương Waymark",
  "last_message_id": null,
  "created_at": "2026-05-22T10:30:00Z",
  "updated_at": "2026-05-22T10:30:00Z",
  "is_pending": true,
  "is_existing": false,
  "other_user_id": "uuid-đối-phương",
  "other_user_username": "duongwaymark",
  "other_user_display_name": "Dương Waymark",
  "other_user_avatar_url": "https://pub-xxx.r2.dev/avatars/...",
  "last_message_text": null,
  "last_message_sender_id": null
}
```

---

### 8.5 `GET /conversations/{conversation_id}/messages` 🔒 — Lấy lịch sử tin nhắn

Trả về danh sách tin nhắn trong cuộc hội thoại, **mới nhất trước** (sắp xếp giảm dần theo `sent_at`). Chỉ thành viên cuộc hội thoại mới truy cập được.

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|---------|-------|
| `limit` | int | 30 | Số lượng tin nhắn trả về (tối đa 100) |
| `before_id` | uuid | - | Lấy tin nhắn cũ hơn tin nhắn có ID này (cursor-based pagination) |

**Response 200:**
```json
[
  {
    "id": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",
    "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "sender_user_id": "11111111-2222-3333-4444-555555555555",
    "message_type": 1,
    "text_content": "Xin chào bạn!",
    "media_id": null,
    "media_url": null,
    "reply_to_message_id": null,
    "sent_at": "2026-05-22T10:30:00Z"
  },
  {
    "id": "a2b3c4d5-e6f7-8901-abcd-ef2345678901",
    "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "sender_user_id": "22222222-3333-4444-5555-666666666666",
    "message_type": 2,
    "text_content": null,
    "media_id": "uuid-media",
    "media_url": "https://pub-xxx.r2.dev/general/uuid-media.webp",
    "reply_to_message_id": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",
    "sent_at": "2026-05-22T10:31:00Z"
  }
]
```

**Lỗi thường gặp:**
| Mã | Chi tiết |
|----|---------|
| 403 | `Not a participant of this conversation` — User không phải thành viên |

> **Phân trang (cursor-based):**
> - Lần đầu mở hội thoại: `GET /messages?limit=30` → nhận 30 tin mới nhất
> - Khi user scroll lên muốn load thêm: lấy `id` của tin nhắn **cũ nhất** trong danh sách hiện tại làm `before_id`
> - `GET /messages?limit=30&before_id=<id-tin-cũ-nhất>` → nhận 30 tin cũ hơn
> - Nếu trả về ít hơn `limit` → đã hết tin nhắn

---

### 8.6 `POST /conversations/{conversation_id}/messages` 🔒 — Gửi tin nhắn

Gửi tin nhắn mới vào cuộc hội thoại. Sau khi lưu, server tự động:
1. Cập nhật `last_message_id` và `updated_at` của cuộc hội thoại.
2. Đẩy payload qua **WebSocket** đến tất cả thành viên đang online.

**Request Body (JSON):**
```json
{
  "text_content": "Nội dung tin nhắn",
  "media_id": null,
  "reply_to_message_id": null
}
```

**Các trường Request:**
| Trường | Kiểu | Bắt buộc | Mô tả |
|--------|------|----------|-------|
| `text_content` | string\|null | Có* | Nội dung text. Bắt buộc nếu không có `media_id`. |
| `media_id` | UUID\|null | Không | ID media đã upload trước đó (dùng `POST /media/upload`). Nếu có → `message_type` tự động = `2`. |
| `reply_to_message_id` | UUID\|null | Không | ID tin nhắn muốn reply. App có thể hiển thị tin nhắn gốc dạng quote. |

> \* Ít nhất phải có `text_content` hoặc `media_id`.

**Response 200:**
```json
{
  "id": "uuid-tin-nhắn-mới",
  "conversation_id": "uuid",
  "sender_user_id": "uuid-của-bạn",
  "message_type": 1,
  "text_content": "Nội dung tin nhắn",
  "media_id": null,
  "media_url": null,
  "reply_to_message_id": null,
  "sent_at": "2026-05-22T10:35:00Z"
}
```

**Lỗi thường gặp:**
| Mã | Chi tiết |
|----|---------|
| 403 | `Not a participant of this conversation` — User không phải thành viên |
| 403 | `Bạn không thể gửi tin nhắn cho người dùng này do có thiết lập chặn.` — Đã chặn hoặc bị chặn (chỉ chat direct) |

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

## 12. THÔNG BÁO & PUSH NOTIFICATION (FIREBASE)

Waymark sử dụng **Firebase Cloud Messaging (FCM)** để gửi push notification tới thiết bị di động. Hệ thống hoạt động theo luồng sau:

```
User A like/comment/follow
        ↓
  API Server lưu Notification vào DB
        ↓
  Celery Worker gửi FCM qua Firebase Admin SDK
        ↓
  Thiết bị của User B nhận push notification
```

---

### 12.1 Đăng ký nhận thông báo — Lưu Device Token

> Đã có ở Section Auth: `POST /auth/device-token` 🔒

Gọi API này **ngay sau khi đăng nhập** để đăng ký thiết bị nhận push notification.

**Request Body (JSON):**
```json
{
  "token": "fMtY8k3Ps0c:APA91bH...",
  "platform": "android"
}
```

| Field | Bắt buộc | Mô tả |
|-------|----------|-------|
| `token` | ✅ | FCM registration token lấy từ `FirebaseMessaging.getInstance().getToken()` |
| `platform` | ❌ | `ios` / `android` / `web` |

**Response 200:**
```json
{ "message": "Device token đã được lưu." }
```

> **Quan trọng:** Lắng nghe sự kiện `onTokenRefresh` của Firebase SDK và gọi lại API này khi token thay đổi để đảm bảo không mất thông báo.

---

### 12.2 Các loại thông báo (notification_type)

| Giá trị | Loại | Khi nào kích hoạt | Tiêu đề FCM |
|---------|------|-------------------|-------------|
| `1` | Like | Ai đó thích kỷ niệm của bạn | "Lượt thích mới" |
| `2` | Comment | Ai đó bình luận về kỷ niệm của bạn | "Bình luận mới" |
| `3` | Follow | Ai đó theo dõi bạn | "Người theo dõi mới" |
| `4` | Chat | Tin nhắn mới trong hội thoại | "Tin nhắn mới" |

**Payload FCM nhận được trên thiết bị:**
```json
{
  "notification": {
    "title": "Lượt thích mới",
    "body": "Dương Waymark đã thích kỷ niệm của bạn."
  },
  "data": {
    "notification_type": "1",
    "reference_id": "<uuid-của-memory>",
    "sender_id": "<uuid-của-người-gửi>"
  }
}
```

> Dùng trường `data.notification_type` và `data.reference_id` để điều hướng người dùng đến đúng màn hình khi tap vào thông báo.

---

### 12.3 `GET /notifications` 🔒 — Lấy danh sách thông báo

Trả về danh sách thông báo, **mới nhất trước**, hỗ trợ cursor-based pagination.

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|---------|-------|
| `limit` | int | 20 | Số lượng trả về (tối đa 50) |
| `before_id` | uuid | - | Lấy thông báo cũ hơn thông báo có ID này |

> **Phân trang:** Lần đầu gọi không cần `before_id`. Khi load thêm, truyền `id` của thông báo **cũ nhất** đang hiển thị vào `before_id`. Nếu trả về ít hơn `limit` → đã hết.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "sender_id": "uuid",
    "sender_username": "duong123",
    "sender_display_name": "Dương Waymark",
    "sender_avatar_url": "https://pub-xxx.r2.dev/avatars/...",
    "notification_type": 1,
    "message": "Dương Waymark đã thích kỷ niệm của bạn.",
    "reference_id": "uuid-của-memory",
    "is_read": false,
    "created_at": "2026-06-26T10:30:00Z"
  }
]
```

---

### 12.4 `POST /notifications/{notification_id}/read` 🔒 — Đánh dấu đã đọc

Đánh dấu một thông báo cụ thể là đã đọc.

**Response 200:**
```json
{ "message": "Notification marked as read" }
```

---

### 12.5 `POST /notifications/read-all` 🔒 — Đánh dấu tất cả đã đọc

Đánh dấu toàn bộ thông báo chưa đọc của user là đã đọc.

**Response 200:**
```json
{ "message": "All notifications marked as read" }
```

---

### 12.6 Quy trình tích hợp FCM cho Mobile App

**Bước 1 — Khởi tạo Firebase SDK** (chỉ làm một lần khi app khởi động):
```dart
// Flutter
await Firebase.initializeApp();
String? token = await FirebaseMessaging.instance.getToken();
```

**Bước 2 — Gửi token lên server** (sau mỗi lần đăng nhập):
```dart
await api.post('/v1/auth/device-token', {
  'token': token,
  'platform': 'android', // hoặc 'ios'
});
```

**Bước 3 — Lắng nghe token refresh**:
```dart
FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
  api.post('/v1/auth/device-token', {'token': newToken, 'platform': 'android'});
});
```

**Bước 4 — Xử lý notification khi app foreground**:
```dart
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  final type = message.data['notification_type'];
  final refId = message.data['reference_id'];
  // Điều hướng theo type: 1=memory, 2=memory, 3=profile, 4=chat
});
```

**Bước 5 — Logout: xóa device token**:
```dart
// Trước khi clear local storage / JWT
await api.post('/v1/auth/logout', {
  'device_token': currentFcmToken,
});
// Sau đó xóa JWT khỏi local storage
```

---

## PHỤ LỤC: RATE LIMITING (CHỐNG SPAM)

Hệ thống giới hạn request dựa trên **IP** (auth) hoặc **User ID** (social/chat/content).

| Endpoint | Giới hạn | Theo |
|----------|---------|------|
| `POST /auth/signup/email` | 5 lần / giờ | IP |
| `POST /auth/login/password` | 10 lần / phút | IP |
| `POST /auth/forgot-password` | 3 lần / giờ | IP |
| `POST /memories/{id}/likes` | 200 lần / giờ | User |
| `POST /memories/{id}/comments` | 30 lần / giờ | User |
| `POST /users/follow` | 50 lần / giờ | User |
| `POST /conversations/{id}/messages` | 30 lần / phút | User |
| `POST /memories` | 20 lần / 24 giờ | User |

**Khi vượt giới hạn — Response `429`:**
```json
{
  "detail": "Quá nhiều yêu cầu. Vui lòng thử lại sau 60 giây."
}
```

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
| 429 | Quá nhiều yêu cầu (Rate Limit) |
| 500 | Lỗi phía Server |

## PHỤ LỤC: MÃ QUYỀN RIÊNG TƯ KỶ NIỆM

| Mã | Ý nghĩa |
|----|---------|
| `1` | **Riêng tư (Private)** — Chỉ bản thân xem được |
| `2` | **Bạn bè (Friends)** — Chỉ người follow chéo nhau |
| `3` | **Công khai (Public)** — Mọi người xem được trong 30 ngày |
