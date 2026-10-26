# Học Vẹt v0.14.1

- Danh sách kịch bản dùng chữ lớn hơn, nền chọn xanh nhạt, phân biệt rõ tên và phím chạy. Hiển thị số bước và số kịch bản đã lưu ngay dưới ô chọn.
- Thêm nút đỏ **Xóa kịch bản** cạnh nút Tạo mới, dùng chung lệnh và phím tắt Xóa kịch bản. Có xác nhận trước khi xóa; chặn xóa trong lúc học / chạy và giữ lại kịch bản nếu không lưu được thư viện.
- Giữ quy tắc thư viện luôn có ít nhất một kịch bản; muốn xóa kịch bản cuối cùng, tạo kịch bản mới trước.

## Nâng cấp

Đóng phiên bản cũ rồi thay EXE hoặc giải nén gói mới. Dữ liệu và cài đặt được giữ tại `%LOCALAPPDATA%\HocVet`; không xóa thư mục này.

## Tải về

- `HocVet.exe`: chạy trực tiếp trên Windows, không cần Python.
- `HocVet-v0.14.1-Windows.zip`: ứng dụng, README, ảnh hướng dẫn và giấy phép.
- `SHA256SUMS.txt`: mã SHA256 để kiểm tra EXE và ZIP.

---

# Học Vẹt v0.14.0

- Bốn tab Chính, Chi tiết / sửa bước, Công việc riêng, Cài đặt. Bỏ thanh cuộn ở các tab; danh sách bước và phím tắt chia trang.
- Tốc độ 1× đến 10×; mỗi mức có thể gán phím.
- Bỏ thông báo Windows, chỉ dùng thông báo của ứng dụng; thêm thanh tiến độ.
- Web chạy trong Edge riêng với chuột và bàn phím ảo, tiếp tục khi đổi ứng dụng / thu vào khay. Cần cài Microsoft Edge.
- Windows / HIS: gửi thao tác nền đến ô nhập và nút chuẩn trong một cửa sổ tương thích, không chiếm chuột thật. Cửa sổ phải giữ nguyên kích thước và không thu nhỏ. Chưa hỗ trợ mọi HIS; điều khiển tùy biến / popup cần phiên Windows hoặc máy ảo riêng.
- Học, tự lưu, nhập và chia sẻ công việc trong tab bằng JSON; dữ liệu riêng với macro màn hình và được giữ khi cập nhật EXE.
- Tiết kiệm cập nhật ảnh khi không xem tab; giới hạn tốc độ xem trước và báo tiến độ; dừng có thể ngắt thời gian chờ và hủy lệnh đang đợi.
- Thêm gán phím cho các nút Công việc, sửa áp dụng lại phím Lưu / Hủy của Cài đặt.

Đã kiểm thử trình duyệt Edge trên trang mẫu cục bộ, nhập tiếng Việt vào cửa sổ Windows chuẩn mà không đổi chuột / tiêu điểm, dừng trong khi chờ, hủy lệnh đang đợi, lưu / nhập và bố cục tab. Chưa xác minh trên phần mềm HIS thực tế hay mọi bộ gõ.

Dữ liệu ở `%LOCALAPPDATA%\HocVet`; không xóa thư mục này khi thay ứng dụng. Đóng phiên bản cũ trước khi mở EXE mới.

Gói Windows: `HocVet.exe`, `HocVet-v0.14.0-Windows.zip`, `SHA256SUMS.txt`.

---

# Học Vẹt v0.13.0

- Bố cục mới theo bảng điều khiển mẫu: nền kem, tiêu đề dạng công nghiệp, thanh trượt đỏ và nút nổi vàng / xanh / đỏ. Màn hình chính còn ba bước chọn kịch bản, điều chỉnh, học/chạy; công cụ sửa bước được đưa vào phần Chi tiết.
- F8 chạy nền đi qua cùng luồng với nút Học. Có thông báo nổi 3–2–1, bắt đầu học và dừng/lưu thành công, không lấy tiêu điểm của phần mềm đang nhập.
- Phím Dừng học luôn hoạt động toàn cục. Sửa trường hợp gán phím số 2 nhưng không dừng được khi ứng dụng đang thu vào khay; hỗ trợ cả bàn phím số và chuyển cấu hình cũ tự động.
- Bỏ qua bấm/cuộn chuột trên cửa sổ Học Vẹt, gồm cú bấm nút Dừng; không đưa phím điều khiển vào kịch bản.
- Giảm vẽ lại khi ghi, cập nhật tiến độ có giới hạn, không phân tích lại phím tắt mỗi lần gõ, tránh sao chép sâu dữ liệu khi lưu.
- Phân trang danh sách bước (1.000 bước/trang), vẫn lưu đủ kịch bản và sửa đúng chỉ số thao tác gốc.
- Hủy được đếm ngược bằng F8, phím dừng hoặc Esc mà không thay đổi kịch bản cũ. Khi lưu thất bại không báo thành công; dữ liệu mới vẫn giữ trong bộ nhớ để xuất ra file.

## Nâng cấp

Dữ liệu và cài đặt vẫn ở `%LOCALAPPDATA%\HocVet`. Không xóa thư mục này khi thay EXE. Nếu gán phím số 2 để dừng học, việc nhập số 2 trong khi đang học cũng sẽ kết thúc lượt học; có thể chọn F6 hoặc tổ hợp khác nếu cần nhập số 2 trong kịch bản.

## File đóng gói

- `HocVet.exe`: file chạy Windows.
- `HocVet-v0.13.0-Windows.zip`: ứng dụng, hướng dẫn, ảnh giao diện và giấy phép.
- `SHA256SUMS.txt`: mã kiểm tra hai file trên.

Đã kiểm thử luồng đếm ngược/chạy nền, phím dừng, bỏ qua chuột trên giao diện, lưu dữ liệu, phím tắt và hiệu năng cập nhật giao diện. Chưa xác minh trực tiếp trên mọi phần mềm HIS / bộ gõ.
