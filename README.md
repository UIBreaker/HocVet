# Học Vẹt · v0.16.0

Trợ lý ghi và phát lại thao tác chuột / bàn phím trên Windows, dành cho công việc văn phòng và phần mềm HIS.

**Tác giả:** Nhật Nam ([@UIBreaker](https://github.com/UIBreaker)) · **Giấy phép:** [MIT](LICENSE)

## Có gì mới trong 0.16.0

- Chỉnh số lần lặp riêng cho từng kịch bản ngay trên bảng nổi bằng **− / +** hoặc bấm số để nhập; **0 = lặp liên tục**.
- Kéo cạnh / góc để đổi kích thước bảng; số kịch bản mỗi trang tự điều chỉnh theo khung.
- Ghi nhớ số lần lặp và kích thước qua lần mở / cập nhật; khóa chỉnh khi đang học / chạy.

Chi tiết tại [ghi chú phát hành](RELEASE_NOTES.md).

## Tải và chạy

Tải **HocVet.exe** hoặc **HocVet-v0.16.0-Windows.zip** tại [bản phát hành 0.16.0](https://github.com/UIBreaker/HocVet/releases/tag/v0.16.0); **SHA256SUMS.txt** dùng để kiểm tra file tải về. Xem bản mới nhất tại [GitHub Releases](https://github.com/UIBreaker/HocVet/releases/latest). Giải nén ZIP rồi chạy **Học Vẹt.exe**, hoặc chạy trực tiếp **HocVet.exe**; không cần cài Python. Chế độ Web riêng cần Microsoft Edge đã cài. Giao diện hiển thị tên **Học Vẹt**; kho mã tại **UIBreaker/HocVet**.

Đóng phiên bản cũ trước khi mở EXE mới. Dữ liệu và cài đặt được giữ trong `%LOCALAPPDATA%\HocVet`; không xóa thư mục này khi nâng cấp.

Khi nâng cấp từ Smart Operation, đặt ứng dụng cạnh `scripts_library.json` cũ trước lần mở đầu tiên. Nếu chạy từ thư mục `dist`, ứng dụng cũng kiểm tra thư mục cha. File cũ được giữ nguyên. Từ lần sau có thể thay / di chuyển file ứng dụng mà vẫn giữ thư viện.

![Giao diện Học Vẹt](docs/images/main.png)

## Sử dụng nhanh

1. Chọn kịch bản (hoặc **+ Tạo mới**). Ở chế độ chuột mặc định, bấm **Học thao tác**; ở chế độ phím, nhấn **F8**. Chờ đếm ngược **3–2–1** và thông báo **Đang học** rồi thao tác trên phần mềm đích. Bấm **Dừng** trên bảng nổi ở chế độ chuột; ở chế độ phím, nhấn lại **F8** hoặc phím **Dừng học** đã gán. Thông báo **Đã dừng & lưu thành công** xuất hiện sau khi lưu xong. Cú bấm Dừng không bị ghi vào kịch bản.
2. Chọn **Chạy** trên màn hình chính hoặc từng dòng ở bảng nổi. Nếu bật chế độ phím, có thể dùng phím riêng của kịch bản (mặc định mẫu: **F9**). Ở chế độ phím, nhấn **Esc** để dừng khẩn cấp; ở chế độ chuột, bấm **Dừng** trên bảng nổi.
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

## Bảng nổi khi chạy nền (v0.15)

Khi bấm **Chạy**, Học Vẹt thu vào khay trước rồi bắt đầu phát sau khoảng 0,2 giây để cửa sổ công việc nhận lại tiêu điểm. Bảng nổi không lấy tiêu điểm; phần trên là tiến trình, phần dưới có tên, số bước và nút **Chạy** cho từng kịch bản màn hình. Chọn **Trước / Sau** hoặc lăn chuột để chuyển trang. Bảng giữ nguyên khi hoàn tất, sẵn sàng cho lượt tiếp theo. Kịch bản rỗng / bị tắt không chạy được.

**Cài đặt → Kích hoạt kịch bản** có hai lựa chọn:

- **Bấm chuột ở bảng nổi** (mặc định): tắt toàn bộ phím đã gán, kể cả Dừng khẩn cấp và phím riêng của kịch bản. Gõ số từng gán để dừng sẽ không ngắt công việc. Bấm **Học thao tác** trên màn hình chính để học, rồi **Dừng** ở bảng nổi để lưu. Không xóa cấu hình phím đã gán.
- **Dùng phím đã gán**: bật các phím đó và khóa nút Học / Chạy / Dừng bằng chuột ở màn hình chính, bảng nổi và tab Công việc. Phím **Dừng khẩn cấp** chỉ hoạt động trong chế độ này.

Kéo tiêu đề bảng để đổi vị trí khi đang rảnh. Bảng giữ nguyên vị trí khi phát. Các nút Chạy / chuyển trang / Mở ứng dụng bị khóa trong lúc chạy; **Dừng** bằng chuột chỉ dùng được ở chế độ chuột. Bấm **Mở ứng dụng** khi đã dừng để trở về màn hình chính.

Bấm vào bảng không được ghi thành thao tác. Khi phát macro màn hình, bảng vẫn hiển thị nhưng nhận diện chuột xuyên qua; cú bấm / cuộn được gửi tới cửa sổ bên dưới tại đúng tọa độ. Bộ lọc riêng chỉ nhận cú bấm chuột thật vào Dừng ở chế độ chuột, không nhận cú bấm do kịch bản phát ra. Các cú bấm tay khác trên bảng trong lúc phát được chặn để không bấm nhầm xuống cửa sổ bên dưới. Sau khi hàng đợi chuột hoàn tất, bảng nhận chuột trở lại. Kiểm tra bàn phím vẫn dừng nếu cửa sổ Học Vẹt bất ngờ nhận tiêu điểm. Macro màn hình vẫn dùng chuột thật của Windows; dùng tab Công việc riêng khi cần nhập liệu độc lập.

![Bảng nổi tiến trình và kịch bản](docs/images/tray-panel.png)

![Bảng nổi khi sẵn sàng](docs/images/tray-panel-idle.png)

## Số lần lặp và kích thước bảng (v0.16)

Dưới mỗi kịch bản có **−**, **số lần**, **+**. Bấm −/+ để đổi từng đơn vị hoặc bấm số để nhập trực tiếp. Nhập **0** nếu muốn chạy liên tục đến khi Dừng. Giá trị được lưu riêng cho đúng kịch bản và đồng bộ với ô Lặp lại trên màn hình chính; nếu lưu thất bại ứng dụng giữ số cũ và báo lỗi.

Kéo bất kỳ cạnh hoặc góc của bảng nổi để đổi kích thước. Bảng hẹp / thấp sẽ hiển thị ít kịch bản hơn trên một trang; bảng cao sẽ hiển thị nhiều hơn. Có giới hạn nhỏ nhất để giữ nút Dừng và điều hướng đọc được, và giới hạn theo vùng màn hình làm việc. Kích thước được lưu khi thả chuột, không ghi file liên tục khi kéo.

Chỉ chỉnh lặp và kích thước khi đang dừng; trong lúc học / chạy các điều khiển này được khóa để giữ ổn định vùng bấm xuyên bảng. Cả chế độ phím và chuột đều có thể chỉnh cấu hình lúc rảnh; việc kích hoạt kịch bản vẫn tuân theo chế độ đã chọn.

![Bảng nổi thu nhỏ](docs/images/tray-panel-small.png)

![Bảng nổi phóng lớn](docs/images/tray-panel-large.png)

## Cài đặt phím tắt

Gán phím đơn (F6, K) hoặc tổ hợp (Ctrl+Shift+K) cho các nút, từng mức tốc độ, tùy chọn, thao tác khay và các nút Lưu / Hủy / Chụp ảnh trong hộp thoại.

Các phím đã gán chỉ hoạt động khi chọn **Cài đặt → Kích hoạt kịch bản → Dùng phím đã gán**. Ở chế độ chuột mặc định, mọi phím gán đều tắt, kể cả **Esc / Dừng khẩn cấp**; dùng nút **Dừng** trên bảng nổi. Đổi chế độ không xóa cấu hình phím.

- Gõ tên phím hoặc bấm **Ghi phím**, rồi chọn **Lưu cài đặt**.
- Chọn **Trong ứng dụng** hoặc **Toàn cục**. Trong chế độ phím, phím toàn cục dùng được khi thu vào khay; Học và Dừng khẩn cấp luôn ở phạm vi toàn cục.
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

Trong **Công việc riêng**, chọn loại phiên rồi bấm **Mở phiên**. Ở chế độ chuột, bấm **Học trong tab**, thao tác trên ảnh xem trước bằng chuột đỏ, nhập tiếng Việt ở ô **Nhập chữ** rồi **Gửi vào phiên**. **Dừng** sẽ tự lưu; chọn **Chạy công việc** để phát lại. Có thể đổi tab, dùng ứng dụng khác hoặc thu Học Vẹt vào khay trong lúc chạy. Ở chế độ phím, các nút Học / Chạy / Dừng bị khóa bằng chuột; gán phím tương ứng trong Cài đặt để sử dụng. Phím Dừng học / Khẩn cấp cũng dừng công việc riêng khi đang ở chế độ phím.

- **Web riêng:** cần Microsoft Edge đã cài. Dùng trình duyệt headless với hồ sơ riêng `%LOCALAPPDATA%\HocVet\web-session`; đăng nhập qua ảnh xem trước nếu cần. Không mở hồ sơ Edge cá nhân. Chuột và phím chỉ gửi vào phiên này. Trang dùng xác thực đặc biệt, tải file hoặc cửa sổ mới chưa được hỗ trợ đầy đủ.
- **Windows / HIS tương thích:** chọn một cửa sổ đang mở và giữ nguyên kích thước khi chạy. Hỗ trợ ô nhập Edit/RichEdit, một số WinForms và nút Windows chuẩn. Có thể dùng ứng dụng khác nhưng không thu nhỏ cửa sổ đích. Không dùng chuột thật, không đưa cửa sổ đích lên trước. Khi bị chặn, mất cửa sổ, đổi tiến trình, thu nhỏ hoặc không cung cấp ảnh, phiên sẽ dừng/báo lỗi. Thông báo hoàn tất chỉ xác nhận đã gửi thao tác; cần kiểm tra kết quả trên phần mềm đích.
- **Giới hạn HIS:** chưa bảo đảm với mọi HIS. Điều khiển tùy biến, WPF/GPU, menu chuột phải và hộp thoại ngoài cửa sổ đích có thể không tương thích. Muốn tự động hóa Windows tùy ý và hoàn toàn độc lập cần một phiên Windows / máy ảo riêng; bản này không tạo máy ảo.

Công việc này dùng tọa độ bên trong phiên, **cần học lại trong tab**, không nhập trực tiếp macro tọa độ màn hình. Lưu tại `%LOCALAPPDATA%\HocVet\workspace_scripts.json`, có bản `.bak` khi lưu, được giữ qua cập nhật EXE. **Nhập / Chia sẻ** dùng một file JSON chứa các bước; không chia sẻ thông tin đăng nhập trong hồ sơ trình duyệt. Kịch bản có thể chứa chữ đã nhập nên cần kiểm tra trước khi gửi.

![Công việc riêng](docs/images/workspace.png)

## Chạy và phát triển từ mã nguồn

Yêu cầu Windows 10 / 11 và Python 3.10 trở lên.

```powershell
git clone https://github.com/UIBreaker/HocVet.git
cd HocVet
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Kiểm thử:

```powershell
python test_core.py
python -m unittest -v test_features test_theme test_workspace test_overlay_input
```

Kiểm thử tích hợp Edge, cửa sổ Windows mẫu và phát chuột xuyên qua bảng nổi (cần Microsoft Edge; bài kiểm thử bảng nổi dùng chuột thật trên cửa sổ mẫu rồi trả lại vị trí cũ):

```powershell
$env:HOCVET_INTEGRATION = '1'
python -m unittest -v test_workspace.IntegrationTests test_overlay_input.NativePassThroughTests
```

Đóng gói (cần PyInstaller):

```powershell
python -m pip install pyinstaller
python build_release.py
```

Lệnh trên kiểm thử, tạo EXE, gói ZIP và `dist/SHA256SUMS.txt`. Phiên bản chạy lấy từ `app_info.py`; kiểu giao diện chung nằm trong `ui_theme.py`.
