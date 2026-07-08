# 货盘查询系统

> 本地部署的货盘查询与管理系统，支持多维度矩阵展示、Excel 导入（含内嵌图片提取）、商品详情查看。

## 快速开始

### 1. 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 双击启动（Windows）

双击项目根目录的 **`启动系统.bat`**，系统会自动：
- 检查 Python 环境
- 安装缺失依赖
- 查找可用端口（8000-8099）
- 启动后端服务
- 打开浏览器

### 3. 手动启动（Mac/Linux）

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

然后打开浏览器访问 `http://localhost:8000`

## 使用说明

### 导入数据

1. 进入「导入管理」页面
2. 点击上传区域，选择 Excel 文件
3. 系统自动识别文件类型（库存表 / 报价表）
4. 预览解析结果，确认后点击「确认导入」
5. 同 SKU 自动覆盖更新，图片按文件日期优先取最新

### 矩阵看板

- 4 种矩阵模式：品类×价格、品类×库存、价格×库存、品类×状态
- 点击单元格跳转到对应商品列表
- 悬停查看缩略图预览

### 商品列表

- 卡片视图 / 表格视图切换
- 支持 SKU/名称搜索、品类筛选、价格区间、库存状态、产品状态筛选
- 分页展示（20/50/100 条/页）

### 商品详情

点击任意商品查看完整信息：
- 基础信息（SKU、名称、品类、状态）
- 价格信息（USD/RMB/限价/头程费）
- 库存信息（总库存/在途/各仓库明细）
- 产品属性（重量/材质/HS CODE/包装方式/特征码）
- 订单处理费（美东/美西，含费用说明）

## 文件结构

```
货盘查询系统/
├── 启动系统.bat              # Windows 双击启动
├── PRD-货盘查询系统.md       # 产品需求文档
├── README.md
├── backend/                  # 后端 (FastAPI)
│   ├── main.py               # 入口
│   ├── config.py             # 配置
│   ├── database.py           # 数据库
│   ├── models/               # 数据模型
│   ├── routers/              # API 路由
│   └── services/             # 业务逻辑（解析器等）
├── frontend/dist/            # 前端 (Vue3 + Ant Design)
│   └── index.html
├── data/                     # 数据目录
│   ├── cargo.db              # SQLite 数据库
│   └── uploads/images/       # 提取的图片
└── archives/                 # 导入归档
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Ant Design 样式 |
| 后端 | Python FastAPI |
| 数据库 | SQLite |
| Excel 解析 | openpyxl |
| 图片处理 | Pillow |

## 支持的 Excel 格式

### 库存表（文件名含"库存"）
- stock Sheet：多仓库分行（SKU/产品名/在途/库存/仓库）
- Sheet2：一行一个 SKU + 内嵌图片

### 报价表（文件名含"报价"）
- 品类 Sheet（软胶/功能软胶产品/飞机杯/阳具与水晶套）：纵向产品块格式
- 美东订单处理费 Sheet
- 美西订单处理费 Sheet
