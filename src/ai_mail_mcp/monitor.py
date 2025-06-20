#!/usr/bin/env python3
"""
AI Mail MCP Monitor - System monitoring and health checks.
"""

import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_mail_mcp.mailbox import MailboxManager
from ai_mail_mcp.agent import AgentIdentifier

logger = logging.getLogger(__name__)


def main():
    """Main monitor entry point."""
    print("📊 AI Mail MCP Monitor")
    print("=" * 25)
    
    try:
        # Initialize system
        data_dir = Path.home() / ".ai_mail"
        db_path = data_dir / "mailbox.db"
        
        if not db_path.exists():
            print("❌ Database not found. Run the server first.")
            return False
        
        mailbox = MailboxManager(db_path)
        
        # Monitor loop
        print("🔍 Starting monitoring...")
        print("Press Ctrl+C to stop")
        
        while True:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            agents = mailbox.get_agents()
            
            print(f"\n[{timestamp}]")
            print(f"📈 Active agents: {len(agents)}")
            
            for agent in agents:
                stats = mailbox.get_message_stats(agent.name)
                print(f"   🤖 {agent.name}: {stats['unread']} unread, {stats['total_received']} total")
            
            time.sleep(30)  # Check every 30 seconds
            
    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped")
        return True
    except Exception as e:
        print(f"❌ Monitor failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)