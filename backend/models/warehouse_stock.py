"""
货盘查询系统 - 仓库库存明细模型
每个 SKU 在不同仓库（CA01/NC01虚拟仓/XISE）的库存分布
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from backend.database import Base


class WarehouseStock(Base):
    """仓库库存明细 — 一个 SKU 多条记录（每个仓库一条）"""

    __tablename__ = "warehouse_stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, comment="关联商品ID")
    sku = Column(String(100), index=True, nullable=False, comment="SKU")
    warehouse = Column(String(100), nullable=False, comment="仓库名称：CA01/NC01虚拟仓/XISE/Multiple")
    stock = Column(Integer, default=0, comment="该仓库库存")
    in_transit = Column(Integer, default=0, comment="该仓库在途")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "warehouse": self.warehouse,
            "stock": self.stock,
            "in_transit": self.in_transit,
        }
