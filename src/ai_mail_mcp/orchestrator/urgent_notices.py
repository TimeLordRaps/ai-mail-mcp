"""
Urgent Notices Manager for AI Mail MCP Orchestrator.

Handles system-wide urgent notices, alerts, and administrative
communications with orchestrator authority.
"""

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from ..mailbox import MailboxManager
from ..models import Message

logger = logging.getLogger(__name__)


class UrgentNoticeManager:
    """
    Manages urgent notices and system-wide alerts with orchestrator authority.
    
    Responsibilities:
    - Send urgent notices with system authority
    - Broadcast critical alerts to all agents
    - Track notice delivery and acknowledgment
    - Manage notice escalation and follow-up
    - Provide notice analytics and reporting
    """
    
    def __init__(self, mailbox: MailboxManager, orchestrator_name: str):
        self.mailbox = mailbox
        self.orchestrator_name = orchestrator_name
        
        # Notice types and their characteristics
        self.notice_types = {
            "system_alert": {
                "priority": "urgent",
                "requires_ack": True,
                "escalation_hours": 2,
                "icon": "🚨",
                "format": "SYSTEM ALERT"
            },
            "system_broadcast": {
                "priority": "high", 
                "requires_ack": False,
                "escalation_hours": 8,
                "icon": "📢",
                "format": "SYSTEM BROADCAST"
            },
            "workload_summary": {
                "priority": "high",
                "requires_ack": False,
                "escalation_hours": None,
                "icon": "📊",
                "format": "ORCHESTRATOR SUMMARY"
            },
            "priority_escalation": {
                "priority": "urgent",
                "requires_ack": True,
                "escalation_hours": 1,
                "icon": "⚡",
                "format": "PRIORITY ESCALATION"
            },
            "system_maintenance": {
                "priority": "normal",
                "requires_ack": False,
                "escalation_hours": 24,
                "icon": "🔧",
                "format": "MAINTENANCE NOTICE"
            },
            "performance_alert": {
                "priority": "high",
                "requires_ack": True,
                "escalation_hours": 4,
                "icon": "📈",
                "format": "PERFORMANCE ALERT"
            },
            "security_notice": {
                "priority": "urgent",
                "requires_ack": True,
                "escalation_hours": 1,
                "icon": "🔒",
                "format": "SECURITY NOTICE"
            }
        }
        
        # Notice tracking
        self.notice_history = []
    
    def send_urgent_notice(
        self, 
        recipient: str, 
        subject: str, 
        body: str, 
        notice_type: str = "system_alert",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Send an urgent notice with orchestrator authority.
        
        Args:
            recipient: Target agent name
            subject: Notice subject line  
            body: Notice content
            notice_type: Type of notice (determines formatting and priority)
            metadata: Additional notice metadata
        """
        notice_config = self.notice_types.get(notice_type, self.notice_types["system_alert"])
        
        # Format the notice with orchestrator authority
        formatted_subject = f"{notice_config['icon']} {notice_config['format']}: {subject}"
        formatted_body = self._format_notice_body(body, notice_type, notice_config, metadata)
        
        # Create notice message
        notice_id = str(uuid.uuid4())
        notice_message = Message(
            id=notice_id,
            sender=self.orchestrator_name,
            recipient=recipient,
            subject=formatted_subject,
            body=formatted_body,
            timestamp=datetime.now(timezone.utc),
            priority=notice_config["priority"],
            tags=["orchestrator", "urgent_notice", notice_type, "system_admin"],
            thread_id=f"notice-{notice_type}-{uuid.uuid4().hex[:8]}"
        )
        
        # Send the notice
        message_id = self.mailbox.send_message(notice_message)
        
        # Track the notice
        notice_record = {
            "notice_id": notice_id,
            "message_id": message_id,
            "notice_type": notice_type,
            "recipient": recipient,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "requires_ack": notice_config["requires_ack"],
            "escalation_hours": notice_config["escalation_hours"],
            "acknowledged": False,
            "acknowledged_at": None,
            "metadata": metadata or {}
        }
        
        self.notice_history.append(notice_record)
        
        logger.info(f"Urgent notice sent: {notice_type} to {recipient} - {message_id}")
        
        return message_id
    
    def broadcast_urgent_notice(
        self, 
        subject: str, 
        body: str, 
        notice_type: str = "system_broadcast",
        exclude_agents: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Broadcast urgent notice to all agents.
        
        Args:
            subject: Notice subject
            body: Notice content
            notice_type: Type of broadcast notice
            exclude_agents: Agents to exclude from broadcast
            metadata: Additional broadcast metadata
            
        Returns:
            Dict mapping agent names to message IDs
        """
        exclude_agents = exclude_agents or []
        exclude_agents.append(self.orchestrator_name)  # Don't send to self
        
        # Get all registered agents
        agents = self.mailbox.get_agents()
        
        broadcast_results = {}
        broadcast_id = f"broadcast-{uuid.uuid4().hex[:8]}"
        
        # Add broadcast metadata
        broadcast_metadata = metadata or {}
        broadcast_metadata.update({
            "broadcast_id": broadcast_id,
            "broadcast_type": "system_wide",
            "total_recipients": len([a for a in agents if a.name not in exclude_agents])
        })
        
        for agent in agents:
            if agent.name in exclude_agents:
                continue
            
            # Customize message for each agent
            agent_metadata = broadcast_metadata.copy()
            agent_metadata["recipient_agent"] = agent.name
            
            message_id = self.send_urgent_notice(
                recipient=agent.name,
                subject=subject,
                body=body,
                notice_type=notice_type,
                metadata=agent_metadata
            )
            
            broadcast_results[agent.name] = message_id
        
        logger.info(f"Broadcast notice sent to {len(broadcast_results)} agents: {notice_type}")
        
        return broadcast_results
    
    def _format_notice_body(
        self, 
        body: str, 
        notice_type: str, 
        notice_config: Dict, 
        metadata: Optional[Dict] = None
    ) -> str:
        """Format notice body with orchestrator authority and context."""
        formatted_parts = []
        
        # Header with authority
        formatted_parts.append(f"{notice_config['icon']} **{notice_config['format']}**")
        formatted_parts.append(f"**From**: System Orchestrator ({self.orchestrator_name})")
        formatted_parts.append(f"**Time**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        formatted_parts.append(f"**Priority**: {notice_config['priority'].upper()}")
        
        # Acknowledgment requirement
        if notice_config["requires_ack"]:
            formatted_parts.append("**⚠️ ACKNOWLEDGMENT REQUIRED**: Please confirm receipt")
        
        formatted_parts.append("")
        formatted_parts.append("---")
        formatted_parts.append("")
        
        # Main content
        formatted_parts.append(body)
        
        # Additional context based on notice type
        if notice_type == "workload_summary":
            formatted_parts.append("")
            formatted_parts.append("---")
            formatted_parts.append("📋 **How to Use This Summary**:")
            formatted_parts.append("• Review urgent items first (🚨)")
            formatted_parts.append("• Use the recommended action sequence")
            formatted_parts.append("• Focus on high-impact, quick-win items")
            formatted_parts.append("• Ask for help if overwhelmed")
            
        elif notice_type == "priority_escalation":
            formatted_parts.append("")
            formatted_parts.append("---")
            formatted_parts.append("⚡ **Escalation Reason**: Automatic priority adjustment")
            formatted_parts.append("🎯 **Required Action**: Address escalated items immediately")
            
        elif notice_type == "system_alert":
            if notice_config["escalation_hours"]:
                formatted_parts.append("")
                formatted_parts.append("---")
                formatted_parts.append(f"⏰ **Response Required Within**: {notice_config['escalation_hours']} hour(s)")
                formatted_parts.append("🔄 **Escalation**: Will auto-escalate if no response")
        
        # Metadata information
        if metadata:
            important_fields = ["deadline", "impact", "action_required", "contact"]
            metadata_lines = []
            
            for field in important_fields:
                if field in metadata:
                    metadata_lines.append(f"• **{field.replace('_', ' ').title()}**: {metadata[field]}")
            
            if metadata_lines:
                formatted_parts.append("")
                formatted_parts.append("---")
                formatted_parts.append("📋 **Additional Information**:")
                formatted_parts.extend(metadata_lines)
        
        # Footer
        formatted_parts.append("")
        formatted_parts.append("---")
        formatted_parts.append("🤖 *This notice was sent automatically by the AI Mail System Orchestrator*")
        formatted_parts.append("*For system issues, check orchestrator status or contact administrator*")
        
        return "\n".join(formatted_parts)
    
    def send_workload_summary_notice(
        self, 
        recipient: str, 
        summary_content: str, 
        workload_stats: Dict[str, Any]
    ) -> str:
        """Send a specialized workload summary notice."""
        subject = f"Workload Summary - {workload_stats.get('unread_count', 0)} Messages Prioritized"
        
        metadata = {
            "summary_type": "workload_optimization",
            "message_count": workload_stats.get("total_messages", 0),
            "unread_count": workload_stats.get("unread_count", 0),
            "urgent_count": workload_stats.get("urgent_messages", 0),
            "action_required": "Review and follow recommended sequence",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        return self.send_urgent_notice(
            recipient=recipient,
            subject=subject,
            body=summary_content,
            notice_type="workload_summary",
            metadata=metadata
        )
    
    def send_priority_escalation_notice(
        self, 
        recipient: str, 
        escalated_messages: List[Dict[str, Any]]
    ) -> str:
        """Send a priority escalation notice."""
        count = len(escalated_messages)
        subject = f"{count} Messages Escalated Due to Age"
        
        # Format escalation details
        escalation_details = []
        escalation_details.append(f"**{count} messages have been automatically escalated:**")
        escalation_details.append("")
        
        for i, msg in enumerate(escalated_messages[:10], 1):  # Show top 10
            escalation_details.append(f"**{i}.** {msg['subject']}")
            escalation_details.append(f"   • From: {msg.get('sender', 'Unknown')}")
            escalation_details.append(f"   • Age: {msg.get('age_hours', 0):.1f} hours")
            escalation_details.append(f"   • Priority: {msg['current_priority']} → {msg['new_priority']}")
            escalation_details.append("")
        
        if len(escalated_messages) > 10:
            escalation_details.append(f"... and {len(escalated_messages) - 10} more messages")
            escalation_details.append("")
        
        escalation_details.append("🎯 **Action Required**: Please review these escalated items immediately")
        escalation_details.append("⏰ **Note**: Messages were escalated due to extended unread time")
        
        body = "\n".join(escalation_details)
        
        metadata = {
            "escalation_type": "age_based",
            "escalated_count": count,
            "escalation_trigger": "stale_messages",
            "action_required": "immediate_review"
        }
        
        return self.send_urgent_notice(
            recipient=recipient,
            subject=subject,
            body=body,
            notice_type="priority_escalation",
            metadata=metadata
        )
    
    def send_system_performance_alert(
        self, 
        performance_issue: str, 
        affected_agents: List[str],
        severity: str = "high"
    ) -> Dict[str, str]:
        """Send system performance alert."""
        subject = f"System Performance Issue: {performance_issue}"
        
        body_parts = []
        body_parts.append(f"**Issue**: {performance_issue}")
        body_parts.append(f"**Severity**: {severity.upper()}")
        body_parts.append(f"**Affected Agents**: {len(affected_agents)}")
        body_parts.append("")
        body_parts.append("**Impact Analysis**:")
        body_parts.append("• Message processing delays may occur")
        body_parts.append("• Response times may be slower than normal")
        body_parts.append("• System optimization is in progress")
        body_parts.append("")
        body_parts.append("**Recommended Actions**:")
        body_parts.append("• Prioritize urgent messages only")
        body_parts.append("• Defer non-critical tasks")
        body_parts.append("• Monitor for system updates")
        
        body = "\n".join(body_parts)
        
        metadata = {
            "issue_type": "performance",
            "severity": severity,
            "affected_agent_count": len(affected_agents),
            "auto_resolution": "in_progress"
        }
        
        # Send to affected agents
        results = {}
        for agent in affected_agents:
            message_id = self.send_urgent_notice(
                recipient=agent,
                subject=subject,
                body=body,
                notice_type="performance_alert",
                metadata=metadata
            )
            results[agent] = message_id
        
        return results
    
    def get_recent_notices(self, limit: int = 20, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent notices sent by the orchestrator."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        recent_notices = []
        for notice in self.notice_history:
            sent_at = datetime.fromisoformat(notice["sent_at"])
            if sent_at >= cutoff_time:
                recent_notices.append(notice)
        
        # Sort by most recent first
        recent_notices.sort(key=lambda x: x["sent_at"], reverse=True)
        
        return recent_notices[:limit]
    
    def get_notice_analytics(self, days_back: int = 7) -> Dict[str, Any]:
        """Get analytics on notice sending patterns."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Filter recent notices
        recent_notices = []
        for notice in self.notice_history:
            sent_at = datetime.fromisoformat(notice["sent_at"])
            if sent_at >= cutoff_time:
                recent_notices.append(notice)
        
        if not recent_notices:
            return {
                "analysis_period_days": days_back,
                "total_notices": 0,
                "message": "No notices sent in the specified period"
            }
        
        # Calculate analytics
        notice_types = {}
        daily_counts = {}
        acknowledgment_stats = {"required": 0, "received": 0}
        
        for notice in recent_notices:
            # Type distribution
            notice_type = notice["notice_type"]
            notice_types[notice_type] = notice_types.get(notice_type, 0) + 1
            
            # Daily distribution
            sent_date = datetime.fromisoformat(notice["sent_at"]).date().isoformat()
            daily_counts[sent_date] = daily_counts.get(sent_date, 0) + 1
            
            # Acknowledgment tracking
            if notice["requires_ack"]:
                acknowledgment_stats["required"] += 1
                if notice["acknowledged"]:
                    acknowledgment_stats["received"] += 1
        
        # Calculate rates
        ack_rate = 0
        if acknowledgment_stats["required"] > 0:
            ack_rate = round((acknowledgment_stats["received"] / acknowledgment_stats["required"]) * 100, 1)
        
        return {
            "analysis_period_days": days_back,
            "total_notices": len(recent_notices),
            "notice_type_distribution": notice_types,
            "daily_notice_counts": daily_counts,
            "acknowledgment_statistics": {
                "required": acknowledgment_stats["required"],
                "received": acknowledgment_stats["received"],
                "acknowledgment_rate_percent": ack_rate
            },
            "most_common_type": max(notice_types.items(), key=lambda x: x[1])[0] if notice_types else None,
            "average_daily_notices": round(len(recent_notices) / days_back, 1)
        }
    
    def check_unacknowledged_notices(self) -> List[Dict[str, Any]]:
        """Check for unacknowledged notices that may need escalation."""
        now = datetime.now(timezone.utc)
        overdue_notices = []
        
        for notice in self.notice_history:
            if not notice["requires_ack"] or notice["acknowledged"]:
                continue
            
            sent_at = datetime.fromisoformat(notice["sent_at"])
            escalation_hours = notice["escalation_hours"]
            
            if escalation_hours and (now - sent_at).total_seconds() > escalation_hours * 3600:
                hours_overdue = (now - sent_at).total_seconds() / 3600 - escalation_hours
                
                overdue_notices.append({
                    "notice_id": notice["notice_id"],
                    "message_id": notice["message_id"],
                    "recipient": notice["recipient"],
                    "notice_type": notice["notice_type"],
                    "subject": notice["subject"],
                    "sent_at": notice["sent_at"],
                    "hours_overdue": round(hours_overdue, 1),
                    "escalation_recommended": True
                })
        
        return overdue_notices
    
    def escalate_unacknowledged_notice(self, notice_id: str) -> str:
        """Escalate an unacknowledged notice."""
        # Find the original notice
        original_notice = None
        for notice in self.notice_history:
            if notice["notice_id"] == notice_id:
                original_notice = notice
                break
        
        if not original_notice:
            raise ValueError(f"Notice {notice_id} not found")
        
        # Send escalation notice
        subject = f"ESCALATION: Unacknowledged Notice - {original_notice['subject']}"
        
        body_parts = []
        body_parts.append("**NOTICE ESCALATION**")
        body_parts.append("")
        body_parts.append(f"**Original Notice**: {original_notice['subject']}")
        body_parts.append(f"**Sent**: {original_notice['sent_at']}")
        body_parts.append(f"**Type**: {original_notice['notice_type']}")
        body_parts.append("")
        body_parts.append("**⚠️ URGENT**: This notice required acknowledgment but has not been confirmed.")
        body_parts.append("")
        body_parts.append("**Required Action**: Please acknowledge the original notice immediately")
        body_parts.append("**Impact**: Continued non-response may affect system coordination")
        body_parts.append("")
        body_parts.append("**Original Message ID**: " + original_notice['message_id'])
        
        body = "\n".join(body_parts)
        
        metadata = {
            "escalation": True,
            "original_notice_id": notice_id,
            "original_message_id": original_notice["message_id"],
            "escalation_reason": "unacknowledged_notice"
        }
        
        escalation_message_id = self.send_urgent_notice(
            recipient=original_notice["recipient"],
            subject=subject,
            body=body,
            notice_type="system_alert",
            metadata=metadata
        )
        
        logger.warning(f"Escalated unacknowledged notice {notice_id} to {original_notice['recipient']}")
        
        return escalation_message_id
    
    def mark_notice_acknowledged(self, notice_id: str, acknowledged_by: str) -> bool:
        """Mark a notice as acknowledged."""
        for notice in self.notice_history:
            if notice["notice_id"] == notice_id:
                notice["acknowledged"] = True
                notice["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                notice["acknowledged_by"] = acknowledged_by
                
                logger.info(f"Notice {notice_id} acknowledged by {acknowledged_by}")
                return True
        
        return False
    
    def send_system_status_broadcast(self, system_status: Dict[str, Any]) -> Dict[str, str]:
        """Send system status broadcast to all agents."""
        status_level = system_status.get("system_load", "unknown")
        
        subject = f"System Status Update - Load: {status_level.upper()}"
        
        body_parts = []
        body_parts.append("**SYSTEM STATUS REPORT**")
        body_parts.append("")
        body_parts.append(f"**System Load**: {status_level.upper()}")
        body_parts.append(f"**Total Agents**: {system_status.get('total_agents', 0)}")
        body_parts.append(f"**Active Agents**: {system_status.get('active_agents', 0)}")
        body_parts.append(f"**Unread Messages**: {system_status.get('unread_messages', 0)}")
        body_parts.append(f"**Urgent Notices**: {system_status.get('urgent_notices', 0)}")
        body_parts.append("")
        
        if system_status.get("bottlenecks"):
            body_parts.append("**⚠️ Current Bottlenecks**:")
            for bottleneck in system_status["bottlenecks"]:
                body_parts.append(f"• {bottleneck}")
            body_parts.append("")
        
        if system_status.get("recommendations"):
            body_parts.append("**📋 System Recommendations**:")
            for rec in system_status["recommendations"][:5]:
                body_parts.append(f"• {rec}")
            body_parts.append("")
        
        body_parts.append("**🎯 Action Required**: Review personal workload and coordinate as needed")
        
        body = "\n".join(body_parts)
        
        metadata = {
            "status_type": "system_overview",
            "system_load": status_level,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return self.broadcast_urgent_notice(
            subject=subject,
            body=body,
            notice_type="system_broadcast",
            metadata=metadata
        )
