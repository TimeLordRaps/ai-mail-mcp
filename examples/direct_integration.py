#!/usr/bin/env python3
"""
Example script showing how to directly integrate with AI Mail MCP.

This demonstrates using the mailbox system without the MCP server,
useful for custom integrations or testing.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ai_mail_mcp.mailbox import MailboxManager
from ai_mail_mcp.models import Message
from ai_mail_mcp.agent import AgentIdentifier


async def main():
    """Example integration with AI Mail MCP."""
    
    print("🚀 AI Mail MCP Direct Integration Example")
    print("=" * 50)
    
    # Set up mailbox
    db_path = Path("./example_mailbox.db")
    mailbox = MailboxManager(db_path)
    
    # Register example agents
    agent_a = "example-agent-a"
    agent_b = "example-agent-b" 
    
    mailbox.register_agent(agent_a, {
        "version": "1.0.0",
        "type": "example",
        "capabilities": ["send", "receive"]
    })
    
    mailbox.register_agent(agent_b, {
        "version": "1.0.0", 
        "type": "example",
        "capabilities": ["send", "receive"]
    })
    
    print(f"📝 Registered agents: {agent_a}, {agent_b}")
    
    # Send a message from A to B
    message = Message(
        id=str(uuid.uuid4()),
        sender=agent_a,
        recipient=agent_b,
        subject="Hello from Python!",
        body="This is a direct integration example showing how to send messages between AI agents.",
        timestamp=datetime.now(timezone.utc),
        priority="normal",
        tags=["example", "integration", "python"]
    )
    
    message_id = mailbox.send_message(message)
    print(f"📧 Sent message: {message_id}")
    
    # Check for messages as agent B
    messages = mailbox.get_messages(agent_b, unread_only=True)
    print(f"📬 Agent B received {len(messages)} message(s)")
    
    for msg in messages:
        print(f"   From: {msg.sender}")
        print(f"   Subject: {msg.subject}")
        print(f"   Body: {msg.body}")
        print(f"   Tags: {', '.join(msg.tags)}")
        print(f"   Time: {msg.timestamp}")
        
        # Mark as read
        mailbox.mark_as_read([msg.id], agent_b)
        print(f"   ✅ Marked as read")
    
    # Send a reply
    reply = Message(
        id=str(uuid.uuid4()),
        sender=agent_b,
        recipient=agent_a,
        subject="Re: Hello from Python!",
        body="Thanks for the message! This integration example is working great.",
        timestamp=datetime.now(timezone.utc),
        reply_to=message_id,
        thread_id=message_id,  # Use original message ID as thread
        priority="normal",
        tags=["reply", "example"]
    )
    
    reply_id = mailbox.send_message(reply)
    print(f"💬 Sent reply: {reply_id}")
    
    # Check thread
    thread_messages = mailbox.get_thread(message_id, agent_a)
    print(f"🧵 Thread has {len(thread_messages)} message(s)")
    
    # Show agent statistics
    stats_a = mailbox.get_message_stats(agent_a)
    stats_b = mailbox.get_message_stats(agent_b)
    
    print("\n📊 Agent Statistics:")
    print(f"   {agent_a}: {stats_a}")
    print(f"   {agent_b}: {stats_b}")
    
    # List all agents
    agents = mailbox.get_agents()
    print(f"\n🤖 Total agents registered: {len(agents)}")
    for agent in agents:
        print(f"   - {agent.name} (last seen: {agent.last_seen})")
    
    print("\n✅ Integration example completed successfully!")
    print(f"📁 Database saved to: {db_path.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
