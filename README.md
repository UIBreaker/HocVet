# Học Vẹt · v0.14.1

Trợ lý ghi và phát lại thao tác chuột / bàn phím trên Windows, dành cho công việc văn phòng và phần mềm HIS.

**Tác giả:** Nhật Nam ([@UIBreaker](https://github.com/UIBreaker)) · **Giấy phép:** [MIT](LICENSE)

## Có gì mới trong 0.14.1

- Danh sách kịch bản chữ lớn, nền chọn xanh nhạt; hiển thị rõ phím chạy, số bước và tổng số kịch bản.
- Thêm nút đỏ **Xóa kịch bản** cạnh **Tạo mới**, có xác nhận trước khi xóa.
- Chặn xóa khi đang học / chạy; giữ lại kịch bản nếu lưu thư viện thất bại. Thư viện luôn giữ ít nhất một kịch bản.

Chi tiết tại [ghi chú phát hành](RELEASE_NOTES.md).

## Tải và chạy

Tải **HocVet.exe** hoặc **HocVet-v0.14.1-Windows.zip** tại [bản phát hành 0.14.1](https://github.com/UIBreaker/Smart_Operation/releases/tag/v0.14.1); **SHA256SUMS.txt** dùng để kiểm tra file tải về. Xem bản mới nhất tại [GitHub Releases](https://github.com/UIBreaker/Smart_Operation/releases/latest). Giải nén ZIP rồi chạy **Học Vẹt.exe**, hoặc chạy trực tiếp **HocVet.exe**; không cần cài Python. Chế độ Web riêng cần Microsoft Edge đã cài. Giao diện hiển thị tên **Học Vẹt**; kho mã vẫn dùng địa chỉ Smart_Operation.

Đóng phiên bản cũ trước khi mở EXE mới. Dữ liệu và cài đặt được giữ trong `%LOCALAPPDATA%\HocVet`; không xóa thư mục này khi nâng cấp.

Khi nâng cấp từ Smart Operation, đặt ứng dụng cạnh `scripts_library.json` cũ trước lần mở đầu tiên. Nếu chạy từ thư mục `dist`, ứng dụng cũng kiểm tra thư mục cha. File cũ được giữ nguyên. Từ lần sau có thể thay / di chuyển file ứng dụng mà vẫn giữ thư viện.

![Giao diện Học Vẹt](docs/images/main.png)

## Sử dụng nhanh

1. Chọn kịch bản (hoặc **+ Tạo mới**), nhấn **F8**. Thông báo nổi đếm ngược **3–2–1**, sau đó báo **Đang học** ngay cả khi cửa sổ đang thu vào khay. Làm các bước trên phần mềm đích; nhấn lại **F8** hoặc phím **Dừng học** đã gán để dừng/lưu. Thông báo **Đã dừng & lưu thành công** xuất hiện sau khi lưu xong. Bấm Dừng trên Học Vẹt không bị ghi vào kịch bản.
2. Chọn **Chạy** hoặc dùng phím riêng của kịch bản (mặc định mẫu: **F9**). Nhấn **Esc** để dừng khẩn cấp, kể cả trong khi chờ điều kiện.
3. Mở **Chi tiết / sửa bước**, chọn một dòng, dùng **+ Chờ cửa sổ** / **+ Chờ ảnh / nút** để chèn điều kiện trước dòng đó; không chọn dòng sẽ thêm ở cuối. **Sửa điều kiện** để đổi ảnh hoặc thời hạn.
4. **Xuất file** tạo một file `.hocvet` nén gồm kịch bản, cài đặt phát và ảnh mẫu. Người nhận dùng **Nhập file** để thêm thành kịch bản mới. Không ghi đè kịch bản đang có; vẫn đọc được JSON cũ.
5. Mở **Hướng dẫn** ngay trong ứng dụng để xem cách lưu, chia sẻ, gán phím và kiểm tra ảnh.

Tab **Chính** điều chỉnh tốc độ từ **1× đến 10×**. Tab **Chi tiết / sửa bước** hiển thị **12 bước/trang**; tab **Cài đặt** hiển thị **6 lệnh/trang**. Chuyển trang để xem đủ các bước và phím tắt.

![Chi tiết và sửa bước](docs/images/details.png)

![Thông báo tiến độ](docs/images/progress.png)

Các phím trên là mặc định, có thể đổi trong Cài đặt.

## Chọn và xóa kịch bản

Ô chọn kịch bản hiển thị rõ **tên · Phím chạy**, có số bước và tổng số kịch bản bên dưới. Nút đỏ **Xóa kịch bản** nằm cạnh **Tạo mới**, hỏi xác nhận trước khi xóa và chỉ dùng khi đã dừng học / chạy. Thư viện giữ ít nhất một kịch bản; hãy tạo kịch bản mới trước khi xóa kịch bản cuối cùng.

Nếu không lưu được thư viện, ứng dụng báo lỗi và giữ nguyên kịch bản. Nút xóa dùng chung lệnh với phím tắt **Xóa kịch bản** trong Cài đặt.

![Danh sách và nút xóa kịch bản](docs/images/script-selector.png)

## Cài đặt phím tắt

Gán phím đơn (F6, K) hoặc tổ hợp (Ctrl+Shift+K) cho các nút, từng mức tốc độ, tùy chọn, thao tác khay và các nút Lưu / Hủy / Chụp ảnh trong hộp thoại.

- Gõ tên phím hoặc bấm **Ghi phím**, rồi chọn **Lưu cài đặt**.
- Chọn **Trong ứng dụng** hoặc **Toàn cục**. Phím toàn cục dùng được khi thu vào khay. Học và Dừng khẩn cấp luôn là toàn cục.
- **Dừng học** luôn là toàn cục; gán phím `2` sẽ dừng được khi đang thao tác ở phần mềm khác. Cài đặt cũ ở phạm vi Trong ứng dụng được chuyển tự động cho lệnh này. Hàng số và bàn phím số đều được hỗ trợ.
- Bỏ trống để bỏ gán, trừ Học và Dừng khẩn cấp. Các nút trong hộp thoại dùng phím theo ngữ cảnh. Khi gán phím, lắng nghe toàn cục tạm ngừng.
- Báo lỗi khi phím trùng / chồng tổ hợp với lệnh hoặc kịch bản khác, ví dụ F6 và Ctrl+F6. Phím chữ đơn không lấy mất ký tự đang nhập trong ô văn bản.
- Chọn **Khôi phục phím mặc định** rồi Lưu để đặt lại. Cài đặt được giữ qua cập nhật.

![Cài đặt phím tắt](docs/images/settings.png)

![Đếm ngược khi chạy nền](docs/images/countdown.png)

## Dữ liệu và cập nhật

Thư viện và cài đặt lưu riêng tại `%LOCALAPPDATA%\HocVet\scripts_library.json`, tách khỏi file ứng dụng. Có thể mở thư mục này từ menu trong ứng dụng. Không xóa thư mục dữ liệu khi cập nhật.

Lưu qua file tạm rồi thay thế; `.bak` giữ lần lưu trước và được đọc khi file chính hỏng. Để chuyển máy, xuất từng kịch bản hoặc sao lưu cả thư mục dữ liệu. Gói phát hành không chứa thư viện cá nhân.

## Độ ổn định và giao diện

- **Chờ cửa sổ:** chờ cửa sổ phía trước có tiêu đề chứa nội dung đã nhập.
- **Chờ ảnh:** chụp một vùng nhỏ, ổn định; mặc định cho phép 2% pixel khác màu rõ rệt. Ảnh được so sánh ở đúng tọa độ đã chụp, không tìm ở vị trí khác. Giữ cùng bố cục, vị trí cửa sổ, độ phân giải và DPI khi chạy / chia sẻ.
- **Hết thời hạn:** kịch bản dừng và báo lỗi trước thao tác tiếp theo. Tốc độ phát không rút ngắn thời hạn chờ.
- **Tiếng Việt:** ghi phím vật lý, bỏ qua phím do bộ gõ tự sinh. Giữ cùng bộ gõ Unicode, Telex/VNI, bố cục bàn phím và Caps Lock khi học / chạy. Kịch bản cũ bị lặp dấu cần học lại.
- **Mượt hơn:** không dựng lại danh sách cho từng sự kiện nhập; đếm số thao tác theo đợt và giới hạn tần suất cập nhật tiến độ. Kịch bản dài xem/sửa theo trang 12 bước, vẫn giữ đầy đủ mọi thao tác.
- **Giao diện thống nhất:** màu kem, nút theo vai trò, ô nhập và hộp thoại dùng chung kiểu hiển thị. Trạng thái luôn hiện ở cuối cửa sổ; chia tab và điều chỉnh theo DPI, hỗ trợ Tab / Enter / Space. Hộp chọn file sử dụng giao diện Windows.

Kịch bản có thể chứa nội dung đã gõ và ảnh chụp màn hình; kiểm tra trước khi chia sẻ. Chưa xác minh trên mọi phần mềm HIS / bộ gõ; thử kịch bản trên dữ liệu mẫu trước khi dùng thực tế.

## Công việc riêng (v0.14)

Bốn tab **Chính**, **Chi tiết / sửa bước**, **Công việc riêng**, **Cài đặt** không có thanh cuộn. Chi tiết chia 12 bước/trang, cài đặt chia 6 lệnh/trang. Thanh tốc độ hỗ trợ mọi mức nguyên từ **1× đến 10×**. Chỉ dùng thông báo nổi của Học Vẹt, có thanh tiến độ khi chạy; không gửi thông báo Windows.

Trong **Công việc riêng**, chọn loại phiên rồi bấm **Mở phiên**. Bấm **Học trong tab**, thao tác trên ảnh xem trước bằng chuột đỏ, nhập tiếng Việt ở ô **Nhập chữ** rồi **Gửi vào phiên**. **Dừng** sẽ tự lưu; chọn **Chạy công việc** để phát lại. Có thể đổi tab, dùng ứng dụng khác hoặc thu Học Vẹt vào khay trong lúc chạy. Phím Dừng học / Khẩn cấp cũng dừng công việc riêng. Các nút của tab đều có thể gán phím trong Cài đặt.

- **Web riêng:** cần Microsoft Edge đã cài. Dùng trình duyệt headless với hồ sơ riêng `%LOCALAPPDATA%\HocVet\web-session`; đăng nhập qua ảnh xem trước nếu cần. Không mở hồ sơ Edge cá nhân. Chuột và phím chỉ gửi vào phiên này. Trang dùng xác thực đặc biệt, tải file hoặc cửa sổ mới chưa được hỗ trợ đầy đủ.
- **Windows / HIS tương thích:** chọn một cửa sổ đang mở và giữ nguyên kích thước khi chạy. Hỗ trợ ô nhập Edit/RichEdit, một số WinForms và nút Windows chuẩn. Có thể dùng ứng dụng khác nhưng không thu nhỏ cửa sổ đích. Không dùng chuột thật, không đưa cửa sổ đích lên trước. Khi bị chặn, mất cửa sổ, đổi tiến trình, thu nhỏ hoặc không cung cấp ảnh, phiên sẽ dừng/báo lỗi. Thông báo hoàn tất chỉ xác nhận đã gửi thao tác; cần kiểm tra kết quả trên phần mềm đích.
- **Giới hạn HIS:** chưa bảo đảm với mọi HIS. Điều khiển tùy biến, WPF/GPU, menu chuột phải và hộp thoại ngoài cửa sổ đích có thể không tương thích. Muốn tự động hóa Windows tùy ý và hoàn toàn độc lập cần một phiên Windows / máy ảo riêng; bản này không tạo máy ảo.

Công việc này dùng tọa độ bên trong phiên, **cần học lại trong tab**, không nhập trực tiếp macro tọa độ màn hình. Lưu tại `%LOCALAPPDATA%\HocVet\workspace_scripts.json`, có bản `.bak` khi lưu, được giữ qua cập nhật EXE. **Nhập / Chia sẻ** dùng một file JSON chứa các bước; không chia sẻ thông tin đăng nhập trong hồ sơ trình duyệt. Kịch bản có thể chứa chữ đã nhập nên cần kiểm tra trước khi gửi.

![Công việc riêng](docs/images/workspace.png)

## Chạy và phát triển từ mã nguồn

Yêu cầu Windows 10 / 11 và Python 3.10 trở lên.

```powershell
git clone https://github.com/UIBreaker/Smart_Operation.git
cd Smart_Operation
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Kiểm thử:

```powershell
python test_core.py
python -m unittest -v test_features test_theme test_workspace
```

Kiểm thử tích hợp Edge và cửa sổ Windows mẫu (cần Microsoft Edge):

```powershell
$env:HOCVET_INTEGRATION = '1'
python -m unittest -v test_workspace.IntegrationTests
```

Đóng gói (cần PyInstaller):

```powershell
python -m pip install pyinstaller
python build_release.py
```

Lệnh trên kiểm thử, tạo EXE, gói ZIP và `dist/SHA256SUMS.txt`. Phiên bản chạy lấy từ `app_info.py`; kiểu giao diện chung nằm trong `ui_theme.py`.
