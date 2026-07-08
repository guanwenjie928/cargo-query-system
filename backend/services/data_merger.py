"""
货盘查询系统 - 数据合并器
将库存表和报价表的数据按 SKU 合并，写入数据库
"""
import os
import shutil
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from backend.models import Product, WarehouseStock, OrderFee, ImportLog
from backend.config import UPLOAD_DIR, ARCHIVE_DIR
from backend.utils import (
    calc_stock_status,
    calc_price_range,
    generate_batch_no,
    extract_file_date,
    is_newer_date,
)
from backend.services.image_extractor import save_image


def import_stock_data(
    db: Session,
    parsed_data: Dict,
    file_path: str,
    file_name: str,
) -> ImportLog:
    """
    将库存表解析数据导入数据库

    流程：
    1. 解析 stock Sheet → 商品主表 + 仓库明细表
    2. 解析 Sheet2 → 更新图片
    3. 同 SKU 覆盖更新
    """
    batch_no = generate_batch_no()
    file_date = extract_file_date(file_name)

    # 归档原始文件（仅记录路径，不复制大文件以节省磁盘空间）
    archive_path = file_path  # 直接记录原始路径

    log = ImportLog(
        batch_no=batch_no,
        file_name=file_name,
        file_type="stock",
        file_path=str(archive_path),
        file_date=file_date,
        status="processing",
    )
    db.add(log)
    db.flush()

    stock_products = parsed_data.get("stock_products", [])
    sheet2_products = parsed_data.get("sheet2_products", [])
    images = parsed_data.get("images", {})

    # Sheet2 数据按 SKU 索引（用于图片和补充信息）
    sheet2_map = {p["sku"]: p for p in sheet2_products}

    total = len(stock_products)
    success = 0
    merged = 0
    fail_details = []

    for item in stock_products:
        try:
            sku = item["sku"]
            existing = db.query(Product).filter(Product.sku == sku).first()

            # Sheet2 补充数据
            s2 = sheet2_map.get(sku, {})

            if existing:
                # 覆盖更新
                merged += 1
                if item.get("product_name"):
                    existing.product_name = item["product_name"]
                existing.stock_total = item.get("stock_total", 0)
                existing.in_transit = item.get("in_transit", 0)
                existing.stock_status = calc_stock_status(existing.stock_total)
                existing.import_batch = batch_no
                existing.updated_at = datetime.now()

                # 图片处理：如果新文件日期更新，则覆盖图片
                if sku in images:
                    if not existing.image_date or is_newer_date(file_date, existing.image_date):
                        img_filename = save_image(images[sku], sku, batch_no, UPLOAD_DIR)
                        existing.image_path = img_filename
                        existing.image_source = "stock"
                        existing.image_date = file_date

                product = existing
            else:
                # 新建商品
                stock = item.get("stock_total", 0)
                product = Product(
                    sku=sku,
                    product_name=item.get("product_name"),
                    stock_total=stock,
                    in_transit=item.get("in_transit", 0),
                    stock_status=calc_stock_status(stock),
                    product_status="在售",
                    import_batch=batch_no,
                )
                db.add(product)
                db.flush()

                # 图片
                if sku in images:
                    img_filename = save_image(images[sku], sku, batch_no, UPLOAD_DIR)
                    product.image_path = img_filename
                    product.image_source = "stock"
                    product.image_date = file_date

            # 写入仓库明细
            # 先删除旧的仓库记录
            db.query(WarehouseStock).filter(WarehouseStock.sku == sku).delete()
            for wh in item.get("warehouses", []):
                ws_record = WarehouseStock(
                    product_id=product.id,
                    sku=sku,
                    warehouse=wh["warehouse"],
                    stock=wh["stock"],
                    in_transit=wh["in_transit"],
                )
                db.add(ws_record)

            # Sheet2 补充的图片（如果 stock Sheet 没有图片）
            if not product.image_path and sku in images:
                img_filename = save_image(images[sku], sku, batch_no, UPLOAD_DIR)
                product.image_path = img_filename
                product.image_source = "stock"
                product.image_date = file_date

            success += 1
        except Exception as e:
            fail_details.append({"sku": item.get("sku"), "error": str(e)})

    log.total_rows = total
    log.success_rows = success
    log.fail_rows = total - success
    log.merged_rows = merged
    log.fail_details = str(fail_details) if fail_details else None
    log.status = "completed"

    db.commit()
    return log


def import_quotation_data(
    db: Session,
    parsed_data: Dict,
    file_path: str,
    file_name: str,
) -> ImportLog:
    """
    将报价表解析数据导入数据库

    流程：
    1. 品类产品 → 商品主表（合并字段）
    2. 美东/美西处理费 → 订单处理费表
    3. 图片提取保存
    4. 同 SKU 覆盖更新
    """
    batch_no = generate_batch_no()
    file_date = extract_file_date(file_name)

    # 归档
    archive_path = ARCHIVE_DIR / f"{batch_no}_{file_name}"
    shutil.copy2(file_path, archive_path)

    log = ImportLog(
        batch_no=batch_no,
        file_name=file_name,
        file_type="quotation",
        file_path=str(archive_path),
        file_date=file_date,
        status="processing",
    )
    db.add(log)
    db.flush()

    products = parsed_data.get("products", [])
    images = parsed_data.get("images", {})
    fees_east = parsed_data.get("fees_east", [])
    fees_west = parsed_data.get("fees_west", [])

    total = len(products)
    success = 0
    merged = 0
    fail_details = []

    for item in products:
        try:
            sku = item["sku"]
            if not sku:
                continue

            # 清理 SKU 前后空格
            sku = sku.strip()
            existing = db.query(Product).filter(Product.sku == sku).first()

            # 获取该 SKU 的图片（以 Model 行号为 key）
            img_data = images.get(sku) or _find_image_by_sku(images, sku, item)

            if existing:
                # 覆盖更新报价信息
                merged += 1
                existing.product_name = item.get("product_name") or existing.product_name
                existing.product_name_en = item.get("product_name_en")
                existing.category = item.get("category")
                existing.weight = item.get("weight")
                existing.material = item.get("material")
                existing.hs_code = item.get("hs_code")
                existing.limit_price = item.get("limit_price")
                existing.packaging = item.get("packaging")
                existing.feature_code = item.get("feature_code")
                existing.product_status = item.get("product_status") or "在售"
                existing.shipping_mark = item.get("shipping_mark")

                if item.get("price_usd") is not None:
                    existing.price_usd = item["price_usd"]
                    existing.price_range = calc_price_range(item["price_usd"])
                if item.get("price_rmb") is not None:
                    existing.price_rmb = item["price_rmb"]
                if item.get("first_leg_fee") is not None:
                    existing.first_leg_fee = item["first_leg_fee"]

                existing.import_batch = batch_no
                existing.updated_at = datetime.now()

                # 图片：如果新文件日期更新则覆盖
                if img_data:
                    if not existing.image_date or is_newer_date(file_date, existing.image_date):
                        img_filename = save_image(img_data, sku, batch_no, UPLOAD_DIR)
                        existing.image_path = img_filename
                        existing.image_source = "quotation"
                        existing.image_date = file_date

                product = existing
            else:
                # 新建商品
                price_usd = item.get("price_usd")
                stock = 0  # 报价表无库存信息
                product = Product(
                    sku=sku,
                    product_name=item.get("product_name"),
                    product_name_en=item.get("product_name_en"),
                    category=item.get("category"),
                    stock_total=stock,
                    stock_status=calc_stock_status(stock),
                    price_usd=price_usd,
                    price_rmb=item.get("price_rmb"),
                    price_range=calc_price_range(price_usd),
                    weight=item.get("weight"),
                    material=item.get("material"),
                    hs_code=item.get("hs_code"),
                    limit_price=item.get("limit_price"),
                    packaging=item.get("packaging"),
                    feature_code=item.get("feature_code"),
                    first_leg_fee=item.get("first_leg_fee"),
                    product_status=item.get("product_status") or "在售",
                    shipping_mark=item.get("shipping_mark"),
                    import_batch=batch_no,
                )
                db.add(product)
                db.flush()

                if img_data:
                    img_filename = save_image(img_data, sku, batch_no, UPLOAD_DIR)
                    product.image_path = img_filename
                    product.image_source = "quotation"
                    product.image_date = file_date

            success += 1
        except Exception as e:
            fail_details.append({"sku": item.get("sku"), "error": str(e)})

    # 导入订单处理费
    for fee in fees_east:
        db.query(OrderFee).filter(
            OrderFee.sku == fee["sku"],
            OrderFee.region == "east",
        ).delete()
        db.add(OrderFee(**fee))

    for fee in fees_west:
        db.query(OrderFee).filter(
            OrderFee.sku == fee["sku"],
            OrderFee.region == "west",
        ).delete()
        db.add(OrderFee(**fee))

    log.total_rows = total
    log.success_rows = success
    log.fail_rows = total - success
    log.merged_rows = merged
    log.fail_details = str(fail_details) if fail_details else None
    log.status = "completed"

    db.commit()
    return log


def _find_image_by_sku(images: Dict, sku: str, item: Dict) -> bytes:
    """尝试多种方式从 images 字典中找到对应 SKU 的图片"""
    # 直接匹配
    if sku in images:
        return images[sku]
    # 尝试去空格
    sku_stripped = sku.strip()
    if sku_stripped in images:
        return images[sku_stripped]
    return None
