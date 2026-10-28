# Học Vẹt v0.20.3

- Giữ thời gian ổn định ô đích trước khi dán ngày ở tốc độ cao, kiểm tra lại cửa sổ nhận dữ liệu để tránh dán lệch ô.
- Hiển thị rõ kiểu dán cho cột đang chọn, hỗ trợ đổi trực tiếp giữa văn bản một ô và ngày ba ô HIS; lưu và kiểm tra lại sau khi mở bảng.
- Dừng trước khi chạy nếu kịch bản vẫn dùng bước sao chép một ô cho cột đã bật ngày ba ô; hướng dẫn học lại thay vì báo hoàn tất sau khi chỉ điền ô ngày.
- Thêm `verify_his_learning.py`: học qua giao diện và bộ ghi chuột/phím, lưu/nạp lại kịch bản rồi chạy 5 ngày khác nhau ở 1× và 10×; đọc cả ba ô và ô phụ sau mỗi lượt, lưu báo cáo và ảnh. Dùng đúng DPI và kích thước cửa sổ Chrome thực khi ghi tọa độ.

- Từ v0.20.0: sửa dán ngày liên tiếp / phát lại bằng Ctrl+V, giữ ô phụ thứ tư và sửa bố cục bảng điều khiển khi thu nhỏ / đổi DPI.

## Nâng cấp và tải về

Đóng phiên bản cũ rồi thay EXE hoặc giải nén ZIP mới. Dữ liệu và cài đặt được giữ tại `%LOCALAPPDATA%\HocVet`; không xóa thư mục này. Cột ngày chia ba ô cần chọn đúng kiểu dán và học lại bước dán; kịch bản cũ chưa phù hợp sẽ bị chặn trước khi chạy.

- `HocVet.exe`: chạy trực tiếp trên Windows, không cần Python.
- `HocVet-v0.20.3-Windows.zip`: ứng dụng, README, ảnh hướng dẫn và giấy phép.
- `SHA256SUMS.txt`: mã kiểm tra EXE và ZIP.

Dán ngày ba ô yêu cầu thứ tự Tab ngày → tháng → năm. Đã kiểm tra trên HIS giả lập; chưa xác minh trên HIS thực tế. Các phím đã gán, kể cả Esc, chỉ hoạt động ở chế độ **Dùng phím đã gán**.

---

# Học Vẹt v0.20.2

- Sửa trường hợp Ctrl+V chỉ dán vào ô đầu tiên: không hủy chế độ tách ngày khi clipboard được ghi lại cùng nội dung; nhận Ctrl+V do công cụ bàn phím phát lại và bỏ qua các phím do chính lượt dán sinh ra.
- Xóa trạng thái giữ phím V sau mỗi lượt để không chặn lượt dán kế tiếp. Tự tạo lại listener nếu listener cũ đã dừng.
- Kiểm tra qua HisPanel → Ctrl+V → ba ô của file HIS giả lập, cả khi đang học; giữ nguyên ô phụ thứ tư. Chưa thử trên HIS thật.

---

# Học Vẹt v0.20.1

- Sửa lỗi thỉnh thoảng phần kịch bản chiếm hết bảng, làm khuất chuyển trang / Mở ứng dụng / Dừng / mở HIS. Dành riêng vùng dưới cho các nút, vùng kịch bản chỉ dùng phần chiều cao còn lại.
- Tính lại chiều cao thực sau khi Tk bố trí xong, thay vì dùng số đo cũ; tự đổi số dòng ngay cả lúc đang chạy hoặc thay đổi DPI. Chặn tính bố cục lặp trong lúc giao diện đang cập nhật.
- Tự bảo đảm chiều cao tối thiểu cho một thẻ kịch bản và giới hạn bảng trong vùng màn hình; giữ các điều khiển lặp của thẻ nhìn thấy.
- Tái hiện được lỗi trước khi sửa; kiểm tra thu nhỏ khi bận, cài / gỡ HIS, ẩn / mở lại và chu kỳ bố cục ở DPI 100% / 125% / 150% / 200%. Kiểm tra tương tác thật trên cửa sổ mẫu vẫn cho chuột phát xuyên bảng và nút Dừng hoạt động.

---

# Học Vẹt v0.20.0

- Trải nghiệm cài / gỡ tiện ích có trạng thái đang xử lý, thanh tiến trình, khóa nút trong lúc thực hiện và thông báo hoàn tất. Gói công cụ đi kèm ứng dụng, không tạo thông báo tải mạng. Gỡ có xác nhận và giữ dữ liệu bảng để cài lại.
- Chuyển Môi trường thao tác thành cửa sổ riêng, mở lại cùng cửa sổ khi đã có; đóng [X] chỉ ẩn, không tạo thêm tab trên cửa sổ chính. Học / dán / tiến độ / bảng dữ liệu được giữ nguyên. Khi lấy ô lúc học, cửa sổ bảng ẩn để trả tiêu điểm về phần mềm đích.
- Bảng điều khiển có nút Mở môi trường HIS sau khi cài; gỡ bỏ nút đó và đóng cửa sổ. Khi đang phát, khóa mở môi trường để bảo vệ tiêu điểm.
- Thêm × ẩn bảng điều khiển, nút Bảng điều khiển trên màn hình chính và menu khay mở / ẩn. Bảng ẩn vẫn để công việc tiếp tục, không tự mở lại bởi thông báo tiến độ. Có thể dừng qua khay hoặc mở lại bảng; bắt đầu học mới hiện đếm ngược.
- Kéo tiêu đề bảng để di chuyển cả lúc đang chạy, cập nhật vùng Dừng / ẩn / kéo theo vị trí mới. Hỗ trợ vùng làm việc màn hình tại vị trí kéo. Chuột do kịch bản phát vẫn xuyên bảng, không kích hoạt kéo / ẩn / dừng.
- Kiểm thử cài / gỡ / cài lại, giữ dữ liệu, cửa sổ riêng không thêm tab, ẩn / mở / di chuyển, bộ lọc chuột thật / chuột phát; kiểm tra tương tác thực trên cửa sổ mẫu và trình duyệt cục bộ. Chưa kiểm thử đăng ký trên HIS thực tế.

- Từ v0.18.0: thêm quản lý cột, đếm ngược học với bảng, màu tiến độ từng ô và tab Thoát toàn bộ luôn ở ngoài cùng bên phải.

## Nâng cấp và tải về

Đóng phiên bản cũ rồi thay EXE hoặc giải nén ZIP mới. Dữ liệu và cài đặt được giữ tại `%LOCALAPPDATA%\HocVet`; không xóa thư mục này. Tiện ích HIS dùng gói có sẵn trong ứng dụng; gỡ tiện ích vẫn giữ các môi trường dữ liệu.

- `HocVet.exe`: chạy trực tiếp trên Windows, không cần Python.
- `HocVet-v0.20.0-Windows.zip`: ứng dụng, README, ảnh hướng dẫn và giấy phép.
- `SHA256SUMS.txt`: mã kiểm tra EXE và ZIP.

Khi ẩn bảng, công việc vẫn chạy; có thể mở lại bảng hoặc dừng qua menu khay. Các phím đã gán, kể cả Esc, chỉ hoạt động ở chế độ **Dùng phím đã gán**. Màu ô chỉ báo việc lấy dữ liệu, không xác nhận kết quả trên HIS; chưa xác minh đăng ký HIS thực tế.

---

# Học Vẹt v0.19.1

- Đưa Thoát toàn bộ về cuối thanh tab; tab tiện ích thêm vào phía trước nên vị trí thoát luôn ở ngoài cùng bên phải.
- Hiển thị nhãn nền đỏ, chữ trắng, giữ thao tác dừng / lưu và thoát hẳn.
- Kiểm tra thứ tự sau cài / gỡ / cài lại tiện ích và chức năng thoát.

---

# Học Vẹt v0.19.0

- Menu Trường dữ liệu cho phép thêm, đổi tên, đổi vị trí trái / phải và xóa cột. Chọn tiêu đề / ô hoặc nhấp chuột phải để thao tác. Xóa có xác nhận và chỉ ảnh hưởng cột trong bảng hiện tại; đổi tên / vị trí giữ mã trường.
- Giữ tham chiếu trường đã xóa để chặn kịch bản cũ trước khi chạy, kể cả khi đang xem bảng khác có cột cùng tên. Lỗi lưu giữ nguyên trường / dữ liệu.
- Học với bảng luôn đếm ngược 3–2–1 ở cả hướng dẫn trong bảng và thông báo ứng dụng. Dừng học hủy đếm ngược mà không ghi đè kịch bản.
- Sau khi sao chép clipboard thành công, cập nhật ô vàng hiện tại và ô xanh đã đi qua theo đúng bảng / trường / STT mỗi vòng. Bảng nổi hiển thị trường vừa lấy; mở lại bảng xem dấu màu. Dừng lỗi giữ ô cuối màu vàng; hoàn tất chuyển các ô đã lấy sang xanh. Không đổi dữ liệu theo màu; sửa dữ liệu / lượt mới xóa dấu tiến độ cũ.
- Kiểm thử xóa / hủy / lỗi lưu, đổi tên / vị trí, chặn tham chiếu cột đã xóa, đếm ngược / hủy, chỉ báo sau sao chép thành công và giữ nguyên dữ liệu. Chưa kiểm thử đăng ký HIS thực tế; màu không xác nhận kết quả nhập trên HIS.

---

# Học Vẹt v0.18.0

- Thêm nhiều môi trường: + Tạo mới tạo bảng có tên riêng, danh sách Bảng chuyển giữa các môi trường; bảng cũ và trạng thái chọn lưu qua lần mở ứng dụng.
- Tự chuyển bảng v0.17 sang cấu trúc nhiều môi trường, giữ trường, mã trường, dữ liệu và tham chiếu kịch bản. Kịch bản lấy đúng bảng đã học khi đang xem bảng khác; không cho trộn trường của nhiều bảng trong một kịch bản.
- Quét vùng bằng kéo chuột, Shift + bấm / mũi tên, Ctrl+A. Tự cuộn khi kéo ra mép. Ctrl+C sao chép vùng dạng bảng, Ctrl+V dán từ góc trên trái vùng chọn.
- Delete / Xóa vùng chọn chỉ xóa nội dung vùng đã chọn; Làm trống bảng hỏi xác nhận rồi xóa dữ liệu bảng hiện tại, giữ tên trường và các bảng khác. Khóa thay đổi dữ liệu / môi trường khi học hoặc chạy.
- Lưu bằng thay thế file sau khi ghi thành công; khi lỗi lưu, giữ dữ liệu hiện có. Kiểm tra giới hạn tổng file 30 MB trước khi lưu để lần mở sau vẫn đọc được.
- Kiểm thử di chuyển dữ liệu cũ, tạo / chuyển / mở lại bảng, chạy đúng nguồn, quét / sao chép / xóa vùng, hủy xác nhận và lỗi lưu. Chưa kiểm thử trực tiếp trên HIS thực tế.

- Từ v0.17.0: bổ sung thanh cuộn dọc / ngang, Ctrl+V dán danh sách hoặc nhiều cột, và tab **Thoát toàn bộ** riêng.

## Nâng cấp và tải về

Đóng phiên bản cũ rồi thay EXE hoặc giải nén ZIP mới. Dữ liệu và cài đặt được giữ tại `%LOCALAPPDATA%\HocVet`; không xóa thư mục này. Bảng v0.17 được chuyển sang cấu trúc nhiều môi trường, giữ trường, dữ liệu và tham chiếu kịch bản.

- `HocVet.exe`: chạy trực tiếp trên Windows, không cần Python.
- `HocVet-v0.18.0-Windows.zip`: ứng dụng, README, ảnh hướng dẫn và giấy phép.
- `SHA256SUMS.txt`: mã kiểm tra EXE và ZIP.

Mặc định dùng chuột: bấm **Dừng** trên bảng nổi. Các phím đã gán, kể cả Esc, chỉ hoạt động ở chế độ **Dùng phím đã gán**. Các giới hạn HIS trong README vẫn áp dụng; chưa xác minh trên HIS thực tế.

---

# Học Vẹt v0.17.1

- Thay nút Hàng trước / sau và Trường trước / sau trong bảng HIS bằng thanh cuộn dọc / ngang. Hỗ trợ con lăn, Shift + con lăn, Page Up / Down và tự cuộn theo ô chọn bằng phím mũi tên; tiêu đề giữ nguyên khi cuộn dọc.
- Chọn ô rồi Ctrl+V hoặc Dán dữ liệu để dán danh sách từ ngoài ứng dụng: mỗi dòng vào một STT, nhiều cột Excel vào các trường liên tiếp. Giữ nguyên tiếng Việt, số 0 đầu và dữ liệu các cột không dán; hiển thị số hàng và khoảng STT vừa dán.
- Bảng chỉ vẽ các hàng đang xem để cuộn cả nghìn hàng mà không dựng toàn bộ bảng. Cuộn khi sửa ô sẽ lưu ô trước khi đổi vị trí.
- Thoát toàn bộ thành tab riêng cạnh Tính năng mở rộng, chọn tab gọi lệnh dừng / lưu và thoát hẳn. Bỏ nút thoát khỏi nội dung trang Tính năng mở rộng.
- Kiểm thử dán 10 tên, nhiều cột / vị trí bắt đầu, chọn / sửa sau khi cuộn bảng 1.000 hàng, cuộn ngang, bàn phím, và chọn tab thoát. Dữ liệu cũ và cách lấy STT theo vòng chạy được giữ nguyên.

---

# Học Vẹt v0.17.0

- Thêm tab Tính năng mở rộng cạnh Cài đặt, công cụ Hỗ trợ ĐK KCB HIS cài / gỡ được. Cài xong có tab Môi trường thao tác; gỡ giữ lại bảng để cài lại.
- Bảng ô có đường kẻ, STT tự động, + thêm trường, sửa ô, phím mũi tên, dán vùng dữ liệu từ Excel và phân trang hàng / trường. Giữ chuỗi văn bản, tiếng Việt và số 0 đầu.
- Khi học lấy ô từ bảng, ghi bước lấy trường / STT thay cho tọa độ ô. Khi phát mỗi vòng lấy hàng kế tiếp, không cần mở lại bảng. Nút Môi trường trên bảng nổi cho phép quay về lấy trường tiếp theo khi đang học.
- Ghi đúng Ctrl khi giữ từ thao tác sao chép trong bảng sang dán ở HIS, bỏ phím thao tác giao diện và giữ đủ sự kiện thả phím khi đổi cửa sổ.
- Kiểm tra dữ liệu trước khi chạy: thiếu hàng / trường / ô trống hoặc học trộn STT sẽ bị chặn trước khi gửi thao tác. Chạy 0 lần với kịch bản dùng bảng sẽ dừng ở hàng dữ liệu cuối.
- Bảng lưu riêng trong his_environment.json, giữ qua cập nhật. Bước lấy dữ liệu không nhúng các hàng vào kịch bản chia sẻ; máy nhận có thể tạo trường cùng tên và nhập bảng của mình. Các bước phím / ảnh khác vẫn cần kiểm tra nội dung trước khi chia sẻ.
- Nút Thoát toàn bộ cạnh menu Tính năng mở rộng và trong tab công cụ: dừng / lưu, đóng công việc riêng, chờ luồng kết thúc rồi thoát hẳn. Khóa kích hoạt công việc mới khi đang thoát.
- Kiểm thử mô phỏng ba vòng lấy đúng ba hàng; kiểm tra cài / gỡ / cài lại, dữ liệu sai / lỗi lưu, sao chép Unicode, bảo toàn số 0, chia sẻ tham chiếu và lưu công việc riêng khi thoát. Chưa thử đăng ký trên HIS thực tế.
- Đóng gói theo thư mục dựng của phiên bản và đối chiếu mã trong EXE với nguồn trước khi tạo gói để tránh phát hành mã cũ từ bộ nhớ dựng.

## Nâng cấp và tải về

Đóng phiên bản cũ rồi thay EXE hoặc giải nén ZIP mới. Dữ liệu và cài đặt được giữ tại `%LOCALAPPDATA%\HocVet`; không xóa thư mục này. Công cụ HIS cần được cài trong tab **Tính năng mở rộng**; bảng dữ liệu lưu riêng, không đi kèm file chia sẻ kịch bản.

- `HocVet.exe`: chạy trực tiếp trên Windows, không cần Python.
- `HocVet-v0.17.0-Windows.zip`: ứng dụng, README, ảnh hướng dẫn và giấy phép.
- `SHA256SUMS.txt`: mã kiểm tra EXE và ZIP.

Mặc định dùng chuột: bấm **Dừng** trên bảng nổi. Các phím đã gán, kể cả Esc, chỉ hoạt động ở chế độ **Dùng phím đã gán**. Các giới hạn HIS trong README vẫn áp dụng; chưa xác minh đăng ký trên HIS thực tế.

---

# Học Vẹt v0.16.1

- Hiển thị rõ cả mười mốc 1×–10× trên thanh tốc độ; mức đang chọn được tô đỏ, số lớn cập nhật ngay khi kéo.
- Làm rõ **Số lần chạy** (đơn vị lần) và **Nghỉ giữa các lần** (đơn vị giây), bổ sung nút tăng / giảm và hướng dẫn 0 lần là liên tục, 0 giây là chạy ngay vòng tiếp theo.
- Giữ cách lưu và phát kịch bản, các mức tốc độ và dữ liệu đã có. Kiểm thử thang tốc độ, giá trị lặp / nghỉ và bố cục màn hình chính.

---

# Học Vẹt v0.16.0

- Thêm bộ chỉnh số lần lặp cho từng kịch bản trên bảng nổi: −/+, bấm số để nhập trực tiếp, 0 là liên tục. Lưu riêng cho từng kịch bản, đồng bộ với màn hình chính và giữ số cũ nếu lưu thất bại.
- Kéo cả bốn cạnh hoặc bốn góc để tăng / giảm chiều rộng, chiều cao của bảng. Tự chia lại số kịch bản mỗi trang theo chiều cao và xuống dòng tên theo chiều rộng; giữ nút Dừng / điều hướng trong khung.
- Ghi nhớ kích thước bảng trong dữ liệu ứng dụng sau khi thả chuột, giữ qua lần chạy / cập nhật sau. Giới hạn nhỏ nhất để các nút còn đọc được, lớn nhất theo vùng làm việc của màn hình.
- Khóa chỉnh lặp và kích thước khi đang học / chạy để giữ vùng chuột xuyên bảng ổn định. Chỉnh cấu hình được ở cả hai chế độ; các quy tắc kích hoạt bằng chuột / phím không thay đổi.
- Kiểm thử chỉnh riêng từng kịch bản, nhập số khi cửa sổ chính đang ẩn, hủy / dữ liệu sai / lỗi lưu, lưu kích thước, thu nhỏ / phóng lớn và chuột xuyên bảng.

## Nâng cấp và tải về

Đóng phiên bản cũ rồi thay EXE hoặc giải nén ZIP mới. Dữ liệu, số lần lặp và cài đặt được giữ tại `%LOCALAPPDATA%\HocVet`; không xóa thư mục này.

- `HocVet.exe`: chạy trực tiếp trên Windows, không cần Python.
- `HocVet-v0.16.0-Windows.zip`: ứng dụng, README, ảnh hướng dẫn và giấy phép.
- `SHA256SUMS.txt`: mã kiểm tra EXE và ZIP.

Mặc định dùng chuột: bấm **Dừng** trên bảng nổi. Các phím đã gán, kể cả Esc, chỉ hoạt động ở chế độ **Dùng phím đã gán**. Macro màn hình dùng chuột thật; các giới hạn Windows / HIS trong README vẫn áp dụng. Chưa xác minh trên HIS thực tế.

---

# Học Vẹt v0.15.1

- Từ v0.14.1: thêm bảng nổi có tiến trình và danh sách kịch bản, thu cửa sổ chính vào khay trước khi chạy; lưu lựa chọn kích hoạt bằng chuột hoặc phím.
- Bỏ việc dừng khi tọa độ trùng bảng nổi. Trong lúc phát, bảng dùng chế độ chuột xuyên qua để thao tác đến đúng cửa sổ bên dưới, vẫn giữ hình ảnh và tiến độ.
- Bộ lọc chuột phân biệt thao tác phát với chuột thật. Chỉ chuột thật bấm Dừng mới dừng ở chế độ chuột; không truyền các cú bấm tay khác trên bảng xuống cửa sổ công việc.
- Xác nhận hàng đợi chuột hoàn tất trước khi bật tương tác với bảng trở lại. Bảng giữ nguyên vị trí, không tự chuyển góc để tránh tọa độ.
- Hai chế độ kích hoạt loại trừ nhau: chuột tắt mọi phím gán; phím khóa các nút Học / Chạy / Dừng bằng chuột. Áp dụng cả màn hình chính, bảng nổi và tab Công việc. Có thể dùng chuột để mở Cài đặt và đổi chế độ.
- Kiểm thử phát 10× bấm / cuộn tại đúng nút Dừng trên bảng: cửa sổ mẫu bên dưới nhận thao tác, không kích hoạt nút trên bảng và không tự dừng.

## Nâng cấp và tải về

Đóng phiên bản cũ rồi thay EXE hoặc giải nén ZIP mới. Dữ liệu và cài đặt được giữ tại `%LOCALAPPDATA%\HocVet`; không xóa thư mục này. Mặc định dùng chuột: các phím đã gán, kể cả Esc, chỉ hoạt động sau khi chọn **Dùng phím đã gán** trong Cài đặt.

- `HocVet.exe`: chạy trực tiếp trên Windows, không cần Python.
- `HocVet-v0.15.1-Windows.zip`: ứng dụng, README, ảnh hướng dẫn và giấy phép.
- `SHA256SUMS.txt`: mã kiểm tra EXE và ZIP.

Macro màn hình dùng chuột thật; Công việc riêng có các giới hạn Windows / HIS như mô tả trong README. Chưa xác minh trên HIS thực tế.

---

# Học Vẹt v0.15.0

- Thu cửa sổ chính vào khay trước khi chạy từ nút Chạy, bảng nổi hoặc phím kịch bản. Các yêu cầu chạy liên tiếp trong lúc chuẩn bị không tạo lượt chạy trùng; bấm Dừng hủy được lượt đang chuẩn bị.
- Bảng nổi giữ tiến trình ở trên, danh sách kịch bản và nút Chạy ở dưới; ba kịch bản/trang, hỗ trợ lăn chuột chuyển trang. Có nút Dừng và Mở ứng dụng; không lấy tiêu điểm của cửa sổ công việc.
- Cài đặt cách kích hoạt bằng chuột hoặc phím đã gán, được lưu qua cập nhật. Mặc định bằng chuột để tránh gõ nhầm phím kích hoạt; giữ phím Dừng khẩn cấp ở mọi chế độ.
- Khi đang chạy, khóa chọn kịch bản / chuyển trang / mở cửa sổ chính. Bảng tự chọn góc ít giao tọa độ kịch bản, kéo được tiêu đề khi rảnh. Bộ phát dừng trước thao tác chuột / phím chạm giao diện Học Vẹt, không điều khiển bảng bằng macro.
- Dừng ở bảng nổi trong khi học sẽ dừng và lưu; không ghi thao tác bấm Dừng. Giữ bảng khi hoàn tất, hiển thị 100%, sẵn sàng cho lượt tiếp theo.

Macro màn hình vẫn sử dụng chuột thật; nếu tọa độ giao với bảng và không có góc phù hợp, cần di chuyển bảng hoặc dùng phiên Công việc riêng. Các giới hạn Windows / HIS của v0.14 vẫn áp dụng.

---

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
