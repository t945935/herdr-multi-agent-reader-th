"""ตรวจหลักฐานเชื่อมข้อกล่าวอ้างกับแหล่งข้อมูล แล้วสร้างรายงานตรวจสอบย้อนกลับได้"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def validate(data):
    if not isinstance(data, dict) or not data.get("question"):
        raise ValueError("ต้องระบุโจทย์วิจัย")
    sources = data.get("sources", [])
    if not isinstance(sources, list) or not sources:
        raise ValueError("ต้องระบุแหล่งข้อมูล")
    by_id = {}
    for source in sources:
        if not {"id", "url", "title", "accessed", "kind"} <= source.keys():
            raise ValueError("ข้อมูลแหล่งอ้างอิงไม่ครบ")
        parsed = urlparse(source["url"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("URL ของแหล่งข้อมูลต้องเป็น HTTP(S)")
        if source["id"] in by_id:
            raise ValueError("รหัสแหล่งอ้างอิงซ้ำกัน")
        by_id[source["id"]] = source
    claims = data.get("claims", [])
    if not claims:
        raise ValueError("ต้องมีข้อกล่าวอ้าง")
    for claim in claims:
        if not claim.get("text") or claim.get("status") not in {"supported", "uncertain", "conflict"}:
            raise ValueError("รูปแบบข้อกล่าวอ้างไม่ถูกต้อง")
        evidence = claim.get("evidence", [])
        if claim["status"] == "supported" and not evidence:
            raise ValueError("ข้อกล่าวอ้าง supported ต้องมีหลักฐาน")
        for item in evidence:
            if item.get("source") not in by_id or not item.get("quote"):
                raise ValueError("หลักฐานต้องอ้างแหล่งที่มีอยู่และมีข้อความอ้างอิง")
    return by_id


def render(data):
    sources = validate(data)
    lines = ["# " + data["question"], "", "## ข้อสรุปและหลักฐาน", ""]
    for claim in data["claims"]:
        lines.extend([f"### {claim['text']}", "", "สถานะ: " + claim["status"], ""])
        for evidence in claim.get("evidence", []):
            source = sources[evidence["source"]]
            lines.extend([f"> {evidence['quote']}", "", f"แหล่งข้อมูล: [{source['title']}]({source['url']})", ""])
    lines.extend(["## รายการแหล่งข้อมูล", ""])
    for source in sources.values():
        lines.append(f"- {source['id']}: [{source['title']}]({source['url']}); {source['kind']}; วันที่เข้าถึง {source['accessed']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = render(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(args.output)
