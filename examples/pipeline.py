"""สายงานแบบมีขอบเขต เก็บ exit code, timeout และตรวจรับอย่างชัดเจน"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(stages, cwd, output):
    result = {"started_at": datetime.now(timezone.utc).isoformat(), "status": "running", "stages": []}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for index, stage in enumerate(stages):
        if not isinstance(stage.get("command"), list) or not stage["command"]:
            raise ValueError("command ต้องเป็นอาร์เรย์ argv ที่ไม่ว่าง")
        try:
            completed = subprocess.run(stage["command"], cwd=cwd, capture_output=True,
                                       text=True, timeout=stage.get("timeout", 60))
            code, log = completed.returncode, completed.stdout + completed.stderr
        except subprocess.TimeoutExpired as exc:
            code, log = 124, f"หมดเวลาหลังจาก {exc.timeout} วินาที\n"
        log_name = f"{index + 1:02d}.log"
        (output / log_name).write_text(log, encoding="utf-8")
        accepted = code == 0 and all((Path(cwd) / p).is_file() for p in stage.get("artifacts", []))
        result["stages"].append({"name": stage["name"], "returncode": code,
                                 "accepted": accepted, "log": log_name})
        if not accepted:
            result["status"] = "failed"
            break
    else:
        result["status"] = "passed"
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    (output / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/pipeline"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    stages = [
        {"name": "ทดสอบหน่วยและ API", "command": [sys.executable, "-m", "pytest", "-q", "tests", "--junitxml", "reports/tests.xml"], "timeout": 120},
        {"name": "สร้างรายงานวิจัย", "command": [sys.executable, "-m", "examples.research", "examples/research-evidence.json",
          "--output", "reports/research-report.md"], "artifacts": ["reports/research-report.md"]},
    ]
    result = run(stages, root, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)
