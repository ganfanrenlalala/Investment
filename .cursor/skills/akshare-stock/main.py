#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from typing import Any, Dict

from adapters import AkshareAdapter
from formatter import render_output
from router import (
    DERIVATIVES,
    FUND_BOND,
    FUNDAMENTAL,
    HK_US_MARKET,
    INDEX_REALTIME,
    INTRADAY_ANALYSIS,
    KLINE_ANALYSIS,
    KLINE_CHART,
    LIMIT_STATS,
    MARGIN_LHB,
    MONEY_FLOW,
    NEWS,
    RESEARCH_REPORT,
    SECTOR_ANALYSIS,
    STOCK_OVERVIEW,
    STOCK_PICK,
    VOLUME_ANALYSIS,
    HELP,
    PORTFOLIO,
    parse_query,
)


def dispatch(intent_obj, adapter: AkshareAdapter) -> Dict[str, Any]:
    if intent_obj.intent == INDEX_REALTIME:
        return adapter.index_spot(top_n=300)

    if intent_obj.intent == KLINE_ANALYSIS:
        top_n = intent_obj.top_n or 10
        symbol = intent_obj.symbol or "000001"
        period = intent_obj.period or "daily"
        return adapter.stock_kline(symbol=symbol, period=period, top_n=top_n)

    if intent_obj.intent == KLINE_CHART:
        symbol = intent_obj.symbol or "000001"
        period = intent_obj.period or "daily"
        days = intent_obj.top_n or 30
        return adapter.stock_chart(symbol=symbol, period=period, days=days)

    if intent_obj.intent == INTRADAY_ANALYSIS:
        top_n = intent_obj.top_n or 30
        symbol = intent_obj.symbol or "000001"
        period = intent_obj.period if intent_obj.period in {"1", "5", "15", "30", "60"} else "1"
        return adapter.stock_intraday(symbol=symbol, period=period, top_n=top_n)

    if intent_obj.intent == VOLUME_ANALYSIS:
        # 调用 a-stock-analysis 脚本进行量能分析
        symbol = intent_obj.symbol or "000001"
        import subprocess
        import os
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "a-stock-analysis", "scripts", "analyze.py")
        result = subprocess.run(
            ["python3", script_path, symbol, "--minute"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return {"ok": True, "text": result.stdout}
        else:
            return {"ok": False, "error": result.stderr}

    if intent_obj.intent == LIMIT_STATS:
        top_n = intent_obj.top_n or 20
        return adapter.limit_pool(date=intent_obj.date, top_n=top_n)

    if intent_obj.intent == STOCK_OVERVIEW:
        symbol = intent_obj.symbol
        if not symbol:
            return {
                "ok": False,
                "error": "请输入股票代码或名称，如：茅台怎么样、宁德时代分析",
                "intent": "STOCK_OVERVIEW",
            }
        return adapter.stock_overview(symbol=symbol)

    if intent_obj.intent == MONEY_FLOW:
        top_n = intent_obj.top_n or 10
        query = intent_obj.query or ""
        if any(k in query for k in ["北向", "南向", "东向", "市场资金", "大盘资金"]):
            return adapter.market_money_flow(top_n=top_n, date=intent_obj.date)
        if any(k in query for k in ["行业资金", "板块资金", "行业流入", "板块流入"]):
            return adapter.sector_money_flow(top_n=top_n)
        symbol = intent_obj.symbol
        if not symbol:
            return {
                "ok": False,
                "error": "请输入股票代码或名称，如：茅台资金流向、600519资金流",
                "intent": "MONEY_FLOW",
            }
        return adapter.money_flow(symbol=symbol, top_n=top_n)

    if intent_obj.intent == FUNDAMENTAL:
        top_n = intent_obj.top_n or 20
        symbol = intent_obj.symbol
        if not symbol:
            return {
                "ok": False,
                "error": "请输入股票代码或名称，如：茅台财务指标、600519基本面",
                "intent": "FUNDAMENTAL",
            }
        return adapter.fundamental(symbol=symbol, top_n=top_n)

    if intent_obj.intent == MARGIN_LHB:
        top_n = intent_obj.top_n or 10
        return adapter.margin_lhb(symbol=intent_obj.symbol, date=intent_obj.date, top_n=top_n)

    if intent_obj.intent == NEWS:
        top_n = min(intent_obj.top_n or 10, 10)
        return adapter.news(top_n=top_n)

    if intent_obj.intent == RESEARCH_REPORT:
        top_n = min(intent_obj.top_n or 10, 10)
        symbol = intent_obj.symbol
        if not symbol:
            return {
                "ok": False,
                "error": "请输入股票代码或名称，如：宁德时代研报、300750机构评级",
                "intent": "RESEARCH_REPORT",
            }
        return adapter.research_report(symbol=symbol, top_n=top_n)

    if intent_obj.intent == STOCK_PICK:
        query = intent_obj.query or ""
        # 提取板块关键词
        sector = None
        sector_keywords = [
            "半导体", "电子", "汽车", "医药生物", "医药",
            "银行", "保险", "证券", "金融",
            "房地产", "地产", "电力", "传媒",
            "锂电池", "电池", "光伏", "光伏设备",
            "软件", "军工", "食品", "饮料", "白酒", "家电", "纺织"
        ]
        for kw in sector_keywords:
            if kw in query:
                sector = kw
                break
        return adapter.stock_pick(top_n=5, sector=sector)

    if intent_obj.intent == SECTOR_ANALYSIS:
        top_n = intent_obj.top_n or 10
        query = intent_obj.query or ""
        if any(k in query for k in ["概念", "题材"]):
            return adapter.sector_analysis(sector_type="concept", top_n=top_n)
        return adapter.sector_analysis(sector_type="industry", top_n=top_n)

    if intent_obj.intent == FUND_BOND:
        top_n = intent_obj.top_n or 10
        query = (intent_obj.query or "").lower()
        scope = "bond" if any(k in query for k in ["可转债", "转债", "债"]) else "fund"
        return adapter.fund_bond(scope=scope, symbol=intent_obj.symbol, top_n=top_n)

    if intent_obj.intent == HK_US_MARKET:
        top_n = intent_obj.top_n or 10
        query = (intent_obj.query or "").lower()
        us_tokens = ["美股", "nasdaq", "dow", "道琼斯", "标普", "sp500", "s&p", "纳指", "us"]
        market = "us" if any(token in query for token in us_tokens) else "hk"
        return adapter.hk_us_market(market=market, top_n=top_n, symbol=intent_obj.symbol)

    if intent_obj.intent == DERIVATIVES:
        top_n = intent_obj.top_n or 10
        query = intent_obj.query or ""
        scope = "options" if any(k in query for k in ["期权", "option", "Option", "OPTIONS"]) else "futures"
        return adapter.derivatives(scope=scope, symbol=intent_obj.symbol, top_n=top_n)

    if intent_obj.intent == HELP:
        return {
            "ok": True,
            "source": "help",
            "text": """📈 A股分析 Skill 使用指南

| 类型 | 示例 |
|------|------|
| 大盘 | A股大盘、上证指数 |
| 分时量能 | 茅台量能分析、600519放量分析 |
| K线 | 茅台近30日K线、600519周线 |
| K线图 | 茅台走势图、宁德时代K线图 |
| 涨跌停 | 今日涨停、跌停统计 |
| 资金流 | 茅台资金流向、市场资金流向 |
| 基本面 | 茅台财务指标、ROE |
| 个股综合 | 茅台怎么样、宁德时代分析 |
| 板块 | 行业板块涨跌、概念板块涨跌 |
| 股票推荐 | 推荐股票、半导体股票推荐 |
| 基金/可转债 | 基金净值、可转债行情 |
| 港股 | 港股行情 |
| 新闻 | 财经新闻、宁德时代研报 |
| 持仓管理 | 我的持仓、添加持仓 600519 --cost 10.5 --qty 1000、持仓分析 |

直接发给我就能查~"""
        }

    if intent_obj.intent == PORTFOLIO:
        import subprocess
        import os
        portfolio_script = os.path.join(os.path.dirname(__file__), "..", "a-stock-analysis", "scripts", "portfolio.py")
        
        query = intent_obj.query or ""
        
        # 解析持仓命令
        if "添加" in query or "add" in query.lower():
            # 提取代码、成本、数量
            import re
            code_match = re.search(r"\b(\d{6})\b", query)
            cost_match = re.search(r"--?cost\s*(\d+\.?\d*)", query)
            qty_match = re.search(r"--?qty\s*(\d+)", query) or re.search(r"数量\s*(\d+)", query)
            
            if code_match and cost_match and qty_match:
                code = code_match.group(1)
                cost = cost_match.group(1)
                qty = qty_match.group(1)
                result = subprocess.run(
                    ["python3", portfolio_script, "add", code, "--cost", cost, "--qty", qty],
                    capture_output=True, text=True, timeout=10
                )
                return {"ok": True, "source": "portfolio", "text": result.stdout or "已添加持仓"}
            else:
                return {"ok": False, "error": "请输入：添加持仓 代码 --cost 成本价 --qty 数量\n例如：添加持仓 600519 --cost 10.5 --qty 1000"}
        
        elif "分析" in query:
            result = subprocess.run(
                ["python3", portfolio_script, "analyze"],
                capture_output=True, text=True, timeout=60
            )
            return {"ok": True, "source": "portfolio", "text": result.stdout or "暂无持仓"}
        
        elif "删除" in query or "移除" in query:
            import re
            code_match = re.search(r"\b(\d{6})\b", query)
            if code_match:
                code = code_match.group(1)
                result = subprocess.run(
                    ["python3", portfolio_script, "remove", code],
                    capture_output=True, text=True, timeout=10
                )
                return {"ok": True, "source": "portfolio", "text": result.stdout or "已删除"}
            else:
                return {"ok": False, "error": "请输入要删除的股票代码"}
        
        else:
            # 显示持仓
            result = subprocess.run(
                ["python3", portfolio_script, "show"],
                capture_output=True, text=True, timeout=10
            )
            return {"ok": True, "source": "portfolio", "text": result.stdout or "暂无持仓"}

    return {
        "ok": True,
        "source": "framework",
        "message": "该意图已识别，当前阶段先返回基础占位结果",
        "intent": intent_obj.intent,
        "parsed": {
            "symbol": intent_obj.symbol,
            "date": intent_obj.date,
            "period": intent_obj.period,
            "top_n": intent_obj.top_n,
        },
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="A股分析 Skill 基础框架")
    parser.add_argument("--query", required=True, help="自然语言请求，例如：分析 600519 最近 30 天 K线")
    parser.add_argument("--platform", default="qq", choices=["qq", "telegram"], help="输出平台")
    args = parser.parse_args()

    intent_obj = parse_query(args.query)
    adapter = AkshareAdapter()
    result = dispatch(intent_obj, adapter)
    output = render_output(intent_obj, result, platform=args.platform)
    print(output)


if __name__ == "__main__":
    main()
