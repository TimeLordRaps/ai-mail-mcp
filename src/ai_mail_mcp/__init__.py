"""
AI Mail MCP - A Model Context Protocol server for AI agent mail communication.

This package provides a mailbox system that allows AI agents on the same machine
to send and receive messages from each other through a locally hosted service.
"""

__version__ = "1.0.0"
__author__ = "TimeLordRaps"
__email__ = "timelordraps@example.com"

from .models import Message
from .mailbox import MailboxManager
from .agent import AgentIdentifier
from .server import server

__all__ = [
    "Message",
    "MailboxManager", 
    "AgentIdentifier",
    "server",
]
