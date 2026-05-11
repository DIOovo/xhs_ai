"""
内容审核 Agent。

职责：在发布前执行风险、标题党、未证实信息等规则审核。
"""

from __future__ import annotations

from typing import Any, Dict


class ReviewAgent:
    """负责发布前内容风险判断。"""

    name = "review_agent"

    def __init__(self, ops_service: Any = None):
        if ops_service is None:
            from src.core.services.content_ops_service import content_ops_service

            ops_service = content_ops_service
        self.ops_service = ops_service

    def review(self, title: str, content: str = "") -> Dict[str, Any]:
        result = self.ops_service.review_risk(title, content)
        decision = str((result or {}).get("decision") or "").strip()
        return {
            **(result or {}),
            "can_publish": decision != "禁止发布",
        }
