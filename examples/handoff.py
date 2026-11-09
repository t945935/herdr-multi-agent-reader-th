"""ตรวจสอบใบส่งต่องานที่ระบุชัด ไม่เชื่อเพียงข้อความของ Agent"""

import argparse
import hashlib
import json
from pathlib import Path


def validate(record, root):
    required = {"task_id", "from", "to", "completed", "next", "artifacts"}
    if not isinstance(record, dict) or not required <= record.keys():
        raise ValueError("ข้อมูลใบส่งต่องานไม่ครบ")
    if any(not isinstance(record[key], str) or not record[key].strip()
           for key in ["task_id", "from", "to", "completed", "next"]):
        raise ValueError("ช่องข้อความในใบส่งต่องานต้องไม่ว่าง")
    if not isinstance(record["artifacts"], list) or not record["artifacts"]:
        raise ValueError("ใบส่งต่องานต้องมีไฟล์ผลงาน")
    root = Path(root).resolve()
    for artifact in record["artifacts"]:
        if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
            raise ValueError("ไฟล์ผลงานต้องระบุ path และ sha256")
        path = (root / artifact["path"]).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("ไฟล์ผลงานต้องอยู่ภายในโปรเจกต์")
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
            raise ValueError("hash ของไฟล์ผลงานไม่ตรงกัน")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    validate(json.loads(args.record.read_text(encoding="utf-8")), args.root)
    print("ตรวจสอบใบส่งต่องานแล้ว")
