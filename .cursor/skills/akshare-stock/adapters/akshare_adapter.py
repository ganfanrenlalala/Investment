#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from io import StringIO
import os
from typing import Any, Dict, Optional


class AkshareAdapter:
    def __init__(self) -> None:
        self._ak = None
        self._import_error = None
        try:
            import akshare as ak  # type: ignore

            self._ak = ak
        except Exception as exc:
            self._import_error = str(exc)

    def _wrap(self, fn_name: str, **payload: Any) -> Dict[str, Any]:
        return {
            "ok": True,
            "source": "akshare",
            "api": fn_name,
            "data": payload,
        }

    def _error(self, fn_name: str, message: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "source": "akshare",
            "api": fn_name,
            "error": message,
        }

    def _ready_or_error(self, fn_name: str) -> Optional[Dict[str, Any]]:
        if self._ak is None:
            return self._error(fn_name, f"akshare import failed: {self._import_error}")
        return None

    def _to_records(self, data: Any, top_n: int = 10) -> Any:
        if data is None:
            return []

        if hasattr(data, "head") and hasattr(data, "to_dict"):
            try:
                if top_n and top_n > 0:
                    return data.head(top_n).to_dict(orient="records")
                return data.to_dict(orient="records")
            except Exception:
                return str(data)

        return data

    def _data_len(self, data: Any) -> int:
        try:
            return int(len(data))
        except Exception:
            return 0

    def _normalize_trade_date(self, value: Optional[str]) -> str:
        if not value or value in {"today", "今日", "今天"}:
            return datetime.now().strftime("%Y%m%d")
        if value in {"yesterday", "昨日", "昨天"}:
            return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        return str(value).replace("-", "").replace("/", "")

    def _clean_symbol(self, symbol: Optional[str]) -> str:
        if not symbol:
            return ""
        return str(symbol).lower().replace("sz", "").replace("sh", "").replace("bj", "")

    def _market_from_symbol(self, symbol: str) -> str:
        market = "sh"
        if symbol.startswith(("0", "3")):
            market = "sz"
        elif symbol.startswith(("8", "4")):
            market = "bj"
        return market

    def _filter_records_by_symbol(self, records: list[dict], symbol: str) -> list[dict]:
        if not symbol:
            return records

        key_pool = ["代码", "股票代码", "证券代码", "symbol", "代码简称"]
        filtered = []
        for row in records:
            if not isinstance(row, dict):
                continue
            for key in key_pool:
                val = row.get(key)
                if val is not None and symbol in str(val):
                    filtered.append(row)
                    break
        return filtered

    def _call_api_candidates(self, candidates: list[tuple[str, list[dict]]]) -> tuple[Optional[str], Any, str]:
        errors = []

        for fn_name, kwargs_list in candidates:
            func = getattr(self._ak, fn_name, None)
            if func is None:
                continue

            args_pool = kwargs_list or [{}]
            for kwargs in args_pool:
                try:
                    result = func(**kwargs)
                    return fn_name, result, ""
                except Exception as exc:
                    errors.append(f"{fn_name}({kwargs}): {exc}")

        return None, None, "; ".join(errors) if errors else "no callable api found"

    def index_spot(self, top_n: int = 300) -> Dict[str, Any]:
        primary_fn = "stock_zh_index_spot_sina"
        err = self._ready_or_error(primary_fn)
        if err:
            return err

        try:
            df = self._ak.stock_zh_index_spot_sina()
            return self._wrap(primary_fn, items=self._to_records(df, top_n=top_n))
        except Exception as exc:
            fallback_fn = "stock_zh_index_spot_em"
            try:
                df = self._ak.stock_zh_index_spot_em()
                return self._wrap(fallback_fn, items=self._to_records(df, top_n=top_n))
            except Exception as fallback_exc:
                return self._error(primary_fn, f"sina failed: {exc}; em failed: {fallback_exc}")

    def stock_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        top_n: int = 60,
    ) -> Dict[str, Any]:
        fn_name = "stock_zh_a_hist"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        if not start_date:
            end_dt = datetime.now()
            if period == "weekly":
                days = top_n * 7
            elif period == "monthly":
                days = top_n * 30
            else:
                days = top_n
            start_dt = end_dt - timedelta(days=days + 50)
            start = start_dt.strftime("%Y%m%d")
        else:
            start = start_date.replace("-", "")

        end = self._normalize_trade_date(end_date)

        try:
            df = self._ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start,
                end_date=end,
                adjust="",
            )
            if hasattr(df, "iloc"):
                df = df.iloc[::-1]
            return self._wrap(
                fn_name,
                symbol=symbol,
                period=period,
                start_date=start,
                end_date=end,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            return self._error(fn_name, str(exc))

    def stock_chart(self, symbol: str, period: str = "daily", days: int = 30) -> Dict[str, Any]:
        """生成股票K线图"""
        fn_name = "stock_chart"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            
            # 设置中文字体
            font_paths = [
                '/Library/Fonts/Microsoft/SimHei.ttf',
                '/Library/Fonts/Microsoft/Microsoft Yahei.ttf',
                '/Users/molezz/Library/Fonts/msyh.ttf',
                '/System/Library/Fonts/STHeiti Medium.ttc',
            ]
            found_font = None
            for fp in font_paths:
                if os.path.exists(fp):
                    found_font = fp
                    break
            if found_font:
                fm.fontManager.addfont(found_font)
                prop = fm.FontProperties(fname=found_font)
                plt.rcParams['font.sans-serif'] = [prop.get_name()]
                plt.rcParams['axes.unicode_minus'] = False
            
            # 计算日期
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days+30)).strftime("%Y%m%d")
            
            # 获取数据
            df = self._ak.stock_zh_a_hist(symbol=symbol, period=period, start_date=start_date, end_date=end_date)
            if df is None or len(df) == 0:
                return self._error(fn_name, "无法获取数据")
            
            # 取最近的数据
            df = df.tail(days)
            
            # 获取股票名称
            name = symbol
            try:
                info = self._ak.stock_individual_info_em(symbol=symbol)
                if info is not None and len(info) > 0:
                    # 尝试获取"股票简称"
                    name_row = info[info.get('item', '') == '股票简称']
                    if len(name_row) > 0:
                        name = name_row.iloc[0].get('value', symbol)
                    else:
                        # 如果没有简称，用代码
                        name = symbol
            except:
                pass
            
            # 绘图
            plt.figure(figsize=(10, 6))
            plt.plot(df['日期'], df['收盘'], 'b-', linewidth=1.5)
            plt.title(f'{name}({symbol}) 近期股价走势', fontsize=14)
            plt.xlabel('日期')
            plt.ylabel('收盘价 (元)')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # 保存
            chart_dir = "/tmp/stock_charts"
            os.makedirs(chart_dir, exist_ok=True)
            filepath = f"{chart_dir}/{symbol}.png"
            plt.savefig(filepath, dpi=120)
            plt.close()
            
            return {
                "ok": True,
                "data": {
                    "symbol": symbol,
                    "name": name,
                    "filepath": filepath,
                    "period": period,
                    "days": days,
                },
                "image_path": filepath
            }
        except Exception as exc:
            return self._error(fn_name, str(exc))

    def stock_intraday(self, symbol: str, period: Optional[str] = None, top_n: int = 30) -> Dict[str, Any]:
        fn_name = "stock_intraday"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        minute_error = None
        minute_period = period if period in {"1", "5", "15", "30", "60"} else "1"

        try:
            df = self._ak.stock_zh_a_minute(symbol=symbol, period=minute_period, adjust="")
            if hasattr(df, "iloc"):
                df = df.iloc[::-1]
            return self._wrap(
                "stock_zh_a_minute",
                symbol=symbol,
                period=minute_period,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            minute_error = str(exc)

        try:
            df = self._ak.stock_intraday_em(symbol=symbol)
            return self._wrap(
                "stock_intraday_em",
                symbol=symbol,
                period="tick",
                fallback=minute_error,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            if minute_error:
                return self._error(fn_name, f"minute failed: {minute_error}; tick failed: {exc}")
            return self._error(fn_name, str(exc))

    def limit_pool(self, date: Optional[str] = None, top_n: int = 50) -> Dict[str, Any]:
        fn_name = "stock_zt_pool_em"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        trade_date = self._normalize_trade_date(date)

        try:
            up_df = self._ak.stock_zt_pool_em(date=trade_date)
            up_count = self._data_len(up_df)
            up_items = self._to_records(up_df, top_n=top_n)

            down_count = 0
            down_items: Any = []
            down_api = None
            down_errors = []

            for api_name in ["stock_zt_pool_dtgc_em", "stock_dt_pool_em"]:
                func = getattr(self._ak, api_name, None)
                if func is None:
                    continue
                try:
                    down_df = func(date=trade_date)
                    down_count = self._data_len(down_df)
                    down_items = self._to_records(down_df, top_n=top_n)
                    down_api = api_name
                    break
                except Exception as exc:
                    down_errors.append(f"{api_name}: {exc}")

            payload: Dict[str, Any] = {
                "date": trade_date,
                "up_count": up_count,
                "down_count": down_count,
                "up_items": up_items,
                "down_items": down_items,
                "items": up_items,
            }
            if down_api:
                payload["down_api"] = down_api
            if down_errors and not down_api:
                payload["down_error"] = "; ".join(down_errors)

            return self._wrap(fn_name, **payload)
        except Exception as exc:
            return self._error(fn_name, str(exc))

    def news(self, top_n: int = 10) -> Dict[str, Any]:
        """财经要闻

        旧实现依赖 akshare.stock_news_em（东财接口），在部分环境下可能长期返回历史日期。
        这里改为用 agent-browser 抓取「东方财富财经首页」的最新要闻链接。

        返回字段尽量与原 formatter 兼容：新闻标题/新闻链接/发布时间/文章来源。
        """

        fn_name = "eastmoney_finance_home"

        # 1) Primary: agent-browser scrape
        try:
            import json
            import subprocess

            n = max(1, min(int(top_n or 10), 20))

            # 打开财经首页（复用默认 session，执行很快）
            subprocess.run(
                ["agent-browser", "open", "https://finance.eastmoney.com/"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            js = r"""
(() => {
  const now = new Date();
  const pad2 = (x) => String(x).padStart(2, '0');
  const today = `${now.getFullYear()}-${pad2(now.getMonth()+1)}-${pad2(now.getDate())}`;
  const ymd = `${now.getFullYear()}${pad2(now.getMonth()+1)}${pad2(now.getDate())}`;
  const ymdYesterday = (() => {
    const d = new Date(now.getTime() - 24*3600*1000);
    return `${d.getFullYear()}${pad2(d.getMonth()+1)}${pad2(d.getDate())}`;
  })();

  const links = Array.from(document.querySelectorAll('a[href]'));
  const items = [];
  const seen = new Set();

  for (const a of links) {
    const href = a.href || '';
    if (!href.includes('finance.eastmoney.com/a/')) continue;
    // 排除频道页（/a/cxxxx.html）
    if (/\/a\/c\w+\.html/.test(href)) continue;

    // 只保留今天/昨天的文章（避免首页混入更早的深链）
    const dm = href.match(/\/a\/(\d{8})\d+\.html/);
    if (!dm) continue;
    const d8 = dm[1];
    if (!(d8 === ymd || d8 === ymdYesterday)) continue;

    const title = (a.textContent || '').replace(/\s+/g, ' ').trim();
    if (!title || title.length < 6) continue;
    if (seen.has(href)) continue;
    seen.add(href);

    const publish = `${d8.slice(0,4)}-${d8.slice(4,6)}-${d8.slice(6,8)}`;

    items.push({
      '新闻标题': title,
      '新闻链接': href,
      '发布时间': publish || today,
      '文章来源': '东方财富网'
    });

    if (items.length >= 80) break;
  }

  return JSON.stringify(items);
})();
"""

            p = subprocess.run(
                ["agent-browser", "eval", js],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            if p.returncode == 0 and p.stdout:
                raw = p.stdout.strip()
                # agent-browser 可能会把 JSON 字符串再包一层引号，这里统一处理
                # agent-browser 的输出有两种形态：
                # 1) 直接 JSON 数组：[{...},{...}]
                # 2) JSON 字符串（外层带引号）："[{...},{...}]"
                data = json.loads(raw)
                if isinstance(data, str):
                    data = json.loads(data)

                items = (data or [])[:n]
                return self._wrap(fn_name, items=items)

            # fallthrough to error
            err_msg = (p.stderr or p.stdout or "agent-browser eval failed").strip()
            return self._error(fn_name, err_msg)

        except Exception as exc:
            return self._error(fn_name, str(exc))

    def research_report(self, symbol: str, top_n: int = 10) -> Dict[str, Any]:
        fn_name = "stock_research_report_em"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        clean_symbol = self._clean_symbol(symbol)
        if not clean_symbol:
            return self._error(fn_name, "symbol is required")

        try:
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                df = self._ak.stock_research_report_em(symbol=clean_symbol)
            items = self._to_records(df, top_n=max(1, min(top_n, 10)))
            return self._wrap(fn_name, symbol=clean_symbol, items=items)
        except Exception as exc:
            return self._error(fn_name, str(exc))

    def money_flow(self, symbol: str, top_n: int = 30) -> Dict[str, Any]:
        fn_name = "stock_individual_fund_flow"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        clean_symbol = self._clean_symbol(symbol)
        market = self._market_from_symbol(clean_symbol)

        try:
            df = self._ak.stock_individual_fund_flow(stock=clean_symbol, market=market)
            if hasattr(df, "iloc"):
                df = df.iloc[::-1]
            return self._wrap(
                fn_name,
                scope="individual",
                symbol=clean_symbol,
                market=market,
                items=self._to_records(df, top_n=top_n),
            )
        except Exception as exc:
            return self._error(fn_name, str(exc))

    def market_money_flow(self, top_n: int = 20, date: Optional[str] = None) -> Dict[str, Any]:
        fn_name = "market_money_flow"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        trade_date = self._normalize_trade_date(date)

        candidates = [
            ("stock_market_fund_flow", [{}]),
            ("stock_hsgt_fund_flow_summary_em", [{}]),
            ("stock_hsgt_north_net_flow_in_em", [{}]),
            ("stock_hsgt_hist_em", [{"symbol": "北向资金"}, {"symbol": "沪股通"}, {"symbol": "深股通"}]),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        if hasattr(df, "iloc"):
            try:
                df = df.iloc[::-1]
            except Exception:
                pass

        return self._wrap(
            api_name or fn_name,
            scope="market",
            date=trade_date,
            items=self._to_records(df, top_n=top_n),
        )

    def sector_money_flow(self, top_n: int = 20) -> Dict[str, Any]:
        fn_name = "sector_money_flow"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        candidates = [
            (
                "stock_sector_fund_flow_rank",
                [
                    {"indicator": "今日", "sector_type": "行业资金流"},
                    {"indicator": "5日", "sector_type": "行业资金流"},
                    {"indicator": "10日", "sector_type": "行业资金流"},
                    {"symbol": "今日", "sector_type": "行业资金流"},
                    {"sector_type": "行业资金流"},
                ],
            ),
            ("stock_fund_flow_industry", [{"symbol": "今日"}, {"symbol": "即时"}, {}]),
            ("stock_sector_fund_flow_summary", [{"sector_type": "行业资金流"}, {}]),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        return self._wrap(
            api_name or fn_name,
            scope="sector",
            items=self._to_records(df, top_n=top_n),
        )

    def fundamental(self, symbol: str, top_n: int = 20) -> Dict[str, Any]:
        fn_name = "fundamental"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        clean_symbol = self._clean_symbol(symbol)

        candidates = [
            (
                "stock_financial_abstract_ths",
                [
                    {"symbol": clean_symbol, "indicator": "按报告期"},
                    {"symbol": clean_symbol, "indicator": "按单季度"},
                    {"symbol": clean_symbol},
                    {"stock": clean_symbol, "indicator": "按报告期"},
                    {"stock": clean_symbol},
                ],
            ),
            (
                "stock_financial_analysis_indicator",
                [
                    {"symbol": clean_symbol},
                    {"stock": clean_symbol},
                ],
            ),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        if hasattr(df, "iloc"):
            try:
                df = df.iloc[::-1]
            except Exception:
                pass

        items = self._to_records(df, top_n=top_n)
        latest = items[0] if isinstance(items, list) and items else {}

        return self._wrap(
            api_name or fn_name,
            scope="fundamental",
            symbol=clean_symbol,
            latest=latest,
            items=items,
        )

    def stock_overview(self, symbol: str) -> Dict[str, Any]:
        fn_name = "stock_overview"
        clean_symbol = self._clean_symbol(symbol)

        if not clean_symbol:
            return self._error(fn_name, "symbol is required")

        sections: Dict[str, Any] = {
            "realtime": {"ok": False, "error": "not called"},
            "money_flow": {"ok": False, "error": "not called"},
            "fundamental": {"ok": False, "error": "not called"},
            "limit_stats": {"ok": False, "error": "not called"},
            "research_report": {"ok": False, "error": "not called"},
        }

        # 1) 实时行情（优先使用分时最新）
        try:
            rt_res = self.stock_intraday(symbol=clean_symbol, period="1", top_n=1)
            if rt_res.get("ok"):
                rt_items = rt_res.get("data", {}).get("items", [])
                latest = rt_items[0] if isinstance(rt_items, list) and rt_items else {}
                sections["realtime"] = {
                    "ok": True,
                    "api": rt_res.get("api"),
                    "latest": latest,
                }
            else:
                sections["realtime"] = {
                    "ok": False,
                    "api": rt_res.get("api"),
                    "error": rt_res.get("error", "unknown error"),
                }
        except Exception as exc:
            sections["realtime"] = {"ok": False, "error": str(exc)}

        # 2) 个股资金流
        try:
            flow_res = self.money_flow(symbol=clean_symbol, top_n=10)
            if flow_res.get("ok"):
                flow_data = flow_res.get("data", {})
                flow_items = flow_data.get("items", [])
                sections["money_flow"] = {
                    "ok": True,
                    "api": flow_res.get("api"),
                    "latest": flow_items[0] if isinstance(flow_items, list) and flow_items else {},
                    "items": flow_items,
                }
            else:
                sections["money_flow"] = {
                    "ok": False,
                    "api": flow_res.get("api"),
                    "error": flow_res.get("error", "unknown error"),
                }
        except Exception as exc:
            sections["money_flow"] = {"ok": False, "error": str(exc)}

        # 3) 基本面摘要
        try:
            fundamental_res = self.fundamental(symbol=clean_symbol, top_n=10)
            if fundamental_res.get("ok"):
                fundamental_data = fundamental_res.get("data", {})
                sections["fundamental"] = {
                    "ok": True,
                    "api": fundamental_res.get("api"),
                    "latest": fundamental_data.get("latest") or {},
                    "items": fundamental_data.get("items") or [],
                }
            else:
                sections["fundamental"] = {
                    "ok": False,
                    "api": fundamental_res.get("api"),
                    "error": fundamental_res.get("error", "unknown error"),
                }
        except Exception as exc:
            sections["fundamental"] = {"ok": False, "error": str(exc)}

        # 4) 近期涨跌停（从近10日池中统计该股出现次数）
        limit_up_count = 0
        limit_down_count = 0
        last_date = None
        limit_errors = []

        code_keys = ["代码", "股票代码", "证券代码", "symbol"]
        name_keys = ["名称", "股票简称", "证券简称", "简称"]

        for offset in range(0, 10):
            trade_date = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
            try:
                limit_res = self.limit_pool(date=trade_date, top_n=300)
                if not limit_res.get("ok"):
                    limit_errors.append(f"{trade_date}: {limit_res.get('error', 'unknown error')}")
                    continue

                payload = limit_res.get("data", {})
                up_items = payload.get("up_items") or payload.get("items") or []
                down_items = payload.get("down_items") or []
                if last_date is None:
                    last_date = payload.get("date") or trade_date

                def _is_target(row: Any) -> bool:
                    if not isinstance(row, dict):
                        return False
                    for key in code_keys:
                        value = row.get(key)
                        if value is not None and clean_symbol == self._clean_symbol(str(value)):
                            return True
                    for key in name_keys:
                        value = row.get(key)
                        if value is not None and str(value) in str(symbol):
                            return True
                    return False

                limit_up_count += sum(1 for row in up_items if _is_target(row))
                limit_down_count += sum(1 for row in down_items if _is_target(row))
            except Exception as exc:
                limit_errors.append(f"{trade_date}: {exc}")

        sections["limit_stats"] = {
            "ok": True,
            "days": 10,
            "date": last_date,
            "up_count": limit_up_count,
            "down_count": limit_down_count,
            "error": "; ".join(limit_errors[:3]) if limit_errors else None,
        }

        # 5) 研报
        try:
            report_res = self.research_report(symbol=clean_symbol, top_n=3)
            if report_res.get("ok"):
                report_data = report_res.get("data", {})
                sections["research_report"] = {
                    "ok": True,
                    "api": report_res.get("api"),
                    "items": report_data.get("items", [])[:3],
                }
            else:
                sections["research_report"] = {
                    "ok": False,
                    "api": report_res.get("api"),
                    "error": report_res.get("error", "unknown error"),
                }
        except Exception as exc:
            sections["research_report"] = {"ok": False, "error": str(exc)}

        has_success = any(section.get("ok") for section in sections.values())
        if not has_success:
            combined_error = "; ".join(
                str(section.get("error"))
                for section in sections.values()
                if section.get("error")
            )
            return self._error(fn_name, combined_error or "all sub-apis failed")

        return self._wrap(
            fn_name,
            symbol=clean_symbol,
            realtime=sections["realtime"],
            money_flow=sections["money_flow"],
            fundamental=sections["fundamental"],
            limit_stats=sections["limit_stats"],
            research_report=sections["research_report"],
        )

    def stock_pick(self, top_n: int = 5, sector: str = None) -> Dict[str, Any]:
        import warnings
        fn_name = "stock_pick"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        def pick(item: dict, keys: list, default: Any = None) -> Any:
            for key in keys:
                value = item.get(key)
                if value not in (None, ""):
                    return value
            return default

        def normalize_code(value: Any) -> str:
            if value is None:
                return ""
            text = str(value).strip().upper()
            if not text:
                return ""
            text = text.replace("SH", "").replace("SZ", "").replace("BJ", "")
            digits = "".join(ch for ch in text if ch.isdigit())
            if len(digits) >= 6:
                return digits[:6]
            return text

        # 板块关键词映射
        sector_keywords = {
            "半导体": ["半导体", "芯片", "集成电路"],
            "电子": ["电子", "科技", "计算机"],
            "汽车": ["汽车", "新能源车", "整车", "汽配"],
            "医药生物": ["医药", "医疗器械", "中药", "生物医药", "医疗", "医药生物"],
            "医药": ["医药", "医疗器械", "中药", "生物医药", "医疗", "医药生物"],
            "光伏": ["光伏", "光伏发电", "光伏设备"],
            "锂电池": ["锂电池", "锂电", "电池", "动力电池"],
            "新能源": ["新能源", "储能", "电动车", "电动汽车"],
            "银行": ["银行", "银行股"],
            "保险": ["保险", "保险股"],
            "证券": ["证券", "券商"],
            "金融": ["金融", "银行", "保险", "证券"],
            "房地产": ["房地产", "地产", "物业"],
            "地产": ["房地产", "地产", "物业"],
            "电力": ["电力", "电力股", "发电"],
            "传媒": ["传媒", "影视", "游戏"],
            "军工": ["军工", "航天", "航空", "船舶", "国防"],
            "软件": ["软件", "互联网", "计算机", "IT", "软件开发"],
            "食品": ["食品", "零食", "食品加工"],
            "饮料": ["饮料", "饮品"],
            "白酒": ["白酒", "酒", "白酒股"],
            "家电": ["家电", "白色家电", "冰洗"],
            "纺织": ["纺织", "纺织服装", "服装"],
        }

        # 板块关键词映射到接口参数（使用 akshare 实际支持的名称）
        sector_map = {
            # 常用板块
            "半导体": "半导体",
            "电子": "电子",
            "汽车": "汽车",
            "医药生物": "医药生物",
            "医药": "医药生物",
            "银行": "银行",
            "保险": "保险",
            "证券": "证券",
            "房地产": "房地产",
            "锂电池": "锂电池",
            "电池": "电池",
            "光伏": "光伏设备",
            "光伏设备": "光伏设备",
            "电力": "电力",
            "传媒": "传媒",
            "军工": "军工",
            "软件": "软件开发",
            "食品": "食品",
            "饮料": "饮料",
            "白酒": "白酒",
            "家电": "家电",
            "纺织": "纺织",
        }

        target_sector = None
        target_symbol = None
        if sector:
            sector_lower = sector.lower()
            for key, keywords in sector_keywords.items():
                if any(k in sector_lower for k in keywords):
                    target_sector = key
                    target_symbol = sector_map.get(key, key)
                    break

        # 1. 如果指定了板块，获取板块成分股
        sector_stocks = []
        if target_sector and target_symbol:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    df = self._ak.stock_board_industry_cons_em(symbol=target_symbol)
                if hasattr(df, 'to_dict'):
                    for row in df.to_dict(orient='records'):
                        if not isinstance(row, dict):
                            continue
                        code = normalize_code(pick(row, ["代码", "股票代码"]))
                        name = pick(row, ["名称", "股票名称"], "")
                        pct = pick(row, ["涨跌幅"])
                        if code:
                            pct_num = _safe_float_local(pct)
                            sector_stocks.append({
                                "code": code,
                                "name": str(name) if name else code,
                                "pct": pct_num if pct_num else 0,
                            })
            except Exception as e:
                pass

        # 如果成功获取到板块成分股，直接用这些数据
        if sector_stocks:
            sector_stocks.sort(key=lambda x: x.get("pct", 0), reverse=True)
            top_candidates = sector_stocks[:top_n]
        else:
            # 2. 获取热门股票（涨跌幅排行）
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    hot_df = self._ak.stock_hot_rank_em()
            except Exception as e:
                return self._error(fn_name, f"热门股票获取失败: {e}")

            hot_items = []
            if hasattr(hot_df, 'to_dict'):
                records = hot_df.to_dict(orient='records')
                for row in records:
                    if not isinstance(row, dict):
                        continue
                    code = normalize_code(pick(row, ["代码", "股票代码", "证券代码", "symbol"]))
                    name = pick(row, ["股票名称", "名称", "简称", "name"], "")
                    pct = pick(row, ["涨跌幅", "涨跌幅%"])
                    if code:
                        pct_num = _safe_float_local(pct)
                        hot_items.append({
                            "code": code,
                            "name": str(name) if name else code,
                            "pct": pct_num if pct_num else 0,
                        })

            if not hot_items:
                return self._error(fn_name, "热门股票数据为空")

            hot_items.sort(key=lambda x: x.get("pct", 0), reverse=True)
            top_candidates = hot_items[:10]

        # 获取行业资金流
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                sector_res = self.sector_money_flow(top_n=15)
        except:
            sector_res = {"ok": False}

        hot_industries = set()
        if sector_res.get("ok"):
            sector_items = sector_res.get("data", {}).get("items", [])
            for row in sector_items:
                if not isinstance(row, dict):
                    continue
                name = pick(row, ["名称", "行业"])
                inflow = _safe_float_local(pick(row, ["今日主力净流入-净额", "主力净流入"]))
                if name and inflow and inflow > 0:
                    hot_industries.add(str(name).strip())

        # 3. 简化：只取研报数据（不做个股详细查询）
        report_map = {}
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                report_df = self._ak.stock_research_report_em()
            if hasattr(report_df, 'to_dict'):
                report_records = report_df.to_dict(orient='records')[:50]
                for row in report_records:
                    if not isinstance(row, dict):
                        continue
                    code = normalize_code(pick(row, ["股票代码", "代码"]))
                    rating = str(pick(row, ["东财评级", "评级"], ""))
                    if "买入" in rating and code not in report_map:
                        report_map[code] = {
                            "org": pick(row, ["机构"], "机构"),
                            "rating": rating,
                            "title": str(pick(row, ["报告名称"], ""))[:20],
                        }
        except:
            pass

        # 4. 组装推荐结果
        selected = []
        for row in top_candidates:
            code = row["code"]
            name = row["name"]
            pct = row["pct"]
            
            report = report_map.get(code, {})
            
            selected.append({
                "name": name,
                "code": code,
                "pct": pct,
                "report_org": report.get("org", ""),
                "report_rating": report.get("rating", ""),
                "report_title": report.get("title", ""),
            })

        return self._wrap(
            fn_name,
            items=selected[:top_n],
            count=len(selected),
        )

    def margin_lhb(self, symbol: Optional[str] = None, date: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
        fn_name = "margin_lhb"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        clean_symbol = self._clean_symbol(symbol)
        trade_date = self._normalize_trade_date(date)

        margin_candidates = [
            (
                "stock_margin_detail",
                [
                    {"date": trade_date, "symbol": clean_symbol},
                    {"date": trade_date, "stock": clean_symbol},
                    {"date": trade_date, "code": clean_symbol},
                    {"date": trade_date},
                ],
            ),
            ("stock_margin_detail_em", [{"date": trade_date}, {"trade_date": trade_date}, {}]),
            ("stock_margin_underlying_info_szse", [{}]),
            ("stock_margin_underlying_info_sse", [{}]),
        ]

        margin_api, margin_df, margin_err = self._call_api_candidates(margin_candidates)
        margin_items: list[dict] = []
        if margin_df is not None:
            margin_items = self._to_records(margin_df, top_n=0)
            if isinstance(margin_items, list):
                margin_items = [item for item in margin_items if isinstance(item, dict)]
                margin_items = self._filter_records_by_symbol(margin_items, clean_symbol)
                margin_items = margin_items[:top_n]
            else:
                margin_items = []

        lhb_candidates = [
            (
                "stock_lhb_detail_em",
                [
                    {"start_date": trade_date, "end_date": trade_date},
                    {"date": trade_date},
                    {},
                ],
            ),
            ("stock_lhb_ggtj_sina", [{"symbol": "5"}, {"symbol": "10"}, {}]),
        ]

        lhb_api, lhb_df, lhb_err = self._call_api_candidates(lhb_candidates)
        lhb_items: list[dict] = []
        if lhb_df is not None:
            lhb_items = self._to_records(lhb_df, top_n=0)
            if isinstance(lhb_items, list):
                lhb_items = [item for item in lhb_items if isinstance(item, dict)]
                lhb_items = self._filter_records_by_symbol(lhb_items, clean_symbol)
                lhb_items = lhb_items[:top_n]
            else:
                lhb_items = []

        if margin_df is None and lhb_df is None:
            return self._error(fn_name, f"margin failed: {margin_err}; lhb failed: {lhb_err}")

        return self._wrap(
            fn_name,
            scope="margin_lhb",
            symbol=clean_symbol,
            date=trade_date,
            margin_api=margin_api,
            lhb_api=lhb_api,
            margin_items=margin_items,
            lhb_items=lhb_items,
            margin_error=margin_err if margin_df is None else None,
            lhb_error=lhb_err if lhb_df is None else None,
        )

    def sector_analysis(self, sector_type: str = "industry", top_n: int = 10) -> Dict[str, Any]:
        fn_name = "stock_sector_name_code"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        normalized = "概念" if sector_type in {"concept", "概念"} else "行业"
        spot_indicator = "概念" if normalized == "概念" else "新浪行业"
        candidates = [
            ("stock_sector_name_code", [{"indicator": "今日涨跌幅", "sector_type": normalized}]),
            ("stock_sector_name_code", [{"sector_type": normalized}]),
            ("stock_sector_spot", [{"indicator": spot_indicator}]),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        records = self._to_records(df, top_n=0)
        if isinstance(records, list):
            records = [item for item in records if isinstance(item, dict)]
            records.sort(
                key=lambda row: _safe_float_local(
                    row.get("涨跌幅")
                    or row.get("今日涨跌幅")
                    or row.get("涨跌幅%")
                    or row.get("涨跌")
                )
                or -9999,
                reverse=True,
            )
            top_gain = records[:top_n]
            top_drop = sorted(
                records,
                key=lambda row: _safe_float_local(
                    row.get("涨跌幅")
                    or row.get("今日涨跌幅")
                    or row.get("涨跌幅%")
                    or row.get("涨跌")
                )
                or 9999,
            )[:top_n]
        else:
            top_gain = []
            top_drop = []

        return self._wrap(
            api_name or fn_name,
            scope="sector_analysis",
            sector_type="concept" if normalized == "概念" else "industry",
            top_gain=top_gain,
            top_drop=top_drop,
            items=top_gain,
        )

    def fund_bond(self, scope: str = "fund", symbol: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
        fn_name = "fund_bond"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        normalized_scope = "bond" if scope in {"bond", "convertible", "cb"} else "fund"

        if normalized_scope == "fund":
            clean_symbol = self._clean_symbol(symbol)
            default_symbol = clean_symbol or "159915"
            candidates = [
                (
                    "fund_etf_hist_em",
                    [
                        {
                            "symbol": default_symbol,
                            "period": "daily",
                            "start_date": (datetime.now() - timedelta(days=90)).strftime("%Y%m%d"),
                            "end_date": datetime.now().strftime("%Y%m%d"),
                            "adjust": "",
                        }
                    ],
                ),
                ("fund_etf_spot_em", [{}]),
                ("fund_open_fund_daily_em", [{}]),
            ]
            api_name, df, err_msg = self._call_api_candidates(candidates)
            if df is None:
                return self._error(fn_name, err_msg)

            records = self._to_records(df, top_n=0)
            if isinstance(records, list):
                records = [item for item in records if isinstance(item, dict)]
                if clean_symbol:
                    records = self._filter_records_by_symbol(records, clean_symbol) or records
                for item in records:
                    if "代码" not in item:
                        item["代码"] = default_symbol
                if records and "日期" in records[0]:
                    try:
                        records = sorted(records, key=lambda r: r.get("日期") or "", reverse=True)
                    except Exception:
                        pass
                records = records[:top_n]
            else:
                records = []

            return self._wrap(
                api_name or fn_name,
                scope="fund",
                symbol=default_symbol,
                items=records,
            )

        candidates = [
            ("bond_zh_hs_cov_spot", [{}]),
            ("bond_zh_hs_cov_daily", [{"symbol": symbol or "sh113527"}]),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        records = self._to_records(df, top_n=0)
        if isinstance(records, list):
            records = [item for item in records if isinstance(item, dict)]
            if symbol:
                records = self._filter_records_by_symbol(records, str(symbol)) or records
            records = records[:top_n]
        else:
            records = []

        return self._wrap(
            api_name or fn_name,
            scope="bond",
            symbol=symbol,
            items=records,
        )

    def hk_us_market(self, market: str = "hk", top_n: int = 10, symbol: Optional[str] = None) -> Dict[str, Any]:
        fn_name = "hk_us_market"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        normalized_market = "us" if market in {"us", "美股", "usa"} else "hk"
        if normalized_market == "hk":
            candidates = [("stock_hk_spot_em", [{}])]
        else:
            candidates = [("stock_us_spot_em", [{}])]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        records = self._to_records(df, top_n=0)
        if isinstance(records, list):
            records = [item for item in records if isinstance(item, dict)]
            if symbol:
                records = self._filter_records_by_symbol(records, str(symbol)) or records
            records = records[:top_n]
        else:
            records = []

        return self._wrap(
            api_name or fn_name,
            scope="hk_us_market",
            market=normalized_market,
            items=records,
        )

    def derivatives(self, scope: str = "futures", symbol: Optional[str] = None, top_n: int = 10) -> Dict[str, Any]:
        fn_name = "derivatives"
        err = self._ready_or_error(fn_name)
        if err:
            return err

        normalized_scope = "options" if scope in {"option", "options", "期权"} else "futures"

        if normalized_scope == "futures":
            candidates = [
                ("futures_display_main_sina", [{}]),
                ("match_main_contract", [{"symbol": "cffex"}]),
                ("futures_main_sina", [{"symbol": "IF0"}, {"symbol": "IH0"}, {"symbol": "IC0"}]),
            ]

            api_name, df, err_msg = self._call_api_candidates(candidates)
            if df is None:
                return self._error(fn_name, err_msg)

            records = self._to_records(df, top_n=0)
            if isinstance(records, list):
                records = [item for item in records if isinstance(item, dict)]
                if symbol:
                    records = self._filter_records_by_symbol(records, str(symbol)) or records
                records = records[:top_n]
            else:
                records = []

            return self._wrap(
                api_name or fn_name,
                scope="futures",
                symbol=symbol,
                items=records,
            )

        candidates = [
            ("option_current_em", [{}]),
            ("option_cffex_hs300_spot_sina", [{}]),
            ("option_finance_board", [{"symbol": "华夏上证50ETF期权"}, {}]),
        ]

        api_name, df, err_msg = self._call_api_candidates(candidates)
        if df is None:
            return self._error(fn_name, err_msg)

        records = self._to_records(df, top_n=0)
        if isinstance(records, list):
            records = [item for item in records if isinstance(item, dict)]
            if symbol:
                records = self._filter_records_by_symbol(records, str(symbol)) or records
            records = records[:top_n]
        else:
            records = []

        return self._wrap(
            api_name or fn_name,
            scope="options",
            symbol=symbol,
            items=records,
        )


def _safe_float_local(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").strip()
    try:
        return float(value)
    except Exception:
        return None
