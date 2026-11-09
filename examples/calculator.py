"""บทเครื่องคิดเลข: สัญญาขนาดเล็กสำหรับฝึกพัฒนาและตรวจทานโค้ด"""

from math import isfinite


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("โปรดระบุตัวเลขที่ไม่ใช่ bool")
    if not isfinite(value):
        raise ValueError("โปรดระบุตัวเลขที่มีค่าจำกัด")
    return value


def add(a, b):
    return _number(a) + _number(b)


def subtract(a, b):
    return _number(a) - _number(b)


def multiply(a, b):
    return _number(a) * _number(b)


def divide(a, b):
    a, b = _number(a), _number(b)
    if b == 0:
        raise ZeroDivisionError("ไม่สามารถหารด้วยศูนย์ได้")
    return a / b
