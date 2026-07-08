"""
货盘查询系统 - 商品历史快照模型
每次更新前保存旧数据快照，支持历史追溯
"""
import json
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from backend.database import Base


class ProductSnapshot(Base):
    """商品历史快照 — 更新前保存旧数据，用于追溯变更历史"""

    __tablename__ = "product_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(100), nullable=False, index=True, comment="SKU")
    batch_no = Column(String(50), index=True, comment="触发快照的导入批次号")
    snapshot_data = Column(Text, nullable=False, comment="更新前的完整字段 JSON")
    created_at = Column(DateTime, server_default=func.now(), comment="快照时间")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "sku": self.sku,
            "batch_no": self.batch_no,
            "snapshot_data": json.loads(self.snapshot_data) if self.snapshot_data else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
