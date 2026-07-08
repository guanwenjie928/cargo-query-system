"""
货盘查询系统 - 商品查询路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from backend.database import get_db
from backend.models import Product, WarehouseStock, OrderFee

router = APIRouter(prefix="/api/products", tags=["商品查询"])


@router.get("")
def get_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: Optional[str] = Query(None, description="SKU或产品名称关键词"),
    category: Optional[str] = Query(None, description="品类筛选"),
    min_price: Optional[float] = Query(None, description="最低USD价格"),
    max_price: Optional[float] = Query(None, description="最高USD价格"),
    stock_status: Optional[str] = Query(None, description="库存状态"),
    product_status: Optional[str] = Query(None, description="产品状态"),
    sort: str = Query("updated_at", description="排序字段"),
    order: str = Query("desc", description="asc/desc"),
    db: Session = Depends(get_db),
):
    """商品列表（分页 + 筛选 + 排序）"""
    query = db.query(Product)

    # 关键词搜索
    if keyword:
        kw = f"%{keyword}%"
        query = query.filter(
            or_(
                Product.sku.ilike(kw),
                Product.product_name.ilike(kw),
            )
        )

    # 品类筛选
    if category:
        cats = [c.strip() for c in category.split(",") if c.strip()]
        if cats:
            query = query.filter(Product.category.in_(cats))

    # 价格区间
    if min_price is not None:
        query = query.filter(Product.price_usd >= min_price)
    if max_price is not None:
        query = query.filter(Product.price_usd <= max_price)

    # 库存状态
    if stock_status:
        statuses = [s.strip() for s in stock_status.split(",") if s.strip()]
        if statuses:
            query = query.filter(Product.stock_status.in_(statuses))

    # 产品状态
    if product_status:
        statuses = [s.strip() for s in product_status.split(",") if s.strip()]
        if statuses:
            conditions = []
            for s in statuses:
                if s == "在售":
                    conditions.append(
                        or_(
                            Product.product_status.is_(None),
                            Product.product_status == "在售",
                        )
                    )
                else:
                    conditions.append(Product.product_status.like(f"%{s}%"))
            query = query.filter(or_(*conditions))

    # 排序
    sort_column = getattr(Product, sort, Product.updated_at)
    if order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # 分页
    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "code": 0,
        "data": {
            "list": [p.to_dict() for p in products],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取品类列表"""
    from sqlalchemy import func
    results = db.query(
        Product.category,
        func.count(Product.id),
    ).filter(
        Product.category.isnot(None),
    ).group_by(Product.category).all()

    return {
        "code": 0,
        "data": [
            {"name": cat, "count": count}
            for cat, count in results
        ],
    }


@router.get("/{product_id}")
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    """商品详情（含仓库明细 + 订单处理费）"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 基础信息
    data = product.to_dict(include_detail=True)

    # 仓库明细
    warehouses = db.query(WarehouseStock).filter(
        WarehouseStock.sku == product.sku
    ).all()
    data["warehouses"] = [w.to_dict() for w in warehouses if w.warehouse != "Multiple"]

    # 订单处理费
    fees = db.query(OrderFee).filter(OrderFee.sku == product.sku).all()
    fee_info = {"east": None, "west": None}
    for fee in fees:
        if fee.region == "east":
            fee_info["east"] = fee.to_dict()
        elif fee.region == "west":
            fee_info["west"] = fee.to_dict()
    data["order_fees"] = fee_info

    # 费用说明
    data["fee_explanations"] = {
        "east": "美东仓库发货时，每笔订单的仓储操作处理费用（$），按SKU核重计算",
        "west": "美西仓库（HYC-Chino仓）发货时，每笔订单的仓储操作处理费用（$），按SKU核重和尺寸计算",
        "first_leg_fee": "国内发往海外仓的头程运输费用（¥/件），已含在成本中",
    }

    return {"code": 0, "data": data}
