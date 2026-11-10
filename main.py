"""
Học Vẹt - Điểm khởi chạy chính của ứng dụng
"""
import sys

if __name__ == "__main__":
    from single_instance import SingleInstance
    instance = SingleInstance()
    if not instance.primary:
        instance.close()
        sys.exit(0)
    try:
        from ui import _run_primary_app
        _run_primary_app(instance)
    finally:
        instance.close()
