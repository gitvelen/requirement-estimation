"""
区间估算服务（min/max + 置信度 + 假设 + 风险提示）
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

TEMPLATE_RANGES = {
    "单表查询": (0.5, 1.0),
    "列表展示": (1.0, 2.0),
    "单表CRUD": (1.0, 2.0),
    "审批流程": (2.0, 4.0),
    "报表统计": (2.0, 3.5),
    "接口开发": (1.5, 3.5),
    "接口对接": (1.5, 3.5),
    "数据改造": (2.0, 4.5),
    "配置管理": (0.8, 1.5),
}


INTEGRATION_KEYWORDS = ("接口", "对接", "联调", "同步", "调用", "回调", "订阅", "ESB", "消息", "MQ")


def apply_interval_estimations(
    features: List[Dict[str, Any]],
    evidence_level: str = None,
    assumptions_threshold: int = 4,
) -> None:
    for feature in features:
        if not isinstance(feature, dict):
            continue
        func_type = feature.get("功能类型") or feature.get("functional_type")
        if not func_type:
            func_type = infer_functional_type(feature)
            feature["功能类型"] = func_type

        base_min, base_max = TEMPLATE_RANGES.get(func_type, (1.0, 2.5))
        est = _safe_float(feature.get("预估人天") or feature.get("aiEstimatedDays") or 0.0)
        if est:
            base_min = min(base_min, est)
            base_max = max(base_max, est)

        adj_min, adj_max = adjust_range((base_min, base_max), feature, evidence_level)
        adj_min = max(round(adj_min, 2), 0.5)
        adj_max = max(round(adj_max, 2), adj_min)

        assumptions = build_assumptions(feature)
        key_factors = build_key_factors(feature)
        confidence = determine_confidence(evidence_level, assumptions)
        risk_flags = build_risk_flags(confidence, assumptions, evidence_level, assumptions_threshold)

        feature["estimate_range"] = {"min": adj_min, "max": adj_max}
        feature["confidence"] = confidence
        feature["assumptions"] = assumptions
        feature["key_factors"] = key_factors
        feature["risk_flags"] = risk_flags
        feature["evidence_level"] = evidence_level

        if adj_max > 5:
            remark = str(feature.get("备注") or "").strip()
            note = "[待确认] 估算区间上限>5人天，建议进一步拆分。"
            feature["备注"] = f"{remark}\n{note}".strip() if remark else note


def infer_functional_type(feature: Dict[str, Any]) -> str:
    text = " ".join(
        str(feature.get(k) or "").strip()
        for k in ("功能模块", "功能点", "业务描述", "备注")
    )
    if "审批" in text or "流程" in text:
        return "审批流程"
    if "报表" in text or "统计" in text or "分析" in text:
        return "报表统计"
    if "接口" in text or "对接" in text or "联调" in text:
        return "接口对接"
    if "查询" in text:
        return "单表查询"
    if "列表" in text or "展示" in text:
        return "列表展示"
    if "新增" in text or "编辑" in text or "删除" in text:
        return "单表CRUD"
    if "配置" in text or "参数" in text:
        return "配置管理"
    return "单表CRUD"


def adjust_range(base_range: Tuple[float, float], feature: Dict[str, Any], evidence_level: str) -> Tuple[float, float]:
    base_min, base_max = base_range
    complexity = str(feature.get("复杂度") or "")
    text = " ".join(
        str(feature.get(k) or "").strip()
        for k in ("功能点", "业务描述", "输入", "输出", "依赖项", "依赖", "备注")
    )
    has_integration = any(k in text for k in INTEGRATION_KEYWORDS)
    has_dependency = bool(feature.get("依赖项") or feature.get("依赖"))

    if complexity == "高":
        base_min += 0.5
        base_max += 1.0
    elif complexity == "低":
        base_min -= 0.2

    if has_integration:
        base_min += 0.3
        base_max += 0.8
    if has_dependency:
        base_min += 0.2
        base_max += 0.4

    if evidence_level in ("E0", "E1"):
        base_max *= 1.4
        base_min *= 1.2

    return base_min, base_max


def build_assumptions(feature: Dict[str, Any]) -> List[str]:
    assumptions = []
    if not _has_value(feature.get("输入")):
        assumptions.append("输入/数据源未明确")
    if not _has_value(feature.get("输出")):
        assumptions.append("输出/结果口径未明确")
    if not _has_value(feature.get("业务描述")):
        assumptions.append("业务规则未明确")
    if not _has_value(feature.get("依赖项") or feature.get("依赖")):
        assumptions.append("依赖与集成范围未明确")
    remark = str(feature.get("备注") or "")
    if "[待确认]" in remark or "待确认" in remark:
        assumptions.append("存在待确认事项")
    return assumptions


def build_key_factors(feature: Dict[str, Any]) -> List[str]:
    factors = []
    text = " ".join(
        str(feature.get(k) or "").strip()
        for k in ("功能点", "业务描述", "备注")
    )
    if any(k in text for k in INTEGRATION_KEYWORDS):
        factors.append("集成点数量")
    complexity = str(feature.get("复杂度") or "")
    if complexity:
        factors.append(f"复杂度:{complexity}")
    return list(dict.fromkeys([f for f in factors if f]))


def determine_confidence(evidence_level: str, assumptions: List[str]) -> str:
    if evidence_level in ("E0", "E1"):
        return "低"
    if len(assumptions) >= 4:
        return "低"
    if evidence_level == "E3" and len(assumptions) <= 1:
        return "高"
    return "中"


def build_risk_flags(
    confidence: str,
    assumptions: List[str],
    evidence_level: str,
    threshold: int
) -> List[str]:
    flags = []
    if confidence == "低":
        flags.append("低置信度")
    if len(assumptions) >= threshold:
        flags.append("假设较多")
    if evidence_level in ("E0", "E1"):
        flags.append("证据不足")
    return flags


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, set)):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())
