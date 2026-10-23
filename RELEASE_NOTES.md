# Học Vẹt v0.12.0

- Đổi tên ứng dụng từ Smart Operation thành Học Vẹt; đồng bộ màn hình chính, Cài đặt, Hướng dẫn, nhập dữ liệu, điều kiện chờ, thông báo lỗi và xác nhận xóa.
- Sửa luồng ghi tiếng Việt: lưu mã phím vật lý và bỏ qua phím do bộ gõ tự sinh để tránh lặp chữ / dấu. Kịch bản cũ bị lỗi cần học lại với cùng chế độ gõ.
- Xuất một kịch bản thành một file `.hocvet` nén, gồm cả ảnh mẫu; nhập thêm thành kịch bản mới, vẫn hỗ trợ JSON cũ.
- Giữ thư viện và phím tắt tại `%LOCALAPPDATA%\HocVet`, có lưu bằng file tạm và bản dự phòng `.bak`; cập nhật EXE không ghi đè thư viện.
- Thêm chờ cửa sổ phía trước hoặc ảnh / nút tại vùng chụp. Hết hạn sẽ dừng và báo lỗi; Esc vẫn dừng ngay khi đang chờ.
- Gán phím đơn / tổ hợp cho các nút, tốc độ và tùy chọn. Có ghi phím trực tiếp, chọn phạm vi Trong ứng dụng / Toàn cục và kiểm tra tổ hợp trùng nhau.
- Thanh trạng thái cố định, phím điều khiển theo ngữ cảnh, hỗ trợ cuộn, bàn phím và DPI. Phiên bản ứng dụng dùng một nguồn thông tin chung.

## Tải xuống

- `HocVet.exe`: chạy trực tiếp trên Windows, không cần Python.
- `HocVet-v0.12.0-Windows.zip`: EXE, hướng dẫn, ghi chú phát hành và giấy phép.
- `SHA256SUMS.txt`: mã SHA-256 của hai file tải xuống.

## Nâng cấp và dữ liệu

Lần đầu nâng cấp từ Smart Operation: đặt EXE cạnh `scripts_library.json` cũ trước khi mở để chuyển dữ liệu. Nếu EXE trong `dist`, ứng dụng cũng kiểm tra thư mục cha. Thư viện cũ được giữ nguyên. Gói phát hành không kèm thư viện cá nhân.

Chờ ảnh so sánh ở đúng tọa độ và DPI đã chụp; giữ nguyên bố cục khi chia sẻ kịch bản. Chưa xác minh trên mọi phần mềm HIS và bộ gõ.

## Kiểm tra

Kiểm thử core, lưu / khôi phục dữ liệu, xuất / nhập, điều kiện chờ, phím tắt và hộp thoại. Đã kiểm tra hiển thị ở tỷ lệ chữ 100% và 150% mô phỏng.
