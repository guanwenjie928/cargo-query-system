"""
货盘查询系统 - 配置管理
"""
import os
from pathlib import Path

# 项目根目录（backend 的上级目录）
BASE_DIR = Path(__file__).resolve().parent.parent

# 后端目录
BACKEND_DIR = BASE_DIR / "backend"

# 数据目录
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads" / "images"
ARCHIVE_DIR = BASE_DIR / "archives"

# 前端构建产物目录
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# 数据库
DATABASE_PATH = DATA_DIR / "cargo.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# 服务端口（启动脚本会通过环境变量传入）
PORT = int(os.environ.get("CARGO_PORT", 8000))

# 库存状态阈值
STOCK_SUFFICIENT_THRESHOLD = 50  # > 50 为充足
STOCK_TENSE_THRESHOLD = 1        # 1-50 为紧张，0 为缺货

# USD 价格区间（元）
PRICE_RANGES = [
    (0, 50, "$0-50"),
    (50, 100, "$50-100"),
    (100, 200, "$100-200"),
    (200, 500, "$200-500"),
    (500, float("inf"), "$500+"),
]

# 报价表中的品类 Sheet 名
CATEGORY_SHEETS = ["软胶", "功能软胶产品", "飞机杯", "阳具与水晶套"]

# 文件大小限制（500MB，Excel 内嵌图片可能很大）
MAX_FILE_SIZE = 500 * 1024 * 1024
