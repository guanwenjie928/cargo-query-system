"""
货盘查询系统 - 矩阵聚合路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services.matrix_aggregator import get_matrix_data, get_stats

router = APIRouter(prefix="/api", tags=["矩阵看板"])


@router.get("/matrix")
def matrix(
    x_axis: str = Query("category", description="横轴维度"),
    y_axis: str = Query("price_range", description="纵轴维度"),
    db: Session = Depends(get_db),
):
    """矩阵聚合数据"""
    # 验证维度字段
    valid_axes = ["category", "price_range", "stock_status", "product_status"]
    if x_axis not in valid_axes:
        x_axis = "category"
    if y_axis not in valid_axes:
        y_axis = "price_range"

    data = get_matrix_data(db, x_axis, y_axis)
    return {"code": 0, "data": data}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """看板统计卡片数据"""
    data = get_stats(db)
    return {"code": 0, "data": data}
