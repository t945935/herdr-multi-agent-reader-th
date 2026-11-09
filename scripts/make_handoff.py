#!/usr/bin/env python3
"""สร้างใบส่งต่องานตัวอย่างที่ผูกกับไฟล์ grades.py จริง"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "examples/grades.py"
record = {
    "task_id": "grade-api-v1", "from": "developer", "to": "qa",
    "completed": "จัดทำสัญญาและโค้ดอ้างอิงระบบคะแนนแล้ว", "next": "รันทดสอบ regression ด้านอันดับและข้อมูลนำเข้า",
    "artifacts": [{"path": "examples/grades.py", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}],
}
out = ROOT / "reports/handoff.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
