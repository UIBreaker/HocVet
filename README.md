# Học Vẹt · v0.12.0

Trợ lý ghi và phát lại thao tác chuột / bàn phím trên Windows, dành cho công việc văn phòng và phần mềm HIS.

**Tác giả:** Nhật Nam ([@UIBreaker](https://github.com/UIBreaker)) · **Giấy phép:** [MIT](LICENSE)

## Tải và chạy

Tải **HocVet.exe** hoặc **HocVet-v0.12.0-Windows.zip** tại [GitHub Releases](https://github.com/UIBreaker/Smart_Operation/releases/latest). Bản đóng gói không cần cài Python. Giao diện hiển thị tên **Học Vẹt**; kho mã vẫn dùng địa chỉ Smart_Operation.

Khi nâng cấp từ Smart Operation, đặt ứng dụng cạnh `scripts_library.json` cũ trước lần mở đầu tiên. Nếu chạy từ thư mục `dist`, ứng dụng cũng kiểm tra thư mục cha. File cũ được giữ nguyên. Từ lần sau có thể thay / di chuyển file ứng dụng mà vẫn giữ thư viện.

![Giao diện Học Vẹt](docs/images/main.png)

## Sử dụng nhanh

1. Tạo hoặc chọn kịch bản, nhấn **F8** để học thao tác. Làm các bước trên phần mềm đích, nhấn lại **F8** để dừng và lưu.
2. Chọn **Chạy** hoặc dùng phím riêng của kịch bản (mặc định mẫu: **F9**). Nhấn **Esc** để dừng khẩn cấp, kể cả trong khi chờ điều kiện.
3. Chọn một dòng, dùng **+ Chờ cửa sổ** / **+ Chờ ảnh / nút** để chèn điều kiện trước dòng đó; không chọn dòng sẽ thêm ở cuối. **Sửa điều kiện** để đổi ảnh hoặc thời hạn.
4. **Xuất file** tạo một file `.hocvet` nén gồm kịch bản, cài đặt phát và ảnh mẫu. Người nhận dùng **Nhập file** để thêm thành kịch bản mới. Không ghi đè kịch bản đang có; vẫn đọc được JSON cũ.
5. Mở **Hướng dẫn** ngay trong ứng dụng để xem cách lưu, chia sẻ, gán phím và kiểm tra ảnh.

Các phím trên là mặc định, có thể đổi trong Cài đặt.

## Cài đặt phím tắt

Gán phím đơn (F6, K) hoặc tổ hợp (Ctrl+Shift+K) cho các nút, từng mức tốc độ, tùy chọn, thao tác khay và các nút Lưu / Hủy / Chụp ảnh trong hộp thoại.

- Gõ tên phím hoặc bấm **Ghi phím**, rồi chọn **Lưu cài đặt**.
- Chọn **Trong ứng dụng** hoặc **Toàn cục**. Phím toàn cục dùng được khi thu vào khay. Học và Dừng khẩn cấp luôn là toàn cục.
- Bỏ trống để bỏ gán, trừ Học và Dừng khẩn cấp. Các nút trong hộp thoại dùng phím theo ngữ cảnh. Khi gán phím, lắng nghe toàn cục tạm ngừng.
- Báo lỗi khi phím trùng / chồng tổ hợp với lệnh hoặc kịch bản khác, ví dụ F6 và Ctrl+F6. Phím chữ đơn không lấy mất ký tự đang nhập trong ô văn bản.
- Chọn **Khôi phục phím mặc định** rồi Lưu để đặt lại. Cài đặt được giữ qua cập nhật.

![Cài đặt phím tắt](docs/images/settings.png)

## Dữ liệu và cập nhật

Thư viện và cài đặt lưu riêng tại `%LOCALAPPDATA%\HocVet\scripts_library.json`, tách khỏi file ứng dụng. Có thể mở thư mục này từ menu trong ứng dụng. Không xóa thư mục dữ liệu khi cập nhật.

Lưu qua file tạm rồi thay thế; `.bak` giữ lần lưu trước và được đọc khi file chính hỏng. Để chuyển máy, xuất từng kịch bản hoặc sao lưu cả thư mục dữ liệu. Gói phát hành không chứa thư viện cá nhân.

## Độ ổn định và giao diện

- **Chờ cửa sổ:** chờ cửa sổ phía trước có tiêu đề chứa nội dung đã nhập.
- **Chờ ảnh:** chụp một vùng nhỏ, ổn định; mặc định cho phép 2% pixel khác màu rõ rệt. Ảnh được so sánh ở đúng tọa độ đã chụp, không tìm ở vị trí khác. Giữ cùng bố cục, vị trí cửa sổ, độ phân giải và DPI khi chạy / chia sẻ.
- **Hết thời hạn:** kịch bản dừng và báo lỗi trước thao tác tiếp theo. Tốc độ phát không rút ngắn thời hạn chờ.
- **Tiếng Việt:** ghi phím vật lý, bỏ qua phím do bộ gõ tự sinh. Giữ cùng bộ gõ Unicode, Telex/VNI, bố cục bàn phím và Caps Lock khi học / chạy. Kịch bản cũ bị lặp dấu cần học lại.
- **Giao diện thống nhất:** màu kem, nút theo vai trò, ô nhập và hộp thoại dùng chung kiểu hiển thị. Trạng thái luôn hiện trên cùng; có cuộn và điều chỉnh theo DPI, hỗ trợ Tab / Enter / Space. Hộp chọn file sử dụng giao diện Windows.

Kịch bản có thể chứa nội dung đã gõ và ảnh chụp màn hình; kiểm tra trước khi chia sẻ. Chưa xác minh trên mọi phần mềm HIS / bộ gõ; thử kịch bản trên dữ liệu mẫu trước khi dùng thực tế.

## Chạy và phát triển từ mã nguồn

Yêu cầu Windows 10 / 11 và Python 3.10 trở lên.

```powershell
git clone https://github.com/UIBreaker/Smart_Operation.git
cd Smart_Operation
python -m pip install -r requirements.txt
python main.py
```

Kiểm thử:

```powershell
python test_core.py
python -m unittest -v test_features test_theme
```

Đóng gói (cần PyInstaller):

```powershell
python -m pip install pyinstaller
python build_release.py
```

Lệnh trên kiểm thử, tạo EXE, gói ZIP và `dist/SHA256SUMS.txt`. Phiên bản chạy lấy từ `app_info.py`; kiểu giao diện chung nằm trong `ui_theme.py`.
