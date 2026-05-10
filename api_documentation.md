# TÀI LIỆU API HỆ THỐNG WAYMARK (API DOCUMENTATION)

Tài liệu này được biên soạn chi tiết, trực quan và dễ hiểu nhất dành cho các lập trình viên ứng dụng di động (Mobile App - iOS/Android) hoặc Frontend để tích hợp toàn bộ tính năng của mạng xã hội bản đồ ký ức **Waymark**.

---

## 🔒 QUY CHUẨN CHUNG (GENERAL STANDARDS)

### 1. Base URL (Đường dẫn gốc):
* **Localhost Development:** `http://localhost:8000/v1`
* **Production API:** `https://api.waymark.vn/v1`

### 2. Định dạng dữ liệu:
* Tất cả các API trao đổi dữ liệu qua định dạng **JSON** (`Content-Type: application/json`).

### 3. Xác thực người dùng (Authentication Header):
Đối với các API yêu cầu đăng nhập, lập trình viên phía App cần gửi Token xác thực dạng **JWT** trong Header của HTTP Request:
```http
Authorization: Bearer <access_token_nhận_được_khi_đăng_nhập>
```

---

## 🔑 CHƯƠNG I: XÁC THỰC NGƯỜI DÙNG (AUTHENTICATION)

### 1. Đăng ký tài khoản bằng Email (`POST /auth/signup/email`)
* **Mô tả:** Đăng ký tài khoản mới và tự động khởi tạo Hồ sơ cá nhân.
* **Request Body:**
```json
{
  "email": "user@example.com",
  "username": "duongwaymark",
  "password": "SecurePassword123",
  "display_name": "Dương Waymark"
}
```
* **Phản hồi thành công (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

---

### 2. Đăng nhập bằng Email & Mật khẩu (`POST /auth/login/email`)
* **Mô tả:** Đăng nhập lấy Token xác thực JWT.
* **Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```
* **Phản hồi thành công (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

---

### 3. Đăng nhập bằng Google (`POST /auth/google`)
* **Mô tả:** Đăng nhập thông qua Token do SDK Google trên App trả về.
* **Request Body:**
```json
{
  "credential": "id_token_tu_google_sdk"
}
```
* **Phản hồi thành công (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

---

### 4. Đăng nhập bằng Facebook (`POST /auth/facebook`)
* **Mô tả:** Đăng nhập thông qua Access Token do SDK Facebook trên App trả về.
* **Request Body:**
```json
{
  "access_token": "access_token_tu_facebook_sdk"
}
```
* **Phản hồi thành công (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

---

### 5. Đăng nhập bằng Apple (`POST /auth/apple`)
* **Mô tả:** Đăng nhập thông qua Identity Token do Apple Sign-In trên thiết bị iOS trả về.
* **Request Body:**
```json
{
  "id_token": "identity_token_tu_apple_sdk",
  "display_name": "Dương Nguyễn" 
}
```
* **Phản hồi thành công (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer"
}
```

---

## 🗺️ CHƯƠNG II: QUẢN LÝ KỶ NIỆM BẢN ĐỒ (MEMORIES)

### 1. Tạo mới Kỷ niệm (`POST /memories`)
* **Yêu cầu đăng nhập:** Có.
* **Mô tả:** Lưu lại một kỷ niệm kèm vị trí tọa độ địa lý (GPS) và mức độ riêng tư.
* **Request Body:**
```json
{
  "title": "Chuyến phượt đèo Mã Pí Lèng",
  "caption": "Cảm giác đứng giữa mây trời thật tuyệt vời!",
  "latitude": 23.2524,
  "longitude": 105.4194,
  "privacy_level": 1, 
  "place_id": "ma_pi_leng_place_id",
  "media_urls": [
    "https://cdn.waymark.vn/media/mapileng1.jpg",
    "https://cdn.waymark.vn/media/mapileng2.jpg"
  ]
}
```
> [!NOTE]
> `privacy_level`: `0` (Chỉ mình tôi), `1` (Công khai), `2` (Chỉ bạn bè - Mutual Follows).

* **Phản hồi thành công (200 OK):**
```json
{
  "id": "memory_12345",
  "title": "Chuyến phượt đèo Mã Pí Lèng",
  "caption": "Cảm giác đứng giữa mây trời thật tuyệt vời!",
  "latitude": 23.2524,
  "longitude": 105.4194,
  "privacy_level": 1,
  "user_id": "user_abc",
  "media_urls": ["..."],
  "created_at": "2026-05-09T15:00:00Z"
}
```

---

### 2. Lấy thông tin chi tiết một Kỷ niệm (`GET /memories/{memory_id}`)
* **Yêu cầu đăng nhập:** Có.
* **Mô tả:** Xem chi tiết kỷ niệm. API này đã được tích hợp cơ chế bảo mật **Anti-IDOR**: Hệ thống tự động chặn `403 Forbidden` nếu người xem bị chủ sở hữu Block hoặc kỷ niệm được cài đặt riêng tư mà người xem chưa kết bạn.
* **Phản hồi thành công (200 OK):** Trả về đầy đủ thông tin kỷ niệm, danh sách bình luận và số lượt thích.

---

### 3. Xóa Kỷ niệm (`DELETE /memories/{memory_id}`)
* **Yêu cầu đăng nhập:** Có.
* **Phản hồi thành công:** `204 No Content`.

---

## 👥 CHƯƠNG III: MẠNG XÃ HỘI & TƯƠNG TÁC (SOCIAL INTERACTION)

### 1. Theo dõi người dùng (Follow) (`POST /users/follow`)
* **Yêu cầu đăng nhập:** Có.
* **Request Body:**
```json
{
  "target_user_id": "id_nguoi_muon_follow"
}
```
* **Mô tả:** Gửi yêu cầu follow. Nếu cả 2 cùng follow chéo nhau, hệ thống sẽ tự động xác lập quan hệ **Bạn bè (Friends)** và cho phép xem các Kỷ niệm bảo mật cấp độ bạn bè (`privacy_level = 2`).

---

### 2. Chặn người dùng (Block) (`POST /users/{user_id}/block`)
* **Yêu cầu đăng nhập:** Có.
* **Mô tả:** Chặn hoàn toàn một người dùng. Sau khi chặn:
  * Người bị chặn không thể xem bất cứ kỷ niệm nào của anh (ngay cả kỷ niệm Public).
  * Người bị chặn không thể nhắn tin hay tìm thấy tài khoản của anh.

---

### 3. Thích / Bỏ Thích Kỷ niệm (`POST` hoặc `DELETE` `/memories/{memory_id}/likes`)
* **Yêu cầu đăng nhập:** Có.
* **Mô tả:** Tương tác thích/bỏ thích bài viết kỷ niệm.

---

### 4. Viết Bình luận / Phản hồi (`POST /memories/{memory_id}/comments`)
* **Yêu cầu đăng nhập:** Có.
* **Mô tả:** Viết bình luận trực tiếp hoặc phản hồi (Reply) bình luận của người khác.
* **Request Body:**
```json
{
  "content": "Tuyệt vời quá anh ơi!",
  "parent_id": null 
}
```
> [!TIP]
> Nếu là bình luận chính: truyền `parent_id = null`. Nếu là phản hồi bình luận khác: truyền `parent_id` là ID của bình luận cha.

---

### 5. Danh sách Bạn bè / Người theo dõi (`GET /friends`, `GET /followers`, `GET /following`)
* **Yêu cầu đăng nhập:** Có.
* **Mô tả:** Trả về danh sách người dùng tương ứng gồm: ID, Tên hiển thị, Ảnh đại diện, Trạng thái hoạt động.

---

## 💬 CHƯƠNG IV: CHAT THỜI GIAN THỰC (REAL-TIME CHAT)

Ứng dụng sử dụng kết nối **WebSocket** để đảm bảo tin nhắn được truyền nhận siêu tốc với độ trễ cực thấp.

### 1. Kết nối kênh truyền nhận tin nhắn (`WS /v1/chat/ws/{token}`)
* **Mô tả:** Lập trình viên App thiết lập kết nối WebSocket tới địa chỉ này kèm theo JWT Token xác thực.
* **Mẫu định dạng tin nhắn gửi qua Socket (JSON):**
```json
{
  "recipient_id": "user_id_nhan",
  "content": "Chào bạn, mình kết bạn nhé!"
}
```

### 2. Danh sách các cuộc hội thoại (`GET /chat`)
* **Yêu cầu đăng nhập:** Có.
* **Mô tả:** Lấy danh sách hộp thư đến hiển thị trên màn hình Inbox của App (gồm tin nhắn cuối cùng, thông tin người chat cùng và số tin nhắn chưa đọc).

### 3. Lấy nội dung tin nhắn trong cuộc hội thoại (`GET /chat/{conversation_id}/messages`)
* **Yêu cầu đăng nhập:** Có.
* **Mô tả:** Lấy lịch sử chat giữa 2 người (hỗ trợ phân trang cuộn mượt).

---

## 📍 CHƯƠNG V: KHÁM PHÁ & BẢN ĐỒ (GEO-DISCOVERY)

### 1. Khám phá các Kỷ niệm xung quanh (`GET /discovery/trending/nearby`)
* **Yêu cầu đăng nhập:** Có.
* **Tham số Truy vấn (Query Parameters):**
  * `lat` (Tọa độ Vĩ độ hiện tại của người dùng)
  * `lon` (Tọa độ Kinh độ hiện tại của người dùng)
  * `radius` (Bán kính tìm kiếm, tính bằng mét. Mặc định `5000` tức là 5km)
* **Mô tả:** Trả về toàn bộ danh sách kỷ niệm xung quanh vị trí người dùng để vẽ các ghim (Marker) lên Bản đồ di động.

### 2. Gom nhóm các Kỷ niệm dày đặc (`GET /discovery/clusters`)
* **Mô tả:** Trả về danh sách các cụm ghim tập trung đông đảo ký ức của cộng đồng giúp App hiển thị tính năng "Cụm ghim" (Clustering) vô cùng chuyên nghiệp.

---

## 🖼️ CHƯƠNG VI: TẢI LÊN MULTIMEDIA (MEDIA UPLOAD)

### 1. Upload ảnh/video kỷ niệm hoặc Avatar (`POST /media/upload`)
* **Yêu cầu đăng nhập:** Có.
* **Định dạng dữ liệu gửi đi:** `multipart/form-data`
* **Mô tả:** Tải ảnh lên vùng lưu trữ đám mây tốc độ cao **Cloudflare R2** của hệ thống Waymark.
* **Phản hồi thành công (200 OK):**
```json
{
  "media_url": "https://pub-waymark.r2.dev/3fa85f64-5717-4562-b3fc-2c963f66afa6.png"
}
```
Lập trình viên App sẽ lấy đường dẫn `media_url` này để gắn vào API Tạo kỷ niệm hoặc Cập nhật hồ sơ cá nhân.
