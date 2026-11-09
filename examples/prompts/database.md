# Database

แก้ได้เฉพาะ `examples/task_manager/db.py` เตรียม `init_db`, `get_tasks`, `get_task`, `create_task`, `update_task`, `delete_task` อนุญาตให้การทดสอบเปลี่ยน DB_PATH ได้ ต้องปิดการเชื่อมต่อ ใช้ transaction ในการเขียน และใช้ SQL แบบกำหนดพารามิเตอร์สำหรับค่า ชื่อคอลัมน์แบบไดนามิกต้องมาจาก allowlist ตายตัว กำหนดให้การไม่พบข้อมูลคืน None／False อย่าปลอมข้อผิดพลาดฐานข้อมูลให้กลายเป็นลิสต์ว่าง
