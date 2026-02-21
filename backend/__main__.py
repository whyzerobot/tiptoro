"""
backend/__main__.py

TipToro 后端启动入口。
确保在 backend/ 目录下运行，或以模块方式运行：

    # 方式一：从项目根目录（推荐）
    cd /path/to/tiptoro
    python3 -m backend          # 开发模式（使用 uvicorn）

    # 方式二：直接运行
    cd /path/to/tiptoro/backend
    python3 -m uvicorn api.main:app --reload
"""
import sys
import os

# 确保 backend/ 目录在 Python 路径中（以便与 cd tiptoro 方式运行）
sys.path.insert(0, os.path.dirname(__file__))

# 延迟导入以避免循环依赖，同时允许单独导入子模块
try:
    import uvicorn
    from api.main import app  # noqa: F401 - import for side effects
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
except ImportError:
    print("❌ uvicorn 或 api.main 未找到，请先安装依赖：")
    print("   pip install -r backend/requirements.txt")
    sys.exit(1)
