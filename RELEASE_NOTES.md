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
