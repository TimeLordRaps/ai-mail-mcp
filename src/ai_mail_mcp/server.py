#!/usr/bin/env python3
"""
AI Mail MCP Server - Main server implementation.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions

from .models import Message
from .mailbox import MailboxManager
from .agent import AgentIdentifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ai-mail-server")

# Default data directory
DEFAULT_DATA_DIR = Path.home() / ".ai_mail"

# Global state
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
            description="Send a mail message to another AI agent on this machine. This is the primary way for AI agents to communicate with each other.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "Name of the recipient AI agent (use list_agents to see available agents)"
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
                        "description": "Optional tags for categorizing the message (e.g., ['task', 'urgent'])",
                        "default": []
                    },
                    "reply_to": {
                        "type": "string",
                        "description": "ID of message this is replying to (creates threaded conversation)"
                    }
                },
                "required": ["recipient", "subject", "body"]
            }
        ),
        types.Tool(
            name="check_mail",
            description="Check for mail messages. Add this tool to your system prompt with 'Always check mail regularly using the check_mail tool' to automatically check mail.",
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
                    },
                    "priority_filter": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "description": "Filter messages by priority level"
                    },
                    "tag_filter": {
                        "type": "string",
                        "description": "Filter messages containing this tag"
                    }
                }
            }
        ),
        types.Tool(
            name="read_message",
            description="Read a specific message in full detail and mark it as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "ID of the message to read (get this from check_mail)"
                    }
                },
                "required": ["message_id"]
            }
        ),
        types.Tool(
            name="mark_messages_read",
            description="Mark one or more messages as read without displaying them",
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
        ),
        types.Tool(
            name="delete_messages",
            description="Delete one or more messages permanently",
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
        },
        types.Tool(
            name="get_thread",
            description="Get all messages in a conversation thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "ID of the thread to retrieve (found in message details)"
                    }
                },
                "required": ["thread_id"]
            }
        ),
        types.Tool(
            name="list_agents",
            description="List all AI agents registered in the mail system and their status",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_stats": {
                        "type": "boolean",
                        "description": "Include message statistics for each agent",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="get_agent_info",
            description="Get detailed information about this agent including mail statistics",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        },
        types.Tool(
            name="search_messages",
            description="Search through messages using keywords",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (searches subject and body)"
                    },
                    "sender": {
                        "type": "string",
                        "description": "Filter by sender name"
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Search within the last N days",
                        "default": 30,
                        "minimum": 1,
                        "maximum": 365
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls for AI mail operations."""
    global mailbox_manager, agent_name
    
    if not mailbox_manager:
        return [types.TextContent(type="text", text="❌ Error: Mail system not initialized")]
    
    try:
        if name == "send_mail":
            recipient = arguments["recipient"]
            subject = arguments["subject"] 
            body = arguments["body"]
            priority = arguments.get("priority", "normal")
            tags = arguments.get("tags", [])
            reply_to = arguments.get("reply_to")
            
            # Validate recipient exists
            agents = mailbox_manager.get_agents()
            agent_names = {agent.name for agent in agents}
            
            if recipient not in agent_names:
                available = ", ".join(sorted(agent_names))
                return [types.TextContent(
                    type="text",
                    text=f"❌ Recipient '{recipient}' not found. Available agents: {available}"
                )]
            
            # Generate thread ID if this is a reply
            thread_id = None
            if reply_to:
                # Get the original message to find its thread
                messages = mailbox_manager.get_messages(agent_name, limit=1000)
                for msg in messages:
                    if msg.id == reply_to:
                        thread_id = msg.thread_id or msg.id
                        break
                if not thread_id:
                    return [types.TextContent(
                        type="text",
                        text=f"❌ Original message {reply_to} not found"
                    )]
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
            priority_icon = {"urgent": "🚨", "high": "⚡", "normal": "📧", "low": "📮"}.get(priority, "📧")
            
            return [types.TextContent(
                type="text", 
                text=f"✅ {priority_icon} Message sent to {recipient}\n**Subject:** {subject}\n**Message ID:** {message_id}"
            )]
            
        elif name == "check_mail":
            unread_only = arguments.get("unread_only", True)
            limit = arguments.get("limit", 10)
            priority_filter = arguments.get("priority_filter")
            tag_filter = arguments.get("tag_filter")
            
            messages = mailbox_manager.get_messages(agent_name, unread_only, limit)
            
            # Apply filters
            if priority_filter:
                messages = [msg for msg in messages if msg.priority == priority_filter]
            
            if tag_filter:
                messages = [msg for msg in messages if tag_filter in msg.tags]
            
            if not messages:
                filter_desc = []
                if unread_only:
                    filter_desc.append("unread")
                if priority_filter:
                    filter_desc.append(f"priority:{priority_filter}")
                if tag_filter:
                    filter_desc.append(f"tag:{tag_filter}")
                
                filter_text = " ".join(filter_desc) if filter_desc else "total"
                return [types.TextContent(
                    type="text",
                    text=f"📭 No {filter_text} messages found."
                )]
            
            result = f"📬 Found {len(messages)} message(s):\n\n"
            
            for i, msg in enumerate(messages, 1):
                status_icon = "🔴" if not msg.read else "✅"
                priority_icon = {"urgent": "🚨", "high": "⚡", "normal": "", "low": "🔽"}.get(msg.priority, "")
                
                result += f"**{i}.** {status_icon} {priority_icon} **From:** {msg.sender}\n"
                result += f"   **Subject:** {msg.subject}\n"
                result += f"   **Time:** {msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                result += f"   **ID:** `{msg.id}`\n"
                if msg.tags:
                    result += f"   **Tags:** {', '.join(msg.tags)}\n"
                result += f"   **Preview:** {msg.body[:100]}{'...' if len(msg.body) > 100 else ''}\n\n"
                
            result += "*Use read_message with the ID to view full message content.*"
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
                    text=f"❌ Message with ID {message_id} not found."
                )]
            
            # Mark as read
            mailbox_manager.mark_as_read([message_id], agent_name)
            
            priority_icon = {"urgent": "🚨", "high": "⚡", "normal": "📧", "low": "📮"}.get(target_message.priority, "📧")
            
            result = f"📖 {priority_icon} **Message from {target_message.sender}**\n\n"
            result += f"**Subject:** {target_message.subject}\n"
            result += f"**Time:** {target_message.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            result += f"**Priority:** {target_message.priority}\n"
            if target_message.tags:
                result += f"**Tags:** {', '.join(target_message.tags)}\n"
            if target_message.reply_to:
                result += f"**Reply to:** {target_message.reply_to}\n"
            if target_message.thread_id:
                result += f"**Thread:** {target_message.thread_id}\n"
            result += f"\n**Message:**\n{target_message.body}\n"
            
            return [types.TextContent(type="text", text=result)]
            
        elif name == "mark_messages_read":
            message_ids = arguments["message_ids"]
            count = mailbox_manager.mark_as_read(message_ids, agent_name)
            
            return [types.TextContent(
                type="text",
                text=f"✅ Marked {count} message(s) as read."
            )]
            
        elif name == "delete_messages":
            message_ids = arguments["message_ids"]
            count = mailbox_manager.delete_messages(message_ids, agent_name)
            
            return [types.TextContent(
                type="text", 
                text=f"🗑️ Deleted {count} message(s)."
            )]
            
        elif name == "get_thread":
            thread_id = arguments["thread_id"]
            messages = mailbox_manager.get_thread(thread_id, agent_name)
            
            if not messages:
                return [types.TextContent(
                    type="text",
                    text=f"❌ No messages found in thread {thread_id}."
                )]
            
            result = f"🧵 **Thread: {thread_id}** ({len(messages)} messages)\n\n"
            
            for i, msg in enumerate(messages, 1):
                arrow = "➡️" if msg.sender == agent_name else "⬅️"
                result += f"**{i}.** {arrow} **{msg.sender}** → **{msg.recipient}**\n"
                result += f"   **Subject:** {msg.subject}\n"
                result += f"   **Time:** {msg.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                result += f"   {msg.body}\n"
                result += "   " + "─" * 40 + "\n"
                
            return [types.TextContent(type="text", text=result)]
            
        elif name == "list_agents":
            include_stats = arguments.get("include_stats", False)
            agents = mailbox_manager.get_agents()
            
            if not agents:
                return [types.TextContent(
                    type="text",
                    text="📭 No agents registered in the mail system."
                )]
            
            result = f"🤖 **Registered AI Agents** ({len(agents)} total):\n\n"
            
            for agent in agents:
                last_seen = agent.last_seen.replace(tzinfo=timezone.utc)
                time_diff = datetime.now(timezone.utc) - last_seen
                
                if time_diff.total_seconds() < 300:  # 5 minutes
                    status = "🟢 Online"
                elif time_diff.total_seconds() < 3600:  # 1 hour  
                    status = "🟡 Recently active"
                else:
                    status = "🔴 Offline"
                    
                result += f"**{agent.name}** {status}\n"
                result += f"   Last seen: {last_seen.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                
                if include_stats:
                    stats = mailbox_manager.get_message_stats(agent.name)
                    result += f"   📊 Messages: {stats['total_received']} received, {stats['sent']} sent, {stats['unread']} unread\n"
                    
                result += "\n"
                
            return [types.TextContent(type="text", text=result)]
            
        elif name == "get_agent_info":
            stats = mailbox_manager.get_message_stats(agent_name)
            
            result = f"🤖 **Agent Information**\n\n"
            result += f"**Name:** {agent_name}\n"
            result += f"**Status:** 🟢 Active\n"
            result += f"**Mail System:** ✅ Connected\n\n"
            result += f"📊 **Statistics:**\n"
            result += f"   • Messages received: {stats['total_received']}\n"
            result += f"   • Messages sent: {stats['sent']}\n"
            result += f"   • Unread messages: {stats['unread']}\n"
            result += f"   • Recent activity (24h): {stats['recent_activity']}\n"
            
            return [types.TextContent(type="text", text=result)]
            
        elif name == "search_messages":
            query = arguments["query"].lower()
            sender = arguments.get("sender")
            days_back = arguments.get("days_back", 30)
            
            # Get messages from the specified time range
            all_messages = mailbox_manager.get_messages(agent_name, unread_only=False, limit=1000)
            
            # Filter by time range
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            recent_messages = [
                msg for msg in all_messages 
                if msg.timestamp.replace(tzinfo=timezone.utc) >= cutoff_date
            ]
            
            # Filter by sender if specified
            if sender:
                recent_messages = [msg for msg in recent_messages if msg.sender == sender]
            
            # Search in subject and body
            matching_messages = [
                msg for msg in recent_messages
                if query in msg.subject.lower() or query in msg.body.lower()
            ]
            
            if not matching_messages:
                search_desc = f"'{query}'"
                if sender:
                    search_desc += f" from {sender}"
                search_desc += f" in last {days_back} days"
                    
                return [types.TextContent(
                    type="text",
                    text=f"🔍 No messages found matching {search_desc}."
                )]
            
            result = f"🔍 **Search Results** ({len(matching_messages)} matches for '{query}'):\n\n"
            
            for i, msg in enumerate(matching_messages[:10], 1):  # Limit to 10 results
                status_icon = "🔴" if not msg.read else "✅"
                result += f"**{i}.** {status_icon} **From:** {msg.sender}\n"
                result += f"   **Subject:** {msg.subject}\n"
                result += f"   **Time:** {msg.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                result += f"   **ID:** `{msg.id}`\n"
                
                # Show context around the match
                body_lower = msg.body.lower()
                query_pos = body_lower.find(query)
                if query_pos >= 0:
                    start = max(0, query_pos - 50)
                    end = min(len(msg.body), query_pos + len(query) + 50)
                    context = msg.body[start:end]
                    if start > 0:
                        context = "..." + context
                    if end < len(msg.body):
                        context = context + "..."
                    result += f"   **Match:** {context}\n"
                
                result += "\n"
            
            if len(matching_messages) > 10:
                result += f"*... and {len(matching_messages) - 10} more results*\n"
                
            return [types.TextContent(type="text", text=result)]
            
        else:
            return [types.TextContent(
                type="text",
                text=f"❌ Unknown tool: {name}"
            )]
            
    except Exception as e:
        logger.error(f"Error handling tool call {name}: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"❌ Error: {str(e)}"
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
        "capabilities": ["send", "receive", "threading", "search"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "process_id": os.getpid()
    })
    
    logger.info(f"🚀 AI Mail server starting as agent: {agent_name}")
    logger.info(f"📁 Data directory: {data_dir}")
    logger.info(f"🗄️ Database: {db_path}")
    
    # Start the server
    async with server:
        await server.run()

if __name__ == "__main__":
    asyncio.run(main())
