"""
货盘查询系统 - 矩阵数据聚合器
按维度交叉统计商品数量
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from backend.models import Product
from backend.config import PRICE_RANGES


def get_matrix_data(
    db: Session,
    x_axis: str = "category",
    y_axis: str = "price_range",
) -> dict:
    """
    获取矩阵聚合数据

    支持的维度：
    - category: 品类
    - price_range: 价格区间
    - stock_status: 库存状态
    - product_status: 产品状态
    """
    # 构建查询
    query = db.query(
        getattr(Product, x_axis).label("x_val"),
        getattr(Product, y_axis).label("y_val"),
        func.count(Product.id).label("count"),
    ).filter(
        getattr(Product, x_axis).isnot(None),
        getattr(Product, y_axis).isnot(None),
    ).group_by(
        getattr(Product, x_axis),
        getattr(Product, y_axis),
    )

    results = query.all()

    # 收集所有 X 和 Y 的标签
    x_labels_set = set()
    y_labels_set = set()
    matrix_map = {}

    for row in results:
        x_val = row.x_val
        y_val = row.y_val
        count = row.count

        x_labels_set.add(x_val)
        y_labels_set.add(y_val)
        matrix_map[(x_val, y_val)] = count

    # 排序标签
    if x_axis == "price_range":
        x_labels = [r[2] for r in PRICE_RANGES if r[2] in x_labels_set]
    elif x_axis == "stock_status":
        order_map = {"充足": 0, "紧张": 1, "缺货": 2}
        x_labels = sorted(x_labels_set, key=lambda x: order_map.get(x, 99))
    else:
        x_labels = sorted(x_labels_set)

    if y_axis == "price_range":
        y_labels = [r[2] for r in PRICE_RANGES if r[2] in y_labels_set]
    elif y_axis == "stock_status":
        order_map = {"充足": 0, "紧张": 1, "缺货": 2}
        y_labels = sorted(y_labels_set, key=lambda y: order_map.get(y, 99))
    else:
        y_labels = sorted(y_labels_set)

    # 构建矩阵
    matrix = []
    for y_label in y_labels:
        row_data = []
        for x_label in x_labels:
            row_data.append(matrix_map.get((x_label, y_label), 0))
        matrix.append(row_data)

    # 获取预览图片（每个单元格前5张）
    preview_images = {}
    for x_label in x_labels:
        for y_label in y_labels:
            products = db.query(Product).filter(
                getattr(Product, x_axis) == x_label,
                getattr(Product, y_axis) == y_label,
                Product.image_path.isnot(None),
            ).limit(5).all()

            if products:
                key = f"{x_labels.index(x_label)}_{y_labels.index(y_label)}"
                preview_images[key] = [
                    f"/api/images/{p.image_path}" for p in products if p.image_path
                ]

    return {
        "x_labels": x_labels,
        "y_labels": y_labels,
        "matrix": matrix,
        "preview_images": preview_images,
    }


def get_stats(db: Session) -> dict:
    """获取看板顶部统计卡片数据"""
    total_skus = db.query(func.count(Product.id)).scalar() or 0

    total_stock = db.query(func.sum(Product.stock_total)).scalar() or 0

    out_of_stock = db.query(func.count(Product.id)).filter(
        Product.stock_status == "缺货"
    ).scalar() or 0

    discontinued = db.query(func.count(Product.id)).filter(
        Product.product_status.like("%下架%")
    ).scalar() or 0

    # 品类分布
    category_dist = {}
    cat_results = db.query(
        Product.category,
        func.count(Product.id),
    ).filter(
        Product.category.isnot(None),
    ).group_by(Product.category).all()

    for cat, count in cat_results:
        category_dist[cat] = count

    return {
        "total_skus": total_skus,
        "total_stock": total_stock,
        "out_of_stock_count": out_of_stock,
        "discontinued_count": discontinued,
        "category_distribution": category_dist,
    }
