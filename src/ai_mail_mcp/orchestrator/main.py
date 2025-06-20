#!/usr/bin/env python3
"""
AI Mail MCP Orchestrator - Main Entry Point

A sophisticated orchestrator for managing multiple AI agents and their mailboxes.
Provides intelligent summarization, priority management, task distribution,
and urgent notices for optimal agent coordination.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import argparse

from . import OrchestrationSystem
from .priority_manager import PriorityManager
from .summary_engine import SummaryEngine
from .task_distributor import TaskDistributor
from .urgent_notices import UrgentNoticeManager
from ..mailbox import MailboxManager
from ..agent import AgentIdentifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path.home() / '.ai_mail' / 'orchestrator.log')
    ]
)
logger = logging.getLogger("ai-mail-orchestrator")


class AIMailOrchestrator:
    """
    Main orchestrator for AI Mail system.
    
    Provides central management of multiple AI agents including:
    - Intelligent message summarization for overwhelmed agents
    - Priority escalation and optimization
    - Task distribution and load balancing
    - System-wide urgent notices
    - Automated maintenance and health monitoring
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / '.ai_mail'
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.mailbox = MailboxManager(self.data_dir)
        self.agent_identifier = AgentIdentifier()
        
        # Initialize orchestration subsystems
        self.priority_manager = PriorityManager(self.mailbox)
        self.summary_engine = SummaryEngine(self.mailbox)
        self.task_distributor = TaskDistributor(self.mailbox)
        self.urgent_notices = UrgentNoticeManager(self.mailbox)
        
        # Orchestration state
        self.running = False
        self.orchestration_interval = 300  # 5 minutes
        self.maintenance_interval = 10800  # 3 hours
        
        logger.info("🎯 AI Mail Orchestrator initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")
        
    async def start_orchestration(self):
        """Start the main orchestration loop."""
        self.running = True
        logger.info("🚀 Starting AI Mail Orchestrator")
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, shutting down...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Main orchestration loop
        last_maintenance = datetime.now(timezone.utc)
        
        while self.running:
            try:
                # Run orchestration cycle
                await self.run_orchestration_cycle()
                
                # Check if maintenance is needed
                now = datetime.now(timezone.utc)
                if (now - last_maintenance).total_seconds() >= self.maintenance_interval:
                    await self.run_maintenance_cycle()
                    last_maintenance = now
                
                # Wait before next cycle
                await asyncio.sleep(self.orchestration_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Orchestrator interrupted by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in orchestration cycle: {e}")
                await asyncio.sleep(60)  # Wait before retrying
                
        logger.info("🏁 AI Mail Orchestrator stopped")
        
    async def run_orchestration_cycle(self):
        """Run a single orchestration cycle."""
        logger.debug("🔄 Running orchestration cycle")
        
        try:
            # Get all active agents
            agents = await self.get_active_agents()
            logger.debug(f"👥 Found {len(agents)} active agents")
            
            # Check for agents with high message loads
            overwhelmed_agents = await self.identify_overwhelmed_agents(agents)
            
            # Generate summaries for overwhelmed agents
            for agent_name in overwhelmed_agents:
                await self.generate_agent_summary(agent_name)
                
            # Update priorities and escalate old messages
            await self.priority_manager.run_priority_optimization()
            
            # Distribute tasks if there are idle agents
            await self.task_distributor.distribute_pending_tasks()
            
            # Check for system-wide urgent notices
            await self.urgent_notices.check_and_send_urgent_notices()
            
            # Update orchestrator status
            await self.update_orchestrator_status()
            
        except Exception as e:
            logger.error(f"❌ Error in orchestration cycle: {e}")
            
    async def run_maintenance_cycle(self):
        """Run system maintenance tasks."""
        logger.info("🔧 Running maintenance cycle")
        
        try:
            # Clean up old messages
            cleaned_count = await self.mailbox.cleanup_old_messages(days=30)
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned up {cleaned_count} old messages")
                
            # Update agent statuses
            await self.update_agent_statuses()
            
            # Optimize database
            await self.mailbox.optimize_database()
            
            # Health check
            health_status = await self.perform_health_check()
            logger.info(f"💚 System health: {health_status}")
            
        except Exception as e:
            logger.error(f"❌ Error in maintenance cycle: {e}")
            
    async def get_active_agents(self) -> List[str]:
        """Get list of agents active in the last hour."""
        try:
            agents = await self.mailbox.get_active_agents(hours=1)
            return [agent['name'] for agent in agents]
        except Exception as e:
            logger.error(f"❌ Error getting active agents: {e}")
            return []
            
    async def identify_overwhelmed_agents(self, agents: List[str]) -> List[str]:
        """Identify agents with high unread message counts."""
        overwhelmed = []
        
        for agent_name in agents:
            try:
                stats = await self.mailbox.get_agent_message_stats(agent_name)
                unread_count = stats.get('unread_count', 0)
                urgent_count = stats.get('urgent_count', 0)
                
                # Thresholds for "overwhelmed"
                if unread_count > 20 or urgent_count > 5:
                    overwhelmed.append(agent_name)
                    logger.info(f"📊 Agent {agent_name} is overwhelmed: {unread_count} unread, {urgent_count} urgent")
                    
            except Exception as e:
                logger.error(f"❌ Error checking agent {agent_name}: {e}")
                
        return overwhelmed
        
    async def generate_agent_summary(self, agent_name: str):
        """Generate and send intelligent summary for an overwhelmed agent."""
        try:
            logger.info(f"📝 Generating summary for overwhelmed agent: {agent_name}")
            
            # Generate summary using the summary engine
            summary = await self.summary_engine.generate_agent_summary(agent_name)
            
            if summary:
                # Send summary as a high-priority message
                await self.mailbox.send_message(
                    sender="ai-mail-orchestrator",
                    recipient=agent_name,
                    subject="📊 Intelligent Message Summary",
                    body=summary,
                    priority="high",
                    tags=["summary", "orchestrator"]
                )
                logger.info(f"✅ Summary sent to {agent_name}")
            else:
                logger.warning(f"⚠️  No summary generated for {agent_name}")
                
        except Exception as e:
            logger.error(f"❌ Error generating summary for {agent_name}: {e}")
            
    async def send_urgent_notice(self, title: str, message: str, agents: Optional[List[str]] = None):
        """Send urgent notice to specific agents or all agents."""
        try:
            if agents is None:
                agents = await self.get_active_agents()
                
            logger.info(f"🚨 Sending urgent notice to {len(agents)} agents: {title}")
            
            for agent_name in agents:
                await self.mailbox.send_message(
                    sender="ai-mail-orchestrator",
                    recipient=agent_name,
                    subject=f"🚨 URGENT: {title}",
                    body=f"**URGENT SYSTEM NOTICE**\n\n{message}\n\n---\nFrom: AI Mail Orchestrator\nTime: {datetime.now(timezone.utc).isoformat()}",
                    priority="urgent",
                    tags=["urgent", "system", "orchestrator"]
                )
                
            logger.info(f"✅ Urgent notice sent to {len(agents)} agents")
            
        except Exception as e:
            logger.error(f"❌ Error sending urgent notice: {e}")
            
    async def update_orchestrator_status(self):
        """Update orchestrator status in database."""
        try:
            await self.mailbox.update_agent_status(
                agent_name="ai-mail-orchestrator",
                status="active",
                metadata={
                    "type": "orchestrator",
                    "last_cycle": datetime.now(timezone.utc).isoformat(),
                    "managed_agents": len(await self.get_active_agents())
                }
            )
        except Exception as e:
            logger.debug(f"Could not update orchestrator status: {e}")
            
    async def update_agent_statuses(self):
        """Update agent statuses and mark inactive agents as offline."""
        try:
            inactive_threshold = datetime.now(timezone.utc) - timedelta(hours=2)
            updated_count = await self.mailbox.mark_inactive_agents_offline(inactive_threshold)
            
            if updated_count > 0:
                logger.info(f"📴 Marked {updated_count} inactive agents as offline")
                
        except Exception as e:
            logger.error(f"❌ Error updating agent statuses: {e}")
            
    async def perform_health_check(self) -> str:
        """Perform system health check."""
        try:
            health_issues = []
            
            # Check database health
            if not await self.mailbox.check_database_health():
                health_issues.append("Database connectivity issues")
                
            # Check for stuck messages
            stuck_messages = await self.mailbox.get_stuck_messages(hours=48)
            if stuck_messages:
                health_issues.append(f"{len(stuck_messages)} messages stuck for >48h")
                
            # Check agent activity
            active_agents = await self.get_active_agents()
            if len(active_agents) == 0:
                health_issues.append("No active agents detected")
                
            if health_issues:
                return f"Issues detected: {', '.join(health_issues)}"
            else:
                return "All systems operational"
                
        except Exception as e:
            return f"Health check failed: {e}"
            
    # CLI command handlers
    async def cmd_status(self):
        """Show orchestrator status."""
        agents = await self.get_active_agents()
        overwhelmed = await self.identify_overwhelmed_agents(agents)
        
        print(f"""
🎯 AI Mail Orchestrator Status

📊 System Overview:
  • Active agents: {len(agents)}
  • Overwhelmed agents: {len(overwhelmed)}
  • Data directory: {self.data_dir}

👥 Active Agents:
{chr(10).join([f"  • {agent}" for agent in agents]) if agents else "  • No active agents"}

📈 Overwhelmed Agents:
{chr(10).join([f"  • {agent}" for agent in overwhelmed]) if overwhelmed else "  • None"}

🏥 Health: {await self.perform_health_check()}
""")

    async def cmd_summary(self, agent_name: str):
        """Generate summary for specific agent."""
        if not agent_name:
            print("❌ Agent name required")
            return
            
        print(f"📝 Generating summary for {agent_name}...")
        await self.generate_agent_summary(agent_name)
        print(f"✅ Summary sent to {agent_name}")
        
    async def cmd_urgent(self, title: str, message: str):
        """Send urgent notice to all agents."""
        if not title or not message:
            print("❌ Both title and message required")
            return
            
        await self.send_urgent_notice(title, message)
        print("🚨 Urgent notice sent to all active agents")
        
    async def cmd_cleanup(self):
        """Run cleanup and maintenance."""
        print("🧹 Running cleanup and maintenance...")
        await self.run_maintenance_cycle()
        print("✅ Cleanup completed")


def main():
    """Main entry point for AI Mail Orchestrator."""
    parser = argparse.ArgumentParser(description="AI Mail MCP Orchestrator")
    parser.add_argument("--data-dir", type=Path, help="Custom data directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command (default)
    subparsers.add_parser("start", help="Start orchestrator daemon")
    
    # Status command
    subparsers.add_parser("status", help="Show orchestrator status")
    
    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Generate summary for agent")
    summary_parser.add_argument("agent", help="Agent name")
    
    # Urgent notice command
    urgent_parser = subparsers.add_parser("urgent", help="Send urgent notice")
    urgent_parser.add_argument("title", help="Notice title")
    urgent_parser.add_argument("message", help="Notice message")
    
    # Cleanup command
    subparsers.add_parser("cleanup", help="Run maintenance and cleanup")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = AIMailOrchestrator(args.data_dir)
    
    # Handle commands
    if args.command == "status":
        asyncio.run(orchestrator.cmd_status())
    elif args.command == "summary":
        asyncio.run(orchestrator.cmd_summary(args.agent))
    elif args.command == "urgent":
        asyncio.run(orchestrator.cmd_urgent(args.title, args.message))
    elif args.command == "cleanup":
        asyncio.run(orchestrator.cmd_cleanup())
    else:
        # Default: start orchestrator
        try:
            asyncio.run(orchestrator.start_orchestration())
        except KeyboardInterrupt:
            print("\n🛑 Orchestrator stopped by user")
            sys.exit(0)


if __name__ == "__main__":
    main()
