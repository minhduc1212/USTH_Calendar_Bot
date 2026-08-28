import json
import base64
import hashlib
import os
import sys
from datetime import datetime
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ================= CẤU HÌNH MÃ HÓA TỪ HỆ THỐNG ERP =================
# Các hằng số được trích xuất từ source JavaScript của hệ thống ERP USTH
E_N = "304c7f6dff373663d32879ac1c1f1318"
E_C = "069635c0806598e069583aee5440e448"

# Key = SHA256(E_N), IV = MD5(E_C)
AES_KEY = hashlib.sha256(E_N.encode('utf-8')).digest()
AES_IV = hashlib.md5(E_C.encode('utf-8')).digest()


def encrypt_payload(data: dict) -> str:
    """Mã hóa payload dạng dict thành chuỗi base64 AES-CBC PKCS7."""
    json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(json_str.encode('utf-8')) + padder.finalize()
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode('utf-8')


def decrypt_payload(payload_b64: str):
    """Giải mã chuỗi base64 AES-CBC PKCS7 trả về từ server thành object JSON."""
    cipher_bytes = base64.b64decode(payload_b64)
    cipher = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV))
    decryptor = cipher.decryptor()
    padded = decryptor.update(cipher_bytes) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(padded) + unpadder.finalize()
    return json.loads(decrypted.decode('utf-8'))


def calculate_checksum(body: dict) -> str:
    """Tính toán giá trị header x-check-sum theo thuật toán của ERP."""
    if not isinstance(body, dict):
        return ""
    # Lọc các trường kiểu nguyên thủy (loại bỏ array/object theo thuật toán frontend)
    filtered = {
        k: v for k, v in body.items()
        if v is None or isinstance(v, (str, int, float, bool))
    }
    sorted_dict = {k: filtered[k] for k in sorted(filtered.keys())}
    json_str = json.dumps(sorted_dict, separators=(',', ':'), ensure_ascii=False)
    serialized = json.dumps(json_str, ensure_ascii=False)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def get_cookies():
    """Lấy cookies từ usth_profile (nếu có playwright) hoặc dùng cookies cấu hình sẵn."""
    if os.path.exists("./usth_profile"):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    user_data_dir="./usth_profile",
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                cookies_list = browser.cookies(["https://erp.usth.edu.vn"])
                browser.close()
                return {c['name']: c['value'] for c in cookies_list}
        except Exception as e:
            print(f"Không thể đọc cookies tự động từ profile ({e}), chuyển sang cookies thủ công.")
    
    # Cookie thủ công dự phòng nếu không dùng browser profile
    return {
        "token": "YOUR_TOKEN_HERE",
        "soict-session-id": "YOUR_SOICT_SESSION_ID_HERE",
        "x-student-portal-token": "YOUR_PORTAL_TOKEN_HERE",
        "x-access-token": "YOUR_ACCESS_TOKEN_HERE"
    }


def refresh_session_cookies():
    """Mở trang timetable trong profile để tự động refresh token/session cookies qua SSO callback."""
    if not os.path.exists("./usth_profile"):
        return None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir="./usth_profile",
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.new_page()
            page.goto("https://erp.usth.edu.vn/students/learn/timetable", timeout=20000)
            page.wait_for_timeout(3000)
            cookies_list = browser.cookies(["https://erp.usth.edu.vn"])
            browser.close()
            return {c['name']: c['value'] for c in cookies_list}
    except Exception as e:
        print(f"⚠️ Không thể tự động làm mới session qua profile: {e}")
        return None


def fetch_timetable(from_time: int, to_time: int, semester: str, weeks: list, auto_retry: bool = True):
    """Gửi request lấy thời khóa biểu bằng requests với payload đã mã hóa."""
    cookies = get_cookies()
    
    body = {
        "fromTime": from_time,
        "toTime": to_time,
        "semester": semester,
        "weeks": weeks
    }
    
    checksum = calculate_checksum(body)
    encrypted_payload = encrypt_payload(body)
    request_data = {"payload": encrypted_payload}
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "origin": "https://erp.usth.edu.vn",
        "Referer": "https://erp.usth.edu.vn/students/learn/timetable",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "x-check-sum": checksum
    }
    
    url = "https://erp.usth.edu.vn/student-services/api/v2/timetables/query-student-timetable-in-range"
    
    print("⏳ Đang gửi request lấy thời khóa biểu...")
    response = requests.post(url, headers=headers, json=request_data, cookies=cookies)
    
    if response.status_code != 200:
        # Cố gắng giải mã response payload nếu server trả về payload mã hóa
        err_detail = response.text
        try:
            res_json = response.json()
            if isinstance(res_json, dict) and "payload" in res_json:
                err_detail = json.dumps(decrypt_payload(res_json["payload"]), ensure_ascii=False)
        except Exception:
            pass

        print(f"❌ Lỗi khi tải dữ liệu. HTTP Status: {response.status_code}")
        print(f"Chi tiết lỗi: {err_detail}")
        
        # Tự động refresh cookie nếu gặp 401 (Invalid Token / Session expired)
        if response.status_code == 401 and auto_retry and os.path.exists("./usth_profile"):
            print("🔄 Phát hiện Token/Session hết hạn. Đang tự động làm mới session qua trình duyệt...")
            refreshed_cookies = refresh_session_cookies()
            if refreshed_cookies:
                print("✅ Đã làm mới session thành công. Đang thử gửi lại request...")
                return fetch_timetable(from_time, to_time, semester, weeks, auto_retry=False)
            else:
                print("👉 Vui lòng chạy lại 'python playwright_get.py' để đăng nhập lại tài khoản.")
        return None
    
    res_json = response.json()
    if isinstance(res_json, dict) and "payload" in res_json:
        data = decrypt_payload(res_json["payload"])
        return data
    return res_json


def display_timetable(calendar_data):
    """In danh sách lịch học ra console."""
    if not calendar_data:
        print("Không có dữ liệu thời khóa biểu.")
        return

    print(f"\n✅ Lấy thành công dữ liệu ({len(calendar_data)} môn học / lớp).")
    
    for course in calendar_data:
        course_name = course.get('courseName') or 'Không xác định'
        schedules = course.get('_calendars', [])

        if schedules:
            class_id = course.get('classId', 'Không xác định')
            print(f"\nMôn học: {course_name} (Lớp: {class_id})")
            
            for schedule in schedules:
                place = schedule.get('place') or 'Chưa rõ'
                teacher_names = schedule.get('teacherNames')
                teachers = ", ".join(teacher_names) if teacher_names else 'Chưa phân công'
                
                # Chuyển đổi timestamp sang ngày tháng
                date_timestamp = schedule.get('date', 0) / 1000.0
                date_str = datetime.fromtimestamp(date_timestamp).strftime('%d/%m/%Y')
                
                print(f"  - Thứ {schedule.get('day')}, ngày {date_str} (Tiết {schedule.get('from')} - {schedule.get('to')})")
                print(f"    Nơi học: {place} | Giảng viên: {teachers}")


if __name__ == "__main__":
    # Ví dụ khoảng thời gian truy vấn
    # Kỳ học 20261 (hoặc kỳ hiện tại bạn muốn lấy)
    data = fetch_timetable(
        from_time=1785085200000,
        to_time=1788713999999,
        semester="20261",
        weeks=[1, 2, 3, 4, 5]
    )
    
    if data:
        # Lưu vào file timetable.json
        with open("timetable.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("📁 Đã lưu dữ liệu vào file 'timetable.json'.")
        
        # In ra màn hình
        display_timetable(data)