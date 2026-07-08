# 货盘查询系统 — PRD（产品需求文档）

> **版本**：v2.0-final（参数已确认）
> **日期**：2026-07-08
> **状态**：✅ 已确认，进入开发
> **部署方式**：本地部署（双击启动）
> **操作系统**：Windows

---

## 一、项目概述

### 1.1 项目背景

当前货盘管理依赖两个 Excel 文件手工操作：

| 文件 | 用途 | 数据量 | 格式特征 |
|------|------|--------|----------|
| 美国仓库存表 | 库存管理 | 154 个 SKU | 标准表格，多仓库分行 |
| 产品新报价表 | 定价 + 品类 + 图片 | 206 个产品（4个品类） | 纵向产品块，非标准表格 |

**痛点**：
- 两个文件数据割裂，查一个产品需要跨文件对照
- 报价表是「纵向产品块」格式（每产品占 8 行），人工查看极不方便
- 图片以嵌入对象形式存在于 Excel 中，无法快速浏览
- 无多维度交叉分析能力
- 更新数据需手动编辑，效率低且易出错

### 1.2 项目目标

构建一套本地部署的货盘查询系统，实现：
- **双文件导入 & 数据合并**：库存表 + 报价表导入后按 SKU 自动关联合并
- **多维度矩阵展示**：按品类×价格、品类×库存、价格×库存等维度交叉分析
- **首屏核心信息**：图片、型号(Sku)、产品名、库存、USD价格、品类、仓库一目了然
- **双击即用**：提供启动脚本，双击即可打开前端页面
- **架构可扩展**：前后端分离，为后续功能迭代预留空间

### 1.3 用户角色

| 角色 | 描述 | 权限 |
|------|------|------|
| 管理员（你） | 导入数据、查看、管理 | 全部功能 |

> 预留多用户权限体系，当前 MVP 单用户即可。

---

## 二、实际数据结构分析（基于用户 Excel）

### 2.1 文件1：美国仓库存表

**文件名**：`2026.6.22号美国仓库存表.xlsx`

#### Sheet: stock（库存主表）
- **格式**：标准表格，每行一条记录
- **总行数**：395 行（含表头），154 个唯一 SKU
- **数据特征**：每个 SKU 有 4 行记录，分别对应 4 个仓库

| 列 | 字段名 | 示例值 | 说明 |
|----|--------|--------|------|
| A | SKU | XS-MA50021 | 产品唯一标识 |
| B | Product Name | Chiquita Ass娇娃 | 产品名称（仅 Multiple 行有值） |
| C | 在途 | 0 | 在途数量 |
| D | 库存 | 98 | 库存数量 |
| E | Warehouse | Multiple/CA01/NC01虚拟仓/XISE | 仓库名称 |

**仓库分布模式**：
```
SKU: XS-MA50021
  ├── Multiple  → 库存 98（汇总值）
  ├── CA01      → 库存 0
  ├── NC01虚拟仓 → 库存 0
  └── XISE      → 库存 98
```

#### Sheet: Sheet2（库存 + 图片）
- **格式**：标准表格，每行一个 SKU（不拆仓库）
- **总行数**：154 行（含表头），153 个 SKU
- **图片**：141 张内嵌图片，锚定在 E 列（图片列）

| 列 | 字段名 | 示例值 | 说明 |
|----|--------|--------|------|
| A | SKU | XS-MA50021 | 产品唯一标识 |
| B | Product Name | Chiquita Ass娇娃 | 产品名称 |
| C | 在途 | 0 | 在途数量 |
| D | 库存 | 98 | 总库存 |
| E | 图片 | （内嵌图片对象） | 产品图片 |

### 2.2 文件2：产品新报价表

**文件名**：`幸色海外仓美国站2025年11月产品新报价.xlsx`

#### 品类 Sheet（软胶/功能软胶产品/飞机杯/阳具与水晶套）

**格式**：纵向产品块（非标准表格），每个产品占 ~8 行

**产品块结构示例**：
```
行N:   A列=唛头/状态     B列=Model       C列=SQ-MA30011     ← 型号
行N+1: A列=已下架/销完下架 B列=Description  C列=丽莲腿模       ← 产品名
行N+2:                   B列=Weight      C列=16kg          ← 重量
行N+3:                   B列=RMB         C列=726            ← 人民币价格
行N+4:                   B列=USD         C列=115            ← 美元价格
行N+5:                   B列=Material    C列=TPR            ← 材质
行N+6:                   B列=HS CODE     C列=9019102050     ← 海关编码
行N+7:                   B列=Description C列=Sex Dolls      ← 英文品类描述
```

**附加字段（G/H 列，非每行都有）**：
| 列 | 字段 | 示例值 | 说明 |
|----|------|--------|------|
| G | 限价 | 329.99美金 | 限价标记 |
| G | 包装方式 | 裸货灰色双色化妆-pe袋-内箱-珍珠棉-纸箱 | 包装说明 |
| G | 特征码 | 002 / 海外仓特征码004 | 内部特征码 |
| H | 头程费 | 192 | 头程运费 |

**A 列状态值统计**：
| 状态 | 含义 |
|------|------|
| 已下架 | 该产品已下架 |
| 销完库存下架 | 售完即下架 |
| 包销 | 独家销售 |
| 唛头 + 编号 | 物流唛头信息（如 `6276 1/668`） |

**各品类 Sheet 统计**：
| Sheet 名 | 品类 | 产品数 | 图片数 | 总行数 |
|----------|------|--------|--------|--------|
| 软胶 | 软胶 | 74 | 74 | 595 |
| 功能软胶产品 | 功能软胶产品 | 81 | 81 | 651 |
| 飞机杯 | 飞机杯 | 22 | 20 | 178 |
| 阳具与水晶套 | 阳具与水晶套 | 29 | 27 | 250 |
| **合计** | - | **206** | **202** | - |

#### Sheet: 美东订单处理费
- **格式**：标准表格
- **数据量**：216 个 SKU
- **列**：SKU、lb(磅)、kg(千克)、处理费($)

#### Sheet: 美西订单处理费
- **格式**：标准表格
- **数据量**：35 个 SKU
- **列**：仓库、SKU、产品名称、标签值、SKU核重(g)、核算尺寸(cm)、订单处理费($)

#### Sheet: 物流查询网址
- 物流商查询链接（UPS/USPS/联邦/国际件），非产品数据，系统不导入

### 2.3 数据关联关系

```
文件1-Sheet2 (库存+图片)          文件2-品类Sheet (报价+图片)
  SKU ◄──────────────────────────► Model (SKU)
  │                                  │
  ├── Product Name                   ├── Description (产品名)
  ├── 在途                           ├── Weight (重量)
  ├── 库存                           ├── RMB (人民币价)
  ├── 图片 (内嵌)                    ├── USD (美元价)
  │                                  ├── Material (材质)
  │                                  ├── HS CODE (海关编码)
  │                                  ├── 限价
  │                                  ├── 包装方式
  │                                  ├── 特征码
  │                                  ├── 头程费
  │                                  ├── 品类 (=Sheet名)
  │                                  └── 图片 (内嵌)
  │
  └── 文件1-stock (分仓库库存明细)
       ├── CA01 库存
       ├── NC01虚拟仓 库存
       └── XISE 库存
```

**关联键**：`SKU`（文件1）↔ `Model`（文件2）

---

## 三、技术架构

### 3.1 技术选型

| 层级 | 技术 | 版本 | 选型理由 |
|------|------|------|----------|
| 前端框架 | React | 18.x | 生态成熟，Ant Design Pro 组件丰富 |
| UI 组件库 | Ant Design Pro | 5.x | ProTable/ProForm 开箱即用，矩阵布局友好 |
| 构建工具 | Vite | 5.x | 极速热更新，打包体积小 |
| 后端框架 | Python FastAPI | 0.110+ | 轻量高性能，异步支持好 |
| ORM | SQLAlchemy | 2.x | Python 主流 ORM，支持 SQLite/MySQL 无缝切换 |
| 数据库 | SQLite | 3.x | 零配置本地部署，万级数据量性能良好 |
| Excel 解析 | openpyxl | 3.x | 支持读取内嵌图片对象、纵向块解析 |
| 图片处理 | Pillow | 10.x | 图片压缩、缩略图生成、格式转换 |
| 启动方式 | Batch 脚本 (.bat) | - | 双击启动后端 + 自动打开浏览器 |

### 3.2 架构图

```
┌──────────────────────────────────────────────────────────┐
│                 前端 (React + Ant Design Pro)             │
│                                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ 矩阵看板  │ │ 商品列表  │ │ 导入管理  │ │ 商品详情    │  │
│  │(多维交叉) │ │(卡片/表格)│ │(双文件合并)│ │(全字段+图片)│  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
└────────────────────────┬─────────────────────────────────┘
                         │ REST API
┌────────────────────────┴─────────────────────────────────┐
│                   后端 (Python FastAPI)                    │
│                                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ 查询服务  │ │导入服务   │ │图片服务   │ │矩阵聚合     │  │
│  │(分页/筛选)│ │(双格式解析)│ │(存储/压缩)│ │(维度统计)   │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
│                                                           │
│  导入解析器：                                               │
│  ┌─────────────────┐  ┌──────────────────────────────┐    │
│  │ 库存表解析器      │  │ 报价表解析器（纵向块格式）       │    │
│  │ (标准表格)        │  │ (按Model行分割产品块)          │    │
│  └─────────────────┘  └──────────────────────────────┘    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────────┐
│                      数据层                                │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│  │ SQLite   │ │ 图片存储      │ │ 导入文件归档           │  │
│  │ cargo.db │ │ uploads/     │ │ archives/            │  │
│  └──────────┘ └──────────────┘ └──────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 3.3 目录结构

```
货盘查询系统/
├── 启动系统.bat                 # ← 双击此文件启动系统
├── README.md
├── PRD-货盘查询系统.md          # 本文档
│
├── backend/                     # 后端服务
│   ├── main.py                  # FastAPI 入口
│   ├── config.py                # 配置管理
│   ├── database.py              # 数据库连接 & ORM
│   ├── models/
│   │   ├── product.py           # 商品主模型
│   │   ├── warehouse_stock.py   # 仓库库存明细模型
│   │   ├── category.py          # 品类模型
│   │   └── import_log.py        # 导入日志模型
│   ├── routers/
│   │   ├── products.py          # 商品查询路由
│   │   ├── matrix.py            # 矩阵聚合路由
│   │   ├── import_excel.py      # Excel 导入路由
│   │   └── images.py            # 图片服务路由
│   ├── services/
│   │   ├── stock_parser.py      # 库存表解析器（标准表格格式）
│   │   ├── quotation_parser.py  # 报价表解析器（纵向产品块格式）
│   │   ├── image_extractor.py   # 内嵌图片提取器（两种锚定方式）
│   │   ├── data_merger.py       # 数据合并器（按SKU关联）
│   │   └── matrix_aggregator.py # 矩阵数据聚合器
│   ├── requirements.txt
│   └── tests/
│
├── frontend/                    # 前端应用
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard/       # 矩阵看板页
│   │   │   ├── ProductList/     # 商品列表页
│   │   │   ├── ProductDetail/   # 商品详情页
│   │   │   ├── ImportExcel/     # 导入管理页
│   │   │   └── Settings/        # 设置页（预留）
│   │   ├── components/
│   │   │   ├── MatrixView/      # 矩阵视图组件
│   │   │   ├── ProductCard/     # 商品卡片组件
│   │   │   └── ImagePreview/    # 图片预览组件
│   │   ├── services/
│   │   │   └── api.ts           # API 请求封装
│   │   └── types/
│   │       └── index.ts         # 类型定义
│   └── dist/                    # 构建产物（部署用）
│
├── data/
│   ├── cargo.db                 # SQLite 数据库文件
│   └── uploads/
│       └── images/              # 提取的图片存储
│
└── archives/                    # 导入文件归档
```

---

## 四、数据模型设计

### 4.1 数据库表结构

#### 4.1.1 products（商品主表 — 合并后数据）

| 字段名 | 类型 | 说明 | 来源 | 约束 |
|--------|------|------|------|------|
| id | INTEGER | 主键 | 系统 | PK, AUTO INCREMENT |
| sku | VARCHAR(100) | SKU/型号 | 库存表.A列 / 报价表.Model | NOT NULL, UNIQUE, INDEX |
| product_name | VARCHAR(200) | 产品名称 | 库存表.B列 / 报价表.Description | INDEX |
| product_name_en | VARCHAR(200) | 英文品类描述 | 报价表第二个Description | 可选 |
| category | VARCHAR(100) | 品类 | 报价表.Sheet名 | INDEX |
| stock_total | INTEGER | 总库存 | 库存表Sheet2.D列 | DEFAULT 0 |
| in_transit | INTEGER | 在途数量 | 库存表.C列 | DEFAULT 0 |
| stock_status | VARCHAR(20) | 库存状态 | 系统计算 | 充足/紧张/缺货 |
| price_usd | DECIMAL(10,2) | 美元价格 | 报价表.USD | INDEX |
| price_rmb | DECIMAL(10,2) | 人民币价格 | 报价表.RMB | |
| price_range | VARCHAR(50) | 价格区间 | 系统计算 | 按 USD 分组 |
| weight | VARCHAR(50) | 重量 | 报价表.Weight | |
| material | VARCHAR(100) | 材质 | 报价表.Material | |
| hs_code | VARCHAR(50) | 海关编码 | 报价表.HS CODE | |
| limit_price | VARCHAR(100) | 限价 | 报价表.G列 | |
| packaging | TEXT | 包装方式 | 报价表.G列 | |
| feature_code | VARCHAR(200) | 特征码 | 报价表.G列 | |
| first_leg_fee | DECIMAL(10,2) | 头程费 | 报价表.H列 | |
| product_status | VARCHAR(100) | 产品状态 | 报价表.A列 | 已下架/销完下架/包销等 |
| shipping_mark | VARCHAR(200) | 唛头 | 报价表.A列 | |
| image_path | VARCHAR(500) | 图片路径 | 图片提取后生成 | 本地相对路径 |
| image_source | VARCHAR(20) | 图片来源 | 系统 | stock/quotation |
| remark | TEXT | 备注 | - | 预留 |
| created_at | DATETIME | 创建时间 | 系统 | |
| updated_at | DATETIME | 更新时间 | 系统 | |
| import_batch | VARCHAR(50) | 导入批次号 | 系统 | 关联导入日志 |

**索引设计**：
```sql
CREATE UNIQUE INDEX idx_sku ON products(sku);
CREATE INDEX idx_category ON products(category);
CREATE INDEX idx_price_usd ON products(price_usd);
CREATE INDEX idx_stock_status ON products(stock_status);
CREATE INDEX idx_category_price ON products(category, price_usd);
CREATE INDEX idx_product_name ON products(product_name);
CREATE INDEX idx_import_batch ON products(import_batch);
```

#### 4.1.2 warehouse_stock（仓库库存明细表）

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | INTEGER | 主键 | PK |
| product_id | INTEGER | 关联商品ID | FK → products.id |
| sku | VARCHAR(100) | SKU | INDEX |
| warehouse | VARCHAR(100) | 仓库名称 | CA01/NC01虚拟仓/XISE |
| stock | INTEGER | 该仓库库存 | DEFAULT 0 |
| in_transit | INTEGER | 该仓库在途 | DEFAULT 0 |
| updated_at | DATETIME | 更新时间 | |

#### 4.1.3 order_fees（订单处理费表）

| 字段名 | 类型 | 说明 | 来源 |
|--------|------|------|------|
| id | INTEGER | 主键 | PK |
| sku | VARCHAR(100) | SKU | INDEX |
| region | VARCHAR(20) | 区域 | east(美东)/west(美西) |
| warehouse | VARCHAR(100) | 仓库 | 美西有仓库名 |
| weight_lb | DECIMAL(10,4) | 重量(磅) | 美东 |
| weight_kg | DECIMAL(10,4) | 重量(kg) | 美东 |
| weight_g | INTEGER | 核重(g) | 美西 |
| dimensions | VARCHAR(100) | 核算尺寸 | 美西 |
| processing_fee | DECIMAL(10,2) | 订单处理费($) | |
| label_value | VARCHAR(50) | 标签值 | 美西 |

#### 4.1.4 import_logs（导入日志表）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| batch_no | VARCHAR(50) | 批次号（唯一） |
| file_name | VARCHAR(200) | 原始文件名 |
| file_type | VARCHAR(20) | 文件类型：stock/quotation |
| file_path | VARCHAR(500) | 归档路径 |
| total_rows | INTEGER | 总行数/产品数 |
| success_rows | INTEGER | 成功数 |
| fail_rows | INTEGER | 失败数 |
| fail_details | TEXT | 失败详情（JSON） |
| status | VARCHAR(20) | processing/completed/failed/rolled_back |
| imported_at | DATETIME | 导入时间 |

---

## 五、功能需求详述

### 5.1 货盘看板（矩阵展示）

**页面路径**：`/dashboard`（首页）

#### 5.1.1 矩阵视图

| 矩阵模式 | 横轴 | 纵轴 | 单元格内容 |
|----------|------|------|------------|
| 品类×价格 | 品类 | USD价格区间 | 商品数量 + 缩略图（hover预览） |
| 品类×库存 | 品类 | 库存状态 | 商品数量 + 颜色标识 |
| 价格×库存 | USD价格区间 | 库存状态 | 商品数量 + 颜色标识 |
| 自定义 | 用户选择维度 | 用户选择维度 | 商品数量 + 缩略图 |

**可选维度**：
- 品类（软胶/功能软胶产品/飞机杯/阳具与水晶套）
- USD价格区间（自动分组）
- 库存状态（充足/紧张/缺货）
- 产品状态（在售/已下架/销完下架/包销）

#### 5.1.2 交互逻辑

- **矩阵模式切换**：顶部 Tab 切换 4 种矩阵模式
- **点击单元格**：展开该维度下的商品列表（侧边抽屉，分页展示）
- **悬停单元格**：显示 Tooltip，包含商品数量 + 前 5 张缩略图
- **颜色标识**：
  - 库存充足（>50）：绿色
  - 库存紧张（1-50）：橙色
  - 缺货（=0）：红色
- **价格区间自动分组**（基于 USD）：
  - $0-50、$50-100、$100-200、$200-500、$500+（待用户确认）

#### 5.1.3 看板顶部统计卡片

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ 总SKU数   │ │ 总库存件数 │ │ 缺货SKU数 │ │ 已下架数   │
│   206    │ │  15,432  │ │    23    │ │    45    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 5.2 商品列表

**页面路径**：`/products`

#### 5.2.1 双视图模式

**卡片视图（默认）**：
```
┌───────────────────────────────┐
│  ┌────────┐                   │
│  │  图片   │  SKU：SQ-MA30011  │
│  │ 缩略图  │  名称：丽莲腿模    │
│  │        │  品类：软胶        │
│  └────────┘  USD：$115        │
│              RMB：¥726        │
│              库存：98件        │
│              状态：在售        │
└───────────────────────────────┘
```

**表格视图**：
| 图片 | SKU | 产品名称 | 品类 | USD | RMB | 库存 | 库存状态 | 产品状态 | 重量 | 操作 |
|------|-----|----------|------|-----|-----|------|----------|----------|------|------|
| [缩略图] | SQ-MA30011 | 丽莲腿模 | 软胶 | $115 | ¥726 | 98 | 充足 | 在售 | 16kg | 详情 |

#### 5.2.2 搜索与筛选

- **关键词搜索**：SKU + 产品名称模糊匹配
- **品类筛选**：下拉多选（软胶/功能软胶产品/飞机杯/阳具与水晶套）
- **价格区间筛选**：USD 最小值~最大值
- **库存状态筛选**：充足/紧张/缺货 多选
- **产品状态筛选**：在售/已下架/销完下架/包销 多选
- **排序**：USD 升降序、库存升降序、更新时间排序

#### 5.2.3 分页

- 默认每页 20 条
- 可切换 20/50/100/200
- 显示总数、当前页码
- 支持跳页

### 5.3 商品详情

**页面路径**：`/products/:id`

**展示内容**：

| 区域 | 字段 |
|------|------|
| 图片区 | 大图展示（支持点击放大） |
| 基础信息 | SKU、产品名称、英文品类描述、品类 |
| 价格信息 | USD、RMB、限价、头程费 |
| 库存信息 | 总库存、在途、库存状态 |
| 仓库明细 | 各仓库库存分布表（CA01/NC01/XISE） |
| 产品属性 | 重量、材质、HS CODE、包装方式、特征码 |
| 状态信息 | 产品状态（已下架/销完下架/包销等）、唛头 |
| 费用信息 | 美东处理费、美西处理费（如有） |
| 操作 | 返回列表 |

### 5.4 Excel 导入

**页面路径**：`/import`

#### 5.4.1 导入流程

支持两种文件类型导入，导入后自动按 SKU 合并：

```
用户上传 Excel 文件
      │
      ▼
┌──────────────────┐
│  文件类型识别     │ ← 根据文件名/Sheet名自动判断
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────────┐
│ 库存表  │ │  报价表     │
│ 解析器  │ │  解析器     │
└───┬────┘ └─────┬──────┘
    │             │
    ▼             ▼
┌────────┐ ┌────────────────────────┐
│标准表格 │ │ 纵向产品块解析           │
│解析     │ │ 1. 找Model行 → 确定块起点 │
│         │ │ 2. 向下扫描至下一个Model │
│         │ │ 3. 按B列字段名提取值     │
│         │ │ 4. Sheet名 → 品类       │
└───┬────┘ └─────────┬──────────────┘
    │                │
    ▼                ▼
┌────────┐ ┌────────────────────┐
│图片提取 │ │ 图片提取            │
│(E列锚定)│ │ (A列锚定，行号对应  │
│        │ │  产品块起始行)      │
└───┬────┘ └─────────┬──────────┘
    │                │
    └───────┬────────┘
            ▼
    ┌──────────────┐
    │  数据合并      │ ← 按 SKU 关联，合并字段
    │  写入数据库    │   库存表的库存 + 报价表的价格
    └──────┬───────┘
           ▼
    ┌──────────────┐
    │  结果展示      │ ← 成功/失败/合并统计
    └──────────────┘
```

#### 5.4.2 库存表解析器（stock_parser.py）

**解析 stock Sheet**：
```python
# 标准表格，按行读取
# 一个 SKU 4 行（Multiple/CA01/NC01虚拟仓/XISE）
# 取 Multiple 行的库存作为总库存
# 各仓库库存存入 warehouse_stock 表
```

**解析 Sheet2**：
```python
# 标准表格，一行一个 SKU
# 提取 SKU、Product Name、在途、库存
# 提取 E 列内嵌图片（锚定行号 = SKU 所在行）
```

#### 5.4.3 报价表解析器（quotation_parser.py）— 核心难点

**纵向产品块解析逻辑**：

```python
# 1. 遍历品类 Sheet（软胶/功能软胶产品/飞机杯/阳具与水晶套）
# 2. Sheet 名 = 品类
# 3. 在 B 列扫描所有 "Model" 行，确定每个产品块的起始位置
# 4. 从 Model 行向下扫描，直到下一个 Model 行（或 Sheet 结尾）
# 5. 按 B 列的字段名提取 C 列的值：

product = {}
for row in range(model_row, next_model_row):
    field_name = ws.cell(row, 2).value  # B列
    field_value = ws.cell(row, 3).value  # C列

    if field_name == 'Model':       product['sku'] = field_value
    elif field_name == 'Description' and not product.get('product_name'):
        product['product_name'] = field_value  # 第一个Description是中文名
    elif field_name == 'Description' and product.get('product_name'):
        product['product_name_en'] = field_value  # 第二个是英文品类
    elif field_name == 'Weight':    product['weight'] = field_value
    elif field_name == 'RMB':       product['price_rmb'] = field_value
    elif field_name == 'USD':       product['price_usd'] = field_value
    elif field_name == 'Material':  product['material'] = field_value
    elif field_name == 'HS CODE':   product['hs_code'] = field_value

    # A列：状态/唛头
    a_value = ws.cell(row, 1).value
    if a_value:
        if '下架' in str(a_value) or '包销' in str(a_value):
            product['product_status'] = a_value
        else:
            product['shipping_mark'] = a_value

    # G列：限价/包装方式/特征码
    g_value = ws.cell(row, 7).value
    if g_value:
        if '美金' in str(g_value) or '限价' in str(g_value):
            product['limit_price'] = g_value
        elif '包装' in str(g_value) or '袋' in str(g_value) or '盒' in str(g_value):
            product['packaging'] = g_value
        elif '特征码' in str(g_value):
            product['feature_code'] = g_value

    # H列：头程费
    h_value = ws.cell(row, 8).value
    if h_value and isinstance(h_value, (int, float)):
        product['first_leg_fee'] = h_value

product['category'] = sheet_name  # Sheet名作为品类
```

#### 5.4.4 内嵌图片提取方案（两种模式）

**模式一：库存表 Sheet2 的图片（E列锚定）**
```python
# 图片锚定在 E 列，anchor._from.row 对应 SKU 所在行
# row 1 = 表头，row 2 = 第一个 SKU
# 图片 anchor._from.row + 1 (0-based → 1-based) = Excel 行号
for img in ws._images:
    row_num = img.anchor._from.row + 1  # 转为 1-based
    sku = ws.cell(row=row_num, column=1).value  # A列的SKU
    img_data = img._data()
    save_image(img_data, sku, batch_no)
```

**模式二：报价表的图片（A列锚定，对应产品块）**
```python
# 图片锚定在 A 列附近，anchor._from.row 对应产品块内某行
# 需要找到该行属于哪个产品块
for img in ws._images:
    img_row = img.anchor._from.row + 1  # 1-based

    # 找到该行属于哪个产品块
    for i, model_row in enumerate(model_rows):
        next_model = model_rows[i+1] if i+1 < len(model_rows) else ws.max_row + 1
        if model_row <= img_row < next_model:
            sku = ws.cell(row=model_row, column=3).value  # C列的Model值
            break

    img_data = img._data()
    save_image(img_data, sku, batch_no)
```

**图片处理**：
- 保存原始图片到 `data/uploads/images/{sku}_{batch_no}.png`
- 用 Pillow 生成缩略图（200x200）用于列表展示
- 图片格式自动检测（PNG/JPEG）

#### 5.4.5 数据合并策略

当同一 SKU 在两个文件中都存在时，合并规则：

| 字段 | 来源优先级 | 说明 |
|------|-----------|------|
| sku | 两者一致 | 关联键 |
| product_name | 报价表 > 库存表 | 报价表更完整 |
| category | 报价表 | 库存表无此字段 |
| stock_total | 库存表 | 库存表更准确 |
| in_transit | 库存表 | 报价表无此字段 |
| price_usd | 报价表 | 库存表无此字段 |
| price_rmb | 报价表 | 库存表无此字段 |
| weight/material/hs_code | 报价表 | 库存表无此字段 |
| 仓库明细 | 库存表 | 报价表无此字段 |
| image | 优先报价表 > 库存表 | 报价表图片更清晰 |
| 产品状态 | 报价表 | 库存表无此字段 |

#### 5.4.6 同 SKU 冲突处理

| 场景 | 处理方式 |
|------|----------|
| 同 SKU 再次导入 | 默认覆盖更新，记录历史值到日志 |
| 仅库存表有此 SKU | 正常入库，价格等字段为空 |
| 仅报价表有此 SKU | 正常入库，库存为 0 |
| 必填字段缺失 | SKU 为空则跳过并记录 |
| 数据类型异常 | 尝试转换，失败则标记 |

#### 5.4.7 导入历史

- 展示历史导入记录（批次号、文件名、文件类型、时间、成功/失败数）
- 支持按批次回滚（删除该批次导入/更新的数据）
- 支持下载原始导入文件

### 5.5 启动方式

#### 5.5.1 启动脚本设计

**文件**：`启动系统.bat`（放在项目根目录）

**功能**：
1. 检查 Python 环境是否存在
2. 检查依赖是否安装（缺失则自动 `pip install`）
3. 启动后端 FastAPI 服务（后台运行）
4. 等待后端就绪（健康检查轮询）
5. 自动打开默认浏览器访问 `http://localhost:8000`
6. 关闭窗口时自动停止后端服务

#### 5.5.2 前端部署方式

- 前端构建后产物 `dist/` 由后端 FastAPI 静态文件服务托管
- 用户只需启动后端，前端页面自动可访问
- 端口：`8000`（可配置）

---

## 六、API 接口设计

### 6.1 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/products` | 商品列表（分页+筛选+排序） |
| GET | `/api/products/{id}` | 商品详情（含仓库明细+处理费） |
| GET | `/api/matrix` | 矩阵聚合数据 |
| GET | `/api/stats` | 看板顶部统计卡片数据 |
| POST | `/api/import/upload` | 上传 Excel 文件 |
| POST | `/api/import/parse` | 解析 Excel（预览，不写入） |
| POST | `/api/import/confirm` | 确认导入（写入数据库） |
| GET | `/api/import/logs` | 导入历史 |
| POST | `/api/import/rollback/{batch_no}` | 回滚批次 |
| GET | `/api/images/{filename}` | 获取图片 |
| GET | `/api/categories` | 品类列表 |
| GET | `/api/health` | 健康检查 |

### 6.2 核心接口示例

#### 6.2.1 商品列表

```
GET /api/products?page=1&page_size=20&keyword=SQ-MA&category=软胶&min_price=10&max_price=500&stock_status=充足&sort=price_usd&order=asc
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": 1,
        "sku": "SQ-MA30011",
        "product_name": "丽莲腿模",
        "category": "软胶",
        "stock_total": 0,
        "stock_status": "缺货",
        "price_usd": 115.00,
        "price_rmb": 726.00,
        "price_range": "100-200",
        "weight": "16kg",
        "product_status": "已下架",
        "image_url": "/api/images/SQ-MA30011_batch001.png",
        "updated_at": "2026-07-08T10:30:00"
      }
    ],
    "total": 206,
    "page": 1,
    "page_size": 20
  }
}
```

#### 6.2.2 商品详情

```
GET /api/products/1
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "id": 1,
    "sku": "SQ-MA30011",
    "product_name": "丽莲腿模",
    "product_name_en": "Sex Dolls",
    "category": "软胶",
    "stock_total": 0,
    "in_transit": 0,
    "stock_status": "缺货",
    "price_usd": 115.00,
    "price_rmb": 726.00,
    "weight": "16kg",
    "material": "TPR",
    "hs_code": "9019102050",
    "limit_price": "329.99美金",
    "packaging": "裸货灰色双色化妆-pe袋-内箱-珍珠棉-纸箱",
    "feature_code": "特征码 002 / 海外仓特征码004",
    "first_leg_fee": 192.00,
    "product_status": "已下架",
    "shipping_mark": "6276 1/668-6276 100/668",
    "image_url": "/api/images/SQ-MA30011_batch001.png",
    "warehouses": [
      {"warehouse": "CA01", "stock": 0, "in_transit": 0},
      {"warehouse": "NC01虚拟仓", "stock": 0, "in_transit": 0},
      {"warehouse": "XISE", "stock": 0, "in_transit": 0}
    ],
    "order_fees": {
      "east": {"processing_fee": 0.62},
      "west": {"processing_fee": 1.65, "warehouse": "美西HYC-Chino仓"}
    }
  }
}
```

#### 6.2.3 矩阵聚合

```
GET /api/matrix?x_axis=category&y_axis=price_range
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "x_labels": ["软胶", "功能软胶产品", "飞机杯", "阳具与水晶套"],
    "y_labels": ["$0-50", "$50-100", "$100-200", "$200-500", "$500+"],
    "matrix": [
      [12, 35, 20, 5, 2],
      [8, 40, 25, 6, 2],
      [15, 5, 2, 0, 0],
      [10, 15, 3, 1, 0]
    ],
    "preview_images": {
      "0_0": ["/api/images/img1.png", "/api/images/img2.png"],
      "0_1": ["/api/images/img3.png"]
    }
  }
}
```

#### 6.2.4 统计卡片

```
GET /api/stats
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "total_skus": 206,
    "total_stock": 15432,
    "out_of_stock_count": 23,
    "discontinued_count": 45,
    "category_distribution": {
      "软胶": 74,
      "功能软胶产品": 81,
      "飞机杯": 22,
      "阳具与水晶套": 29
    }
  }
}
```

---

## 七、非功能需求

### 7.1 性能

| 指标 | 目标 |
|------|------|
| 列表分页查询响应 | < 200ms |
| 矩阵聚合查询响应 | < 500ms |
| 库存表导入（154 SKU） | < 10 秒（含图片提取） |
| 报价表导入（206 产品） | < 20 秒（含图片提取） |
| 图片缩略图加载 | < 100KB/张，首屏 < 2 秒 |
| 前端首屏渲染 | < 3 秒 |

### 7.2 数据安全

- 导入前自动备份当前数据库（`cargo.db.backup.{timestamp}`）
- 每次导入创建独立批次号，支持精确回滚
- 图片文件命名规则防冲突：`{sku}_{batch_no}.png`

### 7.3 兼容性

- 浏览器：Chrome 90+ / Edge 90+ / Firefox 88+
- 操作系统：Windows 10/11（主要）、macOS、Linux
- Excel 格式：`.xlsx`（优先支持）

---

## 八、扩展规划（预留）

### 8.1 第二期功能

| 功能 | 说明 |
|------|------|
| 价格趋势图 | 同 SKU 价格随时间变化折线图（需保留历史导入数据） |
| 库存预警 | 库存低于阈值时自动标红提醒 |
| 数据导出 | 导出当前筛选结果为 Excel |
| 批量编辑 | 批量修改品类、价格等字段 |
| 运费计算器 | 根据区间运费 + 头程费 + 处理费计算最终成本 |
| 多图支持 | 一个商品关联多张图片 |

### 8.2 第三期功能

| 功能 | 说明 |
|------|------|
| 多用户权限 | 管理员/查看者角色分离 |
| 操作日志 | 记录所有增删改操作 |
| 数据看板大屏 | 可视化大屏展示核心指标 |
| 数据库迁移 | SQLite → MySQL 一键迁移 |
| 供应商管理 | 供应商信息独立管理 |

### 8.3 架构预留

- 后端模块化设计，新增功能只需新增 router + service
- 数据库模型预留 remark 等扩展字段
- 前端页面路由预留 Settings 页面
- API 遵循 RESTful 规范，便于后续接入移动端
- import_logs 保留历史数据，为价格趋势功能做数据储备

---

## 九、交付物清单

| 交付物 | 路径 | 说明 |
|--------|------|------|
| PRD 文档 | `PRD-货盘查询系统.md` | 本文档 |
| 后端代码 | `backend/` | FastAPI 完整服务 |
| 前端代码 | `frontend/` | React + AntD Pro 应用 |
| 启动脚本 | `启动系统.bat` | 双击启动 |
| 数据库 | `data/cargo.db` | 自动创建 |
| 图片存储 | `data/uploads/images/` | 自动创建 |
| 使用说明 | `README.md` | 安装与使用指南 |

---

## 十、实施计划

### 第一阶段：基础搭建
- 项目初始化（前后端脚手架）
- 数据库设计与建表
- 基础 API 框架搭建
- 启动脚本编写与测试

### 第二阶段：Excel 导入（核心）
- 库存表解析器（标准表格格式）
- 报价表解析器（纵向产品块格式）— **最复杂**
- 内嵌图片提取器（两种锚定模式）
- 数据合并器（按 SKU 关联合并）
- 导入预览 + 确认 + 日志

### 第三阶段：商品查询
- 商品列表（卡片/表格双视图 + 分页 + 筛选）
- 商品详情页（全字段 + 仓库明细 + 处理费）
- 图片服务（原图 + 缩略图）

### 第四阶段：矩阵看板
- 矩阵聚合 API
- 矩阵视图组件（4种模式 + 自定义）
- 交互逻辑（点击展开、hover预览）
- 统计卡片

### 第五阶段：优化与交付
- 性能优化（索引、分页、图片压缩）
- 启动脚本端到端测试
- 使用文档
- 交付

---

## 十一、已确认事项

| # | 问题 | 用户确认 |
|---|------|----------|
| 1 | USD 价格区间 | ✅ `$0-50 / $50-100 / $100-200 / $200-500 / $500+` |
| 2 | 库存阈值 | ✅ `充足(>50) / 紧张(1-50) / 缺货(=0)` |
| 3 | 同 SKU 再次导入 | ✅ 覆盖最新（自动覆盖，不询问） |
| 4 | 操作系统 | ✅ Windows（启动脚本写 .bat） |
| 5 | 端口号 | ✅ 自动查找空闲端口（不固定 8000） |
| 6 | 图片优先级 | ✅ 优先使用日期最新的文件中的图片 |
| 7 | 产品状态展示 | ✅ 标记出不同状态（已下架/销完下架/包销等），支持筛选 |
| 8 | 订单处理费 | ✅ 在商品详情中展示，并解释费用用途 |

### 11.1 订单处理费说明（商品详情页展示）

| 费用项 | 来源 | 说明 |
|--------|------|------|
| 美东订单处理费 | 美东订单处理费 Sheet | 美东仓库发货时，每笔订单的仓储操作处理费用（$），按 SKU 核重计算 |
| 美西订单处理费 | 美西订单处理费 Sheet | 美西仓库（HYC-Chino仓）发货时，每笔订单的仓储操作处理费用（$），按 SKU 核重和尺寸计算 |
| 头程费 | 报价表 H 列 | 国内发往海外仓的头程运输费用（¥/件），已含在成本中 |

### 11.2 端口自动查找策略

启动脚本按以下顺序查找可用端口：
1. 从 `8000` 开始尝试
2. 若被占用则递增（8001, 8002, ... 8099）
3. 找到可用端口后写入配置，前后端统一使用
4. 浏览器自动打开对应地址

### 11.3 图片优先级策略

- 导入时记录每个文件的「文件日期」（从文件名提取或文件修改时间）
- 同一 SKU 在不同文件中都有图片时，取文件日期最新的图片
- 例：库存表（2026.6.22）> 报价表（2025年11月）→ 使用库存表的图片

---

*参数已全部确认，进入开发阶段*
