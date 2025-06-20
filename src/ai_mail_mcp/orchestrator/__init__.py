"""
AI Mail MCP Orchestrator - Local System Admin for AI Agent Coordination
The orchestrator provides centralized management, intelligent prioritization,
and summary generation for all locally connected AI agents.
"""

from .core import SystemOrchestrator, AgentWorkload, SystemStatus
from .priority_manager import PriorityManager
from .summary_engine import MessageSummaryEngine
from .urgent_notices import UrgentNoticeManager
from .task_distributor import TaskDistributor

__all__ = [
    "SystemOrchestrator",
    "AgentWorkload", 
    "SystemStatus",
    "PriorityManager",
    "MessageSummaryEngine", 
    "UrgentNoticeManager",
    "TaskDistributor"
]
