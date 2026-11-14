<p align="center">
  <img src="../../.github/assets/hem-banner.svg" alt="Nhà quản lý môi trường - chất lượng không khí thông minh hơn, thoải mái hơn, thông gió và kiểm soát khí hậu" width="1200">
</p>

<p align="center">
  <a href="https://ko-fi.com/chreece"><img src="../../.github/assets/ko-fi-banner.svg" alt="Giúp Chreece tiếp tục Ko-fi" width="500"></a>
</p>



<a id="hem---home-environment-manager"></a>
<!-- HEM-LANGUAGE-SELECTOR-START -->
<p align="center">
  <a href="README.ar.md">العربية</a> · <a href="README.bg.md">Български</a> · <a href="README.bn.md">বাংলা</a> · <a href="README.cs.md">Čeština</a> · <a href="README.da.md">Dansk</a> · <a href="README.de.md">Deutsch</a> · <a href="README.el.md">Ελληνικά</a> · <a href="../../README.md">English</a> · <a href="README.es.md">Español</a> · <a href="README.fa.md">فارسی</a> · <a href="README.fi.md">Suomi</a> · <a href="README.fr.md">Français</a> · <a href="README.he.md">עברית</a> · <a href="README.hi.md">हिन्दी</a> · <a href="README.hr.md">Hrvatski</a> · <a href="README.hu.md">Magyar</a> · <a href="README.id.md">Bahasa Indonesia</a> · <a href="README.it.md">Italiano</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.nb.md">Norsk bokmål</a> · <a href="README.nl.md">Nederlands</a> · <a href="README.pl.md">Polski</a> · <a href="README.pt.md">Português</a> · <a href="README.pt-BR.md">Português (Brasil)</a> · <a href="README.ro.md">Română</a> · <a href="README.ru.md">Русский</a> · <a href="README.sk.md">Slovenčina</a> · <a href="README.sr.md">Српски</a> · <a href="README.sv.md">Svenska</a> · <a href="README.ta.md">தமிழ்</a> · <a href="README.th.md">ไทย</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.uk.md">Українська</a> · <a href="README.ur.md">اردو</a> · <strong>Tiếng Việt</strong> · <a href="README.zh-Hans.md">简体中文</a> · <a href="README.zh-Hant.md">繁體中文</a>
</p>
<!-- HEM-LANGUAGE-SELECTOR-END -->

# HEM - Nhà quản lý môi trường

<p align="center">
  <img src="../../.github/assets/hem-logo.svg" alt="HEM logo" width="420">
</p>

<p align="center"><strong>Toàn bộ môi trường nhà của bạn, trong một Home Assistant Thẻ.</strong></p>

**HEM giúp nhà bạn hiểu được môi trường xung quanh và phản ứng với những gì mỗi phòng thực sự cần.** Nó mang đến cho bạn Home Assistant các cảm biến, dữ liệu thời tiết, thông tin cư trú và các thiết bị khí hậu tương thích cùng nhau để bạn có thể theo dõi chất lượng không khí, nhận lời khuyên thông gió hữu ích, quản lý sự thoải mái và tự động hóa thiết bị bạn chọn.

Ví dụ: HEM có thể làm giảm nhiệt trong khi mọi người đi xa, chuẩn bị cho các phòng được chọn trước khi bạn trở lại, sử dụng một mục tiêu độ ẩm khác nhau trong khi bạn ngủ, hoặc yêu cầu bạn mở cửa sổ trước khi chạy một máy tháo ẩm. Nó cũng có thể chỉ **giám sát và khuyến cáo**, mà không kiểm soát bất kỳ thiết bị nào.

**Cứ giữ trách nhiệm.** Mỗi phòng có cài đặt riêng của mình. Mỗi thiết bị được hỗ trợ có bộ điều khiển riêng, chế độ hoạt động, mục tiêu và giới hạn an toàn của riêng mình. HEM không bao giờ cho rằng việc chọn một thiết bị cho phép nó vận hành thiết bị đó.

[Khám phá các tính năng](#what-can-hem-do) · [Xem giao diện](#see-hem-in-action) · [Lắp đặt HEM](#installation) · [Đặt nhà của bạn](#getting-started) · [Hướng dẫn chi tiết](../../docs/advanced-configuration.md)

<a id="what-can-hem-do"></a>
## Điều gì có thể HEM làm được không?

| Tình hình của bạn | Làm thế nào HEM có thể giúp |
| --- | --- |
| **Ngôi nhà trống rỗng** | Chuyển sang mục tiêu Away, tôn trọng các quy tắc hiện diện của mỗi phòng và tránh chạy thiết bị được chọn không cần thiết. |
| **Anh đang trên đường về nhà.** | Nhấn **Hãy chuẩn bị cho sự đến** sử dụng tạm thời các mục tiêu tiện nghi nhà cho các bộ điều khiển tự động đủ điều kiện, ngay cả khi mọi người vẫn còn xa. |
| **Có ai đó đang ngủ.** | Sử dụng các mục tiêu ngủ, giảm tiếng ồn của quạt, hoặc giữ các thiết bị được chọn tắt trong khi mọi phòng đang ngủ. |
| **Một phòng ẩm ướt.** | So sánh độ ẩm và biểu hiện nấm của nó với các mục tiêu, đề xuất không khí hữu ích, hoặc vận hành một dehumidifier được ủy quyền sử dụng tự động hoặc PID kiểm soát. |
| **Nó nóng và nắng.** | Đánh giá nhiệt độ phòng, ánh sáng mặt trời, thời tiết và các cửa sổ liên lạc kết nối trước khi di chuyển màu sắc được chọn. |
| **Không khí ngoài trời trông tốt hơn.** | khuyến cáo thông gió sử dụng nhu cầu trong nhà, ô nhiễm ngoài trời, nhiệt độ, độ ẩm, gió và phân bột hoặc cảnh báo thời tiết có sẵn. |
| **Một bộ sưởi ấm hoặc TRV ngừng đáp ứng** | Hình bày trạng thái không sẵn sàng hoặc chờ đợi của nó, giữ lại bộ điều khiển được cấu hình của nó và báo cáo lỗi thiết bị được hỗ trợ mà không giả định pin hoặc rel đã phục hồi. |

Đây là những ví dụ, không phải là những hành động HEM Các kết quả phụ thuộc vào các cảm biến bạn chọn, Home Assistant khả năng và cài đặt của bạn chọn vào.

<a id="explore-the-features"></a>
## Khám phá các tính năng

<a id="a-complete-home-dashboard"></a>
### Một bảng điều khiển nhà hoàn chỉnh

Các HEM thẻ cung cấp cho bạn một cái nhìn chung hữu ích mà không cần mở ra một số tích hợp.

- Xem điều kiện ngoài trời, chất lượng không khí và liệu thông gió là tốt hay không.
- So sánh tất cả các phòng được giám sát một cái nhìn: nhiệt độ, độ ẩm tương đối, AQI, PM2.5, chỉ định nấm, ánh sáng và các bài đọc hỗ trợ khác.
- Xây dựng bất kỳ không gian nào cho các phép đo chi tiết, thông tin cửa sổ và cửa, tình trạng khí hậu, kiểm soát viên hoạt động, lý do chờ đợi và ước tính vật lý tòa nhà.
- Xem lịch sử và xu hướng, xem các cảm biến nào góp phần vào trung bình và phân biệt các bài đọc thiếu từ các giá trị được đo.
- Phòng nhóm theo thực tế Home Assistant hoặc sử dụng danh sách phòng đơn giản khi bạn không có sàn.

<a id="different-settings-for-the-home-each-room-and-each-device"></a>
### Cài đặt khác nhau cho nhà, mỗi phòng và mỗi thiết bị

HEM giữ các chính sách chia sẻ tách biệt với các quyết định địa phương.

| Mức cài đặt | Những gì bạn có thể cấu hình |
| --- | --- |
| **Nhà** | Thời tiết ngoài trời và các nguồn ô nhiễm, phòng theo dõi, giới hạn thông gió toàn cầu, sự hiện diện của hộ gia đình, chuẩn bị đến và giao thông báo. |
| **Phòng** | Nguồn nhiệt độ và độ ẩm trong nhà, ngưỡng chất lượng không khí, liên lạc cửa sổ và cửa, hành vi ngủ và chiếm đóng, mục tiêu thoải mái cụ thể cho phòng, thông gió và lựa chọn bóng tối. |
| **Thiết bị cá nhân** | Các chế độ điều khiển có sẵn, tự động/Hướng dẫn/PID Phương pháp, mục tiêu cho mỗi hồ sơ, cảm biến, cài đặt fan tĩnh, thời gian hoạt động tối thiểu, bảo vệ điện, hành vi cửa sổ và thông báo lỗi thiết bị. |

Tất cả ba cấp độ đều có thể truy cập thông qua các thiết lập được nhóm, có thể tìm kiếm trong thẻ. Home Assistant thay đổi thiết lập.

<a id="climate-control-and-pid-device-by-device"></a>
### Kiểm soát khí hậu và PID, thiết bị theo thiết bị

HEM có thể làm việc với tương thích Home Assistant **khí hậu**, **máy làm ẩm** và **fan** Thiết bị, bao gồm cả thiết bị sưởi ấm, làm mát, khử ẩm, làm ẩm và hỗ trợ lưu thông không khí hoặc thiết bị làm sạch không khí.

Đối với mỗi **chế độ hoạt động vật lý được hỗ trợ**, chọn phương pháp kiểm soát độc lập:

| Phương pháp | Ý nghĩa của nó |
| --- | --- |
| **Hiện tại** | Để hoạt động với con đường điều khiển hiện có. |
| **Tự động** | Tiếp theo HEMnhu cầu được đo lường, các mục tiêu và quyền dựa trên tình huống. |
| **PID** | Sử dụng điều khiển tương xứng, tích hợp và phái sinh dựa trên phản hồi khi thiết bị và đo hỗ trợ nó. |
| **Hướng dẫn** | Kiểm soát thông qua các yêu cầu và mục tiêu được hỗ trợ rõ ràng. |
| **Tháo đi.** | Giữ bộ điều khiển đó tắt, theo yêu cầu bảo vệ thể chất và phản hồi. |

Ví dụ, một máy điều hòa không khí có thể sử dụng **PID cho sưởi ấm** và **Tự động để làm mát**Một máy khử độ ẩm có thể có bộ phận riêng. PID tiêu chuẩn, mục tiêu và thời gian chu kỳ. PID khi có phản hồi phù hợp và kiểm soát cụ thể về mục đích.

PID là **Không** một sự thay thế phổ quát: HEM chỉ cung cấp các phương pháp một thiết bị cụ thể, chế độ hoạt động và nguồn phản hồi có thể hỗ trợ. Các tùy chọn nâng cao bao gồm điều chỉnh và hiệu chuẩn theo chế độ, điều chỉnh đề xuất / thích ứng, hoạt động yên tĩnh và cài đặt fan giai đoạn hỗ trợ. Bạn chấp thuận các thay đổi đề xuất trừ khi bạn chọn rõ ràng cho điều chỉnh tự động giới hạn.

<a id="comfortable-when-youre-home-economical-when-youre-away"></a>
### Nỗi thoải mái khi ở nhà, tiết kiệm khi xa

HEM có thể lựa chọn **Sự thoải mái, nhà, xa, ngủ và môi trường** Mục tiêu dựa trên tình hình gia đình, bằng chứng phòng và lựa chọn rõ ràng của bạn.

- **Nhà và xa:** Sử dụng các mục tiêu sưởi ấm, làm mát và độ ẩm khác nhau tùy thuộc vào sự hiện diện tại nhà được xác minh.
- **Sự hiện diện trong phòng:** Sử dụng thiết bị đủ điều kiện luôn luôn khi có nhu cầu, chỉ khi phòng của nó được chiếm đóng, hoặc chỉ khi phòng trống.
- **Giấc ngủ:** Sử dụng các mục tiêu qua đêm và hành vi của người hâm mộ yên tĩnh hơn.
- **Môi trường:** Sử dụng các mục tiêu kinh tế khi được cấu hình. Một cánh cửa bên trong đóng cửa có thể tham gia vào chính sách bảo vệ môi trường khi phòng được xác minh trống và các điều kiện khác được đáp ứng; một cánh cửa đóng cửa một mình không chứng minh căn phòng bị cô lập.
- **Chuẩn bị thức dậy:** Sử dụng một nguồn báo động tiếp theo được cấu hình để bỏ Sleep tự động trước khi báo động và cho các thiết bị đủ điều kiện thời gian để phản ứng.

Nếu việc sử dụng, khả năng sẵn có của thiết bị hoặc bằng chứng yêu cầu khác không chắc chắn, HEM không chỉ đơn giản là giả định là an toàn để khởi động một thiết bị tự động.

<a id="prepare-your-environment-before-you-arrive"></a>
### Chuẩn bị môi trường của bạn trước khi bạn đến

**Hãy chuẩn bị cho sự đến** là một hành động được xác định thời gian cho một ngôi nhà Away xác nhận. bắt đầu nó từ thẻ tiêu đề hoặc HEMthiết bị nhà.

HEM tạm thời áp dụng các cấu hình **Mục tiêu gia đình** cho tự động đủ điều kiệnPID điều khiển để các phòng có thể bắt đầu ấm, làm mát hoặc điều chỉnh độ ẩm trước khi bạn trở lại. **Chỉ khi nó đã có giấy phép kiểm soát vật lý cần thiết**.

Việc chuẩn bị không phải là lệnh để bật mọi thứ. Các thiết bị vẫn cần nhu cầu thực sự, cảm biến và ủy quyền hợp lệ, và phải tôn trọng cửa sổ, thời gian ON/OFF tối thiểu và bảo vệ của riêng họ. Home Assistant khởi động lại không khởi động toàn bộ bộ bộ đồng hồ.

<a id="ventilation-advice-windows-doors-and-shading"></a>
### Lời khuyên về thông gió, cửa sổ, cửa và bóng tối

HEM so sánh **một phòng cần gì** với **không khí ngoài trời có thể giúp**.

- khuyến cáo mở hoặc đóng cửa sổ bằng cách sử dụng các phép đo nội thất hiện tại, độ ẩm ngoài trời, ô nhiễm, nhiệt độ, gió, cảnh báo thời tiết và bối cảnh bột hoa tùy chọn.
- Sử dụng các liên hệ cửa sổ và cửa được chọn để giải thích điều kiện trong phòng và tránh coi một liên hệ không rõ ràng là đóng cửa.
- Tùy chọn yêu cầu bạn thử mở cửa sổ trước khi khởi động thiết bị tự động được hỗ trợ, sau đó tiếp tục điều khiển bình thường sau khi phản ứng được cấu hình chờ nếu cần thiết.
- Sử dụng thông tin cửa để nhận thức ranh giới phòng, cảnh báo thông gió và hành vi Eco bảo vệ tùy chọn.
- Quản lý màn trập, màn trần và màu sắc được chọn bằng cách sử dụng cửa sổ thích hợp, nhiệt độ, thời tiết, độ nắng và bằng chứng chiếu sáng tùy chọn.

HEM có thể cung cấp lời khuyên về thông gió mà không có cửa sổ có thể điều khiển. Nó không tự mở cửa sổ chỉ vì không khí sẽ giúp.

<a id="humidity-mold-indication-and-air-quality"></a>
### Độ ẩm, dấu hiệu nấm và chất lượng không khí

HEM kết hợp các bài đọc được hỗ trợ như: **nhiệt độ, độ ẩm, CO2, hạt, VOC, AQI và độ chiếu sáng** để giúp bạn hiểu từng phòng. Home Assistant thiết lập cung cấp.

Đó là **chỉ định nấm** ước tính điều kiện độ ẩm ở một bề mặt lạnh từ nhiệt độ trong phòng và ngoài trời và một phép đo hiệu chuẩn. Khi được cấu hình đúng cách, nó có thể ảnh hưởng đến mục tiêu hiệu quả của bộ điều khiển độ ẩm tự động được hỗ trợ.

**Chỉ số nấm là một ước tính, không phải là một máy dò nấm hoặc chất xốp.** Dữ liệu cảm biến bị thiếu hoặc lỗi thời không thể biện minh cho lệnh thiết bị dựa trên khuôn mới.

<a id="announcements-diagnostics-and-protection"></a>
### Thông báo, chẩn đoán và bảo vệ

Bạn có thể gửi các khuyến nghị và cảnh báo liên quan thông qua cấu hình Home Assistant thông báo, máy phát truyền thông TTS/media player hoặc **Khu vực thông báo**AI có thể thay đổi cách phát âm một tin nhắn; HEMCác quyết định kiểm soát vật lý vẫn là quyết định.

HEM bao gồm cả các biện pháp bảo vệ và chẩn đoán cụ thể cho thiết bị:

- Thời gian ON và OFF tối thiểu, cài đặt thời gian hoạt động tối đa và xử lý chuyển động điện bên ngoài được hỗ trợ.
- Hạn chế cửa sổ và chiếm đóng, xử lý bằng tay và kiểm tra xác nhận lệnh bản địa.
- Hình báo lỗi và không có thiết bị, với sự lựa chọn hành vi thông báo cho mỗi thiết bị.
- Một chú chó giám sát tùy chọn sau khi đóng cửa cho việc tiếp tục sưởi ấm nghi ngờ sau lệnh OFF, với giám sát được bảo vệ và hạn chế các nỗ lực phục hồi.
- Lý do chờ đợi rõ ràng, tình trạng hoạt động hiện tại và nguồn sẵn có, để bạn có thể điều tra trước khi cho phép kiểm soát nhiều hơn.

**Các giới hạn an toàn vẫn có hiệu lực ngay cả khi cảnh báo bị tắt.** HEM không bao giờ xem xét một chuyến phát hành chỉ huy thành công như là bằng chứng cho thấy một thiết bị đã trả lời vật lý.

<a id="see-hem-in-action"></a>
## Nhìn HEM trong hành động

Những hình minh họa bằng tiếng Anh này sử dụng các phòng mẫu và đo lường. Chúng cho thấy giao diện thay vì hiển thị dữ liệu sống từ một ngôi nhà cụ thể.

<a id="home-at-a-glance"></a>
### Một cái nhìn về nhà

Nhận lời khuyên về thông gió, điều kiện thời tiết và tình trạng của mỗi phòng được giám sát trong một thẻ.

<p align="center">
  <img src="../../docs/images/hem-dashboard-overview.svg" alt="HEM bảng điều khiển nhà với tư vấn thông gió và đọc môi trường trong năm phòng" width="900">
</p>

<a id="expand-a-room-for-full-details"></a>
### Tự mở rộng một phòng cho các chi tiết đầy đủ

Kiểm tra chất lượng không khí, chỉ định nấm, hiện diện, trạng thái cửa sổ, điều khiển khí hậu và giải thích cho mỗi quyết định.

<p align="center">
  <img src="../../docs/images/hem-room-expanded.svg" alt="Bảng điều khiển phòng tắm mở rộng với phép đọc và bộ điều khiển thiết bị độc lập" width="760">
</p>

<a id="home-settings"></a>
### Home Settings

Quản lý các nguồn ngoài trời, sự hiện diện trong toàn nhà, phòng theo dõi, giới hạn thông gió, chuẩn bị và thông báo.

<p align="center">
  <img src="../../docs/images/hem-home-settings.svg" alt="HEM Cài đặt nhà với các nhóm tìm kiếm và quản lý nguồn và phòng" width="900">
</p>

<a id="room-settings"></a>
### Cài đặt phòng

Chọn những gì quan trọng cho mỗi phòng: cảm biến riêng của nó, mục tiêu, chỗ ở, cửa, cửa sổ, thông gió, bóng tối và bảo vệ.

<p align="center">
  <img src="../../docs/images/hem-room-settings.svg" alt="Nhóm HEM Thiết lập phòng cho cảm biến, điều khiển thiết bị, giấc ngủ, cửa sổ và bảo vệ" width="760">
</p>

<a id="device-settings"></a>
### Cài đặt thiết bị

Tốt điều chỉnh một thiết bị mà không thay đổi các thiết bị khác, bao gồm các phương pháp điều khiển được hỗ trợ, PID, hoạt động yên tĩnh, thời gian và báo cáo lỗi.

<p align="center">
  <img src="../../docs/images/hem-device-settings.svg" alt="Nhóm HEM cài đặt thiết bị với điều khiển, PID, bảo vệ năng lượng và thông báo" width="900">
</p>

<a id="getting-started"></a>
## Bắt đầu

1. **Hãy sắp xếp phòng của mình.** Trong Home Assistant, tạo hoặc kiểm tra khu vực của bạn và gán các cảm biến và thiết bị thích hợp cho mỗi người.
2. **Chọn những gì để theo dõi.** Thêm thêm HEM, chọn các phòng bạn quan tâm và xem xét nhiệt độ, độ ẩm, cửa sổ, chất lượng không khí và các nguồn thiết bị được đề xuất.
3. **Thiết lập thông tin chia sẻ.** Chọn các nguồn thời tiết ngoài trời / chất lượng không khí có sẵn, bằng chứng về việc chiếm dụng hộ gia đình và bất kỳ điểm đến thông báo nào bạn muốn.
4. **Thêm thẻ đi.** Mở bảng điều khiển trong chế độ chỉnh sửa và thêm **Nhà quản lý môi trường** Bắt đầu với việc giám sát phòng, đọc và tư vấn thông gió.
5. **Chỉ cho phép điều khiển khi hữu ích.** Mở một phòng, chọn một thiết bị được hỗ trợ, xem xét bộ điều khiển của nó và rõ ràng chọn tự động hoặc PID cho các chế độ bạn muốn HEM để hoạt động.

Anh biết. **Không** bắt đầu với các cảm biến bạn có, và giới thiệu điều khiển tự động một thiết bị tại một thời điểm.

<a id="add-the-card-manually"></a>
### Thêm thẻ bằng tay

Việc tích hợp thường đăng ký thẻ Lovelace của riêng mình.

~~~yaml
type: custom:home-environment-manager-card
~~~

Nếu Home Assistant cài đặt có nhiều hơn một HEM cảm biến khuyến nghị, bạn có thể cần thiết phải thiết lập **đơn vị** rõ ràng:

~~~yaml
type: custom:home-environment-manager-card
entity: sensor.your_hem_recommendation_sensor
~~~

Để biết hướng dẫn từng bước về nguồn phòng, hồ sơ, PID cài đặt, chính sách cửa sổ, chuẩn bị, định đo khuôn, bóng mặt trời và giao thông tin, sử dụng [hướng dẫn cấu hình chi tiết](../../docs/advanced-configuration.md).

<a id="installation"></a>
## Thiết lập

<a id="hacs--home-assistant-community-store"></a>
### HACS / Home Assistant Kho hàng cộng đồng

1. Mở **HACS** trong Home Assistant.
2. Thêm thêm **https://github.com/Chreece/HA-Home-Environment-Manager** như một **kho lưu trữ tùy chỉnh** trong **Tích hợp** hạng mục nếu nó chưa được liệt kê.
3. Tìm ra **Nhà quản lý môi trường** và cài đặt nó.
4. Khởi động lại **Home Assistant** để tải bộ tích hợp.
5. Hãy đi. **Cài đặt → Thiết bị & dịch vụ → Thêm tích hợp**, tìm kiếm **Nhà quản lý môi trường** và hoàn thành việc thiết lập.

<a id="manual-installation"></a>
### Thiết lập thủ công

Bản sao của kho lưu trữ **custom_components/environment_manager** thư mục vào bảng xếp hạng **custom_components** thư mục trong Home Assistant cấu hình, giữ tên thư mục **environment_manager**Bắt đầu lại. Home Assistant và thêm sự tích hợp thông qua **Settings → Thiết bị & dịch vụ**.

Đối với các thay đổi cài đặt sau đó, giữ cho các thiết bị hiện có của bạn HEM integration entry and settings. Load the dashboard in your browser if the card's appearance does not refresh immediately.

<a id="common-questions"></a>
## Những câu hỏi thường gặp

**Tôi có thể sử dụng HEM mà không cho nó kiểm soát các thiết bị của tôi?**

Vâng, giám sát, đo lường, tư vấn thông gió, lịch sử và nhiều chỉ số môi trường hoạt động mà không cho phép kích hoạt thiết bị.

**Will. HEM tự động điều khiển mọi thiết bị nó phát hiện ra?**

Không. Bạn chọn các thiết bị vật lý bạn muốn quản lý và rõ ràng chọn phương pháp điều khiển cho các chế độ được hỗ trợ.

**Có phải mọi thiết bị hỗ trợ PID?**

Không, không. HEM hỗ trợ PID cho **đủ điều kiện** đường làm nóng, làm mát, độ ẩm hoặc điều khiển máy bay khi thiết bị và các phép đo được chọn cung cấp khả năng và phản hồi cần thiết. PID kiểm soát.

**Tôi có thể cho mỗi phòng những quy tắc khác nhau không?**

Đúng vậy, điều kiện cư trú, hành vi ngủ, nguồn, mục tiêu và một số sở thích an toàn có thể khác nhau theo phòng, trong khi mỗi thiết bị vật lý có cài đặt hoạt động và bảo vệ riêng của nó.

**Có thể HEM chuẩn bị cho nhà tôi trong khi tôi đi?**

- Phải, tôi biết. **Hãy chuẩn bị cho sự đến** cho phép các bộ điều khiển tự động đủ điều kiện, đã được ủy quyền sử dụng các mục tiêu Home trong một thời gian giới hạn.

**Một khuyến nghị tốt cho thông gió mở cửa sổ của tôi?**

Không. Nó giải thích khi nào không khí có thể giúp. chuyển động tự động là một tính năng riêng biệt, lựa chọn cho màu sắc hoặc lớp phủ được hỗ trợ đủ điều kiện, tùy thuộc vào kiểm tra an toàn của riêng họ.

**Điều gì sẽ xảy ra nếu một cảm biến hoặc thiết bị không có sẵn?**

HEM phân biệt dữ liệu không rõ ràng từ các bài đọc thực tế, giữ lại thông tin kiểm soát được cấu hình khi có thể và phơi bày lý do chờ đợi và chẩn đoán.

<a id="help-and-troubleshooting"></a>
## Hỗ trợ và giải quyết các vấn đề

Nếu có điều gì đó dường như sai, kiểm tra phòng liên quan hoặc điều khiển **Lý do**, **Chẩn đoán**, nguồn sẵn có và phương pháp kiểm soát hiện tại. [hướng dẫn cấu hình chi tiết](../../docs/advanced-configuration.md) bao gồm các trạng thái chờ chung, chính sách hiện diện, PID sự đủ điều kiện, cửa sổ và giải quyết các lỗi phản ứng thiết bị.

Đối với một vấn đề tái tạo, [mở một GitHub vấn đề](https://github.com/Chreece/HA-Home-Environment-Manager/issues) với hành vi mong đợi, hành vi thực tế, cài đặt phòng / thiết bị liên quan và các bước để tái tạo.

Các đóng góp và cải tiến được hoan nghênh. [CONTRIBUTING.md](../../CONTRIBUTING.md).

<a id="support-and-license"></a>
## Hỗ trợ và giấy phép

Nếu HEM là hữu ích cho bạn, bạn có thể [hỗ trợ Chreece trên Ko-fi](https://ko-fi.com/chreece).

Được phân phối dưới [Giấy phép MIT](../../LICENSE).
