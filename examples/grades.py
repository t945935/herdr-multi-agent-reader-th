"""สัญญาระบบคะแนน: จัดอันดับจากผลรวมที่ยังไม่ปัดเศษ"""

from collections.abc import Mapping
from math import isfinite

SUBJECTS = frozenset({"ภาษาไทย", "ภาษาอังกฤษ", "คณิตศาสตร์"})


def validate_scores(scores):
    if not isinstance(scores, Mapping) or set(scores) != SUBJECTS:
        raise ValueError("scores ต้องมีภาษาไทย ภาษาอังกฤษ และคณิตศาสตร์ครบสามวิชา")
    for value in scores.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("คะแนนต้องเป็นตัวเลขและห้ามเป็น bool")
        if not isfinite(value) or not 0 <= value <= 100:
            raise ValueError("คะแนนต้องเป็นค่าจำกัดระหว่าง 0 ถึง 100")
    return scores


def calculate_total(scores):
    return sum(validate_scores(scores).values())


def calculate_average(scores):
    return calculate_total(scores) / 3


def get_grade(average):
    if isinstance(average, bool) or not isinstance(average, (int, float)):
        raise ValueError("ค่าเฉลี่ยต้องเป็นตัวเลขที่ไม่ใช่ bool")
    if not isfinite(average) or not 0 <= average <= 100:
        raise ValueError("ค่าเฉลี่ยต้องเป็นค่าจำกัดระหว่าง 0 ถึง 100")
    return "ผ่าน" if average >= 60 else "ไม่ผ่าน"


def rank_students(students):
    if not isinstance(students, list):
        raise ValueError("students ต้องเป็นลิสต์")
    rows = []
    for student in students:
        if not isinstance(student, Mapping):
            raise ValueError("ข้อมูลนักเรียนแต่ละรายการต้องเป็นออบเจ็กต์")
        name = student.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("ต้องระบุชื่อนักเรียน")
        total = calculate_total(student.get("scores"))
        average = total / 3
        rows.append({"name": name.strip(), "scores": dict(student["scores"]),
                     "total": total, "average": average, "grade": get_grade(average)})
    rows.sort(key=lambda row: row["total"], reverse=True)
    previous = None
    rank = 0
    for index, row in enumerate(rows, 1):
        if previous is None or row["total"] != previous:
            rank = index
        previous = row["total"]
        row["rank"] = rank
    return rows
