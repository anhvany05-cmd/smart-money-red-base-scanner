# Smart Money Red Base Scanner – Auto Data MVP V0.5

App Streamlit quét cổ phiếu Việt Nam theo phong cách:

- Tự tải dữ liệu giá cổ phiếu và VNINDEX từ nguồn online.
- Phát hiện dấu hiệu tay to gom hàng / hấp thụ cung / rũ cung.
- Ưu tiên mua đỏ trong nền, không mua xanh/đu breakout.
- Tự tính vùng mua đỏ A/B/C.
- Tự tính vùng cắt lỗ khi thủng nền.
- Cảnh báo mua đuổi, breakout đã kéo xa, phân phối.

> Đây là công cụ sàng lọc xác suất, không phải khuyến nghị đầu tư.

## 1. Cài đặt

```bash
pip install -r requirements.txt
```

## 2. Chạy app

```bash
streamlit run app.py
```

## 3. Chế độ dữ liệu

App có 5 chế độ:

1. **Tự động: Vnstock → Yahoo fallback**  
   Ưu tiên tải bằng Vnstock, nếu lỗi sẽ thử Yahoo Finance.

2. **Tự động: Vnstock**  
   Tải bằng thư viện `vnstock`, nguồn VCI hoặc KBS.

3. **Tự động: Yahoo**  
   Dùng `yfinance`, thử mã `.VN`, `.HN`.

4. **Upload thủ công**  
   Chỉ dùng khi muốn đưa dữ liệu riêng của bạn vào.

5. **Demo**  
   Dữ liệu giả lập để xem logic app.

## 4. Cách dùng nhanh

1. Mở app.
2. Để mặc định: **Tự động: Vnstock → Yahoo fallback**.
3. Chọn rổ mã: `Top thanh khoản mặc định`, `VN30-like`, hoặc tự nhập mã.
4. Chỉnh số ngày lịch sử nếu cần.
5. App tự tải dữ liệu, tự quét và xuất bảng kết quả.

## 5. Output chính

App trả về:

- Mã cổ phiếu.
- Điểm Smart Money 0–100.
- Pha: gom hàng, rũ cung, tạo nền, đã kéo/breakout, phân phối, suy yếu.
- Vùng nền.
- Vùng mua đỏ tổng.
- Vùng mua A/B/C.
- Vùng cắt lỗ.
- Điều kiện không mua.
- Điều kiện vô hiệu.
- R/R tới đỉnh nền.
- Bằng chứng và cảnh báo.

## 6. Logic điểm

Tổng điểm 100:

| Nhóm | Điểm tối đa |
|---|---:|
| Tay to có thể quan tâm | 15 |
| Gom hàng/hấp thụ | 25 |
| Sức mạnh tương đối | 15 |
| Setup mua đỏ trong nền | 20 |
| Rủi ro/không mua đuổi | 10 |
| Nền tảng & kỳ vọng | 15 |

Ở bản V0.5, nếu chưa có dữ liệu BCTC/kỳ vọng tự động ổn định, app tạm chấm trung tính cho nhóm nền tảng/kỳ vọng và ưu tiên phát hiện hành vi giá-volume-VNIndex.

## 7. Upload thủ công, nếu cần

### prices.csv hoặc prices.xlsx

Cột bắt buộc:

```text
date,ticker,open,high,low,close,volume
```

Cột khuyến nghị:

```text
value,sector
```

### vnindex.csv hoặc vnindex.xlsx

Cột bắt buộc:

```text
date,open,high,low,close
```

### fundamentals.csv hoặc fundamentals.xlsx, tùy chọn

```text
ticker,revenue_growth_yoy,profit_growth_yoy,roe,debt_to_equity,operating_cashflow_positive,expectation_score
```

## 8. Ghi chú thực chiến

Phong cách app ưu tiên:

- Mua khi đỏ/rung lắc về nền.
- Mua gần hỗ trợ để sai thì lỗ ngắn.
- Không mua xanh mạnh.
- Không mua sát đỉnh nền.
- Không mua breakout đã kéo xa.
- Cắt nếu đóng cửa thủng nền hoặc thủng nền với volume lớn.
