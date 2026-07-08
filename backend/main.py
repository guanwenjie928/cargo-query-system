"""
货盘查询系统 - FastAPI 主入口
"""
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from backend.config import PORT, FRONTEND_DIST
from backend.database import init_db
from backend.routers import products, matrix, import_excel, images

app = FastAPI(
    title="货盘查询系统",
    description="多维度货盘查询与管理系统",
    version="1.0.0",
)

# CORS（开发模式需要，生产模式前端由后端托管）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(products.router)
app.include_router(matrix.router)
app.include_router(import_excel.router)
app.include_router(images.router)


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "port": PORT}


@app.on_event("startup")
async def startup_event():
    """启动时初始化数据库"""
    init_db()


# 前端静态文件托管（如果已构建）
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {
            "message": "货盘查询系统 API",
            "docs": "/docs",
            "note": "前端尚未构建，请先构建前端：cd frontend && npm run build",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
    )
