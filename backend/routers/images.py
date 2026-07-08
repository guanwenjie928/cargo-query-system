"""
货盘查询系统 - 图片服务路由
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.config import UPLOAD_DIR

router = APIRouter(prefix="/api/images", tags=["图片服务"])


@router.get("/{filename}")
async def get_image(filename: str):
    """获取图片"""
    # 防止路径遍历攻击
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    # 根据后缀判断媒体类型
    if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        media_type = "image/jpeg"
    else:
        media_type = "image/png"

    return FileResponse(filepath, media_type=media_type)
