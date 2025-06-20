"""
Data models for AI Mail MCP.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Message(BaseModel):
    """Represents a mail message between AI agents."""
    id: str
    sender: str
    recipient: str
    subject: str
    body: str
    timestamp: datetime
    read: bool = False
    priority: str = "normal"  # low, normal, high, urgent
    tags: List[str] = []
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentInfo(BaseModel):
    """Information about an AI agent."""
    name: str
    last_seen: datetime
    metadata: dict = {}
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
