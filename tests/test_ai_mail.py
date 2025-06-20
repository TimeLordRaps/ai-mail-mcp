"""
Tests for AI Mail MCP server.
"""

import asyncio
import json
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_mail_mcp.models import Message, AgentInfo
from ai_mail_mcp.mailbox import MailboxManager
from ai_mail_mcp.agent import AgentIdentifier


class TestMessage:
    """Test Message model."""
    
    def test_message_creation(self):
        """Test basic message creation."""
        msg = Message(
            id="test-123",
            sender="agent-a",
            recipient="agent-b",
            subject="Test Subject",
            body="Test body content",
            timestamp=datetime.now(timezone.utc)
        )
        
        assert msg.id == "test-123"
        assert msg.sender == "agent-a"
        assert msg.recipient == "agent-b"
        assert msg.subject == "Test Subject"
        assert msg.body == "Test body content"
        assert msg.read is False
        assert msg.priority == "normal"
        assert msg.tags == []
        assert msg.reply_to is None
        assert msg.thread_id is None
    
    def test_message_with_all_fields(self):
        """Test message with all optional fields."""
        msg = Message(
            id="test-456",
            sender="agent-a",
            recipient="agent-b", 
            subject="Test Subject",
            body="Test body",
            timestamp=datetime.now(timezone.utc),
            read=True,
            priority="high",
            tags=["urgent", "task"],
            reply_to="original-123",
            thread_id="thread-456"
        )
        
        assert msg.read is True
        assert msg.priority == "high"
        assert msg.tags == ["urgent", "task"]
        assert msg.reply_to == "original-123"
        assert msg.thread_id == "thread-456"


class TestMailboxManager:
    """Test MailboxManager functionality."""
    
    @pytest.fixture
    def temp_mailbox(self):
        """Create a temporary mailbox for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_mailbox.db"
            yield MailboxManager(db_path)
    
    def test_database_initialization(self, temp_mailbox):
        """Test that database is properly initialized."""
        # Check that tables exist
        with sqlite3.connect(temp_mailbox.db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('messages', 'agents')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
        assert "messages" in tables
        assert "agents" in tables
    
    def test_send_message(self, temp_mailbox):
        """Test sending a message."""
        message = Message(
            id="test-001",
            sender="agent-a",
            recipient="agent-b",
            subject="Test Message",
            body="This is a test message",
            timestamp=datetime.now(timezone.utc),
            tags=["test", "demo"]
        )
        
        message_id = temp_mailbox.send_message(message)
        assert message_id == "test-001"
        
        # Verify message is in database
        with sqlite3.connect(temp_mailbox.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE id = ?", 
                (message_id,)
            )
            count = cursor.fetchone()[0]
            
        assert count == 1
    
    def test_get_messages(self, temp_mailbox):
        """Test retrieving messages."""
        # Send test messages
        messages = []
        for i in range(5):
            msg = Message(
                id=f"test-{i:03d}",
                sender="agent-a",
                recipient="agent-b",
                subject=f"Test Message {i}",
                body=f"Body {i}",
                timestamp=datetime.now(timezone.utc),
                read=(i % 2 == 0)  # Alternate read/unread
            )
            messages.append(msg)
            temp_mailbox.send_message(msg)
        
        # Get all messages
        retrieved = temp_mailbox.get_messages("agent-b", unread_only=False)
        assert len(retrieved) == 5
        
        # Get only unread messages  
        unread = temp_mailbox.get_messages("agent-b", unread_only=True)
        assert len(unread) == 2  # Messages 1 and 3 are unread
        
        # Test limit
        limited = temp_mailbox.get_messages("agent-b", unread_only=False, limit=3)
        assert len(limited) == 3
    
    def test_mark_as_read(self, temp_mailbox):
        """Test marking messages as read."""
        # Send test message
        message = Message(
            id="test-read",
            sender="agent-a",
            recipient="agent-b",
            subject="Test Read",
            body="Test body",
            timestamp=datetime.now(timezone.utc),
            read=False
        )
        temp_mailbox.send_message(message)
        
        # Mark as read
        count = temp_mailbox.mark_as_read(["test-read"], "agent-b")
        assert count == 1
        
        # Verify it's marked as read
        messages = temp_mailbox.get_messages("agent-b", unread_only=True)
        assert len(messages) == 0
    
    def test_delete_messages(self, temp_mailbox):
        """Test deleting messages."""
        # Send test messages
        msg_ids = []
        for i in range(3):
            msg = Message(
                id=f"delete-{i}",
                sender="agent-a", 
                recipient="agent-b",
                subject=f"Delete Test {i}",
                body="To be deleted",
                timestamp=datetime.now(timezone.utc)
            )
            temp_mailbox.send_message(msg)
            msg_ids.append(msg.id)
        
        # Delete first two messages
        count = temp_mailbox.delete_messages(msg_ids[:2], "agent-b")
        assert count == 2
        
        # Verify only one message remains
        remaining = temp_mailbox.get_messages("agent-b", unread_only=False)
        assert len(remaining) == 1
        assert remaining[0].id == "delete-2"
    
    def test_threading(self, temp_mailbox):
        """Test message threading functionality."""
        thread_id = str(uuid.uuid4())
        
        # Send original message
        original = Message(
            id="thread-original",
            sender="agent-a",
            recipient="agent-b", 
            subject="Original Message",
            body="Start of thread",
            timestamp=datetime.now(timezone.utc),
            thread_id=thread_id
        )
        temp_mailbox.send_message(original)
        
        # Send reply
        reply = Message(
            id="thread-reply",
            sender="agent-b",
            recipient="agent-a",
            subject="Re: Original Message", 
            body="Reply to original",
            timestamp=datetime.now(timezone.utc),
            reply_to="thread-original",
            thread_id=thread_id
        )
        temp_mailbox.send_message(reply)
        
        # Get thread
        thread_messages = temp_mailbox.get_thread(thread_id, "agent-a")
        assert len(thread_messages) == 2
        assert thread_messages[0].id == "thread-original"
        assert thread_messages[1].id == "thread-reply"
    
    def test_agent_registration(self, temp_mailbox):
        """Test agent registration."""
        metadata = {
            "version": "1.0.0",
            "capabilities": ["send", "receive"]
        }
        
        temp_mailbox.register_agent("test-agent", metadata)
        
        agents = temp_mailbox.get_agents()
        assert len(agents) == 1
        assert agents[0].name == "test-agent"
        assert agents[0].metadata == metadata
    
    def test_message_stats(self, temp_mailbox):
        """Test message statistics."""
        # Send messages from and to test agent
        for i in range(3):
            # Messages received
            msg = Message(
                id=f"received-{i}",
                sender="other-agent",
                recipient="test-agent",
                subject=f"Message {i}",
                body="Body",
                timestamp=datetime.now(timezone.utc),
                read=(i == 0)  # First message is read
            )
            temp_mailbox.send_message(msg)
            
            # Messages sent
            msg = Message(
                id=f"sent-{i}",
                sender="test-agent",
                recipient="other-agent",
                subject=f"Sent {i}",
                body="Body",
                timestamp=datetime.now(timezone.utc)
            )
            temp_mailbox.send_message(msg)
        
        stats = temp_mailbox.get_message_stats("test-agent")
        assert stats["total_received"] == 3
        assert stats["unread"] == 2
        assert stats["sent"] == 3
        assert stats["recent_activity"] == 6  # All messages are recent


class TestAgentIdentifier:
    """Test AgentIdentifier functionality."""
    
    def test_detect_from_environment(self):
        """Test agent name detection from environment variables."""
        with patch.dict('os.environ', {'AI_AGENT_NAME': 'test-agent'}):
            name = AgentIdentifier.detect_agent_name()
            assert name == 'test-agent'
    
    def test_detect_fallback(self):
        """Test fallback agent name detection."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('socket.gethostname', return_value='test-host'):
                name = AgentIdentifier.detect_agent_name()
                assert name == 'agent-test-host'
    
    @patch('ai_mail_mcp.agent.psutil')
    def test_detect_from_process(self, mock_psutil):
        """Test agent name detection from process information."""
        # Mock process hierarchy
        mock_parent = Mock()
        mock_parent.name.return_value = 'code.exe'
        
        mock_process = Mock()
        mock_process.parent.return_value = mock_parent
        
        mock_psutil.Process.return_value = mock_process
        
        name = AgentIdentifier.detect_agent_name()
        assert name == 'vscode-copilot'
    
    def test_ensure_unique_name(self, temp_mailbox):
        """Test unique name generation."""
        # Register some agents
        temp_mailbox.register_agent("test-agent", {})
        temp_mailbox.register_agent("test-agent-1", {})
        
        # Should get test-agent-2
        unique_name = AgentIdentifier.ensure_unique_name(
            temp_mailbox, "test-agent"
        )
        assert unique_name == "test-agent-2"
        
        # Should keep unused name
        unique_name = AgentIdentifier.ensure_unique_name(
            temp_mailbox, "unused-agent"
        )
        assert unique_name == "unused-agent"
    
    def test_validate_agent_name(self):
        """Test agent name validation."""
        # Valid names
        assert AgentIdentifier.validate_agent_name("agent-1")
        assert AgentIdentifier.validate_agent_name("my_agent")
        assert AgentIdentifier.validate_agent_name("agent.test")
        
        # Invalid names
        assert not AgentIdentifier.validate_agent_name("")
        assert not AgentIdentifier.validate_agent_name("a")  # Too short
        assert not AgentIdentifier.validate_agent_name("x" * 65)  # Too long
        assert not AgentIdentifier.validate_agent_name("-agent")  # Starts with dash
        assert not AgentIdentifier.validate_agent_name("agent-")  # Ends with dash
        assert not AgentIdentifier.validate_agent_name("agent@test")  # Invalid chars
    
    def test_suggest_agent_names(self):
        """Test agent name suggestions."""
        existing = {"test-agent", "test-agent-1", "test-agent-ai"}
        suggestions = AgentIdentifier.suggest_agent_names(
            "test-agent", existing, count=3
        )
        
        assert len(suggestions) == 3
        assert "test-agent-2" in suggestions
        assert all(name not in existing for name in suggestions)


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests."""
    
    @pytest.fixture
    async def mail_system(self):
        """Set up a complete mail system for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "integration_test.db"
            mailbox = MailboxManager(db_path)
            
            # Register test agents
            mailbox.register_agent("agent-a", {"type": "test"})
            mailbox.register_agent("agent-b", {"type": "test"})
            
            yield mailbox
    
    async def test_message_flow(self, mail_system):
        """Test complete message flow between agents."""
        # Agent A sends message to Agent B
        msg1 = Message(
            id="flow-001",
            sender="agent-a",
            recipient="agent-b",
            subject="Task Assignment",
            body="Please handle the user authentication task",
            timestamp=datetime.now(timezone.utc),
            priority="high",
            tags=["task", "auth"]
        )
        mail_system.send_message(msg1)
        
        # Agent B checks mail
        messages = mail_system.get_messages("agent-b", unread_only=True)
        assert len(messages) == 1
        assert messages[0].subject == "Task Assignment"
        
        # Agent B marks as read and replies
        mail_system.mark_as_read(["flow-001"], "agent-b")
        
        reply = Message(
            id="flow-002",
            sender="agent-b", 
            recipient="agent-a",
            subject="Re: Task Assignment",
            body="I'll start working on the authentication module",
            timestamp=datetime.now(timezone.utc),
            reply_to="flow-001",
            thread_id=msg1.id  # Use original message ID as thread ID
        )
        mail_system.send_message(reply)
        
        # Agent A checks for replies
        replies = mail_system.get_messages("agent-a", unread_only=True)
        assert len(replies) == 1
        assert replies[0].reply_to == "flow-001"
        
        # Check thread
        thread = mail_system.get_thread(msg1.id, "agent-a")
        assert len(thread) == 2
    
    async def test_multi_agent_broadcast(self, mail_system):
        """Test broadcasting to multiple agents."""
        # Register more agents
        for i in range(3, 6):
            mail_system.register_agent(f"agent-{chr(97+i)}", {"type": "test"})
        
        agents = mail_system.get_agents()
        agent_names = [agent.name for agent in agents]
        
        # Broadcast message
        broadcast_id = str(uuid.uuid4())
        for recipient in agent_names:
            if recipient != "agent-a":  # Don't send to self
                msg = Message(
                    id=f"broadcast-{recipient}",
                    sender="agent-a",
                    recipient=recipient,
                    subject="Team Update",
                    body="Weekly team sync scheduled for tomorrow",
                    timestamp=datetime.now(timezone.utc),
                    thread_id=broadcast_id,
                    tags=["broadcast", "meeting"]
                )
                mail_system.send_message(msg)
        
        # Each agent should have received the message
        for recipient in agent_names:
            if recipient != "agent-a":
                messages = mail_system.get_messages(recipient, unread_only=True)
                assert len(messages) == 1
                assert messages[0].subject == "Team Update"


@pytest.mark.slow
class TestPerformance:
    """Performance tests."""
    
    @pytest.fixture
    def perf_mailbox(self):
        """Create mailbox for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "perf_test.db"
            yield MailboxManager(db_path)
    
    def test_bulk_message_performance(self, perf_mailbox):
        """Test performance with bulk messages."""
        import time
        
        start_time = time.time()
        
        # Send 1000 messages
        for i in range(1000):
            msg = Message(
                id=f"perf-{i:04d}",
                sender="sender-agent",
                recipient="recipient-agent",
                subject=f"Performance Test {i}",
                body=f"This is performance test message {i}" * 10,
                timestamp=datetime.now(timezone.utc)
            )
            perf_mailbox.send_message(msg)
        
        send_time = time.time() - start_time
        
        # Retrieve all messages
        start_time = time.time()
        messages = perf_mailbox.get_messages("recipient-agent", limit=1000)
        retrieve_time = time.time() - start_time
        
        assert len(messages) == 1000
        assert send_time < 10.0  # Should send 1000 messages in under 10 seconds
        assert retrieve_time < 2.0  # Should retrieve 1000 messages in under 2 seconds
        
        # Test messages per second
        mps = 1000 / send_time
        assert mps > 100  # Should handle at least 100 messages per second
    
    def test_concurrent_access(self, perf_mailbox):
        """Test concurrent database access."""
        import threading
        import time
        
        results = []
        
        def worker(worker_id):
            """Worker function for concurrent testing."""
            start_time = time.time()
            
            for i in range(100):
                msg = Message(
                    id=f"worker-{worker_id}-{i:03d}",
                    sender=f"worker-{worker_id}",
                    recipient="test-recipient",
                    subject=f"Concurrent Test {i}",
                    body="Concurrent access test",
                    timestamp=datetime.now(timezone.utc)
                )
                perf_mailbox.send_message(msg)
            
            duration = time.time() - start_time
            results.append(duration)
        
        # Start 5 concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all workers to complete
        for thread in threads:
            thread.join()
        
        # Verify all messages were sent
        messages = perf_mailbox.get_messages("test-recipient", limit=1000)
        assert len(messages) == 500  # 5 workers * 100 messages each
        
        # Check performance
        max_duration = max(results)
        assert max_duration < 5.0  # Each worker should complete in under 5 seconds


if __name__ == "__main__":
    pytest.main([__file__])
