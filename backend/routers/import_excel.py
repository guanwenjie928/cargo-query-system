"""
货盘查询系统 - Excel 导入路由
"""
import os
import shutil
import tempfile
import gc
import time
import uuid
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.config import MAX_FILE_SIZE, DATA_DIR
from backend.models import ImportLog, Product
from backend.services.stock_parser import parse_stock_excel
from backend.services.quotation_parser import parse_quotation_excel
from backend.services.data_merger import import_stock_data, import_quotation_data, apply_selected_data
from backend.utils import extract_file_date

import re

router = APIRouter(prefix="/api/import", tags=["Excel导入"])

# 临时导入目录（compare → apply 流程的文件缓存）
TEMP_IMPORT_DIR = DATA_DIR / "temp_imports"
TEMP_IMPORT_DIR.mkdir(parents=True, exist_ok=True)

# 比对字段定义
STOCK_COMPARE_FIELDS = ["product_name", "stock_total", "in_transit"]
QUOTATION_COMPARE_FIELDS = [
    "product_name", "product_name_en", "category", "price_usd", "price_rmb",
    "weight", "material", "hs_code", "limit_price", "packaging",
    "feature_code", "first_leg_fee", "product_status", "shipping_mark",
]

# 字段中文标签（前端展示用）
FIELD_LABELS = {
    "product_name": "产品名称",
    "product_name_en": "英文品类",
    "category": "品类",
    "price_usd": "美元价格",
    "price_rmb": "人民币价格",
    "weight": "重量",
    "material": "材质",
    "hs_code": "海关编码",
    "limit_price": "限价",
    "packaging": "包装方式",
    "feature_code": "特征码",
    "first_leg_fee": "头程费",
    "product_status": "产品状态",
    "shipping_mark": "唛头",
    "stock_total": "总库存",
    "in_transit": "在途数量",
}


def detect_file_type(filename: str) -> str:
    """根据文件名自动判断文件类型"""
    name = filename.lower()
    if "库存" in filename or "stock" in name:
        return "stock"
    if "报价" in filename or "quotation" in name or "定价" in filename:
        return "quotation"
    return "unknown"


def _normalize_val(val):
    """标准化值用于比较（None/空字符串视为等价，数字转 float）"""
    if val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return None
        try:
            return float(val)
        except ValueError:
            return val.lower()
    if isinstance(val, (int, float)):
        return float(val)
    return val


def _compare_fields(item: dict, existing: Product, fields: list) -> dict:
    """
    比较解析数据与 DB 记录的差异

    返回：{field_name: {"old": old_val, "new": new_val, "label": "中文标签"}} 或空 dict
    """
    changes = {}
    for field in fields:
        new_val = item.get(field)
        old_val = getattr(existing, field, None)

        if _normalize_val(new_val) != _normalize_val(old_val):
            changes[field] = {
                "old": _serialize_val(old_val),
                "new": _serialize_val(new_val),
                "label": FIELD_LABELS.get(field, field),
            }
    return changes


def _serialize_val(val):
    """序列化值为 JSON 可用的类型"""
    if val is None:
        return None
    if isinstance(val, (int, float, str, bool)):
        return val
    return str(val)


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
        for _ in range(3):
            gc.collect()
            try:
                os.unlink(tmp_path)
                break
            except PermissionError:
                time.sleep(0.5)


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
        for _ in range(3):
            gc.collect()
            try:
                os.unlink(tmp_path)
                break
            except PermissionError:
                time.sleep(0.5)


# ============================================================
# 比对 → 手动选择 → 应用 流程
# ============================================================

@router.post("/compare")
async def compare_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    上传 Excel 并与数据库现有数据比对

    返回三类结果：
    - new_items：DB 中不存在的新 SKU
    - changed_items：字段有变化的 SKU（含字段级 old→new diff）
    - unchanged_count：无变化的 SKU 数量
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 格式文件")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过500MB限制")

    # 保存到临时目录（供后续 /apply 使用）
    session_id = str(uuid.uuid4())
    temp_path = TEMP_IMPORT_DIR / f"{session_id}.xlsx"
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        file_type = detect_file_type(file.filename)
        file_date = extract_file_date(file.filename)

        # 文件名无法识别时自动探测
        if file_type == "unknown":
            try:
                parsed = parse_stock_excel(str(temp_path))
                if parsed["summary"]["stock_sheet_count"] > 0:
                    file_type = "stock"
                else:
                    raise ValueError("not stock")
            except Exception:
                try:
                    parsed = parse_quotation_excel(str(temp_path))
                    if parsed["summary"]["product_count"] > 0:
                        file_type = "quotation"
                    else:
                        raise ValueError("无法识别")
                except Exception as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"无法识别文件类型，请确认文件名包含'库存'或'报价': {str(e)}",
                    )

        # 解析
        if file_type == "stock":
            parsed = parse_stock_excel(str(temp_path))
            items = parsed.get("stock_products", [])
        else:
            parsed = parse_quotation_excel(str(temp_path))
            items = parsed.get("products", [])

        # 与 DB 比对
        new_items = []
        changed_items = []
        unchanged_count = 0

        compare_fields = STOCK_COMPARE_FIELDS if file_type == "stock" else QUOTATION_COMPARE_FIELDS

        for item in items:
            sku = (item.get("sku") or "").strip()
            if not sku:
                continue

            existing = db.query(Product).filter(Product.sku == sku).first()

            if not existing:
                new_items.append({
                    "sku": sku,
                    "product_name": item.get("product_name"),
                    "category": item.get("category"),
                    "price_usd": item.get("price_usd"),
                    "stock_total": item.get("stock_total"),
                    "product_status": item.get("product_status") or "在售",
                })
            else:
                changes = _compare_fields(item, existing, compare_fields)
                if changes:
                    changed_items.append({
                        "sku": sku,
                        "product_name": existing.product_name or item.get("product_name"),
                        "changes": changes,
                    })
                else:
                    unchanged_count += 1

        # 保存元数据（供 /apply 使用）
        metadata_path = TEMP_IMPORT_DIR / f"{session_id}.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(
                {"file_name": file.filename, "file_type": file_type, "file_date": file_date},
                f,
                ensure_ascii=False,
            )

        return {
            "code": 0,
            "data": {
                "session_id": session_id,
                "file_type": file_type,
                "file_date": file_date,
                "file_name": file.filename,
                "summary": {
                    "total": len(items),
                    "new_count": len(new_items),
                    "changed_count": len(changed_items),
                    "unchanged_count": unchanged_count,
                },
                "new_items": new_items,
                "changed_items": changed_items,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        # 出错时清理临时文件
        _cleanup_temp(session_id)
        raise HTTPException(status_code=500, detail=f"比对失败: {str(e)}")


@router.post("/apply")
async def apply_import(
    session_id: str = Form(...),
    selected_skus: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    应用选中的 SKU 到数据库

    接收：
    - session_id：比对时返回的会话 ID
    - selected_skus：JSON 格式的 SKU 列表字符串

    逻辑：
    1. 根据 session_id 找到临时文件
    2. 重新解析 Excel
    3. 仅处理选中的 SKU：对已有商品保存快照后更新，对新商品直接创建
    """
    temp_path = TEMP_IMPORT_DIR / f"{session_id}.xlsx"
    metadata_path = TEMP_IMPORT_DIR / f"{session_id}.json"

    if not temp_path.exists():
        raise HTTPException(status_code=404, detail="会话已过期，请重新上传文件")

    try:
        skus = json.loads(selected_skus)
        if not skus:
            raise HTTPException(status_code=400, detail="未选择任何 SKU")

        # 读取元数据
        file_name = "unknown.xlsx"
        file_type = "unknown"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                file_name = metadata.get("file_name", "unknown.xlsx")
                file_type = metadata.get("file_type", "unknown")

        if file_type == "unknown":
            raise HTTPException(status_code=400, detail="文件类型未知，请重新上传")

        # 重新解析
        if file_type == "stock":
            parsed = parse_stock_excel(str(temp_path))
        else:
            parsed = parse_quotation_excel(str(temp_path))

        # 应用选中的 SKU
        log = apply_selected_data(
            db, parsed, str(temp_path), file_name, file_type, skus
        )

        return {
            "code": 0,
            "message": "导入完成",
            "data": log.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用失败: {str(e)}")
    finally:
        _cleanup_temp(session_id)


def _cleanup_temp(session_id: str):
    """清理临时文件"""
    for suffix in [".xlsx", ".json"]:
        try:
            os.unlink(str(TEMP_IMPORT_DIR / f"{session_id}{suffix}"))
        except (FileNotFoundError, PermissionError):
            pass


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
