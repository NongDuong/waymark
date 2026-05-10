# Hướng dẫn chi tiết cách lấy mã Facebook App ID và Apple Client ID

Tài liệu này hướng dẫn từng bước cụ thể giúp anh dễ dàng đăng ký, cấu hình và lấy các mã định danh của Facebook và Apple để điền vào tệp `.env`.

---

## 📘 PHẦN 1: HƯỚNG DẪN LẤY FACEBOOK APP ID (MÃ ỨNG DỤNG FACEBOOK)

Để đăng ký mã Facebook App ID, anh chỉ cần một tài khoản Facebook cá nhân thông thường (miễn phí):

### Bước 1: Truy cập Facebook Developers
* Anh truy cập trang web dành cho nhà phát triển của Facebook: [https://developers.facebook.com](https://developers.facebook.com).
* Đăng nhập bằng tài khoản Facebook của anh. Nếu là lần đầu tiên, hãy bấm nút đăng ký nhà phát triển (mất khoảng 1 phút).

### Bước 2: Tạo ứng dụng mới
* Ở góc trên bên phải trang web, bấm vào mục **My Apps** (Ứng dụng của tôi).
* Bấm vào nút màu xanh **Create App** (Tạo ứng dụng).

### Bước 3: Chọn loại ứng dụng và thiết lập thông tin
* Chọn mục **Authenticate and personalize users with Facebook Login** (Xác thực và cá nhân hóa người dùng bằng Đăng nhập Facebook) hoặc chọn **Consumer** (Người tiêu dùng). Bấm **Next**.
* Điền tên ứng dụng của anh (ví dụ: `Waymark App`).
* Nhập Email liên hệ của anh.
* Bấm nút **Create App** (Tạo ứng dụng). Hệ thống có thể yêu cầu anh nhập mật khẩu Facebook để xác minh bảo mật.

### Bước 4: Thiết lập sản phẩm "Facebook Login"
* Sau khi tạo thành công, anh sẽ được đưa tới màn hình **Dashboard** (Bảng điều khiển) của ứng dụng.
* Tìm biểu tượng **Facebook Login** và bấm nút **Set Up** (Thiết lập).
* Chọn nền tảng là **Web** (WWW).
* Nhập địa chỉ trang web của anh vào mục **Site URL**:
  * Khi chạy thử local: Nhập `http://localhost:8000/`
  * Khi chạy thực tế: Nhập domain chính thức, ví dụ: `https://waymark.vn/`
  * Bấm **Save** rồi bấm Next liên tục đến hết.

### Bước 5: Cấu hình Redirect URIs
* Ở menu bên trái, tìm mục **Facebook Login** -> chọn mục con **Settings** (Cài đặt).
* Tìm phần **Valid OAuth Redirect URIs** (URI chuyển ứng OAuth hợp lệ) và điền các địa chỉ sau:
  * `http://localhost:8000/` (cho môi trường kiểm thử máy cá nhân).
  * `https://waymark.vn/` (thay bằng tên miền thực tế của anh khi deploy).
* Bấm **Save Changes** (Lưu thay đổi) ở góc dưới.

### Bước 6: Lấy mã Facebook App ID
* Nhìn lên thanh tiêu đề trên cùng của trang web, anh sẽ thấy ngay dòng chữ **App ID** (Mã ứng dụng) gồm một chuỗi số dài (Ví dụ: `721058296315024`).
* Sao chép chuỗi số này và điền vào tệp `.env` của anh:
  ```env
  FACEBOOK_APP_ID=721058296315024
  ```

---

## 🍏 PHẦN 2: HƯỚNG DẪN LẤY APPLE CLIENT ID (MÃ DỊCH VỤ APPLE)

> [!IMPORTANT]
> Khác với Google và Facebook, để tích hợp Đăng nhập bằng Apple (Sign In with Apple) lên Website/Backend, anh **bắt buộc** phải đăng ký tài khoản **Apple Developer Program** (Tài khoản nhà phát triển trả phí của Apple, phí duy trì là 99$ / năm).

### Bước 1: Đăng nhập Apple Developer
* Anh truy cập trang quản trị tài khoản phát triển: [https://developer.apple.com/account](https://developer.apple.com/account) và đăng nhập bằng Apple ID có quyền phát triển.

### Bước 2: Tạo App ID chính (Primary App ID)
Apple yêu cầu phải có một App ID chính (thường ứng với một ứng dụng iOS gốc) thì mới cấp được Services ID cho Website:
* Chọn mục **Certificates, Identifiers & Profiles** -> chọn **Identifiers** (Định danh) ở menu trái.
* Bấm nút dấu cộng xanh **(+)** ở trên cùng để thêm mới.
* Chọn **App IDs** -> Bấm Continue.
* Chọn loại ứng dụng là **App** -> Bấm Continue.
* Điền thông tin:
  * **Description:** Mô tả ứng dụng (ví dụ: `Waymark iOS App`).
  * **Bundle ID:** Chọn loại **Explicit**, điền mã định danh dạng ngược (ví dụ: `vn.waymark.app`).
* Kéo xuống danh sách các chức năng (Capabilities) phía dưới, tìm mục **Sign In with Apple** và tích chọn chọn nó.
* Bấm **Continue** -> Bấm **Register** để hoàn tất.

### Bước 3: Tạo Services ID (Đây chính là Client ID cho Website/Backend)
* Lại bấm nút dấu cộng xanh **(+)** ở mục Identifiers.
* Lần này chọn **Services IDs** -> Bấm Continue.
* Điền thông tin:
  * **Description:** Mô tả dịch vụ (ví dụ: `Waymark Web Sign-In`).
  * **Identifier:** Mã định danh dịch vụ (ví dụ: `vn.waymark.app.signin`). **Ghi nhớ chuỗi này, đây chính là mã APPLE_CLIENT_ID cần lấy!**
* Bấm **Continue** -> Bấm **Register**.

### Bước 4: Cấu hình liên kết Services ID với Web Domain
* Nhấp chuột trực tiếp vào Services ID vừa tạo (`vn.waymark.app.signin`).
* Tích chọn ô vuông bên cạnh mục **Sign In with Apple**, sau đó bấm nút **Configure** bên cạnh.
* Một bảng cấu hình hiện lên:
  * **Primary App ID:** Chọn đúng App ID chính anh vừa tạo ở Bước 2 (`vn.waymark.app`).
  * **Web Domains:** Nhập tên miền chạy thực tế của anh (Ví dụ: `waymark.vn`). *(Apple không hỗ trợ localhost trực tiếp trong phần này trừ phi sử dụng các giải pháp như ngrok).*
  * **Return URLs:** Nhập link URL nhận dữ liệu xác thực sau đăng nhập từ Apple:
    * `https://waymark.vn/v1/auth/apple` (Hoặc trang chủ `https://waymark.vn/`).
  * Bấm **Next** -> Bấm **Done** -> Bấm **Continue** -> Bấm **Save** để lưu lại cấu hình.

### Bước 5: Điền mã Apple Client ID vào .env
* Lấy chuỗi Identifier ở Bước 3 (Ví dụ: `vn.waymark.app.signin`) điền vào file `.env`:
  ```env
  APPLE_CLIENT_ID=vn.waymark.app.signin
  ```
