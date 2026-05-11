"""
自主 Agent 抽象层。

services 仍负责底层能力；agents 负责多步任务规划、决策和编排。
"""

from src.agents.analytics_agent import AnalyticsAgent
from src.agents.cover_agent import CoverAgent, CoverResult
from src.agents.hot_agent import HotAgent, TopicCandidate
from src.agents.publish_agent import PublishAgent
from src.agents.review_agent import ReviewAgent
from src.agents.workflow_agent import ContentWorkflowAgent, HotspotWorkflowRequest
from src.agents.writer_agent import GeneratedCopy, WriterAgent

__all__ = [
    "AnalyticsAgent",
    "ContentWorkflowAgent",
    "CoverAgent",
    "CoverResult",
    "GeneratedCopy",
    "HotAgent",
    "HotspotWorkflowRequest",
    "PublishAgent",
    "ReviewAgent",
    "TopicCandidate",
    "WriterAgent",
]
