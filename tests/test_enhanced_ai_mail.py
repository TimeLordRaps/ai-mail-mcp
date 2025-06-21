#!/usr/bin/env python3
"""
Enhanced Python tests for AI Mail MCP Server
Test coverage expansion for better CI/CD integration
"""

import pytest
import asyncio
import json
import tempfile
import sqlite3
import uuid
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_mail_mcp.models import Message, AgentInfo
from ai_mail_mcp.mailbox import MailboxManager
from ai_mail_mcp.agent import AgentIdentifier
from ai_mail_mcp.monitor import SystemMonitor


class TestEnhancedMessage:
    """Enhanced tests for Message model with edge cases."""
    
    def test_message_with_unicode_content(self):
        """Test message with Unicode and special characters."""
        msg = Message(
            id="unicode-test",
            sender="agent-ñ",
            recipient="agent-中文",
            subject="Test with émojis 🚀 and spëcial chars",
            body="Message with Unicode: ñáéíóú, 中文, русский, العربية, 🎉🔥💯",
            timestamp=datetime.now(timezone.utc),
            priority="high",
            tags=["unicode", "测试", "тест"]
        )
        
        assert msg.subject == "Test with émojis 🚀 and spëcial chars"
        assert "中文" in msg.body
        assert "测试" in msg.tags
    
    def test_message_with_very_long_content(self):
        """Test message with very long content."""
        long_content = "x" * 10000  # 10KB content
        
        msg = Message(
            id="long-test",
            sender="sender",
            recipient="recipient",
            subject="Long message test",
            body=long_content,
            timestamp=datetime.now(timezone.utc)
        )
        
        assert len(msg.body) == 10000
        assert msg.body == long_content
    
    def test_message_serialization(self):
        """Test message JSON serialization/deserialization."""
        msg = Message(
            id="serialize-test",
            sender="agent-a",
            recipient="agent-b",
            subject="Serialization Test",
            body="Test content",
            timestamp=datetime.now(timezone.utc),
            priority="urgent",
            tags=["test", "serialization"],
            read=True
        )
        
        # Convert to dict (simulating JSON serialization)
        msg_dict = {
            "id": msg.id,
            "sender": msg.sender,
            "recipient": msg.recipient,
            "subject": msg.subject,
            "body": msg.body,
            "timestamp": msg.timestamp.isoformat(),
            "priority": msg.priority,
            "tags": msg.tags,
            "read": msg.read,
            "reply_to": msg.reply_to,
            "thread_id": msg.thread_id
        }
        
        # Reconstruct from dict
        reconstructed = Message(
            id=msg_dict["id"],
            sender=msg_dict["sender"],
            recipient=msg_dict["recipient"],
            subject=msg_dict["subject"],
            body=msg_dict["body"],
            timestamp=datetime.fromisoformat(msg_dict["timestamp"].replace('Z', '+00:00')),
            priority=msg_dict["priority"],
            tags=msg_dict["tags"],
            read=msg_dict["read"],
            reply_to=msg_dict["reply_to"],
            thread_id=msg_dict["thread_id"]
        )
        
        assert reconstructed.id == msg.id
        assert reconstructed.subject == msg.subject
        assert reconstructed.priority == msg.priority


class TestEnhancedMailboxManager:
    """Enhanced tests for MailboxManager with stress testing and edge cases."""
    
    @pytest.fixture
    def enhanced_mailbox(self):
        """Create enhanced mailbox with performance monitoring."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "enhanced_test.db"
            mailbox = MailboxManager(db_path)
            yield mailbox
    
    def test_bulk_message_insertion_performance(self, enhanced_mailbox):
        """Test bulk message insertion performance."""
        start_time = time.time()
        
        # Insert 1000 messages
        messages = []
        for i in range(1000):
            msg = Message(
                id=f"bulk-{i:04d}",
                sender=f"sender-{i % 10}",
                recipient="test-recipient",
                subject=f"Bulk Message {i}",
                body=f"Content for bulk message {i}" * 10,  # ~250 chars
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=i),
                priority=["urgent", "high", "normal", "low"][i % 4],
                tags=[f"tag-{i % 5}", f"category-{i % 3}"]
            )
            messages.append(msg)
            enhanced_mailbox.send_message(msg)
        
        insertion_time = time.time() - start_time
        
        # Verify all messages were inserted
        retrieved = enhanced_mailbox.get_messages("test-recipient", unread_only=False, limit=1000)
        assert len(retrieved) == 1000
        
        # Performance check: should insert 1000 messages in under 5 seconds
        assert insertion_time < 5.0
        
        # Throughput should be at least 200 messages per second
        throughput = 1000 / insertion_time
        assert throughput > 200
    
    def test_concurrent_database_access(self, enhanced_mailbox):
        """Test concurrent database access with threading."""
        import threading
        import queue
        
        num_threads = 10
        messages_per_thread = 50
        results = queue.Queue()
        
        def worker(thread_id):
            try:
                for i in range(messages_per_thread):
                    msg = Message(
                        id=f"concurrent-{thread_id}-{i}",
                        sender=f"thread-{thread_id}",
                        recipient="concurrent-recipient",
                        subject=f"Concurrent Message {i} from Thread {thread_id}",
                        body=f"Thread {thread_id} message {i}",
                        timestamp=datetime.now(timezone.utc)
                    )
                    enhanced_mailbox.send_message(msg)
                results.put(("success", thread_id, messages_per_thread))
            except Exception as e:
                results.put(("error", thread_id, str(e)))
        
        # Start threads
        threads = []
        start_time = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        execution_time = time.time() - start_time
        
        # Collect results
        successful_threads = 0
        total_messages = 0
        
        while not results.empty():
            status, thread_id, count = results.get()
            if status == "success":
                successful_threads += 1
                total_messages += count
        
        # Verify all threads completed successfully
        assert successful_threads == num_threads
        assert total_messages == num_threads * messages_per_thread
        
        # Verify all messages in database
        all_messages = enhanced_mailbox.get_messages("concurrent-recipient", unread_only=False, limit=1000)
        assert len(all_messages) == num_threads * messages_per_thread
        
        # Should complete in reasonable time
        assert execution_time < 10.0
    
    def test_database_recovery_from_corruption(self, enhanced_mailbox):
        """Test database recovery mechanisms."""
        # Send some initial messages
        for i in range(10):
            msg = Message(
                id=f"recovery-{i}",
                sender="test-sender",
                recipient="test-recipient",
                subject=f"Recovery Test {i}",
                body="Test content",
                timestamp=datetime.now(timezone.utc)
            )
            enhanced_mailbox.send_message(msg)
        
        # Simulate database issues by closing connection
        enhanced_mailbox.db.close()
        
        # Try to perform operations (should handle gracefully)
        with pytest.raises((sqlite3.OperationalError, sqlite3.ProgrammingError)):
            enhanced_mailbox.get_messages("test-recipient")
    
    def test_message_search_performance(self, enhanced_mailbox):
        """Test search performance with large dataset."""
        # Create diverse message set
        keywords = ["urgent", "project", "meeting", "deadline", "report", "review", "update", "task"]
        
        for i in range(500):
            keyword = keywords[i % len(keywords)]
            msg = Message(
                id=f"search-{i:03d}",
                sender=f"user-{i % 20}",
                recipient="search-recipient",
                subject=f"Message about {keyword} #{i}",
                body=f"This message discusses {keyword} and related topics. Message number {i}.",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                tags=[keyword, f"batch-{i // 50}"]
            )
            enhanced_mailbox.send_message(msg)
        
        # Test search performance
        start_time = time.time()
        results = enhanced_mailbox.search_messages("search-recipient", "urgent")
        search_time = time.time() - start_time
        
        # Should find approximately 62-63 messages (500/8 keywords)
        assert 50 <= len(results) <= 80
        
        # Search should complete quickly
        assert search_time < 1.0
        
        # Verify search results are relevant
        for message in results:
            assert "urgent" in message.subject.lower() or "urgent" in message.body.lower() or "urgent" in message.tags
    
    def test_memory_usage_monitoring(self, enhanced_mailbox):
        """Test memory usage during operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        large_messages = []
        for i in range(100):
            large_content = "Large message content " * 1000  # ~20KB per message
            msg = Message(
                id=f"memory-{i}",
                sender="memory-test",
                recipient="memory-recipient",
                subject=f"Large Message {i}",
                body=large_content,
                timestamp=datetime.now(timezone.utc)
            )
            enhanced_mailbox.send_message(msg)
            large_messages.append(msg)
        
        # Check memory after operations
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        
        # Clear references
        large_messages.clear()
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
    
    def test_transaction_rollback(self, enhanced_mailbox):
        """Test database transaction rollback on errors."""
        # Send some initial messages
        for i in range(5):
            msg = Message(
                id=f"rollback-{i}",
                sender="test-sender",
                recipient="test-recipient",
                subject=f"Rollback Test {i}",
                body="Initial content",
                timestamp=datetime.now(timezone.utc)
            )
            enhanced_mailbox.send_message(msg)
        
        initial_count = len(enhanced_mailbox.get_messages("test-recipient", unread_only=False))
        
        # Attempt operation that should fail
        with pytest.raises(Exception):
            # This should fail due to duplicate ID constraint
            duplicate_msg = Message(
                id="rollback-0",  # Duplicate ID
                sender="test-sender",
                recipient="test-recipient",
                subject="Duplicate Message",
                body="Should fail",
                timestamp=datetime.now(timezone.utc)
            )
            enhanced_mailbox.send_message(duplicate_msg)
        
        # Count should remain the same (rollback occurred)
        final_count = len(enhanced_mailbox.get_messages("test-recipient", unread_only=False))
        assert final_count == initial_count


class TestEnhancedAgentIdentifier:
    """Enhanced tests for AgentIdentifier with edge cases."""
    
    @patch('ai_mail_mcp.agent.psutil')
    def test_complex_process_detection(self, mock_psutil):
        """Test complex process hierarchy detection."""
        # Create mock process hierarchy
        mock_grandparent = Mock()
        mock_grandparent.name.return_value = 'explorer.exe'
        mock_grandparent.parent.return_value = None
        
        mock_parent = Mock()
        mock_parent.name.return_value = 'code.exe'
        mock_parent.parent.return_value = mock_grandparent
        
        mock_process = Mock()
        mock_process.parent.return_value = mock_parent
        
        mock_psutil.Process.return_value = mock_process
        
        detected_name = AgentIdentifier.detect_agent_name()
        assert "vscode" in detected_name.lower()
    
    def test_agent_name_collision_resolution(self, enhanced_mailbox):
        """Test resolution of agent name collisions."""
        # Register multiple agents with similar names
        base_name = "test-agent"
        
        # Register first agent
        enhanced_mailbox.register_agent(base_name, {"test": True})
        
        # Try to register agents with conflicting names
        for i in range(5):
            unique_name = AgentIdentifier.ensure_unique_name(enhanced_mailbox, base_name)
            enhanced_mailbox.register_agent(unique_name, {"iteration": i})
            
            # Should get incremented names
            if i == 0:
                assert unique_name == f"{base_name}-2"
            else:
                assert unique_name == f"{base_name}-{i + 2}"
    
    @pytest.mark.parametrize("test_name,expected_valid", [
        ("valid-agent", True),
        ("agent_with_underscores", True),
        ("agent.with.dots", True),
        ("agent123", True),
        ("", False),
        ("a", False),  # Too short
        ("x" * 100, False),  # Too long
        ("-starts-with-dash", False),
        ("ends-with-dash-", False),
        ("has spaces", False),
        ("has@symbols", False),
        ("has\nnewlines", False),
        ("has\ttabs", False),
    ])
    def test_agent_name_validation_comprehensive(self, test_name, expected_valid):
        """Comprehensive agent name validation testing."""
        is_valid = AgentIdentifier.validate_agent_name(test_name)
        assert is_valid == expected_valid
    
    def test_agent_suggestion_algorithm(self):
        """Test agent name suggestion algorithm."""
        existing_agents = {
            "claude-desktop", "claude-desktop-1", "claude-desktop-2",
            "vscode-copilot", "vscode-copilot-1",
            "agent-test", "agent-test-ai", "agent-test-2"
        }
        
        # Test suggestions for various base names
        suggestions = AgentIdentifier.suggest_agent_names("claude-desktop", existing_agents, count=5)
        assert len(suggestions) == 5
        assert "claude-desktop-3" in suggestions  # First available number
        
        # All suggestions should be unique
        assert len(set(suggestions)) == len(suggestions)
        
        # No suggestions should conflict with existing
        for suggestion in suggestions:
            assert suggestion not in existing_agents


class TestSystemMonitor:
    """Test the system monitoring component."""
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = SystemMonitor()
        assert monitor is not None
    
    @patch('ai_mail_mcp.monitor.psutil')
    def test_system_metrics_collection(self, mock_psutil):
        """Test system metrics collection."""
        # Mock system metrics
        mock_psutil.cpu_percent.return_value = 45.2
        mock_psutil.virtual_memory.return_value = Mock(percent=67.8, available=1024*1024*1024)
        mock_psutil.disk_usage.return_value = Mock(percent=34.5)
        
        monitor = SystemMonitor()
        metrics = monitor.get_system_metrics()
        
        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics
        assert "disk_percent" in metrics
        assert metrics["cpu_percent"] == 45.2
        assert metrics["memory_percent"] == 67.8
    
    def test_performance_tracking(self):
        """Test performance metrics tracking."""
        monitor = SystemMonitor()
        
        # Track some operations
        with monitor.track_operation("test_operation"):
            time.sleep(0.1)  # Simulate work
        
        metrics = monitor.get_performance_metrics()
        assert "test_operation" in metrics
        assert metrics["test_operation"]["count"] == 1
        assert metrics["test_operation"]["avg_duration"] >= 0.1


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""
    
    def test_malformed_database_handling(self):
        """Test handling of malformed database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "malformed.db"
            
            # Create a malformed database file
            with open(db_path, 'w') as f:
                f.write("This is not a valid SQLite database")
            
            # Should handle gracefully
            with pytest.raises((sqlite3.DatabaseError, sqlite3.OperationalError)):
                MailboxManager(db_path)
    
    def test_disk_space_exhaustion_simulation(self):
        """Test behavior when disk space is exhausted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "space_test.db"
            mailbox = MailboxManager(db_path)
            
            # Try to create very large messages to simulate space issues
            large_content = "x" * (1024 * 1024)  # 1MB content
            
            for i in range(10):  # Try to create 10MB of data
                try:
                    msg = Message(
                        id=f"large-{i}",
                        sender="space-test",
                        recipient="space-recipient",
                        subject=f"Large Message {i}",
                        body=large_content,
                        timestamp=datetime.now(timezone.utc)
                    )
                    mailbox.send_message(msg)
                except Exception as e:
                    # Should handle gracefully
                    assert isinstance(e, (sqlite3.OperationalError, OSError, IOError))
                    break
    
    def test_unicode_normalization(self):
        """Test Unicode normalization in messages."""
        import unicodedata
        
        # Test with various Unicode forms
        unicode_texts = [
            "café",  # NFC
            "cafe\u0301",  # NFD (combining acute accent)
            "Ñoño",  # Spanish characters
            "🚀🌟💯",  # Emojis
            "اختبار",  # Arabic
            "测试",  # Chinese
            "тест",  # Cyrillic
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "unicode_test.db"
            mailbox = MailboxManager(db_path)
            
            for i, text in enumerate(unicode_texts):
                msg = Message(
                    id=f"unicode-{i}",
                    sender="unicode-sender",
                    recipient="unicode-recipient",
                    subject=f"Unicode Test: {text}",
                    body=f"Body with unicode: {text}",
                    timestamp=datetime.now(timezone.utc)
                )
                mailbox.send_message(msg)
            
            # Retrieve and verify
            messages = mailbox.get_messages("unicode-recipient", unread_only=False)
            assert len(messages) == len(unicode_texts)
    
    def test_timezone_handling(self):
        """Test timezone handling in timestamps."""
        timezones = [
            timezone.utc,
            timezone(timedelta(hours=9)),  # JST
            timezone(timedelta(hours=-5)),  # EST
            timezone(timedelta(hours=5, minutes=30)),  # IST
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "timezone_test.db"
            mailbox = MailboxManager(db_path)
            
            for i, tz in enumerate(timezones):
                msg = Message(
                    id=f"tz-{i}",
                    sender="tz-sender",
                    recipient="tz-recipient",
                    subject=f"Timezone Test {i}",
                    body="Timezone test",
                    timestamp=datetime.now(tz)
                )
                mailbox.send_message(msg)
            
            # Retrieve and verify timestamps are preserved
            messages = mailbox.get_messages("tz-recipient", unread_only=False)
            assert len(messages) == len(timezones)
            
            # All timestamps should be timezone-aware
            for message in messages:
                assert message.timestamp.tzinfo is not None


@pytest.mark.integration
class TestFullSystemIntegration:
    """Full system integration tests."""
    
    def test_complete_workflow_simulation(self):
        """Simulate complete multi-agent workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "workflow_test.db"
            mailbox = MailboxManager(db_path)
            
            # Register multiple agents
            agents = ["orchestrator", "claude-desktop", "vscode-copilot", "monitoring-agent"]
            for agent in agents:
                mailbox.register_agent(agent, {"role": f"{agent}_role"})
            
            # Simulate workflow: orchestrator assigns tasks
            task_assignment = Message(
                id="task-001",
                sender="orchestrator",
                recipient="claude-desktop",
                subject="Task Assignment: Code Review",
                body="Please review the authentication module PR #123",
                timestamp=datetime.now(timezone.utc),
                priority="high",
                tags=["task", "code-review", "auth"]
            )
            mailbox.send_message(task_assignment)
            
            # Claude acknowledges and requests collaboration
            acknowledgment = Message(
                id="ack-001",
                sender="claude-desktop",
                recipient="orchestrator",
                subject="Re: Task Assignment: Code Review",
                body="Acknowledged. Will need VSCode integration for testing.",
                timestamp=datetime.now(timezone.utc),
                reply_to="task-001",
                thread_id="task-001"
            )
            mailbox.send_message(acknowledgment)
            
            # Request collaboration
            collaboration_request = Message(
                id="collab-001",
                sender="claude-desktop",
                recipient="vscode-copilot",
                subject="Collaboration Request: Auth Module Testing",
                body="Need assistance with unit test execution for auth module",
                timestamp=datetime.now(timezone.utc),
                priority="normal",
                tags=["collaboration", "testing", "auth"]
            )
            mailbox.send_message(collaboration_request)
            
            # VSCode responds
            collaboration_response = Message(
                id="collab-resp-001",
                sender="vscode-copilot",
                recipient="claude-desktop",
                subject="Re: Collaboration Request",
                body="Ready to assist. Test suite is available.",
                timestamp=datetime.now(timezone.utc),
                reply_to="collab-001",
                thread_id="collab-001"
            )
            mailbox.send_message(collaboration_response)
            
            # Monitoring agent sends status update
            status_update = Message(
                id="status-001",
                sender="monitoring-agent",
                recipient="orchestrator",
                subject="System Status Update",
                body="All agents active. Task completion rate: 85%",
                timestamp=datetime.now(timezone.utc),
                priority="low",
                tags=["status", "monitoring", "metrics"]
            )
            mailbox.send_message(status_update)
            
            # Verify workflow completion
            # Check orchestrator's messages
            orchestrator_messages = mailbox.get_messages("orchestrator", unread_only=False)
            assert len(orchestrator_messages) == 2  # ack + status
            
            # Check thread integrity
            task_thread = mailbox.get_thread("task-001", "orchestrator")
            assert len(task_thread) == 2  # task + ack
            
            collab_thread = mailbox.get_thread("collab-001", "claude-desktop")
            assert len(collab_thread) == 2  # request + response
            
            # Check agent activity
            agents_list = mailbox.get_agents()
            assert len(agents_list) == 4
            
            # Verify message stats
            claude_stats = mailbox.get_message_stats("claude-desktop")
            assert claude_stats["total_received"] == 1  # task assignment
            assert claude_stats["sent"] == 2  # ack + collab request


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_message_throughput_benchmark(self):
        """Benchmark message processing throughput."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "benchmark.db"
            mailbox = MailboxManager(db_path)
            
            # Benchmark parameters
            num_messages = 1000
            num_recipients = 10
            
            # Warm up
            for i in range(10):
                msg = Message(
                    id=f"warmup-{i}",
                    sender="benchmark-sender",
                    recipient="warmup-recipient",
                    subject="Warmup",
                    body="Warmup message",
                    timestamp=datetime.now(timezone.utc)
                )
                mailbox.send_message(msg)
            
            # Actual benchmark
            start_time = time.time()
            
            for i in range(num_messages):
                recipient = f"recipient-{i % num_recipients}"
                msg = Message(
                    id=f"benchmark-{i:04d}",
                    sender="benchmark-sender",
                    recipient=recipient,
                    subject=f"Benchmark Message {i}",
                    body=f"This is benchmark message number {i} with some content to make it realistic.",
                    timestamp=datetime.now(timezone.utc),
                    priority=["urgent", "high", "normal", "low"][i % 4],
                    tags=[f"tag-{i % 5}", "benchmark"]
                )
                mailbox.send_message(msg)
            
            send_time = time.time() - start_time
            
            # Benchmark retrieval
            start_time = time.time()
            for i in range(num_recipients):
                recipient = f"recipient-{i}"
                messages = mailbox.get_messages(recipient, unread_only=False, limit=200)
            
            retrieve_time = time.time() - start_time
            
            # Calculate metrics
            send_throughput = num_messages / send_time
            retrieve_throughput = (num_recipients * 200) / retrieve_time
            
            print(f"\nPerformance Benchmark Results:")
            print(f"Send throughput: {send_throughput:.2f} messages/second")
            print(f"Retrieve throughput: {retrieve_throughput:.2f} messages/second")
            print(f"Total send time: {send_time:.3f} seconds")
            print(f"Total retrieve time: {retrieve_time:.3f} seconds")
            
            # Performance assertions
            assert send_throughput > 500  # At least 500 messages/second
            assert retrieve_throughput > 1000  # At least 1000 messages/second
            assert send_time < 5.0  # Should complete within 5 seconds
            assert retrieve_time < 2.0  # Should complete within 2 seconds


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=ai_mail_mcp",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=90"
    ])
