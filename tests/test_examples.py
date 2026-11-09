import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from examples.handoff import validate as validate_handoff
from examples.pipeline import run
from examples.queue import Queue, work_once
from examples.research import render, validate


def test_handoff_hash_and_path_validation(tmp_path):
    artifact = tmp_path / "result.txt"
    artifact.write_text("รับงานแล้ว")
    record = {"task_id": "T1", "from": "developer", "to": "qa", "completed": "ทำระบบแล้ว", "next": "ทดสอบ",
              "artifacts": [{"path": "result.txt", "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}]}
    assert validate_handoff(record, tmp_path)
    artifact.write_text("changed")
    with pytest.raises(ValueError, match="hash"):
        validate_handoff(record, tmp_path)
    record["artifacts"][0]["path"] = "../outside"
    with pytest.raises(ValueError, match="ภายในโปรเจกต์"):
        validate_handoff(record, tmp_path)


def test_research_supported_claim_requires_valid_evidence():
    data = {"question": "โจทย์วิจัย", "sources": [{"id": "S1", "title": "เอกสารทางการ", "url": "https://herdr.dev/", "accessed": "2026-11-06", "kind": "ทางการ"}],
            "claims": [{"text": "ข้อกล่าวอ้าง", "status": "supported", "evidence": [{"source": "S1", "quote": "quote"}]}]}
    assert "quote" in render(data)
    data["claims"][0]["evidence"][0]["source"] = "unknown"
    with pytest.raises(ValueError):
        validate(data)
    data["claims"][0]["evidence"] = []
    with pytest.raises(ValueError):
        validate(data)


def test_pipeline_preserves_failure_and_skips_later_stage(tmp_path):
    import sys
    stages = [{"name": "ล้มเหลว", "command": [sys.executable, "-c", "raise SystemExit(7)"]},
              {"name": "ขั้นถัดไป", "command": [sys.executable, "-c", "print(1)"]}]
    report = run(stages, tmp_path, tmp_path / "logs")
    assert report["status"] == "failed" and len(report["stages"]) == 1
    assert report["stages"][0]["returncode"] == 7


def test_pipeline_checks_artifact_and_timeout(tmp_path):
    import sys
    result = run([{"name": "ไม่มีไฟล์ผลลัพธ์", "command": [sys.executable, "-c", "pass"], "artifacts": ["missing"]}], tmp_path, tmp_path / "a")
    assert result["status"] == "failed"
    result = run([{"name": "หมดเวลา", "command": [sys.executable, "-c", "import time; time.sleep(2)"], "timeout": .05}], tmp_path, tmp_path / "b")
    assert result["stages"][0]["returncode"] == 124


def test_queue_deduplicates_and_detects_payload_conflicts(tmp_path):
    queue = Queue(tmp_path / "queue.db")
    queue.enqueue("A", {"numbers": [1, 2]})
    queue.enqueue("A", {"numbers": [1, 2]})
    assert len(queue.jobs()) == 1
    with pytest.raises(ValueError):
        queue.enqueue("A", {"numbers": [9]})
    assert work_once(queue)
    assert queue.jobs()[0]["state"] == "done"
    assert json.loads(queue.jobs()[0]["result"]) == {"sum": 3}


def test_queue_crash_recovery_fences_expired_owner(tmp_path):
    queue = Queue(tmp_path / "queue.db")
    queue.enqueue("A", {"numbers": [1]})
    old = queue.claim(lease_seconds=10, now=100)
    assert queue.claim(now=105) is None
    new = queue.claim(now=111)
    assert new["owner"] != old["owner"]
    assert not queue.finish(old, result="ผลเก่าที่หมดอายุ", now=112)
    assert queue.heartbeat(new, now=112)
    assert queue.finish(new, result="ผลจากเจ้าของปัจจุบัน", now=113)


def test_queue_max_attempts_and_restart(tmp_path):
    path = tmp_path / "queue.db"
    queue = Queue(path)
    queue.enqueue("A", {}, max_attempts=2)
    first = queue.claim(now=100)
    assert queue.finish(first, error="ผิดพลาด", now=101)
    second = queue.claim(lease_seconds=1, now=102)
    assert second
    restarted = Queue(path)
    assert restarted.claim(now=104) is None
    assert restarted.jobs()[0]["state"] == "dead"


def test_queue_concurrent_claim_is_exclusive(tmp_path):
    queue = Queue(tmp_path / "queue.db")
    for index in range(8):
        queue.enqueue(str(index), {"numbers": [index]})
    with ThreadPoolExecutor(max_workers=8) as executor:
        claimed = list(executor.map(lambda _: queue.claim(), range(8)))
    assert len({job["id"] for job in claimed}) == 8


def test_concurrent_conflicting_enqueue_rejects_second_payload(tmp_path):
    queue = Queue(tmp_path / "jobs.db")

    def enqueue(number):
        try:
            queue.enqueue("same-key", {"numbers": [number]})
            return "รับงาน"
        except ValueError:
            return "ขัดแย้ง"

    with ThreadPoolExecutor(max_workers=2) as executor:
        states = sorted(executor.map(enqueue, [1, 2]))
    assert set(states) == {"รับงาน", "ขัดแย้ง"}
    assert len(queue.jobs()) == 1
