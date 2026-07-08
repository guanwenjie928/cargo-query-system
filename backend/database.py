"""
货盘查询系统 - 数据库连接 & ORM 基础
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite 需要此参数
    echo=False,  # 生产环境关闭 SQL 日志
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（建表 + 创建索引）"""
    # 导入所有模型以确保表被注册
    from backend.models import product, warehouse_stock, order_fee, import_log, product_snapshot  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # 创建额外的索引（提升查询性能）
    with engine.connect() as conn:
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku)",
            "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)",
            "CREATE INDEX IF NOT EXISTS idx_products_price_usd ON products(price_usd)",
            "CREATE INDEX IF NOT EXISTS idx_products_stock_status ON products(stock_status)",
            "CREATE INDEX IF NOT EXISTS idx_products_category_price ON products(category, price_usd)",
            "CREATE INDEX IF NOT EXISTS idx_products_product_status ON products(product_status)",
            "CREATE INDEX IF NOT EXISTS idx_warehouse_stock_sku ON warehouse_stock(sku)",
            "CREATE INDEX IF NOT EXISTS idx_order_fees_sku ON order_fees(sku)",
        ]
        for sql in indexes:
            conn.execute(text(sql))
        conn.commit()
