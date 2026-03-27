from datetime import datetime
from playwright.sync_api import sync_playwright
import json
import time

# Đường dẫn trang web và API mục tiêu
PAGE_URL = "https://erp.usth.edu.vn/students/learn/timetable"
API_ENDPOINT = "query-student-timetable-in-range"

def print_timetable_data():
    with open("timetable.json", "r", encoding="utf-8") as f:
        calendar_data = json.load(f)
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
                
                #change to date and time
                date_timestamp = schedule.get('date', 0) / 1000.0
                date_str = datetime.fromtimestamp(date_timestamp).strftime('%d/%m/%Y')
                
                print(f"  - Thứ {schedule.get('day')}, ngày {date_str} (Tiết {schedule.get('from')} - {schedule.get('to')})")
                print(f"    Nơi học: {place} | Giảng viên: {teachers}")

def get_timetable_data():
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./usth_profile", 
            headless=True, 
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()

        print("🌐 Đang mở trang thời khóa biểu...")
        page.goto(PAGE_URL)

        print("⏳ Đang chờ dữ liệu...")
        print("👉 LƯU Ý: Nếu trình duyệt yêu cầu đăng nhập Google, hãy tự đăng nhập. Code sẽ kiên nhẫn chờ tối đa 1 phút.")

        timetable_data = None

        try:
            with page.expect_response(
                lambda response: API_ENDPOINT in response.url and response.status == 200, 
                timeout=60000
            ) as response_info:
                
                response = response_info.value
                timetable_data = response.json()
                print("\n🎉 BẮT ĐƯỢC RỒI! Đã lấy thành công dữ liệu JSON.")
                
        except Exception as e:
            print("\n❌ Quá thời gian chờ hoặc không tìm thấy request API nào.")
            print("Gợi ý: Nếu trang web đã load xong mà không có dữ liệu, hãy thử bấm chọn lại 'Kỳ học' hoặc 'Tuần' trên giao diện để kích hoạt request POST.")

        if timetable_data:
            with open("timetable.json", "w", encoding="utf-8") as f:
                json.dump(timetable_data, f, ensure_ascii=False, indent=4)
            print("Đã lưu toàn bộ dữ liệu vào file 'timetable.json' trong cùng thư mục.")
        print_timetable_data()

        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    get_timetable_data()