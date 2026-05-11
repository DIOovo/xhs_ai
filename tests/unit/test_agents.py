import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.agents.cover_agent import CoverResult
from src.agents.hot_agent import HotAgent, TopicCandidate
from src.agents.workflow_agent import ContentWorkflowAgent, HotspotWorkflowRequest
from src.agents.writer_agent import GeneratedCopy, WriterAgent


@dataclass(frozen=True)
class FakeHotspotItem:
    source: str
    rank: int
    title: str
    hot: int
    url: str


class FakeHotspotClient:
    def fetch(self, source, limit=50):
        return [
            FakeHotspotItem(source=source, rank=1, title="第一个热点", hot=100, url="https://example.com/1"),
            FakeHotspotItem(source=source, rank=2, title="第二个热点", hot=80, url="https://example.com/2"),
        ]

    def fetch_baidu_search_snippets(self, query, limit=3, timeout=10):
        return [{"snippet": f"{query} 的背景摘要"}]


def test_hot_agent_selects_ranked_topic_with_context():
    agent = HotAgent(hotspot_client=FakeHotspotClient())

    topic = agent.select_topic("weibo", rank=2, use_context=True)

    assert topic.title == "第二个热点"
    assert topic.rank == 2
    assert topic.context_text == "第二个热点 的背景摘要"


def test_writer_agent_fallback_returns_publishable_copy():
    result = WriterAgent.fallback_generate_xhs_content("AI效率工具")

    assert result["title"]
    assert "AI效率工具" in result["content"]


class FakeHotAgent:
    name = "hot_agent"

    def select_topic(self, source, rank, use_context=True):
        return TopicCandidate(
            source=source,
            title="AI效率工具爆火",
            url="https://example.com/hot",
            rank=rank,
            hot=1000,
            context_text="搜索摘要",
        )


class FakeWriterAgent:
    name = "writer_agent"

    def generate_xiaohongshu_content(
        self,
        topic,
        header_title="",
        author="",
        allow_fallback=True,
        fallback_topic="",
    ):
        assert "搜索摘要" in topic
        assert fallback_topic == "AI效率工具爆火"
        return GeneratedCopy(title="AI效率工具怎么选", content="先看场景，再看成本。", source="llm")


class FakeReviewAgent:
    name = "review_agent"

    def review(self, title, content=""):
        return {"decision": "可发布", "risk_score": 0, "risk_level": "low", "can_publish": True}


class FakeCoverAgent:
    name = "cover_agent"

    def generate_for_post(self, title, content, topic="", cover_template_id="", page_count=3):
        assert title == "AI效率工具怎么选"
        return CoverResult(images=["/tmp/cover.jpg", "/tmp/page.jpg"], source="fake")


def test_content_workflow_agent_builds_hotspot_payload():
    workflow = ContentWorkflowAgent(
        hot_agent=FakeHotAgent(),
        writer_agent=FakeWriterAgent(),
        review_agent=FakeReviewAgent(),
        cover_agent=FakeCoverAgent(),
    )

    payload = workflow.build_hotspot_payload(
        HotspotWorkflowRequest(source="weibo", rank=1, use_context=True, cover_template_id="tpl", page_count=2)
    )

    assert payload["title"] == "AI效率工具怎么选"
    assert payload["content"] == "先看场景，再看成本。"
    assert payload["images"] == ["/tmp/cover.jpg", "/tmp/page.jpg"]
    assert payload["hotspot_title"] == "AI效率工具爆火"
    assert payload["review"]["decision"] == "可发布"
    assert [step["agent"] for step in payload["agent_steps"]] == [
        "content_workflow_agent",
        "hot_agent",
        "writer_agent",
        "review_agent",
        "cover_agent",
    ]
