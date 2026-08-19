# StockSight Examples

Use these examples as formatting references, not as market recommendations.

## Standard Multi-Stock Report

```markdown
# 📰 2026-05-18 市场异动分析报告

> 📰 一句话总结：今日3只股票中1只触发异动信号，恒生电子量比偏离需重点关注

## 📊 市场脉冲

| <kbd>覆盖标的</kbd> | <kbd>异动标的</kbd> | <kbd>最高风险</kbd> | <kbd>数据源</kbd> |
|:---:|:---:|:---:|:---:|
| 3 只 | 1 只 | 🔶 警告 ▰▰▰▱▱ | 腾讯财经 + 新浪财经 |

## 📊 风险可视化

| <kbd>关注</kbd> | <kbd>警告</kbd> | <kbd>危险</kbd> |
|:---:|:---:|:---:|
| 0 ▱▱▱▱▱ | 1 ▰▰▰▰▰ | 0 ▱▱▱▱▱ |

### 信号构成

| 信号类型 | 数量 | 最高等级 | 分布 |
|:---|---:|:---|:---|
| <kbd>量比偏离</kbd> | 1 | 🔶 警告 | ▰▰▰▰▰ |

## 📋 异动股票列表

| 股票 | 现价 | 涨跌幅 | 量比 | 异动信号 |
|:---|---:|---:|---:|:---|
| 600570 恒生电子 [A] | RMB 27.93 | +3.2% 📈 | 2.15 | <kbd>量比偏离</kbd> ▰▰▰▱▱ 🔥 |
| 00700 腾讯控股 [H] | HKD 380.00 | +1.5% 📈 | — | — |
| AAPL 苹果 [U] | USD 192.3456 | +0.8% 📈 | — | — |

## ⚠️ 风险提示

| 股票 | 风险类型 | 偏离说明 | 等级 |
|:---|:---|:---|:---|
| 600570 | <kbd>量比偏离</kbd> | 量比2.15 vs 均值1.12，为均值的1.9倍（偏离度 1.9x） | 🔶 ▰▰▰▱▱ |

## 🎯 操作建议

🟡 600570 恒生电子：异动特征明显，建议确认方向后再操作
🟢 00700 腾讯控股：量价正常，按既定策略执行
🟢 AAPL 苹果：量价正常，按既定策略执行

📡 数据来源：腾讯财经 + 新浪财经 | 🕐 2026-05-18 10:00
```

## Detailed Single-Stock Report

```markdown
# 🔍 恒生电子 (600570) 深度分析报告

> 📰 一句话总结：`[A]` 恒生电子今日收RMB 27.93，涨跌幅+3.2% 📈，量比偏离（偏离度 1.9x）

## 📊 核心看板

| <kbd>当前价</kbd> | <kbd>涨跌幅</kbd> | <kbd>量比</kbd> | <kbd>换手率</kbd> | <kbd>最高风险</kbd> |
|:---:|:---:|:---:|:---:|:---:|
| RMB 27.93 | +3.2% 📈 | 2.15 | 5.3% | 🔶 警告 ▰▰▰▱▱ |

## 📊 风险可视化

| <kbd>关注</kbd> | <kbd>警告</kbd> | <kbd>危险</kbd> |
|:---:|:---:|:---:|
| 0 ▱▱▱▱▱ | 1 ▰▰▰▰▰ | 0 ▱▱▱▱▱ |

### 信号构成

| 信号类型 | 数量 | 最高等级 | 分布 |
|:---|---:|:---|:---|
| <kbd>量比偏离</kbd> | 1 | 🔶 警告 | ▰▰▰▰▰ |

## 💰 价格概览

| 指标 | 数值 |
|:---|---:|
| 当前价 | RMB 27.93 |
| 开盘价 | RMB 27.50 |
| 最高价 | RMB 28.20 |
| 最低价 | RMB 27.30 |
| 昨收价 | RMB 27.05 |
| 振幅 | 3.3% |

## 📊 量价指标

- 📐 涨跌幅：+3.2% 📈
- 💰 当前价：RMB 27.93
- 📊 成交量：23.4万手
- 📊 成交额：RMB 6,534万
- ⚡ 量比：2.15
- 🔄 换手率：5.3%

## 🔍 异动分析

### 🔶 量比偏离
<kbd>🔶 警告</kbd> ▰▰▰▱▱

量比2.15 vs 均值1.12，为均值的1.9倍（偏离度 1.9x）。

可能原因：
- 近期有重大消息或财报预期
- 主力资金异动
- 板块内部轮动

## ⚠️ 风险提示

🔶 **量比偏离**
量比2.15 vs 均值1.12，为均值的1.9倍（偏离度 1.9x）。

## 🎯 操作建议

🟡 **持有/观望**

- 当前价：RMB 27.93
- 止损参考：RMB 26.53（-5%）
- 目标参考：RMB 29.49（+5.6%）

> 以上参考数值基于技术指标计算，不构成投资建议。

## Technical Indicator Example

Detailed single-stock reports may add:

```markdown
## 📈 技术指标辅助

| 指标 | 状态 |
|:---|:---|
| MACD | 偏空（DIF 0.1600 / DEA 0.1800 / 柱 -0.0400） |
| RSI14 | 74.20（超买区） |
| 近期信号 | 超买：RSI 高于 70，需警惕追高风险。 |
```

HTML detailed reports render the same technical payload as a MACD chart, RSI range strip, and technical signal cards.

📡 数据来源：腾讯财经 | 🕐 2026-05-18 10:00
```

## News-Enabled Report

```markdown
<details>
<summary>🗞️ 相关资讯</summary>

| 来源 | 标题 | 时间 |
|:---|:---|:---|
| 新浪财经 | 恒生电子成交活跃 | 05-18 10:00 |
| 雪球 | 软件板块盘中走强 | 1小时前 |

</details>
```

## HTML Report

Use `render_html_report(data, mode="detailed")` for a self-contained browser page. The HTML output includes built-in CSS cards, risk distribution bars, and `conic-gradient` pie charts; it does not require JavaScript or external assets.
