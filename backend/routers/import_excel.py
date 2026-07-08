"""
货盘查询系统 - Excel 导入路由
"""
import os
import shutil
import tempfile
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.config import MAX_FILE_SIZE
from backend.models import ImportLog
from backend.services.stock_parser import parse_stock_excel
from backend.services.quotation_parser import parse_quotation_excel
from backend.services.data_merger import import_stock_data, import_quotation_data
from backend.utils import extract_file_date

import re

router = APIRouter(prefix="/api/import", tags=["Excel导入"])


def detect_file_type(filename: str) -> str:
    """根据文件名自动判断文件类型"""
    name = filename.lower()
    if "库存" in filename or "stock" in name:
        return "stock"
    if "报价" in filename or "quotation" in name or "定价" in filename:
        return "quotation"
    return "unknown"


@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传 Excel 文件并自动解析导入"""
    # 校验文件格式
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 格式文件")

    # 读取文件内容
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过500MB限制")

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 自动检测文件类型
        file_type = detect_file_type(file.filename)

        if file_type == "stock":
            # 解析库存表
            parsed = parse_stock_excel(tmp_path)
            log = import_stock_data(db, parsed, tmp_path, file.filename)
        elif file_type == "quotation":
            # 解析报价表
            parsed = parse_quotation_excel(tmp_path)
            log = import_quotation_data(db, parsed, tmp_path, file.filename)
        else:
            # 尝试自动判断
            try:
                parsed = parse_stock_excel(tmp_path)
                if parsed["summary"]["stock_sheet_count"] > 0:
                    log = import_stock_data(db, parsed, tmp_path, file.filename)
                else:
                    raise ValueError("无法识别文件类型")
            except Exception:
                try:
                    parsed = parse_quotation_excel(tmp_path)
                    if parsed["summary"]["product_count"] > 0:
                        log = import_quotation_data(db, parsed, tmp_path, file.filename)
                    else:
                        raise ValueError("无法识别文件类型")
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"无法识别文件类型: {str(e)}")

        return {
            "code": 0,
            "message": "导入完成",
            "data": log.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        os.unlink(tmp_path)


@router.post("/parse")
async def parse_excel_preview(
    file: UploadFile = File(...),
):
    """解析 Excel 预览（不写入数据库）"""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 格式文件")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过500MB限制")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        file_type = detect_file_type(file.filename)
        file_date = extract_file_date(file.filename)

        # 当文件名无法识别类型时，尝试自动探测
        if file_type == "unknown":
            try:
                parsed = parse_stock_excel(tmp_path)
                if parsed["summary"]["stock_sheet_count"] > 0:
                    file_type = "stock"
                else:
                    raise ValueError("not stock")
            except Exception:
                try:
                    parsed = parse_quotation_excel(tmp_path)
                    if parsed["summary"]["product_count"] > 0:
                        file_type = "quotation"
                    else:
                        raise ValueError("无法识别文件类型")
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"无法识别文件类型，请确认文件名包含'库存'或'报价': {str(e)}"
                    )

        if file_type == "stock":
            parsed = parse_stock_excel(tmp_path)
            return {
                "code": 0,
                "data": {
                    "file_type": "stock",
                    "file_date": file_date,
                    "summary": parsed["summary"],
                    "preview": [
                        {
                            "sku": p["sku"],
                            "product_name": p.get("product_name"),
                            "stock_total": p.get("stock_total"),
                            "warehouses": len(p.get("warehouses", [])),
                        }
                        for p in parsed["stock_products"][:10]
                    ],
                },
            }
        elif file_type == "quotation":
            parsed = parse_quotation_excel(tmp_path)
            return {
                "code": 0,
                "data": {
                    "file_type": "quotation",
                    "file_date": file_date,
                    "summary": parsed["summary"],
                    "preview": [
                        {
                            "sku": p["sku"],
                            "product_name": p.get("product_name"),
                            "category": p.get("category"),
                            "price_usd": p.get("price_usd"),
                            "product_status": p.get("product_status") or "在售",
                        }
                        for p in parsed["products"][:10]
                    ],
                },
            }
    finally:
        os.unlink(tmp_path)


@router.get("/logs")
def get_import_logs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """导入历史记录"""
    query = db.query(ImportLog).order_by(ImportLog.imported_at.desc())
    total = query.count()
    logs = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "code": 0,
        "data": {
            "list": [log.to_dict() for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/rollback/{batch_no}")
def rollback_import(batch_no: str, db: Session = Depends(get_db)):
    """回滚指定批次的导入"""
    from backend.models import Product, WarehouseStock, OrderFee
    from sqlalchemy import or_

    log = db.query(ImportLog).filter(ImportLog.batch_no == batch_no).first()
    if not log:
        raise HTTPException(status_code=404, detail="批次不存在")

    if log.status == "rolled_back":
        raise HTTPException(status_code=400, detail="该批次已回滚")

    deleted_products = 0
    deleted_fees = 0

    if log.file_type == "stock":
        # 删除该批次导入的仓库明细
        skus = db.query(Product.sku).filter(Product.import_batch == batch_no).all()
        sku_list = [s[0] for s in skus]
        if sku_list:
            db.query(WarehouseStock).filter(
                WarehouseStock.sku.in_(sku_list)
            ).delete(synchronize_session=False)
    elif log.file_type == "quotation":
        # 删除该批次导入的处理费
        deleted_fees = db.query(OrderFee).filter(
            OrderFee.sku.in_(
                db.query(Product.sku).filter(Product.import_batch == batch_no)
            )
        ).delete(synchronize_session=False)

    # 删除该批次导入的商品（仅删除最后导入的批次）
    deleted_products = db.query(Product).filter(
        Product.import_batch == batch_no
    ).delete(synchronize_session=False)

    log.status = "rolled_back"
    db.commit()

    return {
        "code": 0,
        "message": f"已回滚批次 {batch_no}，删除 {deleted_products} 个商品",
        "data": {"deleted_products": deleted_products, "deleted_fees": deleted_fees},
    }
