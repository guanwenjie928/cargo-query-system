"""
货盘查询系统 - 导入日志模型
记录每次 Excel 导入的批次信息和结果
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from backend.database import Base


class ImportLog(Base):
    """导入日志 — 每次导入一条记录"""

    __tablename__ = "import_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_no = Column(String(50), unique=True, nullable=False, comment="批次号")
    file_name = Column(String(200), nullable=False, comment="原始文件名")
    file_type = Column(String(20), comment="文件类型：stock(库存表)/quotation(报价表)/fee(处理费)")
    file_path = Column(String(500), comment="归档路径")
    file_date = Column(String(50), comment="文件日期（从文件名提取或修改时间）")

    total_rows = Column(Integer, default=0, comment="总行数/产品数")
    success_rows = Column(Integer, default=0, comment="成功数")
    fail_rows = Column(Integer, default=0, comment="失败数")
    fail_details = Column(Text, comment="失败详情（JSON）")
    merged_rows = Column(Integer, default=0, comment="合并更新数（已有SKU被覆盖）")

    status = Column(String(20), default="processing", comment="processing/completed/failed/rolled_back")
    imported_at = Column(DateTime, server_default=func.now(), comment="导入时间")

    def to_dict(self):
        return {
            "id": self.id,
            "batch_no": self.batch_no,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_date": self.file_date,
            "total_rows": self.total_rows,
            "success_rows": self.success_rows,
            "fail_rows": self.fail_rows,
            "merged_rows": self.merged_rows,
            "status": self.status,
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
        }
