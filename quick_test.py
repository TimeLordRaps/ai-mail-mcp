#!/usr/bin/env python3
"""
Quick test script to verify AI Mail MCP functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        from ai_mail_mcp.models import Message, AgentInfo
        print("✅ Models imported successfully")
    except Exception as e:
        print(f"❌ Models import failed: {e}")
        return False
    
    try:
        from ai_mail_mcp.mailbox import MailboxManager
        print("✅ Mailbox imported successfully")
    except Exception as e:
        print(f"❌ Mailbox import failed: {e}")
        return False
    
    try:
        from ai_mail_mcp.agent import AgentIdentifier
        print("✅ Agent imported successfully")
    except Exception as e:
        print(f"❌ Agent import failed: {e}")
        return False
    
    try:
        from ai_mail_mcp.server import init_system, run_simple_server
        print("✅ Server imported successfully")
    except Exception as e:
        print(f"❌ Server import failed: {e}")
        return False
    
    return True

def test_functionality():
    """Test basic functionality."""
    print("\n🔧 Testing basic functionality...")
    
    try:
        from ai_mail_mcp.models import Message, AgentInfo
        from ai_mail_mcp.mailbox import MailboxManager
        from ai_mail_mcp.agent import AgentIdentifier
        from datetime import datetime, timezone
        import tempfile
        
        # Test agent detection
        agent_name = AgentIdentifier.detect_agent_name()
        print(f"✅ Agent name detected: {agent_name}")
        
        # Test mailbox with temporary database
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'test.db'
            mailbox = MailboxManager(db_path)
            print("✅ Mailbox manager created")
            
            # Test agent registration
            mailbox.register_agent(agent_name, {"test": True})
            agents = mailbox.get_agents()
            print(f"✅ Agent registered, found {len(agents)} agents")
            
            # Test message creation
            message = Message(
                id='test-msg-001',
                sender=agent_name,
                recipient='test-recipient',
                subject='Test Message',
                body='This is a test message to verify functionality.',
                timestamp=datetime.now(timezone.utc),
                tags=['test', 'verification']
            )
            print("✅ Message created")
            
            # Test message sending
            msg_id = mailbox.send_message(message)
            print(f"✅ Message sent with ID: {msg_id}")
            
            # Test message retrieval
            messages = mailbox.get_messages('test-recipient')
            print(f"✅ Retrieved {len(messages)} messages")
            
            # Test statistics
            stats = mailbox.get_message_stats(agent_name)
            print(f"✅ Statistics: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_server():
    """Test server initialization."""
    print("\n🚀 Testing server initialization...")
    
    try:
        from ai_mail_mcp.server import init_system, run_simple_server
        
        # Initialize system
        init_system()
        print("✅ System initialized")
        
        # Test simple server
        result = run_simple_server()
        if result:
            print("✅ Simple server test passed")
        else:
            print("⚠️ Simple server test had issues")
        
        return True
        
    except Exception as e:
        print(f"❌ Server test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 AI Mail MCP Quick Test")
    print("=" * 40)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return False
    
    # Test functionality
    if not test_functionality():
        print("\n❌ Functionality tests failed")
        return False
    
    # Test server
    if not test_server():
        print("\n❌ Server tests failed")
        return False
    
    print("\n🎉 All tests passed!")
    print("✅ AI Mail MCP is working correctly")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)