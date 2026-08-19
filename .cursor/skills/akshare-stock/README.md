# A股分析 Skill

基于 [AKShare](https://github.com/akfamily/akshare) 的 A股实时分析工具，支持自然语言查询大盘、行情、资金流向、基本面、板块、基金、港股等。

## 功能

### 📈 实时大盘
- 上证、深证、创业板、沪深300、上证50 实时行情

### 📊 分时量能分析（新增！）
- 分时成交量分布（早盘/午盘/尾盘）
- 主力动向判断（抢筹/出货信号）
- 放量时段 TOP 10
- 涨停封单分析

### 🕯️ K线查询
- 支持日/周/月线
- 显示开盘、收盘、涨跌幅

### 📈 股价走势图（新增！）
- K线图直接发送到 QQ
- 支持所有 A 股股票

### 🚦 涨跌停统计
- 涨停/跌停数量统计
- 前10涨停股

### 💰 资金流向
- 个股资金流向（主力净流入）
- 市场资金流向（主力/超大单）
- 行业资金流向（净流入前10）

### 📊 基本面分析
- ROE、毛利率、净利率、资产负债率
- 每股收益、每股净资产
- 营收/净利润同比
- 存货周转率、应收账款周转天数

### 📌 个股综合信息
- 一键查询：实时行情 + 资金流向 + 基本面 + 近期涨跌停 + 研报

### 🧩 板块分析
- 行业板块涨跌排行
- 概念板块涨跌排行

### 🏆 股票推荐
- 全市场热门股票推荐
- 板块股票推荐（半导体、汽车、医药生物、银行、电力、证券、电子、锂电池、光伏设备、房地产、传媒、软件等）

### 📰 财经新闻
- 财经要闻（每条带链接，来源：东方财富财经首页，agent-browser 抓取）
- 个股研报（机构评级、盈利预测）

### 🏛️ 基金/债券
- 基金净值查询
- 可转债行情

### 🌍 港股
- 港股行情

### 📰 财经新闻
- 财经要闻（每条带链接，来源：东方财富财经首页，agent-browser 抓取）
- 个股研报（机构评级、盈利预测）

### 📈 股价走势图（K线图）
- 直接发送图片到 QQ
- 支持所有 A 股股票

### 📋 持仓管理
- 添加/更新/删除持仓
- 持仓盈亏分析（含分时量能）
- 查看当前持仓

## 环境要求

- Python 3.9+
- akshare: `pip install akshare`
- matplotlib: `pip install matplotlib`

## 安装

```bash
git clone https://github.com/molezzz/openclaw-stock-skill.git
cd openclaw-stock-skill
pip install akshare pandas
```

## 使用

```bash
# 实时大盘
python main.py --query "A股大盘"

# 分时量能分析（新增！）
python main.py --query "茅台量能分析"
python main.py --query "600519放量分析"
python main.py --query "宁德时代主力动向"

# K线查询
python main.py --query "茅台最近30日K线"
python main.py --query "600519周线"

# K线图（直接发图片）
python main.py --query "茅台走势图"
python main.py --query "宁德时代K线图"

# 涨跌停
python main.py --query "今日涨停"

# 资金流向
python main.py --query "茅台资金流向"
python main.py --query "市场资金流向"
python main.py --query "行业资金流向"

# 基本面
python main.py --query "茅台财务指标"
python main.py --query "宁德时代ROE"

# 个股综合信息
python main.py --query "茅台怎么样"
python main.py --query "宁德时代分析"

# 板块
python main.py --query "行业板块涨跌"
python main.py --query "概念板块涨跌"

# 股票推荐
python main.py --query "推荐股票"
python main.py --query "半导体股票推荐"
python main.py --query "医药股票推荐"
python main.py --query "汽车股票推荐"

# 基金/债券
python main.py --query "基金净值"
python main.py --query "可转债行情"

# 港股
python main.py --query "港股行情"

# 新闻
python main.py --query "财经新闻"
python main.py --query "宁德时代研报"

# K线图（直接发图片）
python main.py --query "茅台走势图"
python main.py --query "宁德时代K线图"
python main.py --query "长城汽车走势图"

# 持仓管理
python main.py --query "我的持仓"
python main.py --query "添加持仓 600519 --cost 1500 --qty 100"
python main.py --query "持仓分析"
```

## 支持的查询

| 类型 | 示例 |
|------|------|
| 大盘 | "A股大盘"、"上证指数" |
| 分时量能 | "茅台量能分析"、"600519放量分析"、"主力动向" |
| K线 | "茅台近30日K线"、"600519周线" |
| K线图 | "茅台走势图"、"宁德时代K线图" |
| 涨跌停 | "今日涨停"、"跌停统计" |
| 个股资金流 | "茅台资金流向" |
| 市场资金流 | "市场资金流向" |
| 行业资金流 | "行业资金流向" |
| 基本面 | "茅台财务指标"、"ROE" |
| 个股综合 | "茅台怎么样"、"宁德时代分析" |
| 行业板块 | "行业板块涨跌" |
| 概念板块 | "概念板块涨跌" |
| 股票推荐 | "推荐股票"、"半导体股票推荐" |
| 基金 | "基金净值" |
| 可转债 | "可转债行情" |
| 港股 | "港股行情" |
| 财经新闻 | "财经新闻" |
| 个股研报 | "宁德时代研报" |
| K线图 | "茅台走势图"、"宁德时代K线图" |
| 持仓管理 | "我的持仓"、"添加持仓 600519"、"持仓分析" |

## 数据来源

- [AKShare](https://github.com/akfamily/akshare) - 新浪财经/东方财富

**免责声明**：数据仅供参考，不构成投资建议。

## License

MIT
