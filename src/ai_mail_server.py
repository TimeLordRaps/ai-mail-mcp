#!/usr/bin/env python3
"""
AI Mail MCP Server - A Model Context Protocol server for AI agent mail communication.

This server provides a mailbox system that allows AI agents on the same machine
to send and receive messages from each other through a locally hosted service.
"""

import asyncio
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import uuid
import socket
import psutil

import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-mail-server")

# Default data directory
DEFAULT_DATA_DIR = Path.home() / ".ai_mail"

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

class MailboxManager:
    """Manages the SQLite database for storing messages."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    read BOOLEAN DEFAULT FALSE,
                    priority TEXT DEFAULT 'normal',
                    tags TEXT,  -- JSON array of tags
                    reply_to TEXT,
                    thread_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    name TEXT PRIMARY KEY,
                    last_seen TEXT NOT NULL,
                    metadata TEXT  -- JSON metadata about the agent
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_recipient ON messages(recipient)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_thread ON messages(thread_id)")
            
    def send_message(self, message: Message) -> str:
        """Store a new message in the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO messages 
                (id, sender, recipient, subject, body, timestamp, read, priority, tags, reply_to, thread_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.sender,
                message.recipient,
                message.subject,
                message.body,
                message.timestamp.isoformat(),
                message.read,
                message.priority,
                json.dumps(message.tags),
                message.reply_to,
                message.thread_id
            ))
        return message.id
    
    def get_messages(self, recipient: str, unread_only: bool = False, limit: int = 50) -> List[Message]:
        """Retrieve messages for a specific recipient."""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT id, sender, recipient, subject, body, timestamp, read, priority, tags, reply_to, thread_id
                FROM messages 
                WHERE recipient = ?
            """
            params = [recipient]
            
            if unread_only:
                query += " AND read = FALSE"
                
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            messages = []
            
            for row in cursor.fetchall():
                messages.append(Message(
                    id=row[0],
                    sender=row[1],
                    recipient=row[2],
                    subject=row[3],
                    body=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    read=bool(row[6]),
                    priority=row[7],
                    tags=json.loads(row[8]) if row[8] else [],
                    reply_to=row[9],
                    thread_id=row[10]
                ))
                
        return messages
    
    def mark_as_read(self, message_ids: List[str], recipient: str) -> int:
        """Mark messages as read for a specific recipient."""
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join(['?' for _ in message_ids])
            cursor = conn.execute(f"""
                UPDATE messages 
                SET read = TRUE 
                WHERE id IN ({placeholders}) AND recipient = ?
            """, message_ids + [recipient])
            return cursor.rowcount
    
    def delete_messages(self, message_ids: List[str], recipient: str) -> int:
        """Delete messages for a specific recipient."""
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join(['?' for _ in message_ids])
            cursor = conn.execute(f"""
                DELETE FROM messages 
                WHERE id IN ({placeholders}) AND recipient = ?
            """, message_ids + [recipient])
            return cursor.rowcount
    
    def get_thread(self, thread_id: str, agent_name: str) -> List[Message]:
        """Get all messages in a thread that involve the agent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, sender, recipient, subject, body, timestamp, read, priority, tags, reply_to, thread_id
                FROM messages 
                WHERE thread_id = ? AND (sender = ? OR recipient = ?)
                ORDER BY timestamp ASC
            """, (thread_id, agent_name, agent_name))
            
            messages = []
            for row in cursor.fetchall():
                messages.append(Message(
                    id=row[0],
                    sender=row[1],
                    recipient=row[2],
                    subject=row[3],
                    body=row[4],
                    timestamp=datetime.fromisoformat(row[5]),
                    read=bool(row[6]),
                    priority=row[7],
                    tags=json.loads(row[8]) if row[8] else [],
                    reply_to=row[9],
                    thread_id=row[10]
                ))
                
        return messages
    
    def register_agent(self, agent_name: str, metadata: Optional[Dict] = None):
        """Register an agent and update their last seen time."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO agents (name, last_seen, metadata)
                VALUES (?, ?, ?)
            """, (
                agent_name,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(metadata or {})
            ))
    
    def get_agents(self) -> List[Dict]:
        """Get list of all registered agents."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, last_seen, metadata FROM agents
                ORDER BY last_seen DESC
            """)
            
            agents = []
            for row in cursor.fetchall():
                agents.append({
                    'name': row[0],
                    'last_seen': row[1],
                    'metadata': json.loads(row[2]) if row[2] else {}
                })
                
        return agents

class AgentIdentifier:
    """Manages agent identification and naming."""
    
    @staticmethod
    def detect_agent_name() -> str:
        """Attempt to detect the current agent's name from environment and process info."""
        
        # Check environment variables for common agent identifiers
        env_vars = [
            'AI_AGENT_NAME',
            'AGENT_NAME', 
            'MCP_CLIENT_NAME',
            'VSCODE_AGENT_NAME',
            'CURSOR_AGENT_NAME'
        ]
        
        for var in env_vars:
            if os.getenv(var):
                return os.getenv(var)
        
        # Try to detect from process information
        try:
            current_process = psutil.Process()
            parent = current_process.parent()
            
            if parent:
                parent_name = parent.name().lower()
                
                # Common agent process names
                agent_mappings = {
                    'code': 'vscode-copilot',
                    'cursor': 'cursor-ai',
                    'zed': 'zed-ai',
                    'claude': 'claude-desktop',
                    'chatgpt': 'chatgpt-desktop',
                    'python': 'python-agent'
                }
                
                for process_name, agent_name in agent_mappings.items():
                    if process_name in parent_name:
                        return agent_name
                        
        except Exception as e:
            logger.debug(f"Could not detect agent from process: {e}")
        
        # Fallback to hostname-based naming
        hostname = socket.gethostname()
        return f"agent-{hostname}"
    
    @staticmethod
    def ensure_unique_name(mailbox: MailboxManager, preferred_name: str) -> str:
        """Ensure the agent name is unique by adding a suffix if needed."""
        agents = mailbox.get_agents()
        existing_names = {agent['name'] for agent in agents}
        
        if preferred_name not in existing_names:
            return preferred_name
        
        # Extract base name and find next available number
        if preferred_name.endswith(tuple(f'-{i}' for i in range(1, 100))):
            base_name = '-'.join(preferred_name.split('-')[:-1])
        else:
            base_name = preferred_name
        
        counter = 1
        while f"{base_name}-{counter}" in existing_names:
            counter += 1
            
        return f"{base_name}-{counter}"

# Global mailbox manager
mailbox_manager: Optional[MailboxManager] = None
agent_name: str = ""

# MCP Server
server = Server("ai-mail-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for AI mail operations."""
    return [
        types.Tool(
            name="send_mail",
            description="Send a mail message to another AI agent on this machine",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Name of the recipient AI agent"
                    },
                    "subject": {
                        "type": "string", 
                        "description": "Subject line of the message"
                    },
                    "body": {
                        "type": "string",
                        "description": "Body content of the message"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "description": "Message priority level",
                        "default": "normal"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for categorizing the message",
                        "default": []
                    },
                    "reply_to": {
                        "type": "string",
                        "description": "ID of message this is replying to (optional)"
                    }
                },
                "required": ["recipient", "subject", "body"]
            }
        ),
        types.Tool(
            name="check_mail",
            description="Check for new mail messages. Add this to your system prompt to automatically check mail regularly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "unread_only": {
                        "type": "boolean",
                        "description": "Only return unread messages",
                        "default": True
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of messages to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    }
                }
            }
        ),
        types.Tool(
            name="read_message",
            description="Read a specific message and mark it as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "ID of the message to read"
                    }
                },
                "required": ["message_id"]
            }
        ),
        types.Tool(
            name="mark_messages_read",
            description="Mark one or more messages as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of message IDs to mark as read"
                    }
                },
                "required": ["message_ids"]
            }
        },
        types.Tool(
            name="delete_messages",
            description="Delete one or more messages",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of message IDs to delete"
                    }
                },
                "required": ["message_ids"]
            }
        ),
        types.Tool(
            name="get_thread",
            description="Get all messages in a conversation thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "ID of the thread to retrieve"
                    }
                },
                "required": ["thread_id"]
            }
        },
        types.Tool(
            name="list_agents",
            description="List all AI agents registered in the mail system",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        },
        types.Tool(
            name="get_agent_info",
            description="Get information about this agent",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        }
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls for AI mail operations."""
    global mailbox_manager, agent_name
    
    if not mailbox_manager:
        return [types.TextContent(type="text", text="Error: Mail system not initialized")]
    
    try:
        if name == "send_mail":
            recipient = arguments["recipient"]
            subject = arguments["subject"] 
            body = arguments["body"]
            priority = arguments.get("priority", "normal")
            tags = arguments.get("tags", [])
            reply_to = arguments.get("reply_to")
            
            # Generate thread ID if this is a reply
            thread_id = None
            if reply_to:
                # Get the original message to find its thread
                messages = mailbox_manager.get_messages(agent_name, limit=1000)
                for msg in messages:
                    if msg.id == reply_to:
                        thread_id = msg.thread_id or msg.id
                        break
            else:
                thread_id = str(uuid.uuid4())
            
            message = Message(
                id=str(uuid.uuid4()),
                sender=agent_name,
                recipient=recipient,
                subject=subject,
                body=body,
                timestamp=datetime.now(timezone.utc),
                priority=priority,
                tags=tags,
                reply_to=reply_to,
                thread_id=thread_id
            )
            
            message_id = mailbox_manager.send_message(message)
            return [types.TextContent(
                type="text", 
                text=f"Message sent successfully to {recipient}. Message ID: {message_id}"
            )]
            
        elif name == "check_mail":
            unread_only = arguments.get("unread_only", True)
            limit = arguments.get("limit", 10)
            
            messages = mailbox_manager.get_messages(agent_name, unread_only, limit)
            
            if not messages:
                status = "unread" if unread_only else "total"
                return [types.TextContent(
                    type="text",
                    text=f"No {status} messages found."
                )]
            
            result = f"Found {len(messages)} {'unread' if unread_only else ''} message(s):\n\n"
            
            for msg in messages:
                status_icon = "📧" if not msg.read else "✉️"
                priority_icon = {"urgent": "🚨", "high": "⚡", "normal": "", "low": "🔽"}.get(msg.priority, "")
                
                result += f"{status_icon} {priority_icon} **From:** {msg.sender}\n"
                result += f"**Subject:** {msg.subject}\n"
                result += f"**Time:** {msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                result += f"**ID:** {msg.id}\n"
                if msg.tags:
                    result += f"**Tags:** {', '.join(msg.tags)}\n"
                result += f"**Preview:** {msg.body[:100]}{'...' if len(msg.body) > 100 else ''}\n\n"
                
            return [types.TextContent(type="text", text=result)]
            
        elif name == "read_message":
            message_id = arguments["message_id"]
            
            # Get the specific message
            messages = mailbox_manager.get_messages(agent_name, limit=1000)
            target_message = None
            
            for msg in messages:
                if msg.id == message_id:
                    target_message = msg
                    break
                    
            if not target_message:
                return [types.TextContent(
                    type="text",
                    text=f"Message with ID {message_id} not found."
                )]
            
            # Mark as read
            mailbox_manager.mark_as_read([message_id], agent_name)
            
            result = f"📖 **Message from {target_message.sender}**\n\n"
            result += f"**Subject:** {target_message.subject}\n"
            result += f"**Time:** {target_message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            result += f"**Priority:** {target_message.priority}\n"
            if target_message.tags:
                result += f"**Tags:** {', '.join(target_message.tags)}\n"
            if target_message.reply_to:
                result += f"**Reply to:** {target_message.reply_to}\n"
            result += f"\n**Message:**\n{target_message.body}\n"
            
            return [types.TextContent(type="text", text=result)]
            
        elif name == "mark_messages_read":
            message_ids = arguments["message_ids"]
            count = mailbox_manager.mark_as_read(message_ids, agent_name)
            
            return [types.TextContent(
                type="text",
                text=f"Marked {count} message(s) as read."
            )]
            
        elif name == "delete_messages":
            message_ids = arguments["message_ids"]
            count = mailbox_manager.delete_messages(message_ids, agent_name)
            
            return [types.TextContent(
                type="text", 
                text=f"Deleted {count} message(s)."
            )]
            
        elif name == "get_thread":
            thread_id = arguments["thread_id"]
            messages = mailbox_manager.get_thread(thread_id, agent_name)
            
            if not messages:
                return [types.TextContent(
                    type="text",
                    text=f"No messages found in thread {thread_id}."
                )]
            
            result = f"🧵 **Thread: {thread_id}**\n\n"
            
            for i, msg in enumerate(messages):
                result += f"**Message {i+1}** ({msg.timestamp.strftime('%Y-%m-%d %H:%M')})\n"
                result += f"**From:** {msg.sender} → **To:** {msg.recipient}\n"
                result += f"**Subject:** {msg.subject}\n"
                result += f"{msg.body}\n"
                result += "---\n"
                
            return [types.TextContent(type="text", text=result)]
            
        elif name == "list_agents":
            agents = mailbox_manager.get_agents()
            
            if not agents:
                return [types.TextContent(
                    type="text",
                    text="No agents registered in the mail system."
                )]
            
            result = "🤖 **Registered AI Agents:**\n\n"
            
            for agent in agents:
                last_seen = datetime.fromisoformat(agent['last_seen'])
                time_diff = datetime.now(timezone.utc) - last_seen.replace(tzinfo=timezone.utc)
                
                if time_diff.total_seconds() < 300:  # 5 minutes
                    status = "🟢 Online"
                elif time_diff.total_seconds() < 3600:  # 1 hour  
                    status = "🟡 Recently active"
                else:
                    status = "🔴 Offline"
                    
                result += f"**{agent['name']}** {status}\n"
                result += f"Last seen: {last_seen.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
            return [types.TextContent(type="text", text=result)]
            
        elif name == "get_agent_info":
            return [types.TextContent(
                type="text",
                text=f"🤖 **Agent Information**\n\n**Name:** {agent_name}\n**Status:** Active\n**Mail System:** Connected"
            )]
            
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        logger.error(f"Error handling tool call {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    """Main entry point for the AI Mail MCP server."""
    global mailbox_manager, agent_name
    
    # Initialize data directory
    data_dir = Path(os.getenv("AI_MAIL_DATA_DIR", DEFAULT_DATA_DIR))
    db_path = data_dir / "mailbox.db"
    
    # Initialize mailbox manager
    mailbox_manager = MailboxManager(db_path)
    
    # Detect and ensure unique agent name
    detected_name = AgentIdentifier.detect_agent_name()
    agent_name = AgentIdentifier.ensure_unique_name(mailbox_manager, detected_name)
    
    # Register this agent
    mailbox_manager.register_agent(agent_name, {
        "version": "1.0.0",
        "capabilities": ["send", "receive", "threading"],
        "started_at": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"AI Mail server starting as agent: {agent_name}")
    logger.info(f"Data directory: {data_dir}")
    
    # Start the server
    async with server:
        await server.run()

if __name__ == "__main__":
    asyncio.run(main())
