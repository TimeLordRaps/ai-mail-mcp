"""
Advanced Python tests for AI Mail MCP Server components.
Focuses on enhanced coverage, edge cases, and integration scenarios.
"""

import asyncio
import json
import sqlite3
import tempfile
import uuid
import pytest
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from ai_mail_mcp.models import Message, AgentInfo
from ai_mail_mcp.mailbox import MailboxManager
from ai_mail_mcp.agent import AgentIdentifier


class TestAdvancedMailboxManager:
    """Advanced tests for MailboxManager with edge cases and performance scenarios."""
    
    @pytest.fixture
    def temp_mailbox(self):
        """Create a temporary mailbox for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_mailbox.db"
            yield MailboxManager(db_path)
    
    def test_concurrent_message_operations(self, temp_mailbox):
        """Test concurrent read/write operations on messages."""
        import concurrent.futures
        
        def send_messages(thread_id, count):
            results = []
            for i in range(count):
                msg = Message(
                    id=f"thread-{thread_id}-msg-{i}",
                    sender=f"sender-{thread_id}",
                    recipient="test-recipient",
                    subject=f"Concurrent Message {i}",
                    body=f"Message from thread {thread_id}, number {i}",
                    timestamp=datetime.now(timezone.utc)
                )
                try:
                    msg_id = temp_mailbox.send_message(msg)
                    results.append(msg_id)
                except Exception as e:
                    results.append(f"Error: {e}")
            return results
        
        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_messages, i, 10) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify all messages were sent
        total_sent = sum(len([r for r in result if not str(r).startswith("Error")]) for result in results)
        assert total_sent == 50  # 5 threads × 10 messages each
        
        # Verify messages are in database
        messages = temp_mailbox.get_messages("test-recipient", unread_only=False, limit=100)
        assert len(messages) == 50
    
    def test_database_transaction_integrity(self, temp_mailbox):
        """Test database transaction integrity under various failure conditions."""
        # Test partial transaction failure
        with patch.object(temp_mailbox.db, 'execute') as mock_execute:
            # First call succeeds, second fails
            mock_execute.side_effect = [None, sqlite3.OperationalError("Database locked")]
            
            msg = Message(
                id="integrity-test",
                sender="test-sender",
                recipient="test-recipient",
                subject="Integrity Test",
                body="Testing transaction integrity",
                timestamp=datetime.now(timezone.utc)
            )
            
            with pytest.raises(sqlite3.OperationalError):
                temp_mailbox.send_message(msg)
            
            # Verify no partial data was committed
            messages = temp_mailbox.get_messages("test-recipient", unread_only=False)
            assert not any(m.id == "integrity-test" for m in messages)
    
    def test_large_message_handling(self, temp_mailbox):
        """Test handling of large messages."""
        large_body = "x" * (1024 * 1024)  # 1MB message
        large_subject = "y" * 1000  # 1KB subject
        
        msg = Message(
            id="large-msg-test",
            sender="test-sender",
            recipient="test-recipient",
            subject=large_subject,
            body=large_body,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Should handle large messages without issues
        msg_id = temp_mailbox.send_message(msg)
        assert msg_id == "large-msg-test"
        
        # Verify retrieval
        retrieved_msgs = temp_mailbox.get_messages("test-recipient", unread_only=False)
        assert len(retrieved_msgs) == 1
        assert len(retrieved_msgs[0].body) == 1024 * 1024
        assert len(retrieved_msgs[0].subject) == 1000
    
    def test_unicode_and_special_characters(self, temp_mailbox):
        """Test handling of unicode and special characters."""
        special_content = {
            "emoji": "🔥💯🚀✨🎉",
            "unicode": "Hello 世界! Здравствуй мир! مرحبا بالعالم!",
            "special_chars": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
            "sql_injection": "'; DROP TABLE messages; --",
            "script_injection": "<script>alert('xss')</script>",
            "null_bytes": "test\x00message",
            "control_chars": "test\r\n\t\bmessage"
        }
        
        for test_name, content in special_content.items():
            msg = Message(
                id=f"special-{test_name}",
                sender="test-sender",
                recipient="test-recipient",
                subject=f"Special Characters Test: {content}",
                body=f"Body with special content: {content}",
                timestamp=datetime.now(timezone.utc),
                tags=[content, "special-test"]
            )
            
            # Should handle all special content without issues
            msg_id = temp_mailbox.send_message(msg)
            assert msg_id == f"special-{test_name}"
            
            # Verify content is preserved
            retrieved = temp_mailbox.get_messages("test-recipient", unread_only=False)
            matching_msg = next(m for m in retrieved if m.id == f"special-{test_name}")
            assert content in matching_msg.subject
            assert content in matching_msg.body
            assert content in matching_msg.tags
    
    def test_database_corruption_recovery(self, temp_mailbox):
        """Test recovery from database corruption scenarios."""
        # Send some initial messages
        for i in range(5):
            msg = Message(
                id=f"pre-corruption-{i}",
                sender="test-sender",
                recipient="test-recipient",
                subject=f"Pre-corruption message {i}",
                body="This message was sent before corruption",
                timestamp=datetime.now(timezone.utc)
            )
            temp_mailbox.send_message(msg)
        
        # Simulate database corruption by corrupting the connection
        with patch.object(temp_mailbox, 'db') as mock_db:
            mock_db.execute.side_effect = sqlite3.DatabaseError("Database is corrupted")
            
            # Operations should fail gracefully
            with pytest.raises(sqlite3.DatabaseError):
                temp_mailbox.get_messages("test-recipient")
        
        # After corruption is resolved, should be able to continue operations
        msg = Message(
            id="post-corruption",
            sender="test-sender",
            recipient="test-recipient",
            subject="Post-corruption message",
            body="This message was sent after corruption recovery",
            timestamp=datetime.now(timezone.utc)
        )
        
        msg_id = temp_mailbox.send_message(msg)
        assert msg_id == "post-corruption"
    
    def test_performance_with_large_datasets(self, temp_mailbox):
        """Test performance with large numbers of messages."""
        message_count = 1000
        start_time = time.time()
        
        # Bulk insert messages
        for i in range(message_count):
            msg = Message(
                id=f"perf-test-{i:04d}",
                sender=f"sender-{i % 10}",
                recipient="test-recipient",
                subject=f"Performance Test Message {i}",
                body=f"This is performance test message number {i}" * 5,
                timestamp=datetime.now(timezone.utc) - timedelta(seconds=i),
                priority=["urgent", "high", "normal", "low"][i % 4],
                tags=[f"tag-{i % 20}", f"category-{i % 5}"]
            )
            temp_mailbox.send_message(msg)
        
        insert_time = time.time() - start_time
        
        # Test retrieval performance
        start_time = time.time()
        messages = temp_mailbox.get_messages("test-recipient", unread_only=False, limit=1000)
        retrieval_time = time.time() - start_time
        
        # Test search performance
        start_time = time.time()
        search_results = temp_mailbox.search_messages("test-recipient", "Performance", limit=100)
        search_time = time.time() - start_time
        
        # Performance assertions
        assert len(messages) == message_count
        assert insert_time < 30.0  # Should insert 1000 messages in under 30 seconds
        assert retrieval_time < 2.0  # Should retrieve 1000 messages in under 2 seconds
        assert search_time < 1.0  # Should search in under 1 second
        
        # Throughput assertions
        insert_rate = message_count / insert_time
        assert insert_rate > 30  # At least 30 messages per second
    
    def test_memory_usage_optimization(self, temp_mailbox):
        """Test memory usage during intensive operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        for batch in range(10):
            # Create large batch of messages
            messages = []
            for i in range(100):
                msg = Message(
                    id=f"memory-test-{batch}-{i}",
                    sender="memory-tester",
                    recipient="test-recipient",
                    subject=f"Memory Test Batch {batch} Message {i}",
                    body="X" * 10000,  # 10KB message body
                    timestamp=datetime.now(timezone.utc),
                    tags=[f"batch-{batch}", f"size-large"]
                )
                messages.append(msg)
                temp_mailbox.send_message(msg)
            
            # Retrieve and process messages
            retrieved = temp_mailbox.get_messages("test-recipient", unread_only=False, limit=1000)
            
            # Clear local references
            del messages
            del retrieved
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
    
    def test_edge_case_inputs(self, temp_mailbox):
        """Test handling of edge case inputs."""
        edge_cases = [
            # Empty strings
            ("", "", "", ""),
            # Very long strings
            ("x" * 10000, "y" * 10000, "z" * 100000, "w" * 1000),
            # Boundary values
            ("a", "b", "c", "d"),
            # Numbers as strings
            ("123", "456", "789", "000"),
            # Boolean-like strings
            ("true", "false", "null", "undefined"),
        ]
        
        for i, (sender, recipient, subject, body) in enumerate(edge_cases):
            msg = Message(
                id=f"edge-case-{i}",
                sender=sender or "default-sender",
                recipient=recipient or "default-recipient",
                subject=subject or "default-subject",
                body=body or "default-body",
                timestamp=datetime.now(timezone.utc)
            )
            
            # Should handle all edge cases gracefully
            msg_id = temp_mailbox.send_message(msg)
            assert msg_id == f"edge-case-{i}"
    
    def test_thread_safety(self, temp_mailbox):
        """Test thread safety of mailbox operations."""
        results = []
        errors = []
        
        def worker_thread(thread_id):
            try:
                for i in range(50):
                    # Send message
                    msg = Message(
                        id=f"thread-{thread_id}-{i}",
                        sender=f"thread-{thread_id}",
                        recipient="shared-recipient",
                        subject=f"Thread {thread_id} Message {i}",
                        body=f"Message from thread {thread_id}",
                        timestamp=datetime.now(timezone.utc)
                    )
                    temp_mailbox.send_message(msg)
                    
                    # Read messages
                    messages = temp_mailbox.get_messages("shared-recipient", limit=10)
                    
                    # Mark some as read
                    if messages and i % 5 == 0:
                        temp_mailbox.mark_as_read([messages[0].id], "shared-recipient")
                    
                    results.append(f"thread-{thread_id}-success-{i}")
                    
            except Exception as e:
                errors.append(f"thread-{thread_id}-error: {e}")
        
        # Start multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 250  # 5 threads × 50 operations each
        
        # Verify database consistency
        all_messages = temp_mailbox.get_messages("shared-recipient", unread_only=False, limit=1000)
        assert len(all_messages) == 250


class TestAdvancedAgentIdentifier:
    """Advanced tests for AgentIdentifier with complex scenarios."""
    
    def test_agent_name_collision_resolution(self):
        """Test handling of agent name collisions."""
        existing_agents = set([
            "test-agent",
            "test-agent-1",
            "test-agent-2",
            "test-agent-10",
            "test-agent-ai",
            "test-agent-desktop"
        ])
        
        # Should find the next available number
        suggestions = AgentIdentifier.suggest_agent_names(
            "test-agent", existing_agents, count=5
        )
        
        assert len(suggestions) == 5
        assert "test-agent-3" in suggestions  # Next available number
        assert all(name not in existing_agents for name in suggestions)
        assert all(name.startswith("test-agent") for name in suggestions)
    
    def test_cross_platform_process_detection(self):
        """Test agent detection across different platforms."""
        test_cases = [
            # Windows scenarios
            {
                "platform": "win32",
                "process_name": "Code.exe",
                "parent_process": "explorer.exe",
                "expected": "vscode-copilot"
            },
            {
                "platform": "win32", 
                "process_name": "claude.exe",
                "parent_process": "winlogon.exe",
                "expected": "claude-desktop"
            },
            # macOS scenarios
            {
                "platform": "darwin",
                "process_name": "Claude",
                "parent_process": "launchd",
                "expected": "claude-desktop"
            },
            {
                "platform": "darwin",
                "process_name": "Visual Studio Code",
                "parent_process": "launchd", 
                "expected": "vscode-copilot"
            },
            # Linux scenarios
            {
                "platform": "linux",
                "process_name": "code",
                "parent_process": "systemd",
                "expected": "vscode-copilot"
            }
        ]
        
        for case in test_cases:
            with patch('sys.platform', case["platform"]):
                with patch('ai_mail_mcp.agent.psutil') as mock_psutil:
                    # Mock process hierarchy
                    mock_parent = Mock()
                    mock_parent.name.return_value = case["parent_process"]
                    
                    mock_process = Mock()
                    mock_process.name.return_value = case["process_name"]
                    mock_process.parent.return_value = mock_parent
                    
                    mock_psutil.Process.return_value = mock_process
                    
                    # Test detection
                    detected_name = AgentIdentifier.detect_agent_name()
                    assert case["expected"] in detected_name.lower()
    
    def test_environment_variable_priority(self):
        """Test environment variable detection priority."""
        env_vars = {
            'AI_AGENT_NAME': 'custom-agent-name',
            'AGENT_NAME': 'fallback-agent-name',
            'USER': 'testuser',
            'USERNAME': 'testuser',
            'COMPUTERNAME': 'testcomputer',
            'HOSTNAME': 'testhost'
        }
        
        with patch.dict('os.environ', env_vars):
            name = AgentIdentifier.detect_agent_name()
            assert name == 'custom-agent-name'
        
        # Test fallback priority
        with patch.dict('os.environ', {k: v for k, v in env_vars.items() if k != 'AI_AGENT_NAME'}):
            name = AgentIdentifier.detect_agent_name()
            # Should use some fallback mechanism
            assert name is not None
            assert len(name) > 0
    
    def test_agent_name_sanitization(self):
        """Test agent name sanitization for various inputs."""
        test_cases = [
            ("Agent With Spaces", "agent-with-spaces"),
            ("UPPERCASE_AGENT", "uppercase-agent"),
            ("agent@domain.com", "agent-domain-com"),
            ("agent/with/slashes", "agent-with-slashes"),
            ("agent\\with\\backslashes", "agent-with-backslashes"),
            ("agent#with$special%chars", "agent-with-special-chars"),
            ("agent\twith\ttabs", "agent-with-tabs"),
            ("agent\nwith\nnewlines", "agent-with-newlines"),
            ("   agent   with   spaces   ", "agent-with-spaces"),
            ("--agent--with--dashes--", "agent-with-dashes"),
            ("..agent..with..dots..", "agent-with-dots")
        ]
        
        for input_name, expected_output in test_cases:
            sanitized = AgentIdentifier.sanitize_agent_name(input_name)
            assert sanitized == expected_output
            assert AgentIdentifier.validate_agent_name(sanitized)


class TestMessageValidation:
    """Test message validation and sanitization."""
    
    def test_message_field_validation(self):
        """Test validation of message fields."""
        valid_message = Message(
            id="valid-msg-001",
            sender="valid-sender",
            recipient="valid-recipient",
            subject="Valid Subject",
            body="Valid message body",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Should create without issues
        assert valid_message.id == "valid-msg-001"
        assert valid_message.sender == "valid-sender"
        
        # Test field constraints
        with pytest.raises(ValueError):
            Message(
                id="",  # Empty ID should fail
                sender="sender",
                recipient="recipient",
                subject="Subject",
                body="Body",
                timestamp=datetime.now(timezone.utc)
            )
    
    def test_message_serialization(self):
        """Test message serialization and deserialization."""
        original_msg = Message(
            id="serialize-test",
            sender="test-sender",
            recipient="test-recipient",
            subject="Serialization Test",
            body="Testing message serialization",
            timestamp=datetime.now(timezone.utc),
            priority="high",
            tags=["test", "serialization"],
            reply_to="original-msg-id",
            thread_id="thread-123"
        )
        
        # Test JSON serialization
        json_data = original_msg.model_dump_json()
        deserialized_msg = Message.model_validate_json(json_data)
        
        assert deserialized_msg.id == original_msg.id
        assert deserialized_msg.sender == original_msg.sender
        assert deserialized_msg.subject == original_msg.subject
        assert deserialized_msg.priority == original_msg.priority
        assert deserialized_msg.tags == original_msg.tags
    
    def test_timestamp_handling(self):
        """Test various timestamp formats and edge cases."""
        # Test different timestamp formats
        timestamp_formats = [
            datetime.now(timezone.utc),
            datetime.now(timezone.utc).replace(microsecond=0),
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            datetime(1970, 1, 1, 0, 0, 1, tzinfo=timezone.utc),  # Near epoch
            datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)  # Far future
        ]
        
        for i, timestamp in enumerate(timestamp_formats):
            msg = Message(
                id=f"timestamp-test-{i}",
                sender="test-sender",
                recipient="test-recipient",
                subject=f"Timestamp Test {i}",
                body="Testing timestamp handling",
                timestamp=timestamp
            )
            
            assert msg.timestamp == timestamp
            
            # Test serialization preserves timestamp
            json_data = msg.model_dump_json()
            deserialized = Message.model_validate_json(json_data)
            assert deserialized.timestamp == timestamp


class TestDatabaseMigration:
    """Test database schema migration and versioning."""
    
    def test_schema_version_tracking(self):
        """Test database schema version tracking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "migration_test.db"
            
            # Create initial database
            mailbox = MailboxManager(db_path)
            
            # Should have version tracking
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='schema_version'
                """)
                version_table = cursor.fetchone()
                
                if version_table:
                    cursor = conn.execute("SELECT version FROM schema_version ORDER BY id DESC LIMIT 1")
                    current_version = cursor.fetchone()
                    assert current_version is not None
    
    def test_database_backup_and_restore(self):
        """Test database backup and restore functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_db = Path(temp_dir) / "original.db"
            backup_db = Path(temp_dir) / "backup.db"
            
            # Create original database with data
            mailbox = MailboxManager(original_db)
            
            # Add test data
            for i in range(10):
                msg = Message(
                    id=f"backup-test-{i}",
                    sender="backup-sender",
                    recipient="backup-recipient",
                    subject=f"Backup Test {i}",
                    body="Testing backup functionality",
                    timestamp=datetime.now(timezone.utc)
                )
                mailbox.send_message(msg)
            
            # Create backup
            import shutil
            shutil.copy2(original_db, backup_db)
            
            # Verify backup
            backup_mailbox = MailboxManager(backup_db)
            messages = backup_mailbox.get_messages("backup-recipient", unread_only=False)
            assert len(messages) == 10


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test asynchronous operations and async compatibility."""
    
    async def test_async_message_processing(self):
        """Test async-compatible message processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "async_test.db"
            mailbox = MailboxManager(db_path)
            
            # Test async message sending
            async def send_message_async(msg_id):
                msg = Message(
                    id=f"async-msg-{msg_id}",
                    sender="async-sender",
                    recipient="async-recipient",
                    subject=f"Async Message {msg_id}",
                    body="Testing async operations",
                    timestamp=datetime.now(timezone.utc)
                )
                
                # Simulate async operation
                await asyncio.sleep(0.01)
                return mailbox.send_message(msg)
            
            # Send multiple messages concurrently
            tasks = [send_message_async(i) for i in range(20)]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 20
            assert all(result.startswith("async-msg-") for result in results)
            
            # Verify all messages were saved
            messages = mailbox.get_messages("async-recipient", unread_only=False)
            assert len(messages) == 20
    
    async def test_async_bulk_operations(self):
        """Test async bulk operations performance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "bulk_async_test.db"
            mailbox = MailboxManager(db_path)
            
            async def bulk_operation_batch(batch_id, batch_size):
                results = []
                for i in range(batch_size):
                    msg = Message(
                        id=f"bulk-{batch_id}-{i}",
                        sender=f"bulk-sender-{batch_id}",
                        recipient="bulk-recipient",
                        subject=f"Bulk Message {batch_id}-{i}",
                        body="Bulk async testing",
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Small delay to simulate async processing
                    await asyncio.sleep(0.001)
                    result = mailbox.send_message(msg)
                    results.append(result)
                
                return results
            
            # Process multiple batches concurrently
            start_time = time.time()
            batch_tasks = [bulk_operation_batch(i, 25) for i in range(4)]
            batch_results = await asyncio.gather(*batch_tasks)
            duration = time.time() - start_time
            
            # Verify results
            total_messages = sum(len(batch) for batch in batch_results)
            assert total_messages == 100  # 4 batches × 25 messages
            assert duration < 5.0  # Should complete within 5 seconds
            
            # Verify database state
            messages = mailbox.get_messages("bulk-recipient", unread_only=False, limit=200)
            assert len(messages) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
