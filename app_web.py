import streamlit as st
import streamlit.components.v1 as components
from pydantic import BaseModel, Field
from typing import Optional, List
import base64
from openai import OpenAI
import time
import re


st.set_page_config(page_title="Trợ Lý Nhắc Thuốc AI ", layout="wide")


try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    pass


if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Tôi là NHÀ THUỐC AI. Tôi đã sẵn sàng, vui lòng tải toa thuốc lên để tôi có thể hỗ trợ tư vấn chi tiết cho bạn."}
    ]
if "toa_thuoc_context" not in st.session_state:
    st.session_state.toa_thuoc_context = ""
if "quet_thanh_cong" not in st.session_state:
    st.session_state.quet_thanh_cong = False
if "du_lieu_ocr" not in st.session_state:
    st.session_state.du_lieu_ocr = None


with st.sidebar:
    st.markdown("###  Lịch Sử Đơn Thuốc")
    st.caption("Bấm vào từng đơn để xem chi tiết hướng dẫn uống thuốc.")
    
    js_render_history = """
    <div id="history-container">Đang tải lịch sử...</div>
    
    <style>
        #history-container { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #333; }
        .toa-item { background: #f8f9fa; border-radius: 8px; padding: 12px; margin-bottom: 12px; border-left: 5px solid #00796B; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .toa-header { cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
        .toa-title { color: #00796B; font-weight: bold; font-size: 14px; }
        .toa-days { font-size: 11px; background: #e0f2f1; color: #004d40; padding: 2px 6px; border-radius: 4px; }
        .toa-details { display: none; margin-top: 10px; padding-top: 10px; border-top: 1px dashed #ccc; font-size: 13px; }
        .toa-details.active { display: block; }
        .thuoc-khoi { background: #fff; padding: 8px; border-radius: 6px; margin-bottom: 6px; border: 1px solid #e0e0e0; }
        .thuoc-ten { color: #d32f2f; font-weight: bold; }
        .ocr-box { background: #fffde7; padding: 6px; border-radius: 4px; font-size: 11px; color: #555; max-height: 80px; overflow-y: auto; margin-top: 5px; border-left: 2px solid #fbc02d; }
        .btn-xoa { background: #ffebee; color: #c62828; border: 1px solid #ffcdd2; padding: 10px; width: 100%; border-radius: 6px; cursor: pointer; font-weight: bold; margin-top: 15px; transition: 0.2s; }
        .btn-xoa:hover { background: #b71c1c; color: white; }
        @media (prefers-color-scheme: dark) {
            #history-container { color: #f0f0f0; }
            .toa-item { background: #263238; border-left: 5px solid #80CBC4; color: #fff; }
            .toa-title { color: #80CBC4; }
            .toa-days { background: #004d40; color: #80CBC4; }
            .thuoc-khoi { background: #37474F; border-color: #455A64; }
            .thuoc-ten { color: #ff8a80; }
            .ocr-box { background: #4e4d39; color: #e0e0e0; border-left: 2px solid #ffd54f; }
            .btn-xoa { background: #37474F; color: #ff8a80; border-color: #ff8a80; }
            .btn-xoa:hover { background: #d32f2f; color: white; }
        }
    </style>
    
    <script>
        function toggleToa(index) {
            const detailDiv = document.getElementById('details-' + index);
            const muiTen = document.getElementById('arrow-' + index);
            if (detailDiv.classList.contains('active')) {
                detailDiv.classList.remove('active');
                muiTen.innerText = '▼';
            } else {
                detailDiv.classList.add('active');
                muiTen.innerText = '▲';
            }
        }
        function renderHistory() {
            const container = document.getElementById('history-container');
            const dataStr = localStorage.getItem('lichSuToaThuoc');
            if (!dataStr || JSON.parse(dataStr).length === 0) {
                container.innerHTML = '<p style="color: #757575; font-size: 14px; text-align: center; margin-top: 20px;">Chưa có đơn thuốc nào được quét.</p>';
                return;
            }
            try {
                const lichSu = JSON.parse(dataStr);
                let html = '';
                lichSu.forEach((toa, index) => {
                    html += `<div class="toa-item">`;
                    html += `  <div class="toa-header" onclick="toggleToa(${index})">`;
                    html += `    <span class="toa-title"> Đơn thuốc #${index + 1}</span>`;
                    html += `    <div><span class="toa-days">${toa.so_ngay_uong || 1} ngày</span> <span id="arrow-${index}" style="font-size:10px; margin-left:5px; color:gray;">▼</span></div>`;
                    html += `  </div>`;
                    html += `  <div id="details-${index}" class="toa-details">`;
                    if(toa.danh_sach_thuoc && toa.danh_sach_thuoc.length > 0) {
                        toa.danh_sach_thuoc.forEach(thuoc => {
                            const gioUong = (thuoc.gio_uong_goi_y && thuoc.gio_uong_goi_y.length > 0) ? thuoc.gio_uong_goi_y.join(', ') : 'Chưa rõ giờ';
                            html += `    <div class="thuoc-khoi">`;
                            html += `       <div class="thuoc-ten"> ${thuoc.ten_thuoc}</div>`;
                            html += `       <div><b>Liều dùng:</b> ${thuoc.lieu_luong || 'Theo chỉ định'}</div>`;
                            html += `       <div><b>Giờ uống:</b> <span style="color:#00796B; font-weight:bold;">${gioUong}</span></div>`;
                            if(thuoc.ghi_chu) {
                                html += `   <div style="font-size:11px; color:gray; margin-top:3px;"><i>*Lưu ý: ${thuoc.ghi_chu}</i></div>`;
                            }
                            html += `    </div>`;
                        });
                    } else {
                        html += `    <div style="color:gray;">Không bóc tách được chi tiết thuốc.</div>`;
                    }
                    if(toa.van_ban_goc_ocr) {
                        html += `    <div style="font-weight:bold; font-size:11px; margin-top:8px; color:#757575;"> Chữ thô gốc quét được:</div>`;
                        html += `    <div class="ocr-box">${toa.van_ban_goc_ocr}</div>`;
                    }
                    html += `  </div>`;
                    html += `</div>`;
                });
                html += `<button onclick="clearHistory()" class="btn-xoa"> XÓA TOÀN BỘ LỊCH SỬ</button>`;
                if (container.getAttribute('data-len') !== String(lichSu.length)) {
                    container.innerHTML = html;
                    container.setAttribute('data-len', String(lichSu.length));
                }
            } catch(e) {
                container.innerHTML = '<p style="color: red;">Lỗi đọc dữ liệu lịch sử.</p>';
            }
        }
        function clearHistory() {
            if(confirm("Bạn có chắc chắn muốn xóa sạch toàn bộ lịch sử đơn thuốc và tắt tất cả báo thức không?")) {
                localStorage.removeItem('lichSuToaThuoc');
                sessionStorage.clear();
                document.getElementById('history-container').removeAttribute('data-len');
                renderHistory();
            }
        }
        renderHistory();
        setInterval(renderHistory, 3000);
    </script>
    """
    components.html(js_render_history, height=650, scrolling=True)


js_global_alarm = """
<script>
    if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
        Notification.requestPermission();
    }
    if (!window.hasNotificationInterval) {
        window.hasNotificationInterval = true;
        setInterval(function() {
            const now = new Date();
            const gioHienTai = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
            const giayHienTai = now.getSeconds();
            if (giayHienTai < 10) {
                const dataStr = localStorage.getItem('lichSuToaThuoc');
                if(dataStr) {
                    try {
                        const lichSu = JSON.parse(dataStr);
                        if(Array.isArray(lichSu)) {
                            lichSu.forEach(lichLuu => {
                                if(lichLuu && lichLuu.danh_sach_thuoc) {
                                    lichLuu.danh_sach_thuoc.forEach(thuoc => {
                                        if(thuoc.gio_uong_goi_y && thuoc.gio_uong_goi_y.includes(gioHienTai)) {
                                            const notifyKey = 'notified_' + gioHienTai + '_' + thuoc.ten_thuoc;
                                            if (!sessionStorage.getItem(notifyKey)) {
                                                const tieuDe = "ĐẾN GIỜ UỐNG THUỐC!";
                                                const noiDung = thuoc.ten_thuoc + "\\nLiều: " + (thuoc.lieu_luong || "Vừa đủ");
                                                if ("Notification" in window && Notification.permission === "granted") {
                                                    new Notification(tieuDe, { body: noiDung });
                                                } else {
                                                    alert(tieuDe + "\\n" + noiDung);
                                                }
                                                sessionStorage.setItem(notifyKey, "true");
                                            }
                                        }
                                    });
                                }
                            });
                        }
                    } catch(e) { console.error("Lỗi hệ thống báo thức:", e); }
                }
            }
        }, 5000); 
    }
</script>
"""
components.html(js_global_alarm, height=0, width=0)


class ThongTinThuoc(BaseModel):
    ten_thuoc: str = Field(default="")
    lieu_luong: Optional[str] = Field(default="")
    cac_buoi_uong: List[str] = Field(default_factory=list)
    gio_uong_goi_y: List[str] = Field(default_factory=list)
    ghi_chu: Optional[str] = Field(default="")

class ToaThuocSmart(BaseModel):
    van_ban_goc_ocr: str = Field(default="Không trích xuất được chữ") 
    danh_sach_thuoc: List[ThongTinThuoc] = Field(default_factory=list)
    so_ngay_uong: int = Field(default=1)

def tao_thong_bao_trinh_duyet(du_lieu_toa):
    du_lieu_json = du_lieu_toa.model_dump_json()
    js_code = f"""
    <script>
        let lichSu = JSON.parse(localStorage.getItem('lichSuToaThuoc')) || [];
        const donMoi = {du_lieu_json};
        if (!lichSu.some(toa => JSON.stringify(toa.danh_sach_thuoc) === JSON.stringify(donMoi.danh_sach_thuoc))) {{
            lichSu.push(donMoi);
            localStorage.setItem('lichSuToaThuoc', JSON.stringify(lichSu));
        }}
    </script>
    """
    components.html(js_code, height=0, width=0)

def encode_image(file_anh):
    return base64.b64encode(file_anh.getvalue()).decode('utf-8')


def doc_toa_thuoc_bang_ai(file_anh):
    api_key_an = st.secrets["SAMBANOVA_API_KEY"]
    client = OpenAI(api_key=api_key_an, base_url="https://api.sambanova.ai/v1")
    base64_image = encode_image(file_anh)
    
    loi_dan = """
    Hệ thống của bạn bao gồm 2 mô-đun: OCR và NLP.
    1. BƯỚC OCR: Đọc chính xác toàn bộ chữ viết tay/chữ in trong ảnh. Lưu vào "van_ban_goc_ocr".
    2. BƯỚC NLP: Phân tích đoạn chữ đó để bóc tách: tên thuốc, liều dùng, số ngày uống, ghi chú.
    
    BẮT BUỘC - QUY TẮC TỰ ĐỘNG ĐIỀN GIỜ THEO BUỔI (Nếu đơn thuốc không ghi giờ cụ thể):
    - SÁNG -> "08:00" | TRƯA -> "12:00" | CHIỀU -> "16:00" | TỐI -> "20:00"
    
    TRẢ VỀ DUY NHẤT ĐỊNH DẠNG JSON. Không dùng markdown như ```json. 
    Trường "so_ngay_uong" bắt buộc là SỐ NGUYÊN.
    """

    thoi_gian_cho = 4  
    for luot_thu in range(4):
        try:
            response = client.chat.completions.create(
                model="gemma-3-12b-it",  
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": loi_dan},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ],
                temperature=0.1
            )
            
            ket_qua = response.choices[0].message.content
            ket_qua_sach = ket_qua.replace("```json", "").replace("```", "").strip()
            
            match = re.search(r'\{.*\}', ket_qua_sach, re.DOTALL)
            if match:
                chuoi_json_sach = match.group(0)
                return ToaThuocSmart.model_validate_json(chuoi_json_sach)
            else:
                raise ValueError("Không tìm thấy cấu trúc JSON hợp lệ từ AI.")
                
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                if luot_thu < 3:
                    st.warning(f"⚠️ Hệ thống đang quá tải (Lỗi 429). Đang thử lại sau {thoi_gian_cho} giây...")
                    time.sleep(thoi_gian_cho)
                    thoi_gian_cho *= 2
                    continue
            else:
                if luot_thu < 3:
                    time.sleep(2)
                    continue
            st.error(f"⚠️ Lỗi xử lý AI: {e}")
            return None


st.markdown('<div class="main-title">Trợ Lý Y Tế AI Toàn Diện</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Quét đơn thuốc - Lên lịch báo thức - Dược sĩ ảo tư vấn 24/7</div>', unsafe_allow_html=True)

with st.container():
    file_tai_len = st.file_uploader("Tải ảnh toa thuốc của bạn lên đây (Định dạng: JPG, PNG)", type=["jpg", "jpeg", "png"])

if file_tai_len is not None:
    if st.button("KÍCH HOẠT QUÉT ĐƠN THUỐC VÀ LÊN LỊCH"):
        with st.spinner("AI OCR&NLP đang phân tích dữ liệu, vui lòng đợi..."):
            du_lieu = doc_toa_thuoc_bang_ai(file_tai_len)
            if du_lieu:
                st.session_state.du_lieu_ocr = du_lieu
                st.session_state.toa_thuoc_context = du_lieu.model_dump_json()
                st.session_state.quet_thanh_cong = True
                
                
                tom_tat_chatbox = "Tôi đã xử lý xong đơn thuốc của bạn.\n\n"
                tom_tat_chatbox += f"**Thời gian dùng:** {du_lieu.so_ngay_uong} ngày.\n"
                tom_tat_chatbox += "**Danh mục thuốc nhận diện:**\n"
                for idx, t in enumerate(du_lieu.danh_sach_thuoc):
                    tom_tat_chatbox += f"- **{t.ten_thuoc}**: {t.lieu_luong or 'Theo chỉ định'} (Giờ uống: {', '.join(t.gio_uong_goi_y)})\n"
                tom_tat_chatbox += "\nBạn có câu hỏi nào cần tôi tư vấn về liều lượng, kiêng cữ hay tác dụng phụ không?"
                
                # Append thẳng vào luồng hội thoại chatbox
                st.session_state.messages.append({"role": "assistant", "content": tom_tat_chatbox})
                
                tao_thong_bao_trinh_duyet(du_lieu)
                st.success("Hệ thống đã phân tích thành công và cập nhật vào AI !")


if st.session_state.quet_thanh_cong and st.session_state.du_lieu_ocr:
    du_lieu = st.session_state.du_lieu_ocr
    col1, col2 = st.columns([1, 1.2]) 
    
    with col1:
        st.markdown("### Ảnh Toa Thuốc")
        st.image(file_tai_len, use_container_width=True)
        with st.expander("Xem kết quả "):
            st.info("Bản hệ thống đọc được từ ảnh:")
            st.text(du_lieu.van_ban_goc_ocr)

    with col2:
        st.markdown(f"### Lịch Trình Vừa Quét (Dùng trong {du_lieu.so_ngay_uong} ngày)")
        st.info("Báo thức đã được kích hoạt.")
        for i, thuoc in enumerate(du_lieu.danh_sach_thuoc):
            with st.container(border=True):
                st.markdown(f"**Thuốc {i+1}: {thuoc.ten_thuoc or 'Chưa rõ tên'}**")
                st.write(f"Liều lượng: {thuoc.lieu_luong or 'Chưa rõ'}")
                st.write(f"Giờ uống: `{', '.join(thuoc.gio_uong_goi_y) if thuoc.gio_uong_goi_y else 'Chưa thiết lập'}`")
                if thuoc.ghi_chu: 
                    st.caption(f"Lưu ý: {thuoc.ghi_chu}")

st.markdown("<br><hr><br>", unsafe_allow_html=True)


st.markdown("## NHÀ THUỐC AI")
st.caption("AI đã ghi nhớ thông tin đơn thuốc của bạn. Vui lòng đặt câu hỏi nếu có thắc mắc.")

chat_container = st.container(border=True)

with chat_container:
    for message in st.session_state.messages:
        st.chat_message(message["role"]).write(message["content"])

if prompt := st.chat_input("Nhập câu hỏi tại đây (Ví dụ: Thuốc này cần kiêng ăn gì?)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_container:
        st.chat_message("user").write(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Đang tra cứu cơ sở dữ liệu y khoa...")
            
            
            api_key_an = st.secrets["SAMBANOVA_API_KEY"]
            client = OpenAI(api_key=api_key_an, base_url="https://api.sambanova.ai/v1")
            
            system_prompt = "Bạn là NHÀ THUỐC AI, một dược sĩ tận tâm, chuyên nghiệp. Trả lời rõ ràng, lịch sự."
            if st.session_state.toa_thuoc_context:
                system_prompt += f"\nThông tin đơn thuốc của bệnh nhân (Dạng JSON OCR): {st.session_state.toa_thuoc_context}"

            messages_for_api = [{"role": "system", "content": system_prompt}]
            for msg in st.session_state.messages:
                messages_for_api.append({"role": msg["role"], "content": msg["content"]})
            
            thoi_gian_cho_chat = 3
            for luot_thu_chat in range(3):
                try:
                    response = client.chat.completions.create(
                        model="Llama-4-Maverick-17B-128E-Instruct",
                        messages=messages_for_api,
                        temperature=0.7
                    )
                    
                    bot_reply = response.choices[0].message.content
                    message_placeholder.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    break
                    
                except Exception as e:
                    if "429" in str(e) or "rate_limit" in str(e).lower():
                        if luot_thu_chat < 2:
                            time.sleep(thoi_gian_cho_chat)
                            thoi_gian_cho_chat *= 2
                            continue
                    message_placeholder.error(f"Xin lỗi, kết nối máy chủ gián đoạn hoặc quá tải: {e}")
                    break
                # Đặt ở cuối cùng file code của bạn
st.markdown(
    """
    <div style="position: fixed; bottom: 20px; right: 20px; z-index: 9999; font-weight: bold; color: #00796B; background-color: #e0f2f1; padding: 8px 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
        Tác Giả:Thịnh,Khiêm,Huyền,Khánh
    </div>
    """, 
    unsafe_allow_html=True
)