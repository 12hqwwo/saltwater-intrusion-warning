### Các hệ thống và nghiên cứu liên quan

#### Nguồn quan trắc và bản tin hạn mặn

Cổng dữ liệu của Ủy hội sông Mekong (MRC) cung cấp số liệu theo trạm, thông số và thời gian. Báo cáo State of the Basin 2023 sử dụng dữ liệu quan trắc để đánh giá điều kiện lưu vực, trong đó có vấn đề xâm nhập mặn tại Đồng bằng sông Cửu Long [7]. Đối với đề tài, nguồn MRC phù hợp để khảo sát diễn biến EC tại các trạm có chuỗi dài và để thiết lập một bộ nhãn nghiên cứu có thể truy xuất. Giá trị của một mẫu chỉ gắn với vị trí và thời điểm lấy mẫu. Nó không mặc nhiên là trung bình, cực đại của tháng hoặc giá trị tại cống gần trạm.

Các bản tin địa phương cung cấp thông tin phục vụ điều hành theo đợt, thường gồm độ mặn, vị trí và thời điểm đo. Chúng bổ sung bối cảnh vận hành nhưng không thể ghép trực tiếp vào chuỗi EC nếu thông số và đơn vị khác nhau. Một bản tin ghi độ mặn theo g/L và một quan trắc độ dẫn điện theo mS/m phải được lưu ở hai trường riêng. Muốn quy đổi cần phương pháp, nhiệt độ tham chiếu và dữ liệu hiệu chuẩn tại khu vực đo. Việc gắn nhãn nguồn trên bản đồ vì vậy là một yêu cầu của thiết kế dữ liệu, không chỉ là chi tiết trình bày.

#### Nghiên cứu dự báo và trực quan hóa không gian

Các phương pháp chuỗi thời gian như ARIMA khai thác quan hệ giữa giá trị hiện tại và những giá trị trước đó. Random Forest Regressor tiếp nhận đồng thời biến mùa vụ, khí tượng và thủy văn để học quan hệ phi tuyến [1], [4]. Kết quả của hai nhóm phương pháp cần được so sánh trên cùng tập tháng, cùng trạm và cùng giả định về thời điểm dữ liệu đầu vào có thể sử dụng. Một phép chia ngẫu nhiên trên chuỗi thời gian không trả lời đúng câu hỏi dự báo tương lai vì các mẫu gần nhau có thể xuất hiện ở cả tập học và tập kiểm tra [4].

WebGIS kết hợp bản đồ, biểu đồ và thuộc tính đối tượng giúp người dùng xem diễn biến theo cả không gian và thời gian. Bản đồ cũng tạo nguy cơ hiểu sai: màu của một đoạn sông được nội suy có thể bị xem như số đo thực tại mọi điểm trên đoạn. Phương pháp IDW giảm trọng số theo khoảng cách địa lý [10], nhưng khoảng cách đường thẳng không mô tả mạng sông và công trình điều tiết. Với dữ liệu hiện có, việc tạo một bề mặt EC liên tục cho mọi kênh hoặc gán kết quả tại trạm sang từng cống sẽ vượt phạm vi bằng chứng.

#### Hệ thống hỗ trợ quyết định tại công trình

Sàng lọc điều kiện lấy nước cần nhiều thông tin hơn một giá trị EC. Người vận hành còn phải xem mực nước ở hai phía cống, hệ cao độ, thời điểm của phép đo, tình trạng thiết bị và quy trình của công trình. Một hệ thống hỗ trợ có thể kiểm tra tính đầy đủ của các yếu tố này, ghi điều kiện đạt hoặc không đạt và cho biết lý do. Kết quả là thông tin để người có trách nhiệm xem xét; ứng dụng không phát lệnh đóng hoặc mở thiết bị.

Điểm khác biệt của đề tài là giữ ranh giới giữa bốn loại kết quả: quan trắc, dự báo tại trạm, nội suy để trình bày không gian và đánh giá điều kiện từ số liệu hiện trường. Cùng một màu cảnh giác không được dùng để thay thế ý nghĩa của bốn loại dữ liệu. Mỗi kết quả cần có tên thông số, đơn vị, thời gian, nguồn và phương pháp tạo ra nó.

### Những hạn chế của các hướng tiếp cận hiện có

Chuỗi EC có thể dài theo năm nhưng vẫn thưa theo ngày hoặc giờ. Ở ba trạm MRC được tích hợp trong dự án, một tháng thường có một mẫu. Chuỗi đó thích hợp để nghiên cứu giá trị mẫu theo tháng, không đủ để tái dựng đỉnh EC trong ngày hoặc thời điểm nước mặn vượt ngưỡng tại cống. Tập dữ liệu RIA2 có các điểm đo theo đợt nhưng số mẫu ở từng điểm ít; đưa các điểm này vào mô hình tháng như các trạm MRC sẽ tạo ra một tập huấn luyện không đồng nhất.

Kết quả dự báo hồi cứu chịu ảnh hưởng của cách chọn kỳ đánh giá, cách xác định dữ liệu sẵn có và khả năng nhìn thấy tập kiểm tra trong quá trình phát triển. Một MAE thấp của mô hình mới trên giai đoạn đã được dùng để điều chỉnh đặc trưng không phải bằng chứng kiểm định mù. Trường hợp EC cao hiếm cũng khiến sai số trung bình bị chi phối bởi nhiều tháng EC thấp. Vì vậy báo cáo cần trình bày cả sai số tổng thể, sai số tại trường hợp cực trị và đối chứng đơn giản.

Nội suy không gian dựa trên vị trí trạm gặp hai giới hạn. Thứ nhất, các trạm không nhất thiết được lấy mẫu cùng giờ hoặc cùng pha triều. Thứ hai, tuyến sông trên bản đồ chưa xác lập kết nối thủy lực tới mọi nhánh kênh và cống. Sai số đo được tại một điểm neo không chứng minh sai số trên toàn tuyến. Đề tài chỉ diễn giải lớp nội suy như công cụ quan sát xu hướng giữa các điểm có dữ liệu phù hợp.

Một hạn chế khác thuộc về quy tắc vận hành. Ngưỡng EC minh họa trong phần mềm không tự trở thành quy định pháp lý của một cống. Điều kiện lấy nước phụ thuộc mục đích sử dụng nước và kế hoạch của đơn vị quản lý. Ứng dụng phải cho phép xem nguồn và phiên bản của bộ quy tắc, ghi rõ khi người dùng thay đổi tham số và trả trạng thái thiếu dữ liệu thay vì suy đoán giá trị còn thiếu.

### Hướng tiếp cận của đề tài

Đề tài được triển khai thành bốn luồng có ranh giới rõ ràng. Luồng dữ liệu tiếp nhận nguồn EC, khí tượng, thủy văn và hình học; kiểm tra đơn vị, thời gian, tọa độ, bản ghi trùng, giá trị không hợp lệ và lưu nguồn gốc. Luồng mô hình xây dựng đặc trưng theo tháng, huấn luyện và đánh giá theo trình tự thời gian ngoài yêu cầu tương tác của trang web. Luồng bản đồ đọc quan trắc và kết quả mô hình qua API để hiển thị tại đúng trạm, đồng thời minh họa tuyến sông bằng nội suy có nhãn. Luồng cống kiểm tra phiếu hiện trường và các điều kiện cấu hình rồi trả về trạng thái để người vận hành xem xét.

Đối với dự báo, biến mục tiêu là EC của mẫu tháng tại từng trạm, đơn vị mS/m. Mỗi lần dự báo gắn tháng mục tiêu, tháng đầu vào, phiên bản mô hình, đặc trưng thực dùng và trạng thái nguồn. Các mô hình được đánh giá trên cùng tập tháng với baseline giữ EC gần nhất hoặc giá trị cùng tháng năm trước khi dữ liệu đó có thể biết. Kết quả sau tháng 12/2023 chưa có nhãn EC MRC tương ứng trong bộ nghiên cứu, nên không được công bố như đã đạt sai số vận hành.

Đối với không gian, trạm Tân Châu có vai trò giải thích thượng nguồn và điểm neo trên tuyến; Mỹ Thuận và Mỹ Tho nằm trên phần tuyến dùng để khảo sát biến thiên EC. Lớp màu sông sử dụng nội suy tuyến tính từng chặng trên một trục hình học. Vị trí cống được trình bày như đối tượng công trình riêng. Phép chiếu tọa độ cống lên trục để tạo ngữ cảnh dự báo phải có chú giải, vì khoảng cách hình học không xác nhận đường dẫn nước tới cống.

Đối với hỗ trợ vận hành, dự báo tháng có thể kích hoạt mức cảnh giác và yêu cầu mẫu hiện trường còn mới hơn. Nó không tự điền vào ô EC đo ngoài cống. Bộ kiểm tra điều kiện dùng EC và mực nước hai phía, xác nhận cùng hệ cao độ, thời gian đo, trạng thái cơ khí và nguồn số liệu. Kết luận được phân thành cần bổ sung hoặc đo lại, chưa phù hợp để lấy nước và đề nghị xem xét lấy nước. Quy tắc được lưu cùng kết quả để có thể tái hiện lần đánh giá.

[CHÈN ẢNH TẠI ĐÂY: <Sơ đồ bốn luồng dữ liệu gồm nguồn EC, khí tượng, thủy văn và GIS; bước chuẩn hóa và lưu nguồn; nhánh huấn luyện và đánh giá; API và WebGIS; phiếu đo hiện trường và bộ kiểm tra điều kiện cống. Dùng ký hiệu khác nhau cho quan trắc, dự báo, nội suy và dữ liệu người dùng nhập.>]

[TÊN HÌNH: Hình 1.2. Luồng nghiên cứu và ranh giới sử dụng kết quả]

### Tiểu kết chương

Bài toán được giới hạn ở nguyên mẫu WebGIS tra cứu EC, dự báo giá trị mẫu theo tháng tại các trạm có dữ liệu thích hợp và hỗ trợ rà soát điều kiện lấy nước. Cách giới hạn này giữ đúng ý nghĩa của từng nguồn dữ liệu và cho phép đánh giá phần mềm trên bằng chứng có thể truy lại. Các khái niệm, công thức và công nghệ cần cho thiết kế được trình bày ở chương tiếp theo.

## CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ

### Dữ liệu không gian và thời gian

Một quan trắc trong hệ thống được mô tả bởi tối thiểu bốn thành phần: đại lượng đo, giá trị cùng đơn vị, vị trí và thời điểm. Thuộc tính nguồn, phương pháp và cờ chất lượng quyết định cách sử dụng quan trắc. Nếu thiếu vị trí đã xác minh, bản ghi vẫn có thể dùng cho phân tích chuỗi tại một trạm định danh, nhưng không được tự vẽ vào một tọa độ suy đoán. Nếu thiếu thời điểm chi tiết, không thể xác lập quan hệ trước sau ở độ phân giải giờ.

Dữ liệu không gian - thời gian trong đề tài gồm trạm, cống, ranh giới, tuyến sông và các bản ghi EC theo tháng hoặc ngày. Quan hệ một-nhiều giữa trạm và quan trắc cho phép giữ thông tin vị trí riêng khỏi chuỗi đo. Một lần thay đổi tọa độ trạm có thể được quản lý trong danh mục mà không sửa giá trị EC gốc. Với công trình, danh mục cống cũng độc lập với phiếu đo hiện trường và kết quả kiểm tra điều kiện.

Thời gian sự kiện và thời gian sẵn có là hai khái niệm khác nhau. Thời gian sự kiện ghi khi mẫu được lấy hoặc khoảng khí tượng được tổng hợp. Thời gian sẵn có ghi khi nguồn có thể được sử dụng trong một lần phát hành dự báo. Nếu chỉ có tháng của mẫu mà không có ngày công bố thật, giao thức hồi cứu phải khai báo giả định công bố và kiểm tra độ nhạy với giả định đó. Nhãn tháng không thay thế được lịch sử phát hành dữ liệu.

Khi tổng hợp dữ liệu ngày thành tháng, hàm tổng hợp phụ thuộc bản chất biến. Lượng mưa tháng có thể là tổng lượng mưa của các ngày đủ điều kiện; nhiệt độ và tốc độ gió dùng trung bình theo định nghĩa nguồn; mực nước có thể dùng trung bình hoặc một thống kê khác với độ phủ được kiểm tra. EC một mẫu trong tháng vẫn giữ là một mẫu. Nếu giá trị thiếu được nội suy để phục vụ đặc trưng, cột mới phải có nhãn dẫn xuất và không ghi đè quan trắc.

### Hệ tọa độ và dữ liệu GIS

Hình học điểm dùng để biểu diễn trạm và cống; đường biểu diễn tuyến sông; đa giác biểu diễn ranh giới hành chính hoặc vùng nghiên cứu. Mỗi hình học cần gắn hệ quy chiếu tọa độ. Tọa độ kinh độ, vĩ độ theo WGS 84 thường được trao đổi qua API dưới dạng [kinh độ, vĩ độ]. Việc đảo thứ tự hai thành phần có thể đưa đối tượng sang vị trí sai nhưng vẫn tạo ra một cặp số hợp lệ, vì vậy đầu vào phải được kiểm tra cả kiểu dữ liệu lẫn phạm vi tọa độ [5].

Khoảng cách trên kinh độ và vĩ độ không được hiểu trực tiếp là mét. Các phép kiểm khoảng cách đến tuyến hoặc đến cống cần dùng công thức địa lý hoặc hệ chiếu phù hợp. Tuy nhiên, một khoảng cách được tính đúng về hình học vẫn không chứng minh hai điểm thuộc cùng dòng chảy. Trên vùng cửa sông, nhánh sông, kênh và cống tạo thành mạng kết nối có hướng, thay đổi theo triều và trạng thái công trình. Lớp tuyến trong nguyên mẫu chưa thay thế mô hình mạng thủy lực đã hiệu chuẩn.

Trong kho dữ liệu, kiểu geometry của PostGIS lưu hình học cùng SRID và cho phép tạo chỉ mục không gian. Danh mục trạm có thể có cột point; danh mục cống cũng có thể lưu point hoặc trạng thái chưa có tọa độ xác minh. Không nên sinh điểm (0, 0) cho đối tượng thiếu vị trí vì điểm đó là một vị trí địa lý thực. Bản đồ hiển thị trạng thái không xác định vị trí trong danh sách dữ liệu, tách khỏi lớp điểm.

### Electrical Conductivity và xâm nhập mặn

Độ dẫn điện của nước, ký hiệu EC, phản ánh khả năng dẫn dòng điện của dung dịch. Các ion hòa tan góp phần tạo nên khả năng dẫn điện, nên EC có liên hệ với hàm lượng chất hòa tan, trong đó có muối. Quan hệ này phụ thuộc thành phần ion, nhiệt độ và quy trình đo. Đề tài dùng EC như biến mục tiêu để phân tích sự biến động chất lượng nước ở những trạm có chuỗi phù hợp, không định nghĩa EC là độ mặn.

Đơn vị của dữ liệu MRC được giữ ở mS/m. Khi nhập từ nguồn khác, hệ thống phải đọc cả giá trị lẫn đơn vị để tránh so sánh nhầm giữa mS/m, mS/cm và µS/cm. Về mặt đơn vị, 1 mS/cm bằng 100 mS/m, nhưng phép đổi đơn vị không giải quyết vấn đề khác biệt về nhiệt độ bù, thiết bị và vị trí lấy mẫu. Trước khi hợp nhất chuỗi, cần xác nhận giá trị là độ dẫn đo trực tiếp hay độ dẫn đã chuẩn hóa về một nhiệt độ tham chiếu.

Practical Salinity Scale sử dụng độ dẫn điện kết hợp nhiệt độ và áp suất theo phương pháp chuyên ngành [11]. Một hệ số tuyến tính cố định để đổi mọi EC sang g/L có thể tạo cảm giác chính xác giả, nhất là khi nguồn nước có thành phần ion biến đổi theo mùa và vị trí. Vì vậy giao diện giữ EC và độ mặn thành hai thông số; biểu đồ và ngưỡng phải ghi đơn vị. Nếu sau này có cặp đo đồng thời tại các vị trí nghiên cứu, quan hệ chuyển đổi cần được hiệu chỉnh, đánh giá sai số và công bố miền áp dụng.

### Xử lý chuỗi thời gian

Chuỗi EC theo tháng được sắp theo tháng mục tiêu và mã trạm. Trước khi mô hình hóa, hệ thống kiểm tra tháng trùng, giá trị âm hoặc không hữu hạn, khoảng thiếu và sự thay đổi định nghĩa nguồn. Đồ thị theo thời gian giúp nhận diện mức nền, mùa vụ, đỉnh bất thường và các giai đoạn thiếu quan trắc. Một đỉnh cần được đối chiếu bản ghi gốc thay vì loại tự động bằng quy tắc ngoại lai, vì đỉnh thật có thể là sự kiện quan trọng nhất của bài toán.

Đặc trưng trễ có dạng x(t-k), trong đó k là số tháng lùi so với tháng mục tiêu t. Chọn k còn phụ thuộc ngày phát hành. Nếu phát hành đầu tháng t-1, dữ liệu của tháng t-1 có thể chưa được tổng hợp và công bố; dùng x(t-1) trong hồi cứu khi đó gây rò rỉ thông tin. Các thí nghiệm trong dự án sử dụng nhiều giao thức độ trễ khác nhau và phải ghi rõ phiên bản của từng giao thức. Việc so sánh chỉ có ý nghĩa khi các mô hình dùng cùng tập nhãn, thời điểm phát hành và điều kiện khả dụng của đầu vào.

Để biểu diễn mùa vụ, tháng m có thể được mã hóa thành sin(2πm/12) và cos(2πm/12). Cặp giá trị này giữ tính tuần hoàn giữa tháng 12 và tháng 1, khác cách dùng số nguyên 12 và 1 như hai điểm xa nhau. Nó không chứng minh mô hình đã học được quá trình thủy lực theo mùa; đây chỉ là cách mã hóa vị trí của tháng trong năm.

### Mô hình ARIMA

ARIMA(p,d,q) kết hợp thành phần tự hồi quy bậc p, sai phân bậc d và trung bình trượt của sai số bậc q [4]. Sai phân được dùng để xử lý xu hướng không dừng khi phù hợp; thành phần tự hồi quy khai thác các giá trị trước; thành phần sai số mô tả phụ thuộc còn lại. Với chuỗi có mùa vụ, mô hình có thể được mở rộng thành SARIMA bằng các bậc mùa. Mô hình chỉ dùng lịch sử của biến mục tiêu trừ khi được mở rộng với biến ngoại sinh.

Quy trình thử ARIMA gồm quan sát chuỗi và phần dư, xác định biến đổi cần thiết, chọn một tập cấu hình có giới hạn trên tập huấn luyện rồi kiểm tra dự báo trên những tháng đến sau. Không được chọn bậc mô hình bằng cả tập kiểm thử. Ở trạm có chuỗi EC tháng khá dài, ARIMA là mốc so sánh hợp lý để biết mô hình dùng thêm khí tượng và thủy văn có cải thiện thực chất hay không. Khi dữ liệu EC mới đã ngừng từ 2023, một mô hình phụ thuộc nhiều vào các giá trị trễ sẽ khó duy trì dự báo xa mà không cập nhật nhãn.

Sai số của ARIMA vẫn cần được đánh giá theo cùng giao thức thời gian với các phương án khác. Một mô hình khớp lịch sử tốt có thể dự báo kém khi cấu trúc biến động thay đổi hoặc khi xuất hiện đỉnh hiếm. Báo cáo không dùng độ khớp trên tập huấn luyện làm kết luận về khả năng cảnh báo.

### Random Forest Regressor

Random Forest Regressor huấn luyện nhiều cây hồi quy trên các mẫu bootstrap và chọn ngẫu nhiên một tập biến ứng viên tại mỗi lần chia nút. Dự báo hồi quy là trung bình kết quả của các cây [1]. Cách kết hợp làm giảm độ nhạy của một cây đơn lẻ và cho phép học quan hệ phi tuyến, tương tác giữa đặc trưng mùa, mưa, nhiệt độ, gió, lưu lượng và mực nước. Các tham số như số cây, độ sâu tối đa và số mẫu tối thiểu ở lá ảnh hưởng đến mức độ linh hoạt.

Đặc trưng đầu vào phải được xác định theo đúng thời điểm phát hành. Mô hình Mỹ Tho hiện hành sử dụng mùa vụ, khí tượng và một nhóm biến thủy văn thượng nguồn theo độ trễ được khai báo; mô hình của các trạm khác có registry riêng. Một form web nhận khí tượng do người dùng nhập không biến mô hình Mỹ Tho thành mô hình đã được kiểm định cho vị trí nhập. Kết quả luôn gắn tên trạm đích của mô hình.

Random Forest thường dự báo trong miền giá trị đã được biểu diễn bởi các lá cây, nên các đỉnh EC hiếm có thể bị làm phẳng. Do đó báo cáo cần xem sai số trên nhóm EC cao và từng tháng lệch lớn, không chỉ điểm số trung bình. Độ quan trọng của biến do thuật toán xuất ra cũng không được diễn giải là quan hệ nhân quả; lưu lượng và EC có thể đồng biến theo mùa vì nhiều yếu tố chung chưa được kiểm soát.

### Chỉ số đánh giá MAE và RMSE

Với n cặp giá trị thực y(i) và dự báo ŷ(i), MAE = (1/n) × Σ|y(i) - ŷ(i)|. Chỉ số có cùng đơn vị với EC và cho biết độ lớn sai số tuyệt đối trung bình. RMSE = √[(1/n) × Σ(y(i) - ŷ(i))²]. Phép bình phương làm các sai số lớn đóng góp mạnh hơn, hữu ích khi cần phát hiện mô hình bỏ sót đỉnh hoặc báo cao giả. Cả hai chỉ số phải ghi số mẫu, khoảng thời gian và trạm được tính.

Một bảng so sánh chỉ hợp lệ khi các mô hình được chấm trên cùng cặp tháng và cùng nhãn nguồn. Nếu mô hình A bỏ qua các tháng khó do thiếu đầu vào, còn mô hình B được chấm cả những tháng đó, so sánh hai MAE có thể gây sai lệch. Đề tài giữ danh sách tháng được chấm và nguyên nhân loại mẫu. Khi tính sai số theo nhóm EC cao, ngưỡng nhóm phải được xác định trước trên phần dữ liệu phù hợp, không lấy phân vị từ toàn bộ tập kiểm tra rồi tuyên bố khả năng phát hiện đã được kiểm định độc lập.

MAE và RMSE không phải xác suất đúng của một dự báo riêng. Một mô hình đạt MAE thấp trên 24 tháng vẫn có thể sai rất lớn tại một tháng cụ thể. Đối với hỗ trợ cống, cần đánh giá thêm hệ quả của báo cao giả và bỏ sót trạng thái rủi ro trên số liệu tại cống có xác minh; bộ dữ liệu hiện tại chưa cho phép kết luận này.

### Nội suy không gian IDW và nội suy dọc sông

IDW ước lượng giá trị z(x) tại vị trí x bằng trung bình có trọng số của các điểm đo z(i): z(x) = Σw(i)z(i) / Σw(i), với w(i) = 1/d(x,i)^p, p > 0 [10]. Khi x trùng một điểm đo, giá trị điểm đo được giữ để tránh chia cho khoảng cách bằng không. Tham số p càng lớn thì các điểm gần càng chi phối kết quả. Phương pháp cần các điểm đầu vào có cùng đại lượng, đơn vị và khoảng thời gian so sánh được.

Nội suy là một phép ước lượng có sai số, không đơn thuần là thao tác tô màu. Việc chọn điểm đầu vào, cấu trúc không gian và cách kiểm tra bằng các điểm giữ lại cần được xác định trước khi diễn giải bề mặt [2]. Nếu chỉ có một số trạm trên một trục sông, không thể dùng phép kiểm tại một điểm duy nhất để suy sai số tại mọi nhánh kênh. Đề tài vì vậy báo cáo sai số tại vị trí kiểm tra và giới hạn phạm vi kết luận theo đúng tập điểm được dùng.

IDW dùng khoảng cách hình học, không mô hình hóa dòng chảy, triều, pha mặn hoặc tác động đóng mở cống. Với các trạm thưa và nhiều nhánh sông, một bề mặt IDW có thể nối các điểm không liên hệ thủy lực. Vì vậy đề tài trình bày IDW như phương án lý thuyết trong sườn nghiên cứu, nhưng phần mềm hiện hành không công bố một bản đồ trường EC IDW đã hiệu chuẩn. Quyết định này giữ đúng giới hạn dữ liệu thay vì tạo bề mặt có vẻ liên tục mà không có kiểm chứng.

Lớp sông của nguyên mẫu dùng nội suy tuyến tính từng chặng trên trục hình học giữa các điểm neo Tân Châu, Mỹ Thuận và Mỹ Tho. Nếu s nằm giữa hai vị trí s(a) và s(b), tỷ lệ r = [s - s(a)]/[s(b) - s(a)], thì EC(s) = [1-r]EC(a) + rEC(b). Các giá trị đầu mút phải thuộc cùng kỳ và cùng loại kết quả. Khi thiếu Mỹ Thuận, hệ thống có chế độ dự phòng dùng hai điểm neo còn lại và gắn nhãn chế độ. Kết quả chỉ là lớp hiển thị dọc một tuyến, không phải EC đo tại mọi điểm hay tại cống.

[CHÈN ẢNH TẠI ĐÂY: <Sơ đồ so sánh khoảng cách đường thẳng dùng trong IDW với khoảng cách dọc tuyến sông; thể hiện ba điểm neo Tân Châu, Mỹ Thuận, Mỹ Tho, một nhánh kênh và một cống ở gần về tọa độ nhưng chưa xác minh kết nối thủy lực.>]

[TÊN HÌNH: Hình 2.1. Khác biệt giữa nội suy theo khoảng cách địa lý và nội suy dọc tuyến sông]

### PostgreSQL và PostGIS

PostgreSQL là hệ quản trị cơ sở dữ liệu quan hệ dùng để quản lý trạm, nguồn dữ liệu, quan trắc và hồ sơ công trình. PostGIS bổ sung kiểu hình học, hàm và chỉ mục không gian [8]. Thiết kế quan hệ tách danh mục trạm khỏi bản ghi EC để tránh lặp tọa độ và tên trạm trong từng dòng quan trắc. Khóa ngoại từ quan trắc đến trạm và nguồn dữ liệu giúp kiểm tra tính toàn vẹn tham chiếu.

Một bản ghi EC cần có mã trạm, thời điểm hoặc tháng, thông số, giá trị, đơn vị, mã nguồn và trạng thái chất lượng. Ràng buộc giá trị hữu hạn, không âm và duy nhất theo khóa nghiệp vụ giúp loại lỗi ở tầng lưu trữ. Tuy nhiên, ràng buộc cơ sở dữ liệu không thay thế được kiểm tra ý nghĩa: một giá trị EC hợp lệ về kiểu số vẫn có thể mang sai đơn vị hoặc gắn nhầm trạm. Pipeline tiếp nhận phải kiểm tra metadata trước khi ghi.

Hệ thống cũng có chế độ đọc snapshot nghiên cứu có manifest và checksum. Hai chế độ là hai nguồn đọc được chọn rõ ràng. Khi PostgreSQL lỗi, việc tự chuyển âm thầm sang snapshot có thể khiến người dùng tưởng đang xem dữ liệu mới; vì vậy lỗi kết nối được trả riêng. Kết quả dự báo và các phiếu hiện trường được lưu trong cấu trúc tách khỏi bảng quan trắc gốc để không làm tăng số mẫu đo thực.

### FastAPI và RESTful API

FastAPI cung cấp định tuyến HTTP, kiểm tra dữ liệu đầu vào và mô tả giao diện API theo OpenAPI [3]. Các tài nguyên chính của nguyên mẫu gồm danh mục trạm, quan trắc, nguồn dữ liệu, dự báo, lớp không gian và hồ sơ cống. Một phản hồi cần đủ thông tin để giao diện giải thích kết quả: mã trạm, thông số, giá trị, đơn vị, thời gian, nguồn, phiên bản mô hình hoặc bộ quy tắc và các cờ chất lượng liên quan.

API được tách khỏi tính toán mô hình. Tầng route kiểm tra tham số và mã lỗi; service điều phối ca sử dụng; repository đọc nguồn dữ liệu; domain chứa quy tắc và phép tính. Khi người dùng yêu cầu dự báo, service đọc artifact mô hình đã đăng ký rồi suy luận. Huấn luyện và chấm mô hình chạy ngoài request web để kết quả tương tác không thay đổi tùy thời điểm và để giữ bằng chứng của từng lần huấn luyện.

Mã lỗi cũng là một phần của hợp đồng. Thiếu tháng đầu vào, trạm không có mô hình, dữ liệu nguồn cũ hoặc checksum artifact không khớp cần được thông báo bằng trạng thái riêng. Trả HTTP 200 với số không thay cho dự báo không tồn tại sẽ làm sai cả biểu đồ và quyết định tiếp theo. API không phát sinh trường lệnh điều khiển thiết bị.

### GeoJSON

GeoJSON biểu diễn hình học và thuộc tính dưới dạng JSON. Một Feature gồm geometry và properties; FeatureCollection chứa tập Feature. Theo RFC 7946, thứ tự tọa độ trong hệ tham chiếu mặc định là kinh độ rồi vĩ độ [5]. Cấu trúc này phù hợp để API chuyển vị trí trạm, cống, tuyến sông hoặc ranh giới tới giao diện bản đồ mà vẫn mang theo mã đối tượng, tên, nguồn và trạng thái xác minh.

Các thuộc tính nghiệp vụ không nên được suy ra từ hình học. Một Feature cống có tọa độ hợp lệ nhưng chưa có quan trắc hai phía vẫn phải thể hiện trạng thái thiếu dữ liệu. Với đối tượng chưa xác minh tọa độ, danh mục có thể trả bản ghi thuộc tính riêng và không tạo Feature điểm giả. Trước khi hiển thị, giao diện kiểm tra loại geometry và miền tọa độ để tránh bản đồ nhảy đến vị trí ngoài nghiên cứu.

### Công nghệ bản đồ phía trình duyệt

Leaflet.js là thư viện được khảo sát trong kế hoạch ban đầu vì cung cấp thao tác bản đồ và lớp GeoJSON tương đối gọn [6]. Bản cài đặt hiện hành của đề tài sử dụng OpenLayers 6 trong frontend, kết hợp JavaScript và Vite để tổ chức các lớp dữ liệu [9]. Phần mô tả triển khai ở chương 4 dựa trên mã hiện hành; không ghi Leaflet là thư viện đang chạy chỉ vì nó xuất hiện trong sườn bản thảo.

OpenLayers quản lý nền bản đồ, lớp điểm trạm, lớp cống, tuyến sông và sự kiện chọn đối tượng. Giao diện liên kết bản đồ với bảng và biểu đồ chuỗi thời gian. Mỗi lớp có chú giải để phân biệt quan trắc, dự báo, nội suy và phiếu thực địa đã duyệt. Khi đổi trạm hoặc kỳ, kết quả của yêu cầu cũ cần bị hủy hoặc đánh dấu không còn hiện hành nhằm tránh hiển thị dự báo của trạm trước dưới tên trạm mới.

### Tiểu kết chương

Các khái niệm về EC, thời gian sẵn có, sai số dự báo và khoảng cách không gian xác định cách dữ liệu được đưa vào hệ thống. PostgreSQL/PostGIS quản lý quan hệ và hình học; FastAPI cung cấp hợp đồng truy cập; GeoJSON và OpenLayers phục vụ biểu diễn bản đồ. Chương tiếp theo chuyển các nguyên tắc này thành yêu cầu và hồ sơ thiết kế cụ thể.

## PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG

### Phân tích yêu cầu

#### Tác nhân và ca sử dụng

Người xem dữ liệu chọn trạm hoặc khoảng thời gian để tra cứu EC, nguồn, biểu đồ và kết quả dự báo. Người nghiên cứu kiểm tra giao thức thí nghiệm, baseline, sai số và phiên bản artifact. Người rà soát công trình chọn cống, nhập một bộ số đo hiện trường, cấu hình quy tắc được phép và xem trạng thái từng điều kiện. Người quản trị dữ liệu kiểm tra nguồn trước khi tiếp nhận, quản lý tài khoản và quyền ghi khi hệ thống bật chức năng lưu. Đây là các vai trò phần mềm; quyền phê duyệt vận hành công trình vẫn thuộc quy trình bên ngoài.

Một ca sử dụng tra cứu bắt đầu từ danh mục trạm. Sau khi chọn trạm, API trả metadata và các quan trắc phù hợp bộ lọc. Giao diện vẽ điểm lên bản đồ, đồ thị theo thời gian và bảng chi tiết. Một ca dự báo bắt đầu từ trạm có artifact đã đăng ký, tháng mục tiêu và nguồn đặc trưng. Service kiểm tra tính đầy đủ, suy luận rồi trả kết quả có phiên bản. Một ca rà soát cống bắt đầu từ hồ sơ công trình và bộ đo cùng thời điểm; engine kiểm từng điều kiện và trả một kết luận cùng lý do.

#### Yêu cầu chức năng

Nhóm F1 yêu cầu quản lý danh mục trạm và cống, gồm mã ổn định, tên, vị trí, nguồn tọa độ và trạng thái xác minh. Nhóm F2 yêu cầu tiếp nhận và tra cứu quan trắc theo trạm, thông số, thời gian, nguồn và đơn vị. Nhóm F3 yêu cầu hiển thị dữ liệu trên bản đồ và biểu đồ, phân biệt số đo với giá trị dẫn xuất. Nhóm F4 yêu cầu suy luận dự báo từ mô hình đã đăng ký và cung cấp bảng kiểm chứng hồi cứu, baseline, MAE, RMSE. Nhóm F5 yêu cầu hiển thị nội suy dọc tuyến kèm tập điểm neo và chế độ dự phòng. Nhóm F6 yêu cầu kiểm tra điều kiện tại cống từ số đo hai phía, thời điểm, hệ cao độ và trạng thái cơ khí. Nhóm F7 yêu cầu lưu hoặc xuất kết quả nghiên cứu và hồ sơ rà soát theo quyền được cấu hình.

Trong F4, hệ thống phải từ chối yêu cầu khi trạm không có mô hình, tháng nguồn chưa đủ hoặc artifact không khớp manifest. Trong F6, thiếu dữ liệu hoặc mẫu hết hạn được ưu tiên báo là cần bổ sung, kể cả khi một điều kiện khác đang không đạt. Điều này tránh diễn giải một bộ đo không hoàn chỉnh thành kết luận vận hành. F3 không được vẽ giá trị không có dữ liệu bằng màu của EC bằng không. Các quy tắc này được viết thành test case vì chúng ảnh hưởng trực tiếp đến cách người dùng hiểu kết quả.

#### Yêu cầu phi chức năng

Tính truy xuất yêu cầu mỗi giá trị dự báo có thể xác định bộ nguồn, phiên bản mô hình, tháng đặc trưng và giao thức. Tính nhất quán yêu cầu cùng đầu vào và cùng phiên bản quy tắc tạo cùng kết quả; thời điểm đánh giá phải là một tham số rõ ràng. Tính an toàn dữ liệu yêu cầu quan trắc gốc, kết quả mô hình và phiếu người dùng khai báo nằm ở các bảng hoặc lớp dữ liệu khác nhau. Tính khả dụng yêu cầu giao diện thông báo trạng thái lỗi bằng ngôn ngữ dễ hiểu, trong khi API vẫn trả mã lỗi và lý do có cấu trúc.

Khả năng mở rộng được xem xét ở mức nguyên mẫu: thêm trạm không đòi hỏi sửa cấu trúc toàn bộ ứng dụng, nhưng trạm mới chỉ có chức năng dự báo sau khi có dữ liệu, mô hình và đánh giá tương ứng. API đọc dữ liệu có phân trang hoặc lọc thời gian để tránh gửi toàn bộ chuỗi dài cho mỗi thao tác. Các thao tác lưu có kiểm soát quyền và không sửa bản ghi quan trắc khi người dùng thử một kịch bản.

[CHÈN ẢNH TẠI ĐÂY: <Sơ đồ ca sử dụng UML gồm bốn tác nhân người xem dữ liệu, người nghiên cứu, người rà soát cống và quản trị dữ liệu; nối tới tra cứu quan trắc, xem dự báo, xem kiểm chứng, xuất dữ liệu, nhập phiếu hiện trường, kiểm điều kiện và tiếp nhận nguồn.>]

[TÊN HÌNH: Hình 3.1. Sơ đồ ca sử dụng của nguyên mẫu WebGIS]

### Quy trình nghiên cứu và luồng dữ liệu

Dữ liệu gốc được lưu trước khi xử lý để có thể tái lập. Pipeline đọc tệp hoặc phản hồi nguồn, kiểm định schema, chuẩn hóa thời gian và đơn vị, gắn cờ chất lượng, sau đó tạo snapshot nghiên cứu hoặc nạp PostgreSQL theo bước riêng. Tập đặc trưng được xây từ bản đã kiểm tra, không lấy trực tiếp từ phản hồi giao diện. Kết quả huấn luyện gồm artifact mô hình, cấu hình, danh sách tháng đánh giá, dự báo từng tháng, metric và mã băm các nguồn liên quan.

Khi người dùng mở WebGIS, backend chọn nguồn đọc theo chế độ cấu hình và trả metadata tương ứng. Chế độ snapshot đọc các tệp có manifest; chế độ PostgreSQL đọc bảng đã nạp. Dù ở chế độ nào, artifact mô hình có thể vẫn nằm trong kho tệp riêng. Giao diện phải trình bày nguồn thực của từng khối thay vì đặt một huy hiệu chung khiến người dùng nghĩ tất cả đều đến từ cơ sở dữ liệu.

Một lần suy luận dự báo không cập nhật trọng số mô hình. Đầu vào được kiểm tra điều kiện thời gian, tính đặc trưng theo đúng công thức của artifact rồi tạo kết quả có mã phiên bản. Khi người dùng thay đổi tháng, lựa chọn trạm hoặc nguồn, kết quả cũ được hủy trên giao diện. Luồng rà soát cống dùng dữ liệu hiện trường do người dùng khai báo hoặc phiếu đã duyệt, tách khỏi quan trắc MRC và không tự tham gia huấn luyện.

[CHÈN ẢNH TẠI ĐÂY: <Sơ đồ hoạt động thể hiện dữ liệu gốc, kiểm tra chất lượng, snapshot và PostgreSQL, tạo đặc trưng, huấn luyện ngoài web, artifact đã đăng ký, FastAPI, WebGIS và phiếu cống. Chỉ rõ đường ghi dữ liệu và đường đọc dữ liệu.>]

[TÊN HÌNH: Hình 3.2. Quy trình xử lý và sử dụng dữ liệu]

### Thiết kế kiến trúc hệ thống

Kiến trúc gồm tầng dữ liệu, tầng nghiệp vụ/API và tầng giao diện. Tầng dữ liệu bao gồm nguồn gốc, snapshot, PostgreSQL/PostGIS và artifact mô hình. Tầng nghiệp vụ chia route HTTP, service điều phối, repository đọc ghi và domain chứa phép tính. Tầng giao diện gồm các trang quan trắc, dự báo, chất lượng dữ liệu và công trình, sử dụng OpenLayers cho bản đồ cùng biểu đồ và bảng để tra cứu chuỗi thời gian.

Việc tách tầng giúp kiểm thử phép tính mà không cần khởi động trình duyệt. Hàm nội suy nhận các điểm neo và vị trí dọc tuyến; engine cống nhận bộ đo, RuleProfile, ngữ cảnh dự báo và thời điểm đánh giá. Hai hàm không phụ thuộc vào hình thức vẽ bản đồ. Ngược lại, API không cài đặt lại công thức ở route, tránh trường hợp hai endpoint dùng hai quy tắc khác nhau.

Luồng huấn luyện mô hình là một tác vụ riêng. Script nghiên cứu đọc dữ liệu đã chốt, tính đặc trưng, đánh giá theo giao thức và lưu artifact. Backend chỉ đọc phiên bản được registry chọn. Việc có một artifact mới trong thư mục không tự làm thay đổi kết quả đang phục vụ; bước tiếp nhận phiên bản phải kiểm metadata, checksum và hợp đồng đầu ra.

[CHÈN ẢNH TẠI ĐÂY: <Sơ đồ kiến trúc ba tầng với các khối nguồn dữ liệu, PostgreSQL/PostGIS, snapshot, artifact mô hình, repository, domain, service, FastAPI và frontend OpenLayers; thể hiện tác vụ huấn luyện nằm ngoài luồng request.>]

[TÊN HÌNH: Hình 3.3. Kiến trúc tổng thể của hệ thống]

### Thiết kế cơ sở dữ liệu

#### Mô hình thực thể và quan hệ

Thực thể measurement_site lưu mã, tên, loại trạm, vị trí và nguồn tọa độ. Thực thể source_dataset mô tả bộ dữ liệu, đơn vị, thời kỳ, nơi tải và thông tin kiểm tra. conductivity_observation tham chiếu một trạm và một bộ nguồn; mỗi dòng giữ thời điểm mẫu, giá trị EC, đơn vị và cờ chất lượng. irrigation_gate lưu hồ sơ cống, vị trí nếu đã xác minh và các thuộc tính danh mục. Các bảng bổ trợ lưu phiên bản mô hình, dự báo, RuleProfile, phiếu hiện trường và kết quả rà soát nhưng không ghi các giá trị dẫn xuất vào bảng quan trắc gốc.

Quan hệ một-nhiều giữa measurement_site và conductivity_observation phản ánh một trạm có nhiều mẫu. Quan hệ một-nhiều giữa source_dataset và conductivity_observation cho biết nhiều mẫu có thể đến từ một bộ nguồn; mỗi mẫu vẫn cần xác định phiên bản dữ liệu được nhập. Một cống có thể có nhiều phiếu đo theo thời gian. Một phiếu có thể sinh nhiều lần đánh giá nếu RuleProfile thay đổi, nên kết quả phải giữ mã quy tắc và thời điểm đánh giá để không ghi đè lịch sử.

[CHÈN ẢNH TẠI ĐÂY: <Sơ đồ ERD thể hiện measurement_site, source_dataset, conductivity_observation, irrigation_gate, field_measurement, forecast_result, rule_profile và gate_screening_result; ghi khóa chính, khóa ngoại và bội số 1-n cho các quan hệ.>]

[TÊN HÌNH: Hình 3.4. Sơ đồ quan hệ dữ liệu phục vụ quan trắc, dự báo và cống]

#### Ràng buộc và dữ liệu không gian

Khóa nghiệp vụ của quan trắc cần ngăn trùng cùng trạm, thông số, thời điểm và phiên bản nguồn. EC phải là số hữu hạn không âm; thời điểm phải có định dạng xác định. Các ràng buộc này được kiểm lại ở bước ETL để báo lỗi theo từng dòng trước khi nạp. Một bản ghi bị cách ly vẫn được ghi trong nhật ký xử lý với lý do; không biến mất khỏi tổng số dòng nguồn mà không giải thích.

Cột hình học của trạm và cống dùng kiểu Point với SRID được xác định. Tuyến sông dùng LineString hoặc MultiLineString; ranh giới tỉnh dùng Polygon hoặc MultiPolygon. Chỉ mục không gian phục vụ lọc vùng nhìn thấy trên bản đồ. Các vị trí chưa xác minh giữ NULL và cờ trạng thái, không điền tọa độ trung tâm tỉnh làm đại diện cho một cống cụ thể.

Thời gian và nguồn dữ liệu được lập chỉ mục theo nhu cầu truy vấn. Truy vấn biểu đồ thường lọc mã trạm và khoảng tháng; truy vấn bản đồ lọc loại đối tượng và phạm vi hiển thị. Việc tách hai hướng truy vấn tránh gửi toàn bộ lịch sử EC khi người dùng chỉ cần các điểm trên bản đồ. Kết quả dự báo lưu một phiên bản riêng để một lần thay mô hình không làm thay đổi các dự báo đã công bố trước đó.

### Thiết kế ETL Pipeline

ETL gồm ba bước: trích xuất, biến đổi và nạp. Trích xuất giữ nguyên tệp nguồn hoặc phản hồi API cùng manifest và mã băm. Biến đổi kiểm tra schema, mã trạm, đơn vị, thời gian, tọa độ và giá trị. Nạp dữ liệu đã đạt điều kiện vào snapshot hoặc bảng đích; các bản ghi không đạt được đưa vào danh sách kiểm tra. Pipeline có thể chạy lại trên cùng nguồn mà không tạo bản ghi trùng.

Ở bước chuẩn hóa thời gian, ngày có múi giờ được đổi về chuẩn nội bộ nhất quán; bản ghi chỉ có ngày hoặc tháng không được tự thêm một giờ đo giả. Nếu hệ thống cần timestamp kỹ thuật để lưu, metadata phải giữ độ chính xác ban đầu. Ở bước chuẩn hóa đơn vị, chỉ thực hiện phép đổi đơn vị đã xác định rõ, chẳng hạn mS/cm sang mS/m. EC và độ mặn thuộc hai thông số khác nhau nên không có bước đổi chung bằng một hệ số cố định.

Đối với dữ liệu không gian, ETL kiểm tra miền kinh vĩ độ, hệ tọa độ và hình học hợp lệ. Một vị trí ngoài ranh giới nghiên cứu chưa chắc sai, vì Tân Châu là trạm giải thích thượng nguồn. Quy tắc kiểm tra phải phân biệt vị trí ngoài vùng chính có chủ đích và tọa độ nhập nhầm. Sau nạp, pipeline đối chiếu số bản ghi, số tháng, giá trị nhỏ nhất/lớn nhất và checksum với manifest để phát hiện sai khác.

### Thiết kế module dự báo

Mỗi trạm có hồ sơ mô hình gồm mã trạm đích, biến mục tiêu, đơn vị, danh sách đặc trưng, cách tính độ trễ, thời kỳ nhãn, giao thức đánh giá và phiên bản artifact. Service chỉ cho phép suy luận khi tất cả đặc trưng cần thiết hợp lệ. Với mô hình Mỹ Tho có biến thủy văn, thiếu lưu lượng Kratie hoặc mực nước Tân Châu theo tháng yêu cầu phải dẫn đến lỗi thiếu đầu vào, không âm thầm chuyển sang một mô hình khác.

Đầu ra chứa tháng mục tiêu, giá trị EC dự báo, đơn vị mS/m, phiên bản mô hình, dấu nguồn, kỳ dữ liệu và thông báo giới hạn. Các chỉ số hồi cứu được xuất ở trường riêng, không gắn thành khoảng tin cậy cho giá trị mới. Baseline trong bảng đánh giá phải dùng cùng tập tháng và cùng điều kiện khả dụng đầu vào. Các dự báo lưu từ phiên bản cũ được giữ nguyên phiên bản để người dùng phân biệt kết quả trước và sau cập nhật.

### Thiết kế module nội suy không gian

Module nhận danh sách điểm neo có thứ tự dọc trục sông và EC cùng kỳ. Trước khi tính, nó kiểm tra số điểm tối thiểu, giá trị hữu hạn không âm và vị trí dọc tuyến tăng nghiêm ngặt. Với một vị trí nằm giữa hai neo, module tính tỷ lệ dọc đoạn và giá trị tuyến tính. Tại điểm neo, kết quả bằng chính giá trị đầu vào. Ngoài đoạn có neo, hệ thống không kéo dài một xu thế tuyến tính vô hạn; phần hiển thị dùng quy tắc biên riêng có nhãn.

Khi Mỹ Thuận không có kết quả phù hợp cho kỳ đang xem, chế độ dự phòng dùng Tân Châu và Mỹ Tho. Tên chế độ nội suy được trả cùng dữ liệu để lớp màu và chú giải có thể cho biết điểm neo thực dùng. Bản đồ tạo dải màu theo khoảng cách tích lũy của hình học tuyến, không theo số thứ tự đỉnh. Mật độ đỉnh của tệp hình học vì vậy không làm thay đổi vị trí chuyển màu trên một đoạn sông.

### Thiết kế Decision Logic

RuleProfile gồm tên, phiên bản, ngưỡng EC hai phía, chênh lệch mực nước dương tối thiểu, yêu cầu cùng hệ cao độ, trạng thái cơ khí được chấp nhận và tuổi mẫu tối đa. Các ngưỡng mặc định là cấu hình kỹ thuật phục vụ kiểm tra tính nhất quán, không được ghi là quy trình vận hành chính thức của một cống. Khi người dùng sửa ngưỡng, kết quả phải gắn phiên bản hoặc dấu tùy chỉnh và lưu toàn bộ cấu hình đã dùng.

Một lần đánh giá tính tuổi mẫu từ thời điểm đo đến thời điểm đánh giá, không từ lúc bấm nút. Mẫu ở tương lai, EC âm, số không hữu hạn hoặc thời điểm không tồn tại trên lịch bị từ chối. Mực nước có thể âm theo mốc cao độ nên điều kiện mực nước không được viết như điều kiện EC. Chênh lệch hai phía chỉ được tính khi hai số đo cùng hệ cao độ và thuộc một bộ đo có thể so sánh.

Kết quả tổng hợp theo thứ tự: thiếu hoặc quá hạn thì cần bổ sung hoặc đo lại; đủ dữ liệu nhưng có điều kiện không đạt thì chưa phù hợp; tất cả điều kiện đạt thì đề nghị xem xét lấy nước. Bảng chi tiết vẫn giữ mọi vi phạm để người vận hành không bỏ sót một nguyên nhân chỉ vì kết luận chung đã được xác định. Ngữ cảnh dự báo có thể rút ngắn thời hạn chấp nhận mẫu khi mức cảnh giác cao, nhưng không thay thế số đo tại cống.

### Thiết kế API và giao diện WebGIS

Các endpoint quan trắc nhận mã trạm, khoảng thời gian và giới hạn số bản ghi. Endpoint mô hình nhận trạm cùng tháng mục tiêu rồi trả dữ liệu đầu vào được chọn và kết quả suy luận. Endpoint không gian trả GeoJSON có metadata nguồn; endpoint cống trả hồ sơ và cho phép kiểm tra một bộ đo theo RuleProfile. Tên trường số phải có đơn vị hoặc metadata đơn vị đi kèm. Các phản hồi lỗi dùng mã ổn định để frontend hiển thị thông báo phù hợp.

Giao diện tổ chức theo công việc: tổng quan, quan trắc, dự báo, chất lượng dữ liệu và cống. Ở mục quan trắc, bản đồ, biểu đồ và bảng được liên kết bằng cùng mã trạm. Ở mục dự báo, người dùng thấy tháng nguồn, tháng mục tiêu, phiên bản và sai số hồi cứu. Ở mục cống, phiếu nhập tách số đo hiện trường khỏi ngữ cảnh dự báo; bảng điều kiện trình bày giá trị quan sát, ngưỡng và lý do. Giao diện không dùng màu để che giấu trạng thái chưa xác minh.

Trong trạng thái không dữ liệu, khu vực hiển thị thông báo rõ nguồn nào thiếu và hành động nào còn có thể thực hiện. Ví dụ, một trạm có tọa độ nhưng chưa có EC vẫn xuất hiện trong danh mục, nhưng biểu đồ ghi chưa có quan trắc. Một cống chưa có phiếu hiện trường vẫn có thể xem hồ sơ, nhưng không có kết luận lấy nước. Thiết kế này tránh tạo số liệu giả để lấp chỗ trống trong bản đồ.

### Thiết kế giao thức phát hành và truy nguồn dự báo

Một kết quả hồi cứu chỉ có thể đánh giá khả năng dự báo nếu xác định được thời điểm mô hình được phép biết từng đầu vào. Hệ thống vì vậy cần một thực thể phát hành, gồm mã kỳ, trạm đích, tháng mục tiêu, thời điểm dự kiến phát hành, thời điểm phát hành thật, phiên bản mô hình và mã giao thức nhãn. Kết quả đến sau lịch được đánh dấu trễ và không cộng chung vào metric của các bản phát hành đúng hạn. Khi một kỳ không được phát hành, sổ vẫn ghi trạng thái bỏ lỡ để mẫu chấm không chỉ gồm những tháng hệ thống chạy thuận lợi.

Giao thức dự kiến dùng slot 09:00 ngày 06 của tháng trước tháng mục tiêu. Cách chọn mốc nhằm kiểm soát trật tự đầu vào trong nghiên cứu, chưa chứng minh dữ liệu khí tượng và thủy văn lịch sử thật sự được công bố vào đúng ngày này. Bản phát hành phải lưu danh sách nguồn đã dùng, ngày dữ liệu mới nhất của từng nguồn, giả định công bố và checksum. Khi nguồn chưa đủ độ tươi, hệ thống ghi lý do không phát hành hoặc phát hành muộn thay vì tự dùng một tháng khác mà không thông báo.

Nhãn chấm được định nghĩa riêng với phiếu hiện trường. Đối với dự báo EC mẫu tháng của trạm MRC, nhãn phải cùng trạm, cùng loại thông số, đơn vị và tháng mục tiêu; nguồn phải qua kiểm tra chất lượng theo giao thức đã công bố trước khi tháng đó xảy ra. Một mẫu EC25 đo tại cống không thể dùng chấm dự báo mẫu EC MRC ở Mỹ Tho. Nếu về sau có hai nguồn nhãn khác nhau, metric cần báo cáo theo từng nguồn thay vì trộn thành một MAE.

Để tránh sửa lịch sử sau khi đã xem số đo, mỗi bản dự báo được lưu bất biến với version và dấu thời gian. Một lần chạy lại bằng model mới tạo bản khác, không ghi đè bản đã phát hành. Bảng đánh giá có thể tái tạo từ các cặp bản phát hành và nhãn được chấp nhận; khi một nhãn bị sửa sau kiểm tra chất lượng, thay đổi phải có dấu phiên bản. Thiết kế này chuyển bài toán từ “có một con số dự báo” sang một chuỗi bằng chứng về việc con số đó được tạo ra khi nào và được chấm bằng dữ liệu nào.

### Thiết kế phân quyền và bảo vệ dữ liệu

Các thao tác đọc quan trắc công khai, gửi phiếu hiện trường, duyệt phiếu và quản trị cấu hình có mức quyền khác nhau. Người xem không được sửa số đo gốc. Người gửi phiếu có thể tạo một bản ghi kèm nguồn và danh tính thao tác nhưng không tự duyệt phiếu của mình nếu quy trình yêu cầu người duyệt độc lập. Người duyệt cần xem bản gốc, thông tin người gửi và trạng thái kiểm tra trước khi phiếu xuất hiện trên lớp bản đồ đã xác nhận.

Backend kiểm tra quyền ở route và service trước thao tác ghi, không dựa vào việc frontend ẩn nút. Những trường do người dùng nhập như tên trạm, tọa độ hoặc RuleProfile được kiểm kiểu, miền và độ dài để tránh dữ liệu không hợp lệ đi vào truy vấn hoặc giao diện. Cơ sở dữ liệu sử dụng tài khoản và quyền tách theo chức năng đọc, ghi khi triển khai. Các khóa truy cập và chuỗi kết nối được giữ trong cấu hình môi trường, không đưa vào báo cáo hoặc artifact xuất cho người xem.

Một phiếu đã duyệt vẫn có thể bị phát hiện sai sau đó. Cấu trúc trạng thái cần cho phép thu hồi hoặc đánh dấu cần xem lại, giữ lịch sử người thao tác và lý do. Lớp bản đồ chỉ đọc phiên bản được chấp nhận tại thời điểm truy vấn. Quyền duyệt dữ liệu là quyền quản trị thông tin, không đồng nghĩa quyền ra lệnh đóng mở cống; giao diện phải dùng thuật ngữ phù hợp với hai phạm vi này.

### Thiết kế kiểm thử theo ranh giới nghiệp vụ

Bộ kiểm thử được tổ chức từ những trường hợp có nguy cơ làm người dùng hiểu sai. Với dữ liệu, cần kiểm một trạm chưa có mẫu, một mẫu có EC bằng không thật, một mẫu thiếu giá trị và một dòng EC âm. Bốn trường hợp phải cho kết quả khác nhau. Với mô hình, cần kiểm tháng đủ đặc trưng, tháng thiếu một biến thủy văn, tháng nguồn chưa khả dụng và artifact không khớp checksum. Với bản đồ, cần kiểm vị trí hợp lệ, tọa độ bị đảo, công trình thiếu tọa độ và kết quả nội suy ở biên đoạn.

Với cống, các phép thử tập trung vào ranh giới ngưỡng và thời gian. Một giá trị đúng bằng ngưỡng được chấp nhận theo toán tử đã khai báo; giá trị chỉ lớn hơn một lượng nhỏ phải đổi trạng thái. Mẫu đúng mốc hết hạn còn hợp lệ, sau mốc đó phải đo lại. Đối với mực nước, giá trị âm hợp lệ trong một hệ cao độ; phép tính chênh lệch không chạy nếu hai phía không cùng mốc. Các trường hợp này cần kiểm bằng hàm domain trước, rồi kiểm qua API và giao diện để phát hiện sai khác giữa các tầng.

Kiểm thử kết quả dự báo không chỉ so một giá trị số. Một phản hồi đúng phải có trạm đích, tháng mục tiêu, đơn vị, phiên bản và thông tin nguồn. Khi đổi mô hình, giá trị có thể thay đổi nhưng bản đã lưu trước đó phải giữ metadata cũ. Khi chọn trạm khác trên frontend, request cũ không được ghi đè tiêu đề và đồ thị mới. Những điều kiện này được xem là tiêu chí nghiệm thu vì một bản đồ hiển thị sai nhãn có thể nguy hiểm hơn một API trả lỗi rõ ràng.

[CHÈN ẢNH TẠI ĐÂY: <Bản vẽ wireframe của giao diện WebGIS gồm menu công việc, bản đồ, bảng trạm hoặc cống, biểu đồ EC và khu vực thông tin nguồn. Thể hiện rõ chú giải tách quan trắc, dự báo và lớp nội suy.>]

[TÊN HÌNH: Hình 3.5. Thiết kế bố cục giao diện WebGIS]

### Tiểu kết chương

Thiết kế đặt tính truy xuất và giới hạn sử dụng ngay trong hợp đồng dữ liệu. Quan trắc, dự báo, nội suy và phiếu hiện trường được lưu và trình bày riêng. Các module tính toán có đầu vào, đầu ra và điều kiện lỗi xác định, tạo cơ sở cho việc cài đặt và kiểm thử ở chương 4.

## XÂY DỰNG VÀ TRIỂN KHAI HỆ THỐNG

### Môi trường phát triển

Nguyên mẫu được tổ chức thành backend Python, frontend JavaScript, bộ script dữ liệu và thí nghiệm, tệp SQL cùng các thư mục nguồn và kết quả. Backend dùng FastAPI; dữ liệu quan hệ và hình học dùng PostgreSQL/PostGIS khi chạy chế độ cơ sở dữ liệu; frontend dùng OpenLayers và Vite. Cấu hình kết nối, quyền ghi và các khóa truy cập nằm ngoài mã nguồn công khai. Những thư mục chứa dữ liệu gốc, model artifact và manifest được giữ để tái lập kết quả.

Quá trình phát triển được chia thành ba môi trường thao tác. Môi trường nghiên cứu chạy pipeline và huấn luyện ngoài web. Môi trường API đọc dữ liệu, artifact và tính các ca sử dụng. Môi trường trình duyệt hiển thị bản đồ, biểu đồ, form và kết quả kiểm tra. Sự tách biệt này giúp thao tác xem bản đồ không vô tình huấn luyện lại mô hình hoặc thay đổi dữ liệu nguồn.

Phiên bản phần mềm và artifact cần được ghi tại thời điểm xuất báo cáo. Một ảnh giao diện chụp từ bản build cũ không đủ chứng minh tính năng mới đã tích hợp. Vì thế các hình ở chương này phải được chụp từ cùng bản chạy với dữ liệu và registry dùng để báo cáo; chú thích hình ghi tháng hoặc ngày kiểm tra và trạng thái nguồn nếu cần.

### Xây dựng cơ sở dữ liệu PostgreSQL/PostGIS

Các bảng quan trắc chính gồm measurement_site, source_dataset và conductivity_observation. Danh mục công trình được lưu ở irrigation_gate. Cấu trúc này cho phép một trạm có nhiều quan trắc đến từ các bộ nguồn khác nhau, đồng thời cho phép một trạm tồn tại trong danh mục dù chưa có EC. Các bảng hoặc schema bổ trợ giữ kết quả dự báo, cấu hình và hồ sơ cống. Việc phân tách giúp số dòng quan trắc không tăng khi người dùng lưu một kịch bản.

Ở chế độ PostgreSQL, repository chọn một phiên bản nguồn RAW_EC theo trạm và trả đúng các bản ghi thuộc phiên bản đó. Truy vấn lịch sử có bộ lọc thời gian và phân trang. Chế độ snapshot nghiên cứu đọc tệp có manifest, thích hợp cho việc tái lập thí nghiệm khi cơ sở dữ liệu không phải nguồn được chọn. Backend không tự chuyển từ PostgreSQL sang snapshot sau lỗi kết nối; phản hồi lỗi làm rõ dữ liệu chưa được đọc.

Khi nhập hình học, tọa độ của trạm và cống được kiểm tra miền giá trị và SRID. Cống chưa có tọa độ xác minh giữ trạng thái thiếu. Dữ liệu ranh giới Đồng Tháp mới được dùng để xác định phạm vi hiển thị; trạm Tân Châu vẫn được giữ vì phục vụ phân tích thượng nguồn, dù không nên diễn giải nó là một cống hay một trạm thuộc vùng ven biển cần cảnh báo.

### Xây dựng ETL Pipeline

Pipeline tiếp nhận EC giữ bản nguồn và tạo bản chuẩn hóa riêng. Bước đọc kiểm tra tên cột, kiểu dữ liệu, mã trạm và đơn vị. Bước làm sạch xác định bản ghi trùng, ngày không hợp lệ, giá trị không hữu hạn và các cờ chất lượng. Một điểm EC cao không bị loại chỉ vì vượt khoảng tứ phân vị; cần kiểm tra bản gốc và bối cảnh vì chính các đỉnh là trường hợp quan trọng đối với xâm nhập mặn.

Chuỗi MRC được nhóm theo trạm và tháng của mẫu. Trước khi mô hình hóa, pipeline kiểm số tháng trùng, khoảng phủ và số mẫu. Dữ liệu RIA2 theo đợt được lưu để tra cứu nhưng không trộn vào chuỗi huấn luyện MRC tháng. Các tập dữ liệu có chữ “cleaned” trong tên tệp vẫn phải qua kiểm tra nguồn và phương pháp tạo giá trị. Những giá trị EC suy ra từ độ mặn không được đánh dấu thành EC đo trực tiếp.

Với khí tượng, các phản hồi nguồn được lưu cùng thời gian tải và checksum. Biến mưa, nhiệt độ và gió được tính theo tháng với đơn vị riêng; biến thủy văn có kiểm tra số ngày tối thiểu trong tháng. Khi một tháng nguồn không đủ ngày hoặc chưa thỏa giả định sẵn có, đặc trưng cho tháng đích được xem là thiếu. Pipeline không kéo dài dữ liệu bằng một giá trị gần nhất rồi coi đó là nguồn quan trắc hợp lệ.

Đầu ra ETL gồm số dòng đọc, số dòng đạt, số dòng bị cách ly, thời đoạn, đơn vị và dấu nguồn. Những tổng số này hỗ trợ phát hiện sai khác khi chạy lại pipeline sau thay đổi mã. Chúng cũng là cơ sở lập bảng dữ liệu thực nghiệm ở chương 5, thay vì đếm thủ công từ giao diện.

### Xây dựng mô hình dự báo

Mô hình được huấn luyện bằng các script riêng trong thư mục công cụ. Đầu vào của một lần huấn luyện là snapshot nhãn EC cùng tập đặc trưng đã chốt. Script tạo dự báo hồi cứu theo thời gian, tính metric trên cùng tập tháng với baseline và lưu dự báo từng tháng. Artifact sau đó được đăng ký bằng mã phiên bản, danh sách biến, nguồn và checksum. Chỉ phiên bản có hợp đồng dữ liệu hợp lệ được service suy luận đọc.

Mô hình Mỹ Tho chính trong phiên nghiên cứu hiện hành là Random Forest 300 cây, độ sâu tối đa 8, tối thiểu 3 mẫu tại lá, seed 42. Biến đầu vào gồm mùa vụ, ba biến khí tượng và nhóm biến thủy văn từ lưu lượng Kratie cùng mực nước Tân Châu ở độ trễ t-2. Các thống kê ba tháng và tỷ lệ so với lịch sử được tính bằng công thức cố định trong artifact. Mô hình được fit trên 463 mẫu EC Mỹ Tho đến 12/2023; không có EC sau 2023 được thêm vào nhãn. Mỹ Thuận và Tân Châu dùng mô hình, registry và nguồn đặc trưng riêng; việc gọi cùng tên thuật toán không có nghĩa ba trạm dùng chung một bộ trọng số.

API suy luận kiểm tra tháng khí tượng và thủy văn cần thiết trước khi chạy Mỹ Tho. Nếu thiếu một biến bắt buộc, hệ thống trả trạng thái không đủ đầu vào. Người dùng có thể nhập khí tượng cho form theo hợp đồng nhưng không thể bỏ qua nhóm thủy văn của model Mỹ Tho chính. Phản hồi ghi giá trị từng đặc trưng, nguồn khí tượng, nguồn thủy văn, phiên bản model và giả định thời điểm sẵn có.

Các thí nghiệm cũ như RF_compact được giữ làm bằng chứng nghiên cứu riêng. RF_compact có số cây, tập đặc trưng và giao thức khác, nên metric của nó không được gán cho form suy luận đang chạy. Các dự báo lưu trước lần đổi registry cũng giữ version cũ. Giao diện cho phép người đọc phân biệt một dự báo hồi cứu, một ước tính từ khí tượng cùng tháng và một dự báo cho tháng mục tiêu được tạo trước kỳ đó.

### Xây dựng lớp nội suy dọc sông

Module nội suy lấy các điểm neo theo vị trí dọc trục. Vị trí Mỹ Thuận trên trục hiện dùng là khoảng 85,22 km tính từ đầu trục tham chiếu, nằm giữa Tân Châu và Mỹ Tho. Đây là lý trình trên hình học dùng cho giao diện, không phải cự ly thủy lực khảo sát. Hàm nội suy kiểm tra vị trí tăng dần, EC hữu hạn không âm và có ít nhất hai điểm neo trước khi tính.

Trong chế độ ba trạm, một vị trí nằm giữa Tân Châu và Mỹ Thuận được tính từ hai neo đó; vị trí nằm giữa Mỹ Thuận và Mỹ Tho dùng cặp còn lại. Khi Mỹ Thuận thiếu giá trị hợp lệ cho kỳ được chọn, module chuyển sang hai neo Tân Châu và Mỹ Tho, gắn tên chế độ dự phòng. Điều kiện dự phòng được thể hiện trong phản hồi API và chú giải bản đồ, không ẩn trong mã giao diện.

Dải màu trên bản đồ được chia theo khoảng cách tích lũy dọc hình học tuyến. Nếu một đoạn có nhiều đỉnh vì dữ liệu hình học chi tiết hơn, màu vẫn thay đổi theo chiều dài chứ không theo số đỉnh. Phương pháp này cải thiện sự nhất quán thị giác. Nó không tạo thêm quan trắc và không xác định độ trễ truyền mặn. Bản đồ vì thế dùng nhãn “nội suy hiển thị” hoặc “mô phỏng” tại nơi người dùng xem lớp màu.

### Xây dựng module kiểm tra điều kiện cống

Engine cống nhận phiếu đo và RuleProfile để tính các điều kiện theo cùng một hàm. Phiếu có EC trong và ngoài cống, mực nước hai phía, xác nhận cùng hệ cao độ, thời gian đo, tình trạng cơ khí và nguồn đo. Thời điểm đánh giá được truyền vào hàm để một bộ đầu vào cho cùng kết quả ở môi trường thử nghiệm. Hàm không đọc trực tiếp đồng hồ hệ thống và không ghi dữ liệu khi tính.

Ngưỡng mặc định đang dùng trong phần mềm là cấu hình kỹ thuật minh họa, gồm EC ngoài tối đa 156,25 mS/m, EC trong tối đa 125 mS/m và chênh lệch mực nước dương tối thiểu 0,05 m. Mẫu thường có hạn 6 giờ; khi ngữ cảnh dự báo kích hoạt cảnh giác cao, hạn rút còn 2 giờ. Các giá trị này phục vụ kiểm tra logic nhất quán của nguyên mẫu, chưa phải ngưỡng vận hành được cơ quan quản lý phê duyệt cho từng cống. Người dùng thay ngưỡng phải thấy nhãn cấu hình tùy chỉnh trong kết quả.

Ngữ cảnh dự báo có thể dựa vào EC ở điểm chiếu hình học của cống trên tuyến. Hệ thống dùng nó để điều chỉnh mức cảnh giác, không gọi đó là EC ngoài cống đo thực tế. Nếu không xác định được vị trí hoặc không có dự báo, kết quả thông báo thiếu ngữ cảnh và dùng thời hạn mặc định. Kết luận đề nghị xem xét lấy nước chỉ xuất hiện khi phiếu hiện trường đủ điều kiện; nó không phải lệnh mở cống.

Phiếu thực địa là loại dữ liệu riêng với cơ chế gửi, duyệt và truy nguồn. Một phiếu được duyệt có thể hiển thị trên bản đồ nhưng chưa tự trở thành nhãn EC tháng cho mô hình. Để dùng làm nhãn chấm dự báo, phiếu còn phải thỏa giao thức trạm, vị trí, thời điểm, phương pháp đo và điều kiện chất lượng đã định trước. Tách hai bước giúp tránh tăng số mẫu nghiên cứu chỉ vì người dùng đã duyệt một bản ghi giao diện.

### Xây dựng Backend FastAPI và Frontend WebGIS

Backend đăng ký các route workspace, quan trắc, mô hình, trạng thái nguồn và hồ sơ cống. Route chuyển dữ liệu đầu vào sang service; service chọn repository và gọi domain khi cần tính. Các schema kiểm tra kiểu số, mã trạm, tháng và thời điểm. Các lỗi thiếu đầu vào, sai phạm vi hoặc trùng bản ghi được trả thành mã HTTP phù hợp, kèm thông điệp mà frontend có thể trình bày rõ.

Frontend được xây theo các mục công việc thay vì một trang chứa mọi điều khiển. Mục quan trắc cung cấp bản đồ, biểu đồ, bảng và xuất dữ liệu. Mục dự báo cho chọn trạm, tháng, nguồn đầu vào, chạy suy luận và xem kiểm chứng. Mục chất lượng dữ liệu cho biết nguồn, cờ, độ phủ và những dữ liệu chưa được tiếp nhận. Mục cống trình bày danh mục công trình, phiếu đo và bảng từng điều kiện của kết quả sàng lọc.

Việc chọn trạm trên bản đồ cập nhật biểu đồ và bảng theo mã trạm. Khi người dùng thay lựa chọn trước lúc request cũ hoàn tất, giao diện hủy request hoặc bỏ kết quả không còn phù hợp. Các trạng thái quan trắc, dự báo, nội suy và phiếu đã duyệt dùng ký hiệu khác nhau. Một lớp giá trị nội suy không được trình bày như lớp trạm quan trắc. Bên cạnh biểu đồ có thông tin đơn vị, nguồn, tháng cuối của nhãn EC và phiên bản mô hình nếu có dự báo.

[CHÈN ẢNH TẠI ĐÂY: <Ảnh chụp giao diện thật của mục Quan trắc trên bản build dùng để nộp, có bản đồ trạm, bộ lọc thời gian, biểu đồ EC, bảng bản ghi và nhãn nguồn; che thông tin nhạy cảm nếu có.>]

[TÊN HÌNH: Hình 4.1. Giao diện tra cứu quan trắc EC]

[CHÈN ẢNH TẠI ĐÂY: <Ảnh chụp giao diện thật của mục Dự báo cho trạm Mỹ Tho, thể hiện tháng mục tiêu, đầu vào khí tượng và thủy văn, giá trị dự báo, phiên bản mô hình và cảnh báo giới hạn sử dụng.>]

[TÊN HÌNH: Hình 4.2. Giao diện suy luận dự báo EC tại trạm]

[CHÈN ẢNH TẠI ĐÂY: <Ảnh chụp giao diện thật của phiếu cống với các số đo hai phía, thời điểm mẫu, bảng điều kiện đạt hoặc thiếu, kết luận và nhãn cấu hình quy tắc; dùng bộ dữ liệu thử có ghi rõ là thử nghiệm.>]

[TÊN HÌNH: Hình 4.3. Giao diện kiểm tra điều kiện tại cống]

### Tích hợp hệ thống và kiểm soát phiên bản

Frontend gọi API qua hợp đồng JSON thống nhất. Các giá trị số giữ nguyên kiểu số cho tới lúc định dạng để hiển thị; việc làm tròn trên màn hình không thay số lưu trong artifact. API trả mã trạm, thông số, đơn vị và nguồn để cùng một giá trị có thể xuất hiện nhất quán ở bản đồ, biểu đồ và bảng. Khi một lớp không có dữ liệu, frontend cho biết lý do thay vì dùng giá trị của lớp khác.

Quá trình tích hợp kiểm tra cả snapshot và PostgreSQL theo chế độ đã chọn, nhưng không coi kết quả của một chế độ là bằng chứng chế độ kia hoạt động. Manifest và checksum giúp phát hiện artifact thiếu hoặc bị thay. Các tính năng mới như sổ phát hành dự báo và độ tươi nguồn được lưu theo phiên bản riêng; một kết quả phát hành trễ được chấm tách khỏi kỳ đúng hạn để không làm sai metric vận hành tương lai.

### Triển khai sổ phát hành và kiểm tra độ tươi nguồn

Sổ phát hành giữ một bản ghi cho từng kỳ dự kiến, kể cả kỳ bị bỏ lỡ. Lịch đang cấu hình là 09:00 ngày 06 của tháng trước tháng mục tiêu. Một slot được nhận diện bằng tháng mục tiêu, trạm, phiên bản lịch và loại kết quả; cùng một slot không được ghi hai bản đúng hạn có cùng định danh. Nếu job chạy sau lịch, bản phát hành mang trạng thái trễ, lưu thời điểm thật và không được đưa vào nhóm điểm đúng hạn. Cách ghi này tránh thiên lệch chỉ chấm những tháng hệ thống chạy thành công.

Trước phát hành, service kiểm độ tươi riêng cho khí tượng, thủy văn và nhãn EC có thể dùng. Phản hồi nêu tháng cuối của từng nguồn, tháng mục tiêu xa nhất còn có thể hỗ trợ và giả định độ trễ công bố. Ở Mỹ Tho, thiếu một tháng thủy văn bắt buộc sẽ chặn mô hình chính. Một nguồn khí tượng có dữ liệu đến 2026 cũng không biến dữ liệu EC kết thúc 2023 thành nhãn mới; hai chỉ báo độ tươi phải xuất hiện riêng trong giao diện.

Mỗi bản phát hành lưu đặc trưng thực dùng, phiên bản mô hình và hash nguồn. Khi một nguồn được cập nhật hoặc sửa, lịch sử của bản dự báo cũ vẫn phải chỉ tới dấu nguồn tại thời điểm phát hành. Phần mềm có thể chạy lại để nghiên cứu sai khác, nhưng lần chạy lại phải có mã riêng. Tính bất biến này giúp phân biệt khả năng dự báo đã cam kết trước khi có nhãn với kết quả hồi cứu được tính sau.

Sổ phát hành được mở trong tháng 11/2026; lịch đầu tiên sau khi mở là ngày 06/12/2026 cho tháng 01/2027. Không tạo kết quả phát hành hồi tố cho những lịch trước ngày mở sổ. Ở thời điểm lập báo cáo, chưa có một chuỗi nhãn mới đủ điều kiện để tính MAE vận hành từ sổ này. Vì vậy màn hình sổ phát hành chứng minh hạ tầng lưu và đối chiếu, chưa chứng minh độ chính xác dự báo mới.

### Triển khai phiếu EC thực địa và trạng thái duyệt

Phiếu thực địa được lưu trong một bảng tách khỏi conductivity_observation của MRC. Người gửi ghi vị trí, thời điểm, đại lượng, đơn vị, nguồn đo và thông tin thiết bị. Quy trình yêu cầu một quyền gửi và một quyền duyệt khác. Chỉ phiếu được duyệt mới xuất hiện trên lớp bản đồ tương ứng. Một phiếu chưa duyệt vẫn có thể được giữ để kiểm tra, nhưng không xuất hiện như số đo đã xác nhận và không được đưa vào tập huấn luyện.

Giao diện trình bày phiếu thực địa bằng ký hiệu riêng với trạm MRC. Chú giải cho biết trạng thái đã duyệt và nguồn người đo. Trường hợp giá trị khác xa trung vị lịch sử cùng tháng ở trạm lân cận được gắn cờ cần xem lại. Cờ này không tự chứng minh phiếu sai; nó yêu cầu kiểm thiết bị, tọa độ, đơn vị và thời điểm trước khi diễn giải. Đối với vùng cửa sông, một giá trị cao có thể là sự kiện thật cần giữ trong hồ sơ.

Điều kiện dùng phiếu để chấm dự báo nghiêm ngặt hơn điều kiện hiển thị. Giao thức nhãn được chốt trước khi nhận phiếu đầu tiên yêu cầu vị trí gần trạm đích, cửa sổ ngày và giờ đo, mã thiết bị, biên bản hiệu chuẩn, EC25 và ít nhất hai mẫu độc lập. Nếu các mẫu chênh quá mức cho phép, hệ thống chuyển kiểm tra thủ công. Một phiếu đo trong đồng hoặc ngay trong cống có thể có giá trị cho hồ sơ công trình nhưng không phải nhãn của dự báo mẫu sông tại trạm MRC.

Do cơ sở bù nhiệt của chuỗi MRC lịch sử chưa được xác nhận, metric dùng nhãn MRC và metric dùng phiếu EC25 cần báo cáo tách theo nguồn. Việc có cùng đơn vị mS/m không bảo đảm hai quy trình đo tương đương. Khi chưa có nhãn đáp ứng giao thức, sổ phát hành trả “chưa có dữ liệu chấm” thay vì hiển thị sai số bằng không.

### Tiểu kết chương

Nguyên mẫu đã có các thành phần dữ liệu, mô hình, API, bản đồ và kiểm tra cống. Phần triển khai giữ nguồn và phiên bản của kết quả, đồng thời phân biệt rõ chức năng đã chạy với phương án nghiên cứu như IDW. Chương 5 đánh giá dữ liệu, sai số dự báo, phép nội suy và các trạng thái kiểm thử theo những bằng chứng đã lưu.

## THỰC NGHIỆM VÀ ĐÁNH GIÁ

### Mô tả dữ liệu thực nghiệm

Bộ quan trắc EC MRC dùng trong nghiên cứu gồm ba trạm. Tân Châu có 464 mẫu, Mỹ Thuận có 451 mẫu và Mỹ Tho có 463 mẫu; tổng là 1.378 mẫu. Mẫu Mỹ Thuận phủ từ 15/05/1985 đến 15/12/2023; các chuỗi MRC dùng trong mô hình đều kết thúc ở 12/2023. Tập snapshot còn có 50 bản ghi RIA2 tại 10 điểm theo đợt trong năm 2025, nhưng chúng không tham gia tập huấn luyện ba mô hình tháng. Tổng số dòng trong snapshot và tổng số nhãn mô hình vì vậy không phải cùng một đại lượng.

Đơn vị EC MRC được giữ ở mS/m. Các mẫu được kiểm tra hữu hạn, không âm, không trùng tháng trong từng chuỗi sử dụng. Cờ chất lượng nguồn chưa xác minh và cơ sở bù nhiệt chưa rõ vẫn được giữ trong metadata. Dữ liệu khí tượng lấy tại tọa độ tương ứng với mỗi trạm và lưu phản hồi gốc; nhóm biến thủy văn thượng nguồn dùng cho mô hình Mỹ Tho có nguồn cùng manifest. Dữ liệu độ mặn theo g/L từ bản tin không được đưa thành nhãn EC.

Bảng 5.1. Phạm vi dữ liệu EC sử dụng trong đánh giá

| Nhóm dữ liệu | Số mẫu | Độ phân giải | Vai trò |
| Tân Châu, MRC | 464 | Mẫu theo tháng | Nhãn tại trạm và điểm neo thượng nguồn |
| Mỹ Thuận, MRC | 451 | Mẫu theo tháng | Nhãn tại trạm và điểm neo giữa tuyến |
| Mỹ Tho, MRC | 463 | Mẫu theo tháng | Nhãn tại trạm hạ lưu |
| Mười điểm RIA2 | 50 | Theo đợt | Tra cứu và kiểm toán, không huấn luyện mô hình tháng |

Thời kỳ 2022-2023 có 24 tháng được dùng cho kiểm tra hồi cứu tại mỗi trạm MRC. Trong 24 tháng đối chiếu ba trạm, 23 tháng có mẫu cùng ngày; tháng 12/2022, Tân Châu lấy ngày 12 còn Mỹ Thuận và Mỹ Tho lấy ngày 15. Cùng ngày không bảo đảm cùng giờ hoặc cùng pha triều. Điều này cần được giữ khi giải thích phép so sánh không gian tại Mỹ Thuận.

[CHÈN ẢNH TẠI ĐÂY: <Biểu đồ thời gian có ba hàng Tân Châu, Mỹ Thuận, Mỹ Tho; đánh dấu mỗi tháng có mẫu EC từ 1985 đến 2023, vùng đánh giá 2019-2021 và 2022-2023, cùng chú thích RIA2 là chuỗi theo đợt riêng. Tạo từ dữ liệu nguồn thực tế.>]

[TÊN HÌNH: Hình 5.1. Độ phủ thời gian của các chuỗi EC dùng trong nghiên cứu]

### Phương pháp chia tập và giao thức hồi cứu

Tập dữ liệu được chia theo thời gian để mô phỏng tình huống dự báo những tháng chưa quan sát. Các thí nghiệm mô hình sử dụng giai đoạn 2019-2021 để lựa chọn và xem xét cấu hình, sau đó trình bày kết quả hồi cứu 2022-2023. Một số phương án và đặc trưng đã được phát triển sau khi nhóm nghiên cứu xem kết quả ở 2022-2023. Vì vậy giai đoạn này là tập hồi cứu có giá trị mô tả, không phải kiểm định mù còn nguyên tính độc lập.

Ở giao thức theo ngày phát hành, tháng t được dự báo vào ngày 06 của tháng t-1. Khí tượng tháng t-2 và thủy văn tháng t-2 chỉ được dùng nếu thỏa giả định về độ trễ sẵn có. Nhãn EC lịch sử được xét theo hai giả định công bố sau cuối tháng 5 hoặc 35 ngày để kiểm tra độ nhạy. Ngày công bố thực của từng mẫu không có trong nguồn hiện lưu, nên đây là giả định nghiên cứu. Baseline giữ EC gần nhất cũng phải tuân thủ cùng giả định, không được sử dụng một nhãn chưa thể biết ở ngày phát hành.

Mỗi bảng metric ghi trạm, mô hình, số tháng, MAE, RMSE, đơn vị và giao thức. Kết quả của mô hình dùng khí tượng cùng tháng mục tiêu được gọi là ước tính hồi cứu khi khí tượng đã được quan sát, không là dự báo trước tháng. Những CSV ước tính cho 2024-2026 không bổ sung nhãn EC thật sau 2023. Sổ phát hành dự báo mới được triển khai để về sau có thể ghi bản dự báo đúng hạn, bản trễ và nhãn chấm độc lập; đến thời điểm báo cáo chưa có chuỗi nhãn mới đủ điều kiện tính MAE vận hành.

### Kết quả dự báo tại Mỹ Tho

Mô hình Mỹ Tho dùng khí tượng và thủy văn thượng nguồn được đối chiếu với Random Forest chỉ khí tượng và baseline giữ EC cuối cùng trong các kỳ mất EC liên tục. Cùng cấu hình 300 cây, sâu tối đa 8, tối thiểu 3 mẫu ở lá và seed 42 được giữ cho phép so sánh nhóm biến. Kết quả trong Bảng 5.2 lấy từ hồ sơ thí nghiệm ngày 08/11/2026; đơn vị của cả MAE và RMSE là mS/m.

Bảng 5.2. Sai số hồi cứu Mỹ Tho khi bổ sung biến thủy văn

| Kỳ kiểm tra | Số tháng | RF chỉ khí tượng MAE/RMSE | RF thêm thủy văn MAE/RMSE | Giữ EC cuối MAE/RMSE |
| 2019-2021 | 36 | 69,55 / 147,73 | 57,81 / 133,82 | 80,20 / 191,23 |
| 2021-2023 | 36 | 28,31 / 64,23 | 16,57 / 31,21 | 19,13 / 42,57 |
| 2022-2023 | 24 | 18,39 / 49,35 | 12,19 / 25,43 | 10,76 / 16,46 |

Thêm thủy văn làm giảm cả MAE và RMSE so với RF chỉ khí tượng ở ba kỳ trên. Tuy nhiên, trong kỳ 2022-2023 baseline giữ EC cuối cùng có sai số thấp hơn mô hình thủy văn. Kết quả không cho phép gọi RF thủy văn là phương án tốt nhất ở mọi giai đoạn. Các kỳ đã được xem trong quá trình chọn phương án; mức cải thiện là kết quả hồi cứu của dữ liệu đã biết.

Hai trường hợp chỉ ra giới hạn quan trọng. Ở tháng 03/2020, EC nguồn là 692 mS/m nhưng mô hình thủy văn dự báo 213,67 mS/m, tức bỏ sót phần lớn đỉnh. Ở tháng 04/2022, EC nguồn là 25,7 mS/m còn dự báo là 100,04 mS/m, tạo báo cao giả lớn. Một mô hình có MAE toàn kỳ thấp vẫn có thể gây diễn giải sai cho tháng cụ thể. Báo cáo vì vậy không chuyển trực tiếp kết quả này thành trạng thái đóng hoặc mở cống.

[CHÈN ẢNH TẠI ĐÂY: <Biểu đồ đường từ artifact thực nghiệm Mỹ Tho gồm EC nguồn, RF chỉ khí tượng, RF thêm thủy văn và baseline trên 36 tháng 2019-2021; đánh dấu tháng 03/2020 với giá trị nguồn 692 mS/m và dự báo 213,67 mS/m.>]

[TÊN HÌNH: Hình 5.2. Đối chiếu dự báo và EC nguồn tại Mỹ Tho giai đoạn 2019-2021]

### Kết quả dự báo tại Mỹ Thuận

Mỹ Thuận được huấn luyện bằng EC của chính trạm và khí tượng tại tọa độ trạm, không dùng khí tượng Mỹ Tho để thay thế. Thí nghiệm Random Forest giữ 300 cây, sâu tối đa 8, ít nhất 3 mẫu ở lá, ba biến khí tượng và cặp sin/cos tháng. Trên 24 tháng 2022-2023 với giả định EC công bố sau cuối tháng 5 ngày, mô hình được so sánh với Persistence và trung bình theo tháng lịch của tập huấn luyện.

Bảng 5.3. Sai số hồi cứu EC Mỹ Thuận trên 24 tháng 2022-2023

| Phương án | MAE, mS/m | RMSE, mS/m |
| Random Forest Mỹ Thuận | 3,917 | 4,856 |
| Persistence | 4,806 | 5,772 |
| Trung bình theo tháng lịch | 3,957 | 4,720 |

Random Forest có MAE thấp hơn hai baseline trong bảng, nhưng RMSE cao hơn phương án trung bình theo tháng lịch. Chênh MAE giữa hai phương án này nhỏ, nên kết quả không chứng minh RF vượt mọi baseline. Khi thay giả định công bố EC từ 5 lên 35 ngày, RF đạt MAE 3,896 và RMSE 4,832 mS/m; nhận định về thứ tự các phương án không thay đổi. Đây vẫn là đánh giá hồi cứu với lịch công bố giả định.

### Kết quả nội suy tại vị trí Mỹ Thuận

Phép kiểm tra không gian đặt câu hỏi: nếu không dùng EC đo tại Mỹ Thuận làm đầu vào, giá trị ước tính tại vị trí này khác nhãn Mỹ Thuận bao nhiêu? Trục sông của WebGIS đặt Mỹ Thuận tại lý trình quy đổi 85,217605 km, tương ứng tỷ lệ 0,68174084 trên đoạn Tân Châu - Mỹ Tho của bản đồ. Khoảng cách từ tọa độ trạm tới trục là khoảng 0,863 km. Các số này mô tả phép chiếu hình học đang dùng, không phải cự ly truyền nước.

Bảng 5.4. Sai số ước tính tại vị trí Mỹ Thuận trên 24 tháng 2022-2023

| Phương án | MAE, mS/m | RMSE, mS/m |
| Tuyến tính hai đầu mút thực đo | 5,443 | 9,838 |
| Tuyến tính hai đầu mút dự báo | 11,250 | 33,125 |
| Ba điểm neo, dự báo RF Mỹ Thuận | 3,917 | 4,856 |
| IDW bình phương khoảng cách, hai đầu mút thực đo | 6,528 | 11,748 |
| IDW bình phương khoảng cách, hai đầu mút dự báo | 13,609 | 40,230 |

Thêm dự báo riêng của Mỹ Thuận làm điểm neo đưa MAE tại đúng Mỹ Thuận xuống bằng sai số mô hình trạm này. So với tuyến tính hai đầu mút dự báo, mức giảm MAE tại vị trí kiểm tra là khoảng 65,18% và RMSE khoảng 85,34%. Kết quả chỉ chứng minh cải thiện tại Mỹ Thuận trong 24 tháng đã xét. Nó không chứng minh độ chính xác của từng điểm khác trên sông, vì ở điểm neo mới sai số chính là sai số mô hình Mỹ Thuận.

Phương án hai đầu mút thực đo là phép tái dựng hồi cứu khi biết EC của tháng cần ước tính ở Tân Châu và Mỹ Tho; nó không phải dự báo có thể phát hành trước tháng. Phương án dùng hai đầu mút dự báo gần hơn với tình huống phát hành, nhưng sai số lớn hơn rõ rệt. Sự khác nhau này cho thấy cần ghi loại đầu vào trên lớp bản đồ. Khi xét riêng 23 tháng có mẫu cùng ngày tại cả ba trạm, xu hướng cải thiện tại Mỹ Thuận vẫn giữ, nhưng cùng ngày chưa xác nhận cùng giờ hoặc cùng pha triều.

[CHÈN ẢNH TẠI ĐÂY: <Biểu đồ cột lấy đúng năm phương án và số MAE/RMSE trong Bảng 5.4, có trục đơn vị mS/m, tách chú giải thực đo hai đầu mút, dự báo hai đầu mút và dự báo Mỹ Thuận.>]

[TÊN HÌNH: Hình 5.3. So sánh sai số các phương án ước tính EC tại Mỹ Thuận]

### Kiểm thử Decision Logic

Module kiểm tra điều kiện được thử bằng các bộ đầu vào có kết quả kỳ vọng xác định trước. Nhóm dữ liệu hợp lệ gồm trường hợp tất cả tiêu chí đạt, EC ngoài vượt ngưỡng, EC trong vượt ngưỡng, chênh lệch mực nước không đạt và cơ khí chưa sẵn sàng. Nhóm thiếu hoặc hết hạn gồm thiếu một trong hai số đo EC, thiếu mốc cao độ, mẫu quá hạn và thời điểm đo nằm trong tương lai. Nhóm biên kiểm đúng tại ngưỡng EC, chênh lệch 0,05 m và đúng thời điểm hết hạn.

Thứ tự kết luận là yêu cầu nghiệp vụ quan trọng. Nếu mẫu quá hạn và EC ngoài cũng vượt ngưỡng, kết quả chung phải yêu cầu đo lại, đồng thời bảng chi tiết vẫn ghi EC ngoài không đạt. Nếu tất cả dữ liệu đủ và còn hạn nhưng một điều kiện không đạt, kết quả là chưa phù hợp để lấy nước. Chỉ khi mọi điều kiện đạt, engine mới trả đề nghị xem xét. Các test dùng thời điểm đánh giá truyền rõ để kết quả không phụ thuộc giờ chạy máy.

Ngữ cảnh dự báo được kiểm riêng với phiếu. Khi dự báo làm tăng mức cảnh giác, thời hạn mẫu có thể giảm từ 6 giờ xuống 2 giờ; cùng một phiếu cũ hơn 2 giờ phải chuyển sang quá hạn. Dự báo không tự ghi EC ngoài cống. Trường hợp thiếu dự báo hoặc thiếu vị trí chiếu của cống phải có thông báo nguồn ngữ cảnh đã dùng. Các phép thử này xác nhận logic phần mềm, chưa kiểm định ngưỡng kỹ thuật cho công trình thực tế.

### Kiểm thử API và WebGIS

Kiểm thử API tập trung vào hợp đồng dữ liệu và trạng thái lỗi: trạm không tồn tại, khoảng ngày đảo chiều, thiếu đầu vào dự báo, model không đăng ký, lỗi kết nối DB, bản ghi trùng và nguồn chưa đủ độ tươi. Kiểm thử frontend xác nhận thay trạm hoặc tháng không giữ kết quả cũ, lớp quan trắc tách dự báo, dữ liệu không có giá trị không bị vẽ thành 0 và kết luận cống đổi khi phiếu hoặc quy tắc thay đổi. Bản build Vite phải hoàn tất để kiểm tra tích hợp module, nhưng build thành công không thay phép kiểm trên trình duyệt.

Theo hồ sơ kiểm tra mã ngày 14/11/2026, bộ Python có 165 kiểm thử đạt và 1 kiểm thử bỏ qua; bộ JavaScript có 172 kiểm thử đạt, build Vite thành công. Những số này phản ánh lần kiểm tra đó, không phải cam kết mọi chức năng sẽ luôn đạt sau các thay đổi tiếp theo. Chưa có phiếu thực địa thật đủ điều kiện làm nhãn chấm dự báo, nên không có MAE vận hành sau khi sổ phát hành được mở.

Kiểm tra giao diện cần dùng bản build đúng với registry mô hình và dữ liệu được trình bày trong báo cáo. Kịch bản người dùng gồm chọn trạm, đọc EC gốc và nguồn, chạy một dự báo có đủ đầu vào, xem phép so sánh hồi cứu, mở lớp nội suy và nhập một phiếu cống thử. Ảnh chụp phải cho thấy nhãn “dự báo”, “nội suy” hoặc “dữ liệu thử” ở vị trí người đọc dễ thấy.

### Phân tích trường hợp EC cao và sai số lớn

Giá trị 692 mS/m tại Mỹ Tho ngày 15/03/2020 được giữ là một quan trắc cần phân tích, không loại tự động như ngoại lai. Mô hình thủy văn hồi cứu cho tháng này dự báo 213,67 mS/m. Sai số tuyệt đối 478,33 mS/m lớn hơn nhiều so với MAE của toàn kỳ 2019-2021. Nếu chỉ công bố MAE 57,81 mS/m, người đọc có thể đánh giá quá cao khả năng xử lý các đỉnh EC hiếm. Chính các đỉnh này lại có ý nghĩa lớn đối với việc theo dõi mặn.

Kiểm tra phân bố dự báo của 300 cây cho tháng 03/2020 cho thấy phân vị 90% khoảng 360,97 mS/m, phân vị 95% khoảng 425,92 mS/m và giá trị cây lớn nhất khoảng 691,50 mS/m. Không cây nào đạt giá trị nguồn 692 mS/m. Phân vị các cây là phân bố kết quả của ensemble theo cấu hình huấn luyện, không phải khoảng dự báo đã hiệu chuẩn. Trên 36 tháng 2019-2021, mốc phân vị 90% của cây chỉ bao phủ 22 tháng; trong sáu tháng EC từ 100 mS/m trở lên, nó bao phủ một tháng. Vì vậy không đưa đường phân vị cây lên giao diện với nhãn “giới hạn an toàn”.

Tháng 04/2022 cho tình huống ngược: EC nguồn 25,7 mS/m nhưng mô hình dự báo 100,04 mS/m. Nếu một ngưỡng cảnh giác nằm giữa hai giá trị này, giao diện có thể tạo cảnh giác cao giả. Trong nguyên mẫu, ngữ cảnh dự báo chỉ rút ngắn thời hạn hiệu lực của phiếu đo, không cho phép tự động bác bỏ hoặc chấp nhận lấy nước. Người dùng phải thấy số đo hiện trường và lý do của từng điều kiện trước khi đưa ra quyết định ngoài phần mềm.

Phân tích sai số riêng cho tháng EC cao cần xác định ngưỡng từ dữ liệu huấn luyện hoặc quy tắc nghiệp vụ có nguồn, không chọn ngưỡng sau khi nhìn kết quả tập kiểm tra. Số mẫu nhóm cao cũng phải được báo cáo. Một nhóm có sáu tháng không đủ để suy ra xác suất bỏ sót ổn định cho các mùa khô tương lai. Những phép kiểm này xác định điều kiện cho nghiên cứu tiếp theo: bổ sung mùa khô có nhãn mới, so sánh mô hình trên kỳ chưa được dùng lựa chọn và kiểm riêng hai loại lỗi báo cao giả, bỏ sót đỉnh.

### Thử nghiệm biến triều và kết quả không được chọn

Ảnh hưởng của triều tới xâm nhập mặn là một giả thuyết có cơ sở vật lý, nhưng một đặc trưng triều thêm vào mô hình không mặc nhiên làm giảm sai số. Nhóm nghiên cứu thử các biến từ atlas FES2022b tại điểm biển gần cửa Tiểu, gồm cực đại hoặc trung bình trong cửa sổ ban ngày ngày 13-17, cực đại nửa đầu tháng và biên độ ngày 05-12. Các cửa sổ được xác định bằng lịch cố định, không dùng ngày lấy mẫu EC thực tế của tháng đích để chọn biến, nhằm tránh nhìn trước thông tin mục tiêu.

Trong kỳ 2019-2021, RF thủy văn không FES có MAE 57,81 mS/m. Thêm trung bình triều ban ngày ngày 13-17 cho MAE 57,93 mS/m, tức không cải thiện kỳ này. Ở kỳ 2022-2023, MAE giảm từ 12,19 xuống 11,73 mS/m, nhưng dự báo tháng 03/2020 chỉ tăng từ 213,67 lên 229,86 mS/m, vẫn thấp xa giá trị nguồn. Nhóm sáu tháng EC từ 100 mS/m ở kỳ 2019-2021 có MAE tăng từ 285,92 lên 290,05 mS/m khi thêm biến đó. Kết quả vì vậy chưa hỗ trợ thay mô hình chính.

Bảng 5.5. MAE của các phương án thêm một biến triều FES, đơn vị mS/m

| Biến bổ sung | 2019-2021, 36 tháng | 2021-2023, 36 tháng | 2022-2023, 24 tháng |
| Không thêm FES | 57,81 | 16,57 | 12,19 |
| Cực đại ban ngày 13-17 | 57,95 | 16,44 | 12,26 |
| Trung bình ban ngày 13-17 | 57,93 | 15,59 | 11,73 |
| Cực đại nửa đầu tháng | 57,94 | 16,66 | 12,20 |
| Biên độ ngày 05-12 | 58,64 | 16,71 | 12,61 |

FES2022b được xây dựng và công bố sau những ngày phát hành giả định của nhiều tháng lịch sử. Phép sử dụng nó để tính lại đặc trưng cho quá khứ là hindcast nghiên cứu, không phải bằng chứng rằng người dự báo ở năm 2020 đã có đúng phiên bản atlas này. Dữ liệu EC MRC cũng không xác nhận giờ lấy mẫu thật: các dấu thời gian trong tệp đều là 00:00. Cửa sổ 07:00-16:00 chỉ là giả định thử nghiệm, không nên viết thành lịch lấy mẫu của trạm.

Kết quả âm tính có giá trị phương pháp. Nó giúp loại một cách giải thích quá đơn giản rằng chỉ cần thêm biến triều ngoài biển là dự báo đúng đỉnh EC ở Mỹ Tho. Để thử tác động triều nghiêm túc hơn cần mực nước đo tại các cửa và trên sông, thời gian lấy mẫu EC thực, điều kiện dòng chảy và mô hình liên kết có kiểm chứng. Một tương quan giữa pha mực nước ở hai trạm không cho thời gian truyền muối.

[CHÈN ẢNH TẠI ĐÂY: <Biểu đồ cột MAE của năm phương án trong Bảng 5.5 trên ba kỳ kiểm tra; dùng cùng thang màu cho từng phương án, ghi rõ FES là thí nghiệm hindcast và đánh dấu mô hình không FES đang được giữ.>]

[TÊN HÌNH: Hình 5.4. Sai số khi thử thêm biến triều FES vào mô hình Mỹ Tho]

### Đánh giá độ phù hợp của dữ liệu công trình

Danh mục công trình từ nguồn nghiên cứu có số lượng lớn hơn số vị trí đủ điều kiện đưa lên bản đồ. Trong một đợt rà soát, tệp danh mục ghi 190 công trình nhưng chỉ 27 có tọa độ để kiểm tra GIS. Các cặp công trình trùng tọa độ và sự lẫn giữa cống với trạm bơm cần xác minh trước khi nhập thành danh mục chính. Một cống không có điểm xác minh có thể được giữ trong bảng hồ sơ, nhưng không được đặt tại tâm xã hoặc điểm suy đoán để tăng số marker.

Phép đối chiếu với tuyến GRIT cho thấy cả 27 vị trí có tọa độ nằm trong ranh giới Đồng Tháp mới, nhưng 10 vị trí cách đường GRIT gần nhất hơn 2 km. Điều này có thể do mạng tuyến thiếu kênh, vị trí cần kiểm hoặc công trình không nối với nhánh đã mô hình hóa. Không thể chọn một nguyên nhân chỉ từ khoảng cách. Đối với các cống này, phần mềm cần ghi “chưa xác minh kết nối” và không dùng EC nội suy trên tuyến chính làm EC ngoài cống.

Hồ sơ vận hành từ tệp nguồn nghiên cứu gồm các dòng mô tả và ngưỡng, song chưa đủ nhất quán để tự chuyển thành RuleProfile pháp lý. Một log vận hành có giá trị đánh giá cần mã cống, thời điểm mở đóng, trạng thái trước và sau, mực nước, EC hai phía, người thực hiện và nguồn quy trình. Nếu thiếu các trường đó, số dòng log không tương đương số sự kiện vận hành có thể đối chiếu. Đây là lý do chương trình giữ ngưỡng minh họa tách khỏi quy định của từng cống.

Phiếu đo thực địa có thể khắc phục một phần khoảng trống, nhưng cần quy trình chấp nhận. Trạng thái “đã gửi” chỉ xác nhận có người nhập thông tin; trạng thái “đã duyệt” xác nhận một bước kiểm tra dữ liệu; trạng thái “đủ làm nhãn chấm” yêu cầu thêm điều kiện về vị trí, thời gian, thiết bị và EC25. Ba trạng thái không được dùng thay nhau. Ở thời điểm lập báo cáo chưa có bộ phiếu thật đạt giao thức nhãn mới, nên phần đánh giá cống dừng ở kiểm thử quy tắc bằng dữ liệu thử và phân tích tính khả thi của nguồn.

### Đối chiếu mục tiêu nghiên cứu với sản phẩm

Mục tiêu thứ nhất là tích hợp và truy xuất dữ liệu không gian - thời gian. Nguyên mẫu đã có danh mục trạm, ba chuỗi EC MRC dùng nghiên cứu, lớp dữ liệu theo đợt được giữ riêng, thông tin nguồn và hai đường đọc snapshot hoặc PostgreSQL. Người dùng có thể xem trạm trên bản đồ, chọn thời kỳ, đọc biểu đồ và bảng. Mức hoàn thành được xác định ở phạm vi các nguồn đã được kiểm tra; không suy rằng mọi điểm trong danh mục đều có chuỗi EC đủ dài. Phần còn thiếu là đối chiếu chất lượng và cơ sở bù nhiệt của một số nguồn, cùng việc xác minh tọa độ của các công trình chưa có điểm GIS đáng tin cậy.

Mục tiêu thứ hai là dự báo EC tại trạm. Hệ thống đã huấn luyện, lưu và suy luận các mô hình có phiên bản; có bảng kiểm chứng hồi cứu và baseline. Kết quả tại Mỹ Tho, Mỹ Thuận được báo bằng sai số cụ thể ở những kỳ đã xét, gồm cả trường hợp mô hình kém baseline. Điều kiện hoàn thành ở đây là phần mềm tạo được dự báo có truy nguồn và nghiên cứu đã đánh giá giới hạn của nó. Điều kiện “cảnh báo nghiệp vụ đã kiểm định” chưa đạt vì chưa có nhãn EC mới độc lập sau 2023 và chưa đánh giá trên lịch phát hành thực. Sổ phát hành mới là hạ tầng để thực hiện bước đó trong tương lai.

Mục tiêu thứ ba là biểu diễn sự biến thiên theo không gian. Bản đồ đã thể hiện vị trí trạm, tuyến sông, công trình có tọa độ và dải màu nội suy theo các điểm neo. Phép đối chiếu tại Mỹ Thuận cho thấy thêm mô hình riêng ở điểm neo cải thiện sai số tại chính vị trí kiểm tra. Không có bằng chứng đủ để gọi dải màu là bản đồ độ mặn thực tại mọi nhánh kênh hoặc để ước lượng EC tại một cống bất kỳ. Vì vậy kết quả hoàn thành là chức năng trực quan hóa có giới hạn rõ ràng, không phải mô hình lan truyền muối đã hiệu chuẩn.

Mục tiêu thứ tư là hỗ trợ xem xét điều kiện vận hành cống. Engine đã kiểm phiếu hai phía và RuleProfile, phân biệt trường hợp thiếu, quá hạn và không đạt. Giao diện hiển thị từng tiêu chí để người dùng thấy lý do kết luận. Chưa có ngưỡng được phê duyệt theo từng cống hoặc một tập số đo vận hành thật đủ để đánh giá tỷ lệ kết luận đúng. Kết quả là công cụ rà soát nhất quán theo điều kiện cấu hình, chưa phải hệ thống điều khiển hoặc khuyến nghị có hiệu lực pháp lý.

Bảng 5.6. Đối chiếu mục tiêu, bằng chứng hiện có và giới hạn

| Mục tiêu | Bằng chứng đã có | Giới hạn cần giữ khi kết luận |
| Tích hợp dữ liệu | Chuỗi EC, nguồn, snapshot và PostgreSQL | Không đồng nhất mọi nguồn; có cờ chưa xác minh |
| Dự báo tại trạm | Artifact, hồi cứu và baseline theo kỳ | Chưa có kiểm định vận hành sau 2023 |
| Biểu diễn không gian | Bản đồ và phép kiểm tại Mỹ Thuận | Không suy sai số cho mọi cống và nhánh kênh |
| Hỗ trợ cống | RuleProfile, phiếu và test case | Chưa có ngưỡng phê duyệt và phiếu thật đủ chấm |

### Khả năng tái lập kết quả

Một bảng metric chỉ có thể kiểm lại khi người khác biết dữ liệu đầu vào, quy tắc chọn tháng, phiên bản mã và cách tính. Hồ sơ thí nghiệm của dự án lưu bảng dự báo từng tháng, số mẫu huấn luyện, các baseline, manifest nguồn và cấu hình mô hình. Để tái lập Bảng 5.2, cần lấy đúng artifact của thí nghiệm Mỹ Tho thêm thủy văn ngày 08/11/2026, chọn các kỳ mất EC liên tục được nêu và tính lại MAE/RMSE từ từng cặp dự báo - nhãn. Không được lấy model đã fit toàn bộ đến 2023 để dự báo lại tháng 03/2020 rồi gọi đó là hồi cứu hợp lệ, vì model như vậy đã nhìn thấy nhãn tương lai.

Để tái lập Bảng 5.4, các giá trị đầu mút phải thuộc đúng cùng tháng và đúng loại phương án. Cột “hai đầu mút thực đo” là tái dựng lịch sử; cột “hai đầu mút dự báo” dùng dự báo ngoài mẫu; cột “ba điểm neo” dùng dự báo riêng của Mỹ Thuận ở vị trí kiểm tra. Nếu lấy thực đo Mỹ Thuận làm điểm neo rồi chấm tại chính Mỹ Thuận, sai số sẽ bằng không theo định nghĩa và phép đánh giá không còn ý nghĩa. Kiểm thử tái lập phải xác nhận đầu vào của điểm kiểm tra không chứa nhãn cần dự đoán.

Với bảng kiểm thử phần mềm, con số test đạt chỉ gắn với phiên bản mã và môi trường chạy ở ngày kiểm tra. Khi sửa API, schema hoặc frontend, cần chạy lại những bộ kiểm tra liên quan và cập nhật biên bản. Ảnh giao diện cũng phải lấy từ bản build tương ứng. Báo cáo không dùng ảnh tháng trước làm minh chứng cho một nút mới được thêm sau đó. Các placeholder hình trong bản Word nêu nội dung cần chụp hoặc vẽ từ chính artifact, giúp việc bổ sung hình sau này giữ đúng thời kỳ và phiên bản.

Đối với dữ liệu bên ngoài, mã băm chứng minh một tệp không thay đổi giữa hai lần kiểm nhưng không tự chứng minh phương pháp đo của nhà cung cấp đúng. Cần giữ metadata, giấy phép hoặc đường dẫn nguồn, ngày tải và các cờ QA. Nếu nguồn được sửa, một manifest mới phải mô tả thay đổi; kết quả cũ không được âm thầm tính lại bằng tệp mới rồi vẫn giữ cùng số phiên bản. Cách quản lý này cho phép hội đồng phân biệt sai số do mô hình với sai khác do dữ liệu hoặc quy tắc tiền xử lý.

### Thảo luận kết quả và hạn chế nghiên cứu

Kết quả thực nghiệm chứng minh hệ thống có thể tổ chức nguồn EC, chạy suy luận mô hình theo phiên bản, trình bày kết quả trên WebGIS và kiểm tra tính nhất quán của phiếu cống. Thí nghiệm cũng chỉ ra giới hạn định lượng: mô hình Mỹ Tho cải thiện so với RF chỉ khí tượng nhưng không luôn vượt baseline, còn các đỉnh và báo cao giả có sai số lớn. Mô hình Mỹ Thuận tốt hơn Persistence trong một kỳ nhưng không có RMSE thấp nhất. Những nhận định này dựa trên tập hồi cứu đã được xem trong quá trình phát triển.

Không có nhãn EC MRC sau 12/2023 trong bộ hiện dùng để đánh giá dự báo 2024-2026. Dữ liệu khí tượng mới hoặc một giá trị ước tính trên timeline không thay thế nhãn EC đo thật. Lịch công bố lịch sử của các nguồn đầu vào chưa được xác minh; các phép hồi cứu theo ngày khả dụng dựa vào giả định 5 hoặc 35 ngày. Muốn đánh giá khả năng dự báo được phát hành thực, cần lưu dự báo trước khi nhận nhãn và chấm trên những nhãn mới độc lập với quá trình chọn mô hình.

Lớp sông còn thiếu số đo đồng thời, mạng kênh có kết nối xác minh, mặt cắt và điều kiện biên để hiệu chuẩn mô hình truyền mặn. Lý trình trên bản đồ không phải thời gian truyền nước. Cống có tọa độ gần trục sông chưa chắc nhận nguồn nước từ nhánh đó. Bản đồ nội suy vì vậy chỉ phục vụ giải thích biến thiên giữa các điểm neo đã nêu; nó không cho phép tính EC tại từng cống theo giờ.

Phần cống có bộ quy tắc kiểm tra và phiếu hiện trường nhưng chưa có cơ sở để gọi là hệ thống điều hành công trình đã kiểm định. Ngưỡng mặc định là cấu hình thử nghiệm. Phiếu người dùng khai báo chưa trở thành quan trắc được thẩm định chỉ vì phần mềm đã lưu hoặc hiển thị nó. Các bước tiếp theo là thu thập EC và mực nước hai phía cống với thời điểm, hệ cao độ và người đo, xác minh quy trình từng cống, rồi đánh giá hệ quả báo cao giả và bỏ sót trên một tập tình huống chưa dùng thiết kế quy tắc.

### Tiểu kết chương

Các bảng sai số cho thấy giá trị của việc đối chiếu mô hình với baseline trên cùng giai đoạn và xem riêng trường hợp lệch lớn. Thử nghiệm nội suy xác nhận điểm neo Mỹ Thuận cải thiện ước tính tại chính vị trí đó, chưa xác nhận độ chính xác toàn tuyến. Kiểm thử phần mềm chứng minh các hợp đồng và quy tắc đã cài đặt hoạt động trong bộ trường hợp thử; kiểm định vận hành vẫn cần dữ liệu hiện trường và nhãn EC mới.

# PHẦN KẾT LUẬN

Đề tài đã xây dựng nguyên mẫu WebGIS để tra cứu EC theo trạm và thời gian, xem nguồn dữ liệu, suy luận dự báo mẫu EC theo tháng, hiển thị biến thiên dọc một tuyến sông và rà soát điều kiện lấy nước từ phiếu tại cống. Dữ liệu, kết quả mô hình và kết quả kiểm tra công trình được tách theo loại và phiên bản. Cách tổ chức đó cho phép người sử dụng truy lại một giá trị trên bản đồ hoặc một kết luận trong phiếu về nguồn và phương pháp đã tạo ra nó.

Về dự báo, mô hình Mỹ Tho thêm thủy văn giảm sai số so với Random Forest chỉ khí tượng trong các kỳ hồi cứu đã xét, nhưng chưa vượt baseline ở mọi kỳ và vẫn sai lớn tại một số tháng. Mô hình Mỹ Thuận có MAE thấp hơn hai baseline trong kỳ 2022-2023, song RMSE không thấp nhất. Nội suy ba trạm giảm sai số tại vị trí Mỹ Thuận so với hai đầu mút dự báo; kết quả này không đại diện cho mọi điểm trên sông. Chưa có EC MRC sau 2023 để chấm dự báo mới trong điều kiện phát hành thực.

Hạn chế lớn nhất của nguyên mẫu là thiếu số đo mới và bằng chứng thủy lực tại cống. Chức năng cống hiện kiểm tra tính đầy đủ và điều kiện của một phiếu theo RuleProfile kỹ thuật, không thay quy trình vận hành và không phát lệnh thiết bị. Hướng phát triển ưu tiên là thu thập EC cùng mực nước hai phía công trình với giờ đo và nguồn xác minh, lưu bản dự báo trước kỳ mục tiêu, chấm trên nhãn mới và hiệu chuẩn quan hệ không gian bằng các điểm đo đồng thời. Chỉ sau những bước đó mới có cơ sở đánh giá hệ thống như công cụ hỗ trợ vận hành ở một công trình cụ thể.

# TÀI LIỆU THAM KHẢO

[1] Breiman L., “Random Forests,” Machine Learning, tập 45, 2001, tr. 5-32.

[2] Cressie N., Statistics for Spatial Data, bản sửa đổi, Wiley, New York, 1993.

[3] FastAPI, “FastAPI Documentation,” https://fastapi.tiangolo.com/, truy cập ngày 17/11/2026.

[4] Hyndman R. J. và Athanasopoulos G., Forecasting: Principles and Practice, lần xuất bản thứ 3, OTexts, Melbourne, 2021.

[5] Internet Engineering Task Force, “The GeoJSON Format,” RFC 7946, 2016.

[6] Leaflet, “Leaflet Documentation,” https://leafletjs.com/reference.html, truy cập ngày 17/11/2026.

[7] Mekong River Commission, State of the Basin Report 2023, Vientiane, 2023.

[8] PostGIS Project, “PostGIS Documentation,” https://postgis.net/documentation/, truy cập ngày 17/11/2026.

[9] OpenLayers, “OpenLayers Documentation,” https://openlayers.org/doc/, truy cập ngày 17/11/2026.

[10] Shepard D., “A two-dimensional interpolation function for irregularly-spaced data,” Proceedings of the 1968 ACM National Conference, 1968, tr. 517-524.

[11] UNESCO, Algorithms for Computation of Fundamental Properties of Seawater, UNESCO Technical Papers in Marine Science 44, Paris, 1983.
