"""
货盘查询系统 - 内嵌图片提取器
从 Excel 工作表中提取内嵌图片对象

支持两种锚定模式：
1. 标准表格模式：图片锚定行号 = SKU 所在行（库存表 Sheet2）
2. 产品块模式：图片锚定行号在产品块范围内，需通过 model_rows 关联（报价表）
"""
import io
from typing import Dict, List, Optional
from PIL import Image


def extract_images_from_sheet(
    ws,
    sku_col: int = 1,
    model_rows: Optional[List[int]] = None,
) -> Dict[int, bytes]:
    """
    提取工作表中的内嵌图片

    参数：
        ws: openpyxl 工作表对象
        sku_col: SKU 所在列号（1-based），用于按行关联
        model_rows: 产品块起始行列表（报价表模式），如果提供则按产品块关联

    返回：{Excel行号(1-based): 图片二进制数据(PNG格式)}
    """
    images = {}

    if not hasattr(ws, "_images") or not ws._images:
        return images

    for img in ws._images:
        try:
            # 获取图片锚点位置
            anchor = img.anchor
            if hasattr(anchor, "_from"):
                row_num = anchor._from.row + 1  # 0-based → 1-based
            else:
                continue

            # 提取图片二进制数据
            img_data = img._data()
            if not img_data:
                continue

            # 转为 PNG 格式（统一存储），激进压缩以节省磁盘空间
            try:
                pil_img = Image.open(io.BytesIO(img_data))
                # 缩放到合理尺寸（最大宽度 600px）
                if pil_img.width > 600:
                    ratio = 600 / pil_img.width
                    new_size = (600, int(pil_img.height * ratio))
                    pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

                # 转为 JPEG 格式（体积更小）
                if pil_img.mode in ('RGBA', 'P'):
                    pil_img = pil_img.convert('RGB')

                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=75, optimize=True)
                img_bytes = buf.getvalue()
            except Exception:
                # 如果 PIL 处理失败，直接用原始数据
                img_bytes = img_data

            # 关联到行号
            if model_rows:
                # 报价表模式：找到该行属于哪个产品块
                associated_row = _find_product_block_row(row_num, model_rows)
                if associated_row:
                    images[associated_row] = img_bytes
            else:
                # 标准表格模式：直接用行号
                images[row_num] = img_bytes

        except Exception:
            continue

    return images


def _find_product_block_row(row_num: int, model_rows: List[int]) -> Optional[int]:
    """
    在报价表中，找到某行属于哪个产品块
    返回该产品块的 Model 行号（作为关联键）
    """
    for i, model_row in enumerate(model_rows):
        next_model = model_rows[i + 1] if i + 1 < len(model_rows) else float("inf")
        if model_row <= row_num < next_model:
            return model_row
    return None


def save_image(
    img_data: bytes,
    sku: str,
    batch_no: str,
    upload_dir,
) -> str:
    """
    保存图片到本地文件系统

    返回：相对路径（用于数据库存储和 URL 生成）
    """
    # 清理 SKU 中的特殊字符
    safe_sku = "".join(c for c in sku if c.isalnum() or c in "-_")
    filename = f"{safe_sku}_{batch_no}.jpg"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        f.write(img_data)

    return filename
