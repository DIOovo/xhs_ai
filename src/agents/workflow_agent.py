"""
内容工作流编排 Agent。

职责：把 hot/writer/review/cover 等单一 Agent 串成一次可执行的多步任务。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.agents.base import AgentStep
from src.agents.cover_agent import CoverAgent
from src.agents.hot_agent import HotAgent
from src.agents.review_agent import ReviewAgent
from src.agents.writer_agent import WriterAgent


@dataclass(frozen=True)
class HotspotWorkflowRequest:
    source: str = "weibo"
    rank: int = 1
    use_context: bool = True
    cover_template_id: str = ""
    page_count: int = 3
    header_title: str = ""
    author: str = ""
    block_on_reject: bool = False


class ContentWorkflowAgent:
    """小红书内容生产工作流 Agent。"""

    name = "content_workflow_agent"

    def __init__(
        self,
        *,
        hot_agent: Any = None,
        writer_agent: Any = None,
        review_agent: Any = None,
        cover_agent: Any = None,
    ):
        self.hot_agent = hot_agent or HotAgent()
        self.writer_agent = writer_agent or WriterAgent()
        self.review_agent = review_agent or ReviewAgent()
        self.cover_agent = cover_agent or CoverAgent()

    def build_hotspot_payload(self, request: HotspotWorkflowRequest) -> Dict[str, Any]:
        """根据热点自动完成选题、写作、审核、配图，返回可发布 payload。"""

        steps: List[AgentStep] = [
            AgentStep(self.name, "plan", "completed", "规划热点发布任务", {"workflow": "hotspot_publish"}),
        ]

        topic = self.hot_agent.select_topic(
            source=request.source,
            rank=request.rank,
            use_context=request.use_context,
        )
        steps.append(
            AgentStep(
                self.hot_agent.name,
                "select_topic",
                "completed",
                f"选择热点：{topic.title}",
                {"source": topic.source, "rank": topic.rank, "url": topic.url},
            )
        )

        llm_topic = topic.title
        if topic.context_text:
            llm_topic = f"{topic.title}\n\n参考信息（百度搜索摘要）：\n{topic.context_text}".strip()

        generated = self.writer_agent.generate_xiaohongshu_content(
            llm_topic,
            header_title=request.header_title,
            author=request.author,
            allow_fallback=True,
            fallback_topic=topic.title,
        )
        title = str(generated.title or "").strip()
        content = str(generated.content or "").strip()
        steps.append(
            AgentStep(
                self.writer_agent.name,
                "write",
                "completed",
                "生成标题与正文",
                {"source": generated.source, "fallback_error": generated.error},
            )
        )

        if not title and not content:
            raise RuntimeError("生成失败：标题/内容为空")

        review = self.review_agent.review(title, content)
        steps.append(
            AgentStep(
                self.review_agent.name,
                "review",
                "completed",
                str(review.get("decision") or ""),
                {"risk_score": review.get("risk_score"), "risk_level": review.get("risk_level")},
            )
        )
        if request.block_on_reject and not bool(review.get("can_publish", True)):
            raise RuntimeError("审核失败：内容被判定为禁止发布")

        cover = self.cover_agent.generate_for_post(
            title=title,
            content=content,
            topic=topic.title,
            cover_template_id=request.cover_template_id,
            page_count=request.page_count,
        )
        if cover.title_override:
            title = cover.title_override
        if cover.content_override:
            content = cover.content_override
        images = list(cover.images or [])
        steps.append(
            AgentStep(
                self.cover_agent.name,
                "generate_images",
                "completed",
                f"生成 {len(images)} 张图片",
                {"source": cover.source},
            )
        )

        if not images:
            raise RuntimeError("生成失败：图片为空")

        return {
            "title": title,
            "content": content,
            "images": images,
            "hotspot_title": topic.title,
            "hotspot_source": topic.source,
            "hotspot_rank": topic.rank,
            "hotspot_url": topic.url,
            "review": review,
            "agent_steps": [step.to_dict() for step in steps],
        }

    @staticmethod
    def request_from_action(action: Dict[str, Any]) -> HotspotWorkflowRequest:
        source = str(action.get("hotspot_source") or "weibo").strip().lower() or "weibo"
        try:
            rank = int(action.get("hotspot_rank") or 1)
        except Exception:
            rank = 1
        try:
            page_count = int(action.get("page_count") or 3)
        except Exception:
            page_count = 3

        header_title, author = ContentWorkflowAgent._load_title_config()
        return HotspotWorkflowRequest(
            source=source,
            rank=max(1, rank),
            use_context=bool(action.get("use_hotspot_context", True)),
            cover_template_id=str(action.get("cover_template_id") or "").strip(),
            page_count=max(1, page_count),
            header_title=header_title,
            author=author,
        )

    @staticmethod
    def _load_title_config():
        try:
            from src.config.config import Config

            title_cfg = Config().get_title_config()
        except Exception:
            title_cfg = {}
        header_title = str((title_cfg or {}).get("title") or "").strip()
        author = str((title_cfg or {}).get("author") or "").strip()
        return header_title, author
