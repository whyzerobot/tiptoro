"""
backend/conftest.py  (also serves as PYTHONPATH helper)

当从项目根目录运行测试或脚本时，此文件确保 backend/ 目录自动加入 sys.path。
pytest 会自动加载此文件。
"""
import sys
from pathlib import Path

# 允许 `python3 -m pytest` 从项目根运行时正确找到所有后端模块
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
