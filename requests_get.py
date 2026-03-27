import json
from datetime import datetime
import requests


headers = {
    "accept": "application/json",
    "accept-encoding": "gzip, deflate",
    "accept-language": "en-US,en;q=0.9,vi;q=0.8",
    "Content-type": "application/json",
    "Cookie": "_ga_DMHDSY29QY=GS2.1.s1770899438$o6$g1$t1770899558$j60$l0$h0; _ga=GA1.1.2040301921.1768664475; language=vi; _ga_CWFTHLQHPT=GS2.1.s1774321153$o5$g0$t1774321156$j57$l0$h0; JSESSIONID=aCEzFaYmgEJNPnRCSYUqkg.node0; token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NzQ5MjU5ODQsImVtYWlsIjoiZHVjbm0uMjNiYTE0MDU2QHVzdGguZWR1LnZuIn0.EfzQSX-VFtMKj1gxqLUYFIM4DGeD5Owt1hzSGrVnx4s; soict-session-id=7C4FF215-7770-431A-BC1F-A4B5B73E8537-1774321184461_1774321184461; x-student-portal-token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjoiOGg3b294M3ByQzJyYWJzSTF5MFoyVkRzb2cyR29QQ0UvZG5VakxBMkVVQzBkZmtETVNocW5lVjd0d2dkWkRqeTc1am5MRThkZVB6M3Nvc3hLTzBpekJHb24raVc0TERhK3JBdFpwVkcwQTFVcktSbVIyQUNXL3UyU2dQUmtEelMiLCJpYXQiOjE3NzQzMjExODcsImV4cCI6MTc3NDQwNzU4N30.XDe8RY4o4WHtiC5tf0UPGnTHlC9n6ZYQFrkf3PL66oQ; _ga_0Q453EM71J=GS2.1.s1774320702$o85$g1$t1774321584$j60$l0$h0",
    "origin": "https://erp.usth.edu.vn",
    "priority": "u=1, i",
    "Referer": "https://erp.usth.edu.vn/students/learn/timetable",
    "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "x-check-sum": "c92426d0028f06515a587fef8c4e7cc1ca55e4c25f6c7890701d2812799ea83a"
}

payload = {
    "fromTime": 1771779600000,
    "toTime": 1775408399999,
    "semester": "20252",
    "weeks": [30, 31, 32, 33, 34, 35]
}

response = requests.post('https://erp.usth.edu.vn/student-services/api/v2/timetables/query-student-timetable-in-range', headers=headers, json=payload)

if response.status_code == 200:
    calendar_data = response.json()
else:
    print("Failed to retrieve timetable data")
    exit()

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