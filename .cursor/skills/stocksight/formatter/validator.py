# -*- coding: utf-8 -*-
"""报告输出校验器

对标 VISUAL_SPECS.md Section 7（模板验证规则）。
在 formatter 生成报告文本后调用，逐条校验。

校验规则：
  1. 必填字段：title / summary / data_source / timestamp / stocks 非空
  2. ⚠️ 风险区块：存在信号时必须有风险区块
  3. 📡 数据来源标注：必须存在
  4. 区块顺序：核心数据在风险提示之前
  5. 表格列数 ≤ 5
  6. Emoji 在已注册符号表内
  7. 容错规则：缺失数据用"—"占位
"""

import re
from typing import Dict, List, Optional

from core import ReportData, RiskSignal


# 已注册的 emoji 集合（来自 VISUAL_SPECS Section 2）
REGISTERED_EMOJI = {
    # 行情状态
    "📈", "📉", "➡️", "🔥",
    # 核心指标
    "💰", "🔄", "⚡", "📊", "📐",
    # 状态与提示
    "⚠️", "💡", "📡", "🏷️", "🕐",
    # 区块标题
    "📰", "📋", "🔍", "🎯", "🗞️", "❓",
    # 风险等级
    "🔸", "🔶", "🔴",
    # 操作建议
    "🟢", "🟡",
    # 其他常见
    "✅", "❌", "—", "🕐",
}


class ValidationError(Exception):
    """报告校验失败"""


class ValidationResult:
    """校验结果"""

    def __init__(self):
        self.passed: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, msg: str):
        self.passed = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def __str__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        parts = [f"校验结果: {status}"]
        if self.errors:
            parts.append("错误:")
            for e in self.errors:
                parts.append(f"  - {e}")
        if self.warnings:
            parts.append("警告:")
            for w in self.warnings:
                parts.append(f"  - {w}")
        return "\n".join(parts)


def validate_report(report_text: str, data: Optional[ReportData] = None) -> ValidationResult:
    """校验生成的报告

    Args:
        report_text: formatter 渲染出的 Markdown 文本
        data: 原始数据（可选，提供后可以校验字段完整性）

    Returns:
        校验结果
    """
    result = ValidationResult()

    _validate_required_fields(result, data)
    _validate_risk_section(result, report_text, data)
    _validate_data_source(result, report_text)
    _validate_block_order(result, report_text)
    _validate_table_columns(result, report_text)
    _validate_emoji(result, report_text)
    _validate_allowed_html(result, report_text)
    _validate_empty_data(result, report_text)

    return result


def _validate_required_fields(result: ValidationResult, data: Optional[ReportData]):
    """规则 1：必填字段"""
    if data is None:
        return

    checks = {
        "报告标题": data.title,
        "一句话摘要": data.summary,
        "数据来源": data.data_source,
        "时间戳": data.timestamp,
        "股票列表": data.stocks,
    }

    for field_name, value in checks.items():
        if not value:
            result.add_error(f"必填字段缺失: {field_name}")
        elif isinstance(value, (list, tuple)) and len(value) == 0:
            result.add_error(f"必填字段为空: {field_name}")


def _validate_risk_section(
    result: ValidationResult, text: str, data: Optional[ReportData]
):
    """规则 2：存在信号时必须有 ⚠️ 风险区块"""
    has_signals = data is not None and len(data.signals) > 0
    has_risk_section = "⚠️" in text and ("风险" in text or "风险提示" in text)

    if has_signals and not has_risk_section:
        result.add_error("存在异动信号但缺少 ⚠️ 风险提示区块")

    calm_risk_copy = any(
        phrase in text
        for phrase in ["未发现显著异动", "未检测到显著风险", "当前市场状态平稳"]
    )
    if not has_signals and has_risk_section and not calm_risk_copy:
        result.add_warning("无异动信号但仍包含风险提示区块")


def _validate_data_source(result: ValidationResult, text: str):
    """规则 3：📡 数据来源标注必须存在"""
    if "📡" not in text and "数据来源" not in text:
        result.add_error("缺少 📡 数据来源标注")


def _validate_block_order(result: ValidationResult, text: str):
    """规则 4：核心数据区块在风险提示之前"""
    lines = text.split("\n")
    data_section_line = -1
    risk_section_line = -1

    for i, line in enumerate(lines):
        if line.startswith("##") and ("数据" in line or "列表" in line or "概览" in line):
            data_section_line = i
        if line.startswith("##") and "风险提示" in line:
            risk_section_line = i

    if data_section_line >= 0 and risk_section_line >= 0:
        if data_section_line > risk_section_line:
            result.add_warning("区块顺序异常：数据区块在风险提示区块之后")


def _validate_table_columns(result: ValidationResult, text: str):
    """规则 5：表格列数不超过 5"""
    table_pattern = re.compile(r"^\|.+\|$")
    in_table = False
    for line in text.split("\n"):
        if table_pattern.match(line):
            in_table = True
            cols = line.count("|") - 1
            if cols > 5:
                result.add_warning(f"表格列数 {cols} 超过限制（5列）: {line[:40]}...")


def _validate_emoji(result: ValidationResult, text: str):
    """规则 6：Emoji 在已注册符号表内"""
    # Normalize variation-selector emoji so symbols like ⚠️ and ➡️ do not
    # get split into a base character and trigger false warnings.
    emoji_pattern = re.compile(
        r"[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]\ufe0f?"
    )
    for match in emoji_pattern.finditer(text):
        symbol = match.group(0)
        if symbol not in REGISTERED_EMOJI:
            result.add_warning(f"未注册的 Emoji 符号: {symbol}")


def _validate_allowed_html(result: ValidationResult, text: str):
    """允许轻量 GitHub Markdown HTML，提示复杂标签。"""
    allowed_tags = {"kbd", "details", "summary"}
    tag_pattern = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")
    for match in tag_pattern.finditer(text):
        tag = match.group(1).lower()
        if tag not in allowed_tags:
            result.add_warning(f"不建议使用的 HTML 标签: <{tag}>")


def _validate_empty_data(result: ValidationResult, text: str):
    """规则 7：容错检查

    - 所有股票失败时应有明确提示
    - 缺失数据使用了占位符
    """
    if "实时数据不可用" in text or "无可用数据" in text:
        return

    dash_count = text.count("—")
    if dash_count == 0:
        return

    has_quality_note = "不可用" in text or "已显示为" in text
    if not has_quality_note:
        result.add_warning("报告中使用了 — 占位符但缺少数据完整性说明")
