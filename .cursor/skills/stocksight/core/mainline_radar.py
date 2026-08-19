# -*- coding: utf-8 -*-
"""A-share mainline radar scoring.

The radar deliberately separates observable market heat from the user's full
10-item mainline score. Missing inputs stay pending instead of being counted as
failed checks.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional, Sequence


MAINLINE_PENDING_CHECKS = [
    "板块是否连续 2-3 个交易日强于大盘",
    "板块内是否至少 5-10 只个股同步走强",
    "板块内是否有中军股放量上涨",
    "龙头股是否具有持续性而不是一日游",
    "板块成交额是否连续放大",
    "第一次分歧后是否能够修复",
    "板块指数是否站上 20 日线或突破阶段平台",
    "主线内部是否出现多个有效分支扩散",
    "最近 7-14 天是否有真实产业/政策/业绩/订单/价格催化",
    "其他方向是否持续性弱，资金是否反复回流该方向",
    "60 日涨幅是否处于第一波中段而非老主线二波",
]


@dataclass(frozen=True)
class SectorRadarInput:
    """Normalized sector snapshot for mainline radar scoring."""

    code: str
    name: str
    board_type: str = "industry"
    change_percent: float = 0.0
    turnover_rate: float = 0.0
    up_count: int = 0
    down_count: int = 0
    leader: str = ""
    leader_change_percent: float = 0.0
    main_net_inflow: float = 0.0
    index_price: float = 0.0

    @property
    def total_count(self) -> int:
        return max(0, int(self.up_count or 0) + int(self.down_count or 0))

    @property
    def up_ratio(self) -> Optional[float]:
        total = self.total_count
        if total <= 0:
            return None
        return self.up_count / total


@dataclass(frozen=True)
class MainlineRadarResult:
    """Explainable radar output for one sector."""

    sector: SectorRadarInput
    radar_score: float
    status: str
    auto_hits: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    pending_checks: List[str] = field(default_factory=list)
    generated_at: str = ""


def _float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "-":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value, default: int = 0) -> int:
    try:
        if value is None or value == "-":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def sector_from_mapping(row: dict) -> SectorRadarInput:
    """Build a radar input from provider sector dictionaries."""
    return SectorRadarInput(
        code=str(row.get("code") or row.get("板块代码") or ""),
        name=str(row.get("name") or row.get("板块名称") or ""),
        board_type=str(row.get("board_type") or "industry"),
        change_percent=_float(row.get("change") or row.get("涨跌幅")),
        turnover_rate=_float(row.get("turnover_rate") or row.get("换手率")),
        up_count=_int(row.get("up_count") or row.get("上涨家数")),
        down_count=_int(row.get("down_count") or row.get("下跌家数")),
        leader=str(row.get("leader") or row.get("领涨股票") or ""),
        leader_change_percent=_float(row.get("leader_change") or row.get("领涨股票-涨跌幅")),
        main_net_inflow=_float(row.get("main_net_inflow") or row.get("主力净流入")),
        index_price=_float(row.get("index_price") or row.get("最新价")),
    )


def radar_status(score: float) -> str:
    """Human-readable status for the automatic radar score."""
    if score >= 7:
        return "强势雷达"
    if score >= 5:
        return "跟踪观察"
    return "仅记录"


def evaluate_sector_radar(
    sector: SectorRadarInput,
    *,
    market_change: float = 0.0,
    generated_at: Optional[str] = None,
) -> MainlineRadarResult:
    """Score observable heat for one sector.

    This is not the final 10-item mainline score. It only answers whether the
    sector is worth tracking today.
    """
    score = 0.0
    hits: List[str] = []
    warnings: List[str] = []
    relative = sector.change_percent - market_change

    if relative >= 3:
        score += 3
        hits.append(f"今日明显强于大盘 {relative:+.2f}pct")
    elif relative >= 2:
        score += 2
        hits.append(f"今日强于大盘 {relative:+.2f}pct")
    elif relative >= 1:
        score += 1
        hits.append(f"今日略强于大盘 {relative:+.2f}pct")
    else:
        hits.append(f"今日相对大盘不足 {relative:+.2f}pct")

    up_ratio = sector.up_ratio
    if up_ratio is not None:
        if up_ratio >= 0.75:
            score += 2
            hits.append(f"板块内普涨 {sector.up_count}/{sector.total_count}")
        elif up_ratio >= 0.60:
            score += 1
            hits.append(f"板块内偏强 {sector.up_count}/{sector.total_count}")
        else:
            hits.append(f"板块内分歧 {sector.up_count}/{sector.total_count}")
    else:
        warnings.append("缺少上涨/下跌家数，同步性待确认")

    if sector.leader_change_percent >= 7:
        score += 1.5
        hits.append(f"领涨股强势：{sector.leader or '未命名'} {sector.leader_change_percent:+.2f}%")
    elif sector.leader_change_percent >= 5:
        score += 1
        hits.append(f"领涨股走强：{sector.leader or '未命名'} {sector.leader_change_percent:+.2f}%")
    elif sector.leader_change_percent > 0:
        hits.append(f"领涨股强度一般：{sector.leader or '未命名'} {sector.leader_change_percent:+.2f}%")

    if sector.main_net_inflow > 0:
        score += 1
        hits.append("主力净流入为正")
    else:
        warnings.append("主力净流入未确认或为负")

    if 2 <= sector.change_percent <= 7:
        score += 1
        hits.append("板块涨幅处于可观察区")
    elif sector.change_percent > 7:
        warnings.append("板块短线过热，不能按低风险主线中段处理")

    if sector.turnover_rate > 0:
        if 1 <= sector.turnover_rate <= 8:
            score += 1
            hits.append(f"板块换手处于可观察区 {sector.turnover_rate:.2f}%")
        elif sector.turnover_rate > 12:
            warnings.append(f"板块换手偏极端 {sector.turnover_rate:.2f}%")
    else:
        warnings.append("缺少板块换手率")

    return MainlineRadarResult(
        sector=sector,
        radar_score=min(10.0, score),
        status=radar_status(score),
        auto_hits=hits,
        warnings=warnings,
        pending_checks=list(MAINLINE_PENDING_CHECKS),
        generated_at=generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def evaluate_sector_rows(
    rows: Iterable[dict],
    *,
    market_change: float = 0.0,
    limit: Optional[int] = None,
) -> List[MainlineRadarResult]:
    """Evaluate provider rows and return sorted radar results."""
    results = [
        evaluate_sector_radar(sector_from_mapping(row), market_change=market_change)
        for row in rows
        if (row.get("name") or row.get("板块名称"))
    ]
    results.sort(
        key=lambda item: (
            item.radar_score,
            item.sector.change_percent,
            item.sector.leader_change_percent,
        ),
        reverse=True,
    )
    if limit is not None:
        return results[:limit]
    return results


def render_mainline_radar_markdown(
    results: Sequence[MainlineRadarResult],
    *,
    title: str = "StockSight 主线雷达",
    market_change: float = 0.0,
) -> str:
    """Render radar results as Markdown."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# {title}",
        "",
        f"- 生成时间：{now}",
        f"- 大盘参考涨跌幅：{market_change:+.2f}%",
        "- 说明：自动雷达分只用于发现方向；完整 10 项主线评分达到 6 分，才进入观察/候选流程。",
        "- 原则：脚本拿不到的数据标为待确认，不能按 0 分处理。",
        "",
        "## 雷达榜",
        "",
        "| 排名 | 类型 | 板块 | 涨跌幅 | 领涨股 | 领涨幅 | 上涨/总数 | 自动雷达分 | 状态 |",
        "|---:|---|---|---:|---|---:|---:|---:|---|",
    ]

    for index, item in enumerate(results, 1):
        sector = item.sector
        total = sector.total_count or 0
        breadth = f"{sector.up_count}/{total}" if total else "待确认"
        board_label = "行业" if sector.board_type == "industry" else "概念"
        lines.append(
            f"| {index} | {board_label} | {sector.name} | {sector.change_percent:+.2f}% | "
            f"{sector.leader or '—'} | {sector.leader_change_percent:+.2f}% | "
            f"{breadth} | {item.radar_score:.1f}/10 | {item.status} |"
        )

    tracked = [item for item in results if item.radar_score >= 5]
    lines.extend(["", "## 跟踪观察", ""])
    if not tracked:
        lines.append("暂无达到自动雷达跟踪阈值的方向。")
    for item in tracked[:8]:
        sector = item.sector
        lines.extend([
            f"### {sector.name}｜{item.status}｜自动雷达 {item.radar_score:.1f}/10",
            "",
            "**自动命中项：**",
        ])
        for hit in item.auto_hits:
            lines.append(f"- {hit}")
        if item.warnings:
            lines.append("")
            lines.append("**风险/缺口：**")
            for warning in item.warnings:
                lines.append(f"- {warning}")
        lines.append("")
        lines.append("**10项主线评分待确认：**")
        for check in item.pending_checks:
            lines.append(f"- [ ] {check}")
        lines.append("")
        lines.append("- 下一步：补齐待确认项；完整 10 项评分达到 6 分，才进入正式观察/候选。")
        lines.append("")

    return "\n".join(lines)
