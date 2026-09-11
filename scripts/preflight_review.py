#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate one daily after-market review without changing the report.

The check is intentionally dependency-free. It validates the report contract,
chart input, referenced images, source attribution, and a temporary chart render.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable


IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
REQUIRED_SOURCES = ("akshare-stock", "stocksight", "firecrawl-cli")
EXPECTED_CHARTS = {
    "indices": "01_indices.png",
    "limits": "02_limit.png",
    "watch_groups": "03_watch.png",
    "fund_flow": "04_flow.png",
}


class Checker:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def check_file(self, path: Path, label: str) -> bool:
        if not path.is_file():
            self.error(f"缺少{label}：{path}")
            return False
        return True


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _all_zero(values: Iterable[object]) -> bool:
    numbers = [float(value) for value in values if _is_number(value)]
    return bool(numbers) and all(value == 0 for value in numbers)


def _numeric_rows(payload: Any, section: str, checker: Checker) -> list[float]:
    if not isinstance(payload, list):
        checker.error(f"charts/data.json 的 {section} 必须是数组")
        return []

    values: list[float] = []
    for index, row in enumerate(payload):
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            checker.error(f"{section}[{index}] 缺少 name")
            continue
        value = row.get("value")
        if not _is_number(value):
            checker.error(f"{section}[{index}] 的 value 必须是有限数字")
            continue
        values.append(float(value))
    return values


def _validate_chart_data(path: Path, expected_date: str, checker: Checker) -> dict[str, Any] | None:
    if not checker.check_file(path, "charts/data.json"):
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checker.error(f"charts/data.json 无法解析：{exc}")
        return None

    if not isinstance(payload, dict):
        checker.error("charts/data.json 顶层必须是对象")
        return None
    if payload.get("date") != expected_date:
        checker.error(f"charts/data.json 日期为 {payload.get('date')!r}，应为 {expected_date}")
    if "_comment" in payload:
        checker.error("charts/data.json 仍包含示例注释，可能尚未替换真实数据")

    if "indices" in payload:
        values = _numeric_rows(payload["indices"], "indices", checker)
        if _all_zero(values):
            checker.warning("indices 全为 0，请确认不是缺失数据占位")

    limits = payload.get("limits")
    if limits is not None:
        if not isinstance(limits, dict):
            checker.error("limits 必须是对象")
        else:
            for key in ("up", "down"):
                value = limits.get(key)
                if not _is_number(value) or float(value) < 0:
                    checker.error(f"limits.{key} 必须是非负有限数字")
            if all(_is_number(limits.get(key)) and float(limits[key]) == 0 for key in ("up", "down")):
                checker.warning("limits 的涨停和跌停均为 0，请确认不是缺失数据占位")

    groups = payload.get("watch_groups")
    if groups is not None:
        if not isinstance(groups, list):
            checker.error("watch_groups 必须是数组")
        else:
            values: list[float] = []
            for index, group in enumerate(groups):
                if not isinstance(group, dict) or not isinstance(group.get("title"), str):
                    checker.error(f"watch_groups[{index}] 缺少 title")
                    continue
                values.extend(_numeric_rows(group.get("items"), f"watch_groups[{index}].items", checker))
            if _all_zero(values):
                checker.warning("watch_groups 全为 0，请确认不是缺失数据占位")

    if "fund_flow" in payload:
        values = _numeric_rows(payload["fund_flow"], "fund_flow", checker)
        if _all_zero(values):
            checker.warning("fund_flow 全为 0，请确认不是缺失数据占位")

    return payload


def _validate_report(report_dir: Path, checker: Checker) -> str | None:
    report_path = report_dir / "复盘.md"
    radar_path = report_dir / "主线雷达.md"
    if not checker.check_file(report_path, "复盘报告"):
        return None
    checker.check_file(radar_path, "主线雷达报告")

    try:
        report = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        checker.error(f"复盘报告无法读取：{exc}")
        return None

    for marker in ("今日结论", "数据可视化", "风险提示", "数据来源"):
        if marker not in report:
            checker.error(f"复盘报告缺少章节：{marker}")
    if "不构成投资建议" not in report:
        checker.error("复盘报告缺少研究风险声明")
    for source in REQUIRED_SOURCES:
        if source.lower() not in report.lower():
            checker.error(f"复盘报告缺少来源状态：{source}")

    for reference in IMAGE_RE.findall(report):
        if reference.startswith(("http://", "https://")):
            continue
        image_path = (report_dir / reference).resolve()
        if not image_path.is_file():
            checker.error(f"复盘报告引用的图片不存在：{reference}")
    return report


def _validate_sources(report_dir: Path, checker: Checker) -> None:
    source_dir = report_dir / "sources"
    if not source_dir.is_dir():
        checker.warning(f"sources 目录不存在：{source_dir}")
        return
    if not any(source_dir.iterdir()):
        checker.warning(f"sources 目录为空：{source_dir}")


def _render_chart_smoke_test(root: Path, data_path: Path, payload: dict[str, Any], checker: Checker) -> None:
    chart_script = root / "scripts" / "make_recap_charts.py"
    if not checker.check_file(chart_script, "图表脚本"):
        return

    with tempfile.TemporaryDirectory(prefix="investment-preflight-") as temp_dir:
        temp_data = Path(temp_dir) / "data.json"
        shutil.copyfile(data_path, temp_data)
        result = subprocess.run(
            [sys.executable, str(chart_script), str(temp_data)],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip().splitlines()
            checker.error(f"图表生成 smoke test 失败：{detail[-1] if detail else '未知错误'}")
            return

        for section, filename in EXPECTED_CHARTS.items():
            if section in payload and not (Path(temp_dir) / filename).is_file():
                checker.error(f"{section} 已提供，但图表脚本未生成 {filename}")


def _default_date() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    except (ImportError, KeyError):
        return date.today().isoformat()


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="预检一份 Investment 盘后复盘报告")
    parser.add_argument("date", nargs="?", default=None, help="报告日期 YYYY-MM-DD；默认使用当前日期")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skip-render", action="store_true", help="跳过临时图表生成检查")
    args = parser.parse_args(argv)

    expected_date = args.date or _default_date()
    report_dir = args.root / "reports" / expected_date
    checker = Checker()

    if not report_dir.is_dir():
        checker.error(f"报告目录不存在：{report_dir}")
    else:
        payload = _validate_chart_data(report_dir / "charts" / "data.json", expected_date, checker)
        _validate_report(report_dir, checker)
        _validate_sources(report_dir, checker)
        if payload is not None and not args.skip_render:
            _render_chart_smoke_test(args.root, report_dir / "charts" / "data.json", payload, checker)

    for message in checker.errors:
        print(f"FAIL: {message}")
    for message in checker.warnings:
        print(f"WARN: {message}")
    if checker.errors:
        print(f"预检失败：{len(checker.errors)} 个错误，{len(checker.warnings)} 个警告")
        return 1
    print(f"预检通过：{report_dir}（{len(checker.warnings)} 个警告）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
