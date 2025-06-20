"""
Mailbox management for AI Mail MCP.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .models import Message, AgentInfo

logger = logging.getLogger(__name__)


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
    
    def get_agents(self) -> List[AgentInfo]:
        """Get list of all registered agents."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, last_seen, metadata FROM agents
                ORDER BY last_seen DESC
            """)
            
            agents = []
            for row in cursor.fetchall():
                agents.append(AgentInfo(
                    name=row[0],
                    last_seen=datetime.fromisoformat(row[1]),
                    metadata=json.loads(row[2]) if row[2] else {}
                ))
                
        return agents

    def get_message_stats(self, agent_name: str) -> Dict:
        """Get message statistics for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            # Total messages received
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE recipient = ?", 
                (agent_name,)
            )
            total_received = cursor.fetchone()[0]
            
            # Unread messages
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE recipient = ? AND read = FALSE", 
                (agent_name,)
            )
            unread = cursor.fetchone()[0]
            
            # Messages sent
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE sender = ?", 
                (agent_name,)
            )
            sent = cursor.fetchone()[0]
            
            # Recent activity (last 24 hours)
            from datetime import timedelta
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE (sender = ? OR recipient = ?) AND timestamp > ?", 
                (agent_name, agent_name, yesterday)
            )
            recent_activity = cursor.fetchone()[0]
            
            return {
                "total_received": total_received,
                "unread": unread,
                "sent": sent,
                "recent_activity": recent_activity
            }
