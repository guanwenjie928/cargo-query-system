"""
货盘查询系统 - 商品主表模型
合并库存表和报价表数据后的统一商品表
"""
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, func
from backend.database import Base


class Product(Base):
    """商品主表 — 一个 SKU 一条记录，字段来自库存表和报价表的合并"""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(100), nullable=False, unique=True, index=True, comment="SKU/型号")
    product_name = Column(String(200), index=True, comment="产品名称")
    product_name_en = Column(String(200), comment="英文品类描述（如 Sex Dolls）")
    category = Column(String(100), index=True, comment="品类（来自报价表 Sheet 名）")

    # 库存信息（来自库存表）
    stock_total = Column(Integer, default=0, comment="总库存")
    in_transit = Column(Integer, default=0, comment="在途数量")
    stock_status = Column(String(20), comment="库存状态：充足/紧张/缺货")

    # 价格信息（来自报价表）
    price_usd = Column(Numeric(10, 2), index=True, comment="美元价格")
    price_rmb = Column(Numeric(10, 2), comment="人民币价格")
    price_range = Column(String(50), comment="价格区间（系统计算）")

    # 产品属性（来自报价表）
    weight = Column(String(50), comment="重量（如 16kg）")
    material = Column(String(100), comment="材质（如 TPR）")
    hs_code = Column(String(50), comment="海关编码")

    # 附加信息（来自报价表 G/H 列）
    limit_price = Column(String(100), comment="限价（如 329.99美金）")
    packaging = Column(Text, comment="包装方式")
    feature_code = Column(String(200), comment="特征码")
    first_leg_fee = Column(Numeric(10, 2), comment="头程费")

    # 状态信息（来自报价表 A 列）
    product_status = Column(String(100), comment="产品状态：已下架/销完库存下架/包销/在售")
    shipping_mark = Column(String(200), comment="唛头")

    # 图片
    image_path = Column(String(500), comment="图片本地路径")
    image_source = Column(String(50), comment="图片来源文件类型：stock/quotation")
    image_date = Column(String(50), comment="图片来源文件日期（用于优先级判断）")

    # 系统字段
    remark = Column(Text, comment="备注（预留）")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    import_batch = Column(String(50), index=True, comment="导入批次号")

    def to_dict(self, include_detail=False):
        """转换为字典（API 响应用）"""
        data = {
            "id": self.id,
            "sku": self.sku,
            "product_name": self.product_name,
            "category": self.category,
            "stock_total": self.stock_total,
            "stock_status": self.stock_status,
            "price_usd": float(self.price_usd) if self.price_usd is not None else None,
            "price_rmb": float(self.price_rmb) if self.price_rmb is not None else None,
            "price_range": self.price_range,
            "product_status": self.product_status or "在售",
            "image_url": f"/api/images/{self.image_path}" if self.image_path else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_detail:
            data.update({
                "product_name_en": self.product_name_en,
                "in_transit": self.in_transit,
                "weight": self.weight,
                "material": self.material,
                "hs_code": self.hs_code,
                "limit_price": self.limit_price,
                "packaging": self.packaging,
                "feature_code": self.feature_code,
                "first_leg_fee": float(self.first_leg_fee) if self.first_leg_fee is not None else None,
                "shipping_mark": self.shipping_mark,
                "remark": self.remark,
            })

        return data
