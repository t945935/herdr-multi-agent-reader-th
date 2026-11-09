#!/usr/bin/env python3
"""เก็บหลักฐาน CLI และเลือกทดสอบเฉพาะ sibling Pane ที่สร้างขึ้นใหม่"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="สร้างและปิด Pane shell สำหรับทดสอบ")
    parser.add_argument("--agents", choices=["pi", "codex", "opencode"], help="เริ่ม Agent ทดสอบสองตัวด้วย")
    parser.add_argument("--receipts", action="store_true", help="ตรวจใบรับงานเฉพาะ task ด้วย scripts/team.py")
    args = parser.parse_args()
    if args.receipts and not args.agents:
        parser.error("--receipts ต้องใช้คู่กับ --agents")
    if os.environ.get("HERDR_ENV") != "1":
        raise SystemExit("โปรดรัน probe ภายใน Pane ที่ Herdr จัดการ")
    records, owned = [], []

    def command(*argv, timeout=30):
        started = datetime.now(timezone.utc).isoformat()
        proc = subprocess.run(["herdr", *argv], text=True, capture_output=True, timeout=timeout)
        records.append({"command": ["herdr", *argv], "started_at": started,
                        "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        help_result = len(argv) == 1 and argv[0] in {"agent", "pane", "workspace", "tab"} and proc.returncode == 2
        if proc.returncode and not help_result:
            raise RuntimeError(proc.stderr or proc.stdout)
        try:
            return json.loads(proc.stdout)["result"]
        except (ValueError, KeyError, TypeError):
            return proc.stdout

    success, failure = False, None
    try:
        for argv in [("--version",), ("status",), ("agent",), ("pane",), ("workspace",),
                     ("tab",), ("agent", "list"), ("pane", "current", "--current")]:
            command(*argv)
        if args.live:
            pane = command("pane", "split", "--current", "--direction", "right", "--cwd", str(ROOT), "--no-focus")["pane"]["pane_id"]
            owned.append(pane)
            marker = "TH_BOOK_SHELL_" + str(time.time_ns())
            command("pane", "run", pane, f'python3 -c \'print("{marker}")\'')
            command("pane", "wait-output", pane, "--regex", "^" + marker + "$", "--timeout", "10000")
            output = command("pane", "read", pane, "--source", "recent-unwrapped", "--lines", "20")
            if marker not in [line.strip() for line in str(output).splitlines()]:
                raise RuntimeError("พบเพียง echo ของคำสั่ง ไม่พบ marker เป็นบรรทัดผลลัพธ์แยก")
            if args.agents:
                second = command("pane", "split", pane, "--direction", "down", "--cwd", str(ROOT), "--no-focus")["pane"]["pane_id"]
                owned.append(second)
                suffix = str(time.time_ns())[-7:]
                names = ["th_check_a_" + suffix, "th_check_b_" + suffix]
                for name, target in zip(names, [pane, second]):
                    command("agent", "start", name, "--kind", args.agents, "--pane", target, "--timeout", "30000", timeout=40)
                prompts = ["ตอบเฉพาะ TH_AGENT_A_OK นี่คือการทดสอบสื่อสาร ห้ามใช้เครื่องมือ อ่าน／เขียนไฟล์ หรือเริ่ม Agent อื่น",
                           "ตอบเฉพาะ TH_AGENT_B_OK นี่คือการทดสอบสื่อสาร ห้ามใช้เครื่องมือ อ่าน／เขียนไฟล์ หรือเริ่ม Agent อื่น"]
                for name, prompt in zip(names, prompts):
                    command("agent", "prompt", name, prompt)
                for index, (name, token) in enumerate(zip(names, ["TH_AGENT_A_OK", "TH_AGENT_B_OK"])):
                    state = command("agent", "wait", name, "--timeout", "90000", timeout=100)
                    if state.get("agent", {}).get("agent_status") == "blocked":
                        raise RuntimeError("Agent อยู่ในสถานะ blocked ต้องให้ผู้ใช้จัดการ")
                    command("pane", "wait-output", owned[index], "--match", token, "--timeout", "90000", timeout=100)
                    transcript = command("agent", "read", name, "--source", "recent-unwrapped", "--lines", "60")
                    if token not in str(transcript):
                        raise RuntimeError("ไม่พบ marker ของคำตอบที่ต้องการ")
                if args.receipts:
                    for name in names:
                        output = ROOT / "reports" / (name + "-receipt.json")
                        cmd = [sys.executable, str(ROOT / "scripts/team.py"), name,
                               str(ROOT / "examples/prompts/receipt-smoke.md"), "--output", str(output)]
                        done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=310)
                        records.append({"command": cmd, "returncode": done.returncode,
                                        "stdout": done.stdout, "stderr": done.stderr})
                        if done.returncode:
                            raise RuntimeError(done.stderr or done.stdout)
        success = True
    except Exception as exc:
        failure = str(exc)
    finally:
        for pane in reversed(owned):
            try:
                command("pane", "close", pane)
            except Exception as exc:
                failure = (failure or "") + " cleanup: " + str(exc)
                success = False
        report = {"captured_at": datetime.now(timezone.utc).isoformat(), "success": success,
                  "live_shell": args.live, "agent_kind": args.agents, "task_receipts": args.receipts,
                  "error": failure, "commands": records}
        out = ROOT / "reports" / "herdr-probe.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"success": success, "commands": len(records), "report": str(out), "error": failure}, ensure_ascii=False))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
