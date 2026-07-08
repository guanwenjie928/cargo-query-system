"""
货盘查询系统 - 订单处理费模型
美东/美西仓库的订单处理费用
"""
from sqlalchemy import Column, Integer, String, Numeric, func
from backend.database import Base


class OrderFee(Base):
    """订单处理费 — 按 SKU 和区域记录"""

    __tablename__ = "order_fees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(100), index=True, nullable=False, comment="SKU")
    region = Column(String(20), nullable=False, comment="区域：east(美东)/west(美西)")

    # 美东字段
    weight_lb = Column(Numeric(10, 4), comment="重量(磅) — 美东")
    weight_kg = Column(Numeric(10, 4), comment="重量(kg) — 美东")

    # 美西字段
    warehouse = Column(String(200), comment="仓库名称 — 美西")
    label_value = Column(String(50), comment="标签值 — 美西")
    weight_g = Column(Integer, comment="SKU核重(g) — 美西")
    dimensions = Column(String(100), comment="核算尺寸(cm) — 美西")

    # 通用字段
    processing_fee = Column(Numeric(10, 2), comment="订单处理费($)")

    created_at = Column(String(50), comment="创建时间")

    def to_dict(self):
        return {
            "region": self.region,
            "warehouse": self.warehouse,
            "weight_lb": float(self.weight_lb) if self.weight_lb else None,
            "weight_kg": float(self.weight_kg) if self.weight_kg else None,
            "weight_g": self.weight_g,
            "dimensions": self.dimensions,
            "label_value": self.label_value,
            "processing_fee": float(self.processing_fee) if self.processing_fee else None,
        }
