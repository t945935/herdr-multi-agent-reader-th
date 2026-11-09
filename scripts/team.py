#!/usr/bin/env python3
"""มอบหมายงานหนึ่งครั้งแก่ Agent ที่ idle และตรวจใบรับงานเฉพาะงานนี้"""

import argparse
import json
import os
import subprocess
import uuid
from pathlib import Path


def call(*args, timeout=310):
    done = subprocess.run(["herdr", *args], text=True, capture_output=True, timeout=timeout)
    if done.returncode:
        raise RuntimeError(done.stderr or done.stdout)
    return json.loads(done.stdout)["result"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("prompt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("HERDR_ENV") != "1":
        raise SystemExit("โปรดรันภายใน Pane ที่ Herdr จัดการ")
    agent = call("agent", "get", args.target)["agent"]
    if agent["agent_status"] not in {"idle", "done"}:
        raise SystemExit("ต้องให้ Agent อยู่ในสถานะ idle/done ก่อนเริ่มงาน")
    path = args.output.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit("เลือกพาธใบรับงานใหม่ ห้ามใช้พาธของงานก่อนซ้ำ")
    task_id = uuid.uuid4().hex
    prompt = args.prompt.read_text(encoding="utf-8") + (
        f"\n\ntask_id รอบนี้={task_id}\ncompletion_path={path}\n"
        'หลังทำงานจริง ให้บันทึก JSON: {"task_id":"รหัสข้างต้น","status":"completed",'
        '"summary":"ผลงานและการตรวจสอบที่เฉพาะเจาะจง","artifacts":["พาธไฟล์ผลงานจริง"]} '
        "หากทำไม่สำเร็จให้ใช้ status=blocked และอธิบายใน summary ห้ามสร้าง Agent ตัวอื่น"
    )
    settled = call("agent", "prompt", args.target, prompt, "--wait", "--timeout", "300000")
    state = settled["agent"]["agent_status"]
    if state not in {"idle", "done"} or not path.is_file():
        raise SystemExit("Agent หยุดโดยไม่มีใบรับงานที่ยอมรับได้ โปรดตรวจ agent get/read")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("task_id") != task_id or receipt.get("status") != "completed" or not receipt.get("summary"):
        raise SystemExit("ใบรับงานยังไม่ยืนยันความสำเร็จของ task นี้")
    for artifact in receipt.get("artifacts", []):
        candidate = Path(artifact)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if not candidate.is_file():
            raise SystemExit(f"ไม่พบไฟล์ผลงาน: {artifact}")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
