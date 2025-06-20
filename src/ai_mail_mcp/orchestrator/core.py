"""
Core System Orchestrator for AI Mail MCP.

Provides centralized management and coordination for all AI agents
in the local mail system.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..mailbox import MailboxManager
from ..models import Message, AgentInfo
from .priority_manager import PriorityManager
from .summary_engine import MessageSummaryEngine
from .urgent_notices import UrgentNoticeManager
from .task_distributor import TaskDistributor

logger = logging.getLogger(__name__)


@dataclass
class AgentWorkload:
    """Represents an agent's current workload and status."""
    agent_name: str
    total_messages: int
    unread_messages: int
    urgent_messages: int
    high_priority_messages: int
    recent_activity: int
    last_seen: datetime
    status: str  # 'overwhelmed', 'busy', 'normal', 'idle'
    recommendations: List[str]


@dataclass
class SystemStatus:
    """Overall system status and metrics."""
    total_agents: int
    active_agents: int
    total_messages: int
    unread_messages: int
    urgent_notices: int
    system_load: str  # 'critical', 'high', 'normal', 'low'
    bottlenecks: List[str]
    recommendations: List[str]


class SystemOrchestrator:
    """
    Central orchestrator for managing AI agent coordination and workload.
    
    Responsibilities:
    - Monitor agent workloads and system health
    - Create intelligent summaries for overwhelmed agents
    - Manage urgent notices and system-wide priorities
    - Distribute tasks efficiently across available agents
    - Provide administrative oversight and optimization
    """
    
    def __init__(self, mailbox: MailboxManager, orchestrator_name: str = "system-orchestrator"):
        self.mailbox = mailbox
        self.orchestrator_name = orchestrator_name
        
        # Initialize sub-components
        self.priority_manager = PriorityManager(mailbox)
        self.summary_engine = MessageSummaryEngine(mailbox)
        self.urgent_notices = UrgentNoticeManager(mailbox, orchestrator_name)
        self.task_distributor = TaskDistributor(mailbox)
        
        # Configuration
        self.workload_thresholds = {
            'overwhelming': 50,  # Unread messages
            'busy': 20,
            'normal': 10,
            'idle': 0
        }
        
        self.priority_thresholds = {
            'urgent_ratio': 0.15,    # 15% urgent messages triggers action
            'high_ratio': 0.30,      # 30% high priority triggers action
            'stale_hours': 24        # Messages older than 24h need attention
        }
        
        # Register orchestrator as special admin agent
        self._register_orchestrator()
    
    def _register_orchestrator(self):
        """Register the orchestrator as a special administrative agent."""
        metadata = {
            "role": "system_orchestrator",
            "capabilities": [
                "system_monitoring",
                "workload_management", 
                "priority_coordination",
                "summary_generation",
                "urgent_notices",
                "task_distribution"
            ],
            "admin_level": "system",
            "version": "1.0.0"
        }
        self.mailbox.register_agent(self.orchestrator_name, metadata)
    
    def analyze_system_status(self) -> SystemStatus:
        """Analyze overall system status and identify issues."""
        agents = self.mailbox.get_agents()
        
        total_agents = len(agents)
        active_agents = 0
        total_messages = 0
        unread_messages = 0
        urgent_notices_count = 0
        
        # Analyze each agent
        agent_workloads = []
        for agent in agents:
            if agent.name == self.orchestrator_name:
                continue
                
            workload = self.analyze_agent_workload(agent.name)
            agent_workloads.append(workload)
            
            # Aggregate metrics
            if workload.status != 'idle':
                active_agents += 1
            total_messages += workload.total_messages
            unread_messages += workload.unread_messages
            urgent_notices_count += workload.urgent_messages
        
        # Determine system load
        avg_unread = unread_messages / max(active_agents, 1)
        if avg_unread > 30 or urgent_notices_count > 10:
            system_load = 'critical'
        elif avg_unread > 15 or urgent_notices_count > 5:
            system_load = 'high'
        elif avg_unread > 5:
            system_load = 'normal'
        else:
            system_load = 'low'
        
        # Identify bottlenecks
        bottlenecks = []
        overwhelmed_agents = [w for w in agent_workloads if w.status == 'overwhelmed']
        if overwhelmed_agents:
            bottlenecks.append(f"{len(overwhelmed_agents)} agents overwhelmed")
        
        if urgent_notices_count > 10:
            bottlenecks.append(f"{urgent_notices_count} urgent notices pending")
        
        # Generate recommendations
        recommendations = self._generate_system_recommendations(agent_workloads, system_load)
        
        return SystemStatus(
            total_agents=total_agents,
            active_agents=active_agents,
            total_messages=total_messages,
            unread_messages=unread_messages,
            urgent_notices=urgent_notices_count,
            system_load=system_load,
            bottlenecks=bottlenecks,
            recommendations=recommendations
        )
    
    def analyze_agent_workload(self, agent_name: str) -> AgentWorkload:
        """Analyze a specific agent's workload and status."""
        # Get agent info
        agents = self.mailbox.get_agents()
        agent_info = next((a for a in agents if a.name == agent_name), None)
        
        if not agent_info:
            return AgentWorkload(
                agent_name=agent_name,
                total_messages=0,
                unread_messages=0,
                urgent_messages=0,
                high_priority_messages=0,
                recent_activity=0,
                last_seen=datetime.now(timezone.utc),
                status='idle',
                recommendations=["Agent not found or not registered"]
            )
        
        # Get message statistics
        stats = self.mailbox.get_message_stats(agent_name)
        messages = self.mailbox.get_messages(agent_name, unread_only=False, limit=1000)
        
        # Analyze message priorities
        urgent_messages = len([m for m in messages if m.priority == 'urgent' and not m.read])
        high_priority_messages = len([m for m in messages if m.priority == 'high' and not m.read])
        
        # Determine status
        unread_count = stats['unread']
        if unread_count >= self.workload_thresholds['overwhelming']:
            status = 'overwhelmed'
        elif unread_count >= self.workload_thresholds['busy']:
            status = 'busy'
        elif unread_count > self.workload_thresholds['idle']:
            status = 'normal'
        else:
            status = 'idle'
        
        # Generate recommendations
        recommendations = self._generate_agent_recommendations(
            agent_name, unread_count, urgent_messages, high_priority_messages, messages
        )
        
        return AgentWorkload(
            agent_name=agent_name,
            total_messages=stats['total_received'],
            unread_messages=unread_count,
            urgent_messages=urgent_messages,
            high_priority_messages=high_priority_messages,
            recent_activity=stats['recent_activity'],
            last_seen=agent_info.last_seen,
            status=status,
            recommendations=recommendations
        )
    
    def _generate_agent_recommendations(
        self, 
        agent_name: str, 
        unread_count: int, 
        urgent_count: int, 
        high_priority_count: int,
        messages: List[Message]
    ) -> List[str]:
        """Generate specific recommendations for an agent."""
        recommendations = []
        
        # Workload recommendations
        if unread_count >= self.workload_thresholds['overwhelming']:
            recommendations.append("🚨 CRITICAL: Generate summary to help agent prioritize")
            recommendations.append("📋 Consider task redistribution to other agents")
            
        if urgent_count > 5:
            recommendations.append(f"⚡ {urgent_count} urgent messages need immediate attention")
            
        if high_priority_count > 10:
            recommendations.append(f"🔥 {high_priority_count} high-priority messages pending")
        
        # Staleness analysis
        now = datetime.now(timezone.utc)
        stale_messages = [
            m for m in messages 
            if not m.read and (now - m.timestamp.replace(tzinfo=timezone.utc)).total_seconds() > 86400
        ]
        
        if stale_messages:
            recommendations.append(f"⏰ {len(stale_messages)} messages older than 24 hours")
        
        # Task distribution recommendations
        if len(messages) > 30:
            similar_agents = self._find_similar_agents(agent_name)
            if similar_agents:
                recommendations.append(f"🔄 Consider delegating to: {', '.join(similar_agents)}")
        
        return recommendations
    
    def _generate_system_recommendations(
        self, 
        agent_workloads: List[AgentWorkload], 
        system_load: str
    ) -> List[str]:
        """Generate system-wide recommendations."""
        recommendations = []
        
        if system_load == 'critical':
            recommendations.append("🚨 SYSTEM CRITICAL: Immediate orchestrator intervention needed")
            recommendations.append("📊 Generate summaries for all overwhelmed agents")
            recommendations.append("⚡ Escalate all urgent notices")
            
        elif system_load == 'high':
            recommendations.append("⚠️ High system load: Monitor closely")
            recommendations.append("🔄 Consider workload redistribution")
        
        # Specific agent recommendations
        overwhelmed = [w for w in agent_workloads if w.status == 'overwhelmed']
        if overwhelmed:
            for workload in overwhelmed:
                recommendations.append(f"🆘 {workload.agent_name}: {workload.unread_messages} unread - needs summary")
        
        # Load balancing recommendations
        busy_agents = [w for w in agent_workloads if w.status in ['overwhelmed', 'busy']]
        idle_agents = [w for w in agent_workloads if w.status == 'idle']
        
        if busy_agents and idle_agents:
            recommendations.append(f"⚖️ Load balance: {len(busy_agents)} busy, {len(idle_agents)} idle agents")
        
        return recommendations
    
    def _find_similar_agents(self, agent_name: str) -> List[str]:
        """Find agents with similar capabilities for task delegation."""
        agents = self.mailbox.get_agents()
        similar = []
        
        # Basic similarity matching (can be enhanced with more sophisticated logic)
        for agent in agents:
            if agent.name != agent_name and agent.name != self.orchestrator_name:
                # Check if agent has capacity
                workload = self.analyze_agent_workload(agent.name)
                if workload.status in ['normal', 'idle']:
                    similar.append(agent.name)
        
        return similar[:3]  # Return top 3 candidates
    
    def create_agent_summary(self, agent_name: str, max_messages: int = 50) -> str:
        """Create an intelligent summary for an overwhelmed agent."""
        return self.summary_engine.create_comprehensive_summary(agent_name, max_messages)
    
    def send_urgent_notice(
        self, 
        recipient: str, 
        subject: str, 
        body: str, 
        notice_type: str = "system_alert"
    ) -> str:
        """Send an urgent notice with orchestrator authority."""
        return self.urgent_notices.send_urgent_notice(recipient, subject, body, notice_type)
    
    def broadcast_urgent_notice(
        self, 
        subject: str, 
        body: str, 
        notice_type: str = "system_broadcast",
        exclude_agents: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """Broadcast urgent notice to all agents."""
        return self.urgent_notices.broadcast_urgent_notice(subject, body, notice_type, exclude_agents)
    
    def redistribute_workload(
        self, 
        overloaded_agent: str, 
        target_agents: Optional[List[str]] = None,
        criteria: str = "equal_distribution"
    ) -> Dict[str, Any]:
        """Redistribute workload from overloaded agent to others."""
        return self.task_distributor.redistribute_workload(
            overloaded_agent, target_agents, criteria
        )
    
    def optimize_priorities(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Optimize message priorities system-wide or for specific agent."""
        return self.priority_manager.optimize_priorities(agent_name)
    
    def escalate_stale_messages(self, hours_threshold: int = 24) -> Dict[str, Any]:
        """Escalate messages that have been unread for too long."""
        return self.priority_manager.escalate_stale_messages(hours_threshold)
    
    def get_orchestrator_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive orchestrator dashboard data."""
        system_status = self.analyze_system_status()
        
        # Get detailed agent workloads
        agents = self.mailbox.get_agents()
        agent_workloads = []
        for agent in agents:
            if agent.name != self.orchestrator_name:
                workload = self.analyze_agent_workload(agent.name)
                agent_workloads.append(workload.__dict__)
        
        # Get recent urgent notices
        recent_notices = self.urgent_notices.get_recent_notices(limit=10)
        
        # Get priority optimization suggestions
        priority_suggestions = self.priority_manager.analyze_priority_distribution()
        
        # Get task distribution recommendations
        distribution_recommendations = self.task_distributor.get_load_balancing_recommendations()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_status": system_status.__dict__,
            "agent_workloads": agent_workloads,
            "recent_urgent_notices": recent_notices,
            "priority_analysis": priority_suggestions,
            "load_balancing": distribution_recommendations,
            "orchestrator_metadata": {
                "name": self.orchestrator_name,
                "uptime": "active",
                "capabilities": [
                    "system_monitoring",
                    "workload_management",
                    "priority_coordination", 
                    "summary_generation",
                    "urgent_notices",
                    "task_distribution"
                ]
            }
        }
    
    def perform_system_optimization(self) -> Dict[str, Any]:
        """Perform comprehensive system optimization."""
        optimization_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actions_taken": [],
            "recommendations": [],
            "system_health_improvement": {}
        }
        
        # Analyze current system status
        system_status = self.analyze_system_status()
        
        # 1. Handle overwhelmed agents
        agents = self.mailbox.get_agents()
        for agent in agents:
            if agent.name == self.orchestrator_name:
                continue
                
            workload = self.analyze_agent_workload(agent.name)
            
            if workload.status == 'overwhelmed':
                # Generate summary
                summary = self.create_agent_summary(agent.name)
                summary_msg_id = self.send_urgent_notice(
                    agent.name,
                    f"🚨 ORCHESTRATOR SUMMARY: {workload.unread_messages} Messages Prioritized",
                    summary,
                    "workload_summary"
                )
                
                optimization_results["actions_taken"].append({
                    "action": "generated_summary",
                    "agent": agent.name,
                    "unread_count": workload.unread_messages,
                    "summary_message_id": summary_msg_id
                })
                
                # Suggest redistribution if possible
                similar_agents = self._find_similar_agents(agent.name)
                if similar_agents:
                    redistribution = self.redistribute_workload(agent.name, similar_agents[:2])
                    optimization_results["actions_taken"].append({
                        "action": "workload_redistribution",
                        "from_agent": agent.name,
                        "to_agents": similar_agents[:2],
                        "details": redistribution
                    })
        
        # 2. Escalate stale messages
        stale_escalation = self.escalate_stale_messages(24)
        if stale_escalation.get("escalated_count", 0) > 0:
            optimization_results["actions_taken"].append({
                "action": "escalated_stale_messages",
                "details": stale_escalation
            })
        
        # 3. Optimize priorities system-wide
        priority_optimization = self.optimize_priorities()
        if priority_optimization.get("optimizations_applied", 0) > 0:
            optimization_results["actions_taken"].append({
                "action": "priority_optimization",
                "details": priority_optimization
            })
        
        # 4. Generate system-wide recommendations
        optimization_results["recommendations"] = system_status.recommendations
        
        # 5. Calculate health improvement
        post_optimization_status = self.analyze_system_status()
        optimization_results["system_health_improvement"] = {
            "before": {
                "system_load": system_status.system_load,
                "unread_messages": system_status.unread_messages,
                "urgent_notices": system_status.urgent_notices
            },
            "after": {
                "system_load": post_optimization_status.system_load,
                "unread_messages": post_optimization_status.unread_messages,
                "urgent_notices": post_optimization_status.urgent_notices
            }
        }
        
        return optimization_results
