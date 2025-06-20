"""
Priority Manager for AI Mail MCP Orchestrator.

Handles intelligent priority management, escalation, and optimization
of message priorities across the system.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from ..mailbox import MailboxManager
from ..models import Message

logger = logging.getLogger(__name__)


class PriorityManager:
    """
    Manages message priorities and escalation policies.
    
    Responsibilities:
    - Analyze and optimize message priority distribution
    - Escalate messages based on staleness and importance
    - Rebalance priorities to improve agent efficiency
    - Provide priority-based recommendations
    """
    
    def __init__(self, mailbox: MailboxManager):
        self.mailbox = mailbox
        
        # Priority escalation rules
        self.escalation_rules = {
            'urgent': {
                'max_age_hours': 2,      # Urgent messages escalate after 2 hours
                'escalate_to': 'urgent',  # Already at max
                'notification_required': True
            },
            'high': {
                'max_age_hours': 8,      # High priority escalates after 8 hours
                'escalate_to': 'urgent',
                'notification_required': True
            },
            'normal': {
                'max_age_hours': 24,     # Normal escalates after 24 hours
                'escalate_to': 'high',
                'notification_required': False
            },
            'low': {
                'max_age_hours': 72,     # Low escalates after 72 hours
                'escalate_to': 'normal',
                'notification_required': False
            }
        }
        
        # Priority scoring for intelligent rebalancing
        self.priority_scores = {
            'urgent': 100,
            'high': 75,
            'normal': 50,
            'low': 25
        }
        
        # Content-based priority keywords
        self.priority_keywords = {
            'urgent': [
                'critical', 'emergency', 'urgent', 'immediate', 'asap',
                'breaking', 'crisis', 'failure', 'down', 'error'
            ],
            'high': [
                'important', 'priority', 'deadline', 'soon', 'required',
                'blocker', 'blocking', 'needs attention', 'review needed'
            ],
            'normal': [
                'update', 'status', 'information', 'please', 'when possible'
            ],
            'low': [
                'fyi', 'for your information', 'heads up', 'note',
                'eventually', 'nice to have'
            ]
        }
    
    def analyze_priority_distribution(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyze priority distribution across system or for specific agent."""
        if agent_name:
            messages = self.mailbox.get_messages(agent_name, unread_only=False, limit=1000)
            scope = f"agent '{agent_name}'"
        else:
            # Get all messages for system-wide analysis
            agents = self.mailbox.get_agents()
            messages = []
            for agent in agents:
                agent_messages = self.mailbox.get_messages(agent.name, unread_only=False, limit=500)
                messages.extend(agent_messages)
            scope = "system-wide"
        
        # Analyze current distribution
        priority_counts = defaultdict(int)
        unread_priority_counts = defaultdict(int)
        age_by_priority = defaultdict(list)
        
        now = datetime.now(timezone.utc)
        
        for message in messages:
            priority = message.priority
            priority_counts[priority] += 1
            
            if not message.read:
                unread_priority_counts[priority] += 1
            
            # Calculate message age
            age_hours = (now - message.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            age_by_priority[priority].append(age_hours)
        
        # Calculate statistics
        total_messages = len(messages)
        total_unread = sum(unread_priority_counts.values())
        
        distribution_analysis = {
            "scope": scope,
            "total_messages": total_messages,
            "total_unread": total_unread,
            "priority_distribution": dict(priority_counts),
            "unread_priority_distribution": dict(unread_priority_counts),
            "priority_percentages": {
                priority: round((count / total_messages) * 100, 1) if total_messages > 0 else 0
                for priority, count in priority_counts.items()
            },
            "average_age_by_priority": {
                priority: round(sum(ages) / len(ages), 1) if ages else 0
                for priority, ages in age_by_priority.items()
            }
        }
        
        # Generate recommendations
        recommendations = self._generate_priority_recommendations(distribution_analysis, age_by_priority)
        distribution_analysis["recommendations"] = recommendations
        
        # Identify optimization opportunities
        optimizations = self._identify_priority_optimizations(distribution_analysis, age_by_priority)
        distribution_analysis["optimization_opportunities"] = optimizations
        
        return distribution_analysis
    
    def _generate_priority_recommendations(
        self, 
        distribution: Dict[str, Any], 
        age_by_priority: Dict[str, List[float]]
    ) -> List[str]:
        """Generate recommendations based on priority analysis."""
        recommendations = []
        
        # Check for priority imbalances
        percentages = distribution["priority_percentages"]
        
        if percentages.get('urgent', 0) > 20:
            recommendations.append("⚠️ High urgent message percentage - review escalation criteria")
        
        if percentages.get('low', 0) > 50:
            recommendations.append("📈 Many low priority messages - consider auto-processing some")
        
        if percentages.get('normal', 0) < 30:
            recommendations.append("⚖️ Few normal priority messages - may indicate over-escalation")
        
        # Check for stale high-priority messages
        urgent_ages = age_by_priority.get('urgent', [])
        if urgent_ages and max(urgent_ages) > 4:  # 4 hours
            recommendations.append("🚨 Urgent messages older than 4 hours - immediate attention needed")
        
        high_ages = age_by_priority.get('high', [])
        if high_ages and max(high_ages) > 12:  # 12 hours
            recommendations.append("⚡ High priority messages older than 12 hours - review required")
        
        # Overall workload recommendations
        if distribution["total_unread"] > 50:
            recommendations.append("📊 High unread count - consider summary generation")
        
        return recommendations
    
    def _identify_priority_optimizations(
        self, 
        distribution: Dict[str, Any], 
        age_by_priority: Dict[str, List[float]]
    ) -> List[Dict[str, Any]]:
        """Identify specific optimization opportunities."""
        optimizations = []
        
        # Suggest escalations for stale messages
        for priority, ages in age_by_priority.items():
            if not ages:
                continue
                
            rule = self.escalation_rules.get(priority)
            if not rule:
                continue
            
            stale_count = len([age for age in ages if age > rule['max_age_hours']])
            if stale_count > 0:
                optimizations.append({
                    "type": "escalate_stale_messages",
                    "priority": priority,
                    "stale_count": stale_count,
                    "max_age_threshold": rule['max_age_hours'],
                    "escalate_to": rule['escalate_to'],
                    "recommended_action": f"Escalate {stale_count} {priority} messages to {rule['escalate_to']}"
                })
        
        # Suggest content-based priority adjustments
        if distribution["total_messages"] > 20:
            optimizations.append({
                "type": "content_based_reprioritization",
                "description": "Analyze message content for automatic priority adjustment",
                "recommended_action": "Run content analysis to optimize priorities"
            })
        
        # Suggest workload redistribution
        unread_count = distribution["total_unread"]
        if unread_count > 30:
            optimizations.append({
                "type": "workload_redistribution", 
                "unread_count": unread_count,
                "recommended_action": "Consider redistributing messages to less busy agents"
            })
        
        return optimizations
    
    def escalate_stale_messages(self, hours_threshold: int = 24, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Escalate messages that have been unread for too long."""
        if agent_name:
            messages = self.mailbox.get_messages(agent_name, unread_only=True, limit=1000)
            scope = f"agent '{agent_name}'"
        else:
            # System-wide escalation
            agents = self.mailbox.get_agents()
            messages = []
            for agent in agents:
                agent_messages = self.mailbox.get_messages(agent.name, unread_only=True, limit=500)
                messages.extend(agent_messages)
            scope = "system-wide"
        
        now = datetime.now(timezone.utc)
        escalated_messages = []
        
        for message in messages:
            age_hours = (now - message.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            
            # Check if message meets escalation criteria
            rule = self.escalation_rules.get(message.priority)
            if not rule:
                continue
            
            # Use custom threshold or rule-based threshold
            threshold = min(hours_threshold, rule['max_age_hours'])
            
            if age_hours > threshold and message.priority != 'urgent':
                # Escalate the message priority
                new_priority = rule['escalate_to']
                
                # Note: In a real implementation, you'd update the message priority in the database
                # For now, we'll track what would be escalated
                escalated_messages.append({
                    "message_id": message.id,
                    "current_priority": message.priority,
                    "new_priority": new_priority,
                    "age_hours": round(age_hours, 1),
                    "subject": message.subject,
                    "recipient": message.recipient
                })
        
        escalation_summary = {
            "scope": scope,
            "threshold_hours": hours_threshold,
            "total_evaluated": len(messages),
            "escalated_count": len(escalated_messages),
            "escalated_messages": escalated_messages,
            "escalation_breakdown": self._summarize_escalations(escalated_messages)
        }
        
        return escalation_summary
    
    def _summarize_escalations(self, escalated_messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize escalation actions by type."""
        breakdown = defaultdict(int)
        
        for escalation in escalated_messages:
            transition = f"{escalation['current_priority']} → {escalation['new_priority']}"
            breakdown[transition] += 1
        
        return dict(breakdown)
    
    def optimize_priorities(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Optimize message priorities using content analysis and rules."""
        if agent_name:
            messages = self.mailbox.get_messages(agent_name, unread_only=True, limit=200)
            scope = f"agent '{agent_name}'"
        else:
            # System-wide optimization
            agents = self.mailbox.get_agents()
            messages = []
            for agent in agents:
                agent_messages = self.mailbox.get_messages(agent.name, unread_only=True, limit=100)
                messages.extend(agent_messages)
            scope = "system-wide"
        
        optimization_suggestions = []
        
        for message in messages:
            suggested_priority = self._analyze_message_priority(message)
            
            if suggested_priority != message.priority:
                optimization_suggestions.append({
                    "message_id": message.id,
                    "current_priority": message.priority,
                    "suggested_priority": suggested_priority,
                    "confidence": self._calculate_priority_confidence(message, suggested_priority),
                    "reason": self._explain_priority_suggestion(message, suggested_priority),
                    "subject": message.subject,
                    "recipient": message.recipient
                })
        
        # Categorize suggestions by confidence
        high_confidence = [s for s in optimization_suggestions if s["confidence"] > 0.8]
        medium_confidence = [s for s in optimization_suggestions if 0.5 < s["confidence"] <= 0.8]
        low_confidence = [s for s in optimization_suggestions if s["confidence"] <= 0.5]
        
        return {
            "scope": scope,
            "total_analyzed": len(messages),
            "total_suggestions": len(optimization_suggestions),
            "high_confidence_suggestions": high_confidence,
            "medium_confidence_suggestions": medium_confidence,
            "low_confidence_suggestions": low_confidence,
            "optimization_summary": {
                "high_confidence_count": len(high_confidence),
                "medium_confidence_count": len(medium_confidence),
                "low_confidence_count": len(low_confidence),
                "auto_apply_recommended": len(high_confidence)
            }
        }
    
    def _analyze_message_priority(self, message: Message) -> str:
        """Analyze message content to suggest appropriate priority."""
        content = f"{message.subject} {message.body}".lower()
        
        # Score each priority level based on keyword matches
        priority_scores = {}
        
        for priority, keywords in self.priority_keywords.items():
            score = 0
            for keyword in keywords:
                score += content.count(keyword) * (len(keyword) / 5)  # Weight by keyword length
            priority_scores[priority] = score
        
        # Add context-based scoring
        if message.reply_to:
            # Replies often inherit or escalate priority
            priority_scores['high'] += 10
        
        if len(message.tags) > 0:
            # Tagged messages may be more important
            priority_scores['normal'] += 5
            
            # Check for priority-indicating tags
            urgent_tags = ['urgent', 'critical', 'emergency', 'blocker']
            if any(tag.lower() in urgent_tags for tag in message.tags):
                priority_scores['urgent'] += 20
        
        # Consider message age (older unread messages may need escalation)
        now = datetime.now(timezone.utc)
        age_hours = (now - message.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        
        if age_hours > 48:  # 2 days old
            priority_scores['high'] += 15
        elif age_hours > 24:  # 1 day old
            priority_scores['normal'] += 10
        
        # Return highest scoring priority
        if not priority_scores or all(score == 0 for score in priority_scores.values()):
            return 'normal'  # Default fallback
        
        return max(priority_scores.items(), key=lambda x: x[1])[0]
    
    def _calculate_priority_confidence(self, message: Message, suggested_priority: str) -> float:
        """Calculate confidence score for priority suggestion."""
        content = f"{message.subject} {message.body}".lower()
        
        # Base confidence on keyword density and clarity
        keywords = self.priority_keywords.get(suggested_priority, [])
        matches = sum(1 for keyword in keywords if keyword in content)
        
        if not keywords:
            return 0.5  # Medium confidence for default
        
        keyword_confidence = min(matches / len(keywords), 1.0)
        
        # Boost confidence for strong indicators
        strong_indicators = {
            'urgent': ['critical', 'emergency', 'urgent'],
            'high': ['important', 'deadline', 'blocker'],
            'normal': ['update', 'status'],
            'low': ['fyi', 'heads up']
        }
        
        strong_matches = sum(1 for keyword in strong_indicators.get(suggested_priority, []) if keyword in content)
        if strong_matches > 0:
            keyword_confidence = min(keyword_confidence + 0.3, 1.0)
        
        # Consider message structure and length
        structure_confidence = 0.5
        if message.reply_to and suggested_priority in ['high', 'urgent']:
            structure_confidence += 0.2
        
        if len(message.tags) > 0:
            structure_confidence += 0.1
        
        return min((keyword_confidence + structure_confidence) / 2, 1.0)
    
    def _explain_priority_suggestion(self, message: Message, suggested_priority: str) -> str:
        """Provide explanation for priority suggestion."""
        content = f"{message.subject} {message.body}".lower()
        
        # Find matching keywords
        keywords = self.priority_keywords.get(suggested_priority, [])
        found_keywords = [kw for kw in keywords if kw in content]
        
        reasons = []
        
        if found_keywords:
            reasons.append(f"Contains {suggested_priority} keywords: {', '.join(found_keywords[:3])}")
        
        if message.reply_to:
            reasons.append("Part of ongoing conversation thread")
        
        if message.tags:
            urgent_tags = [tag for tag in message.tags if tag.lower() in ['urgent', 'critical', 'emergency']]
            if urgent_tags:
                reasons.append(f"Tagged with priority indicators: {', '.join(urgent_tags)}")
        
        # Age-based reasoning
        now = datetime.now(timezone.utc)
        age_hours = (now - message.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        
        if age_hours > 24:
            reasons.append(f"Message is {age_hours:.1f} hours old")
        
        return "; ".join(reasons) if reasons else "Content analysis based on message structure"
    
    def apply_priority_optimizations(
        self, 
        suggestions: List[Dict[str, Any]], 
        confidence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """Apply priority optimizations automatically for high-confidence suggestions."""
        applied_changes = []
        
        for suggestion in suggestions:
            if suggestion["confidence"] >= confidence_threshold:
                # In a real implementation, you would update the message priority in the database
                # For now, we'll just track what would be changed
                applied_changes.append({
                    "message_id": suggestion["message_id"],
                    "old_priority": suggestion["current_priority"],
                    "new_priority": suggestion["suggested_priority"],
                    "confidence": suggestion["confidence"],
                    "reason": suggestion["reason"]
                })
        
        return {
            "total_suggestions": len(suggestions),
            "applied_changes": len(applied_changes),
            "confidence_threshold": confidence_threshold,
            "changes": applied_changes,
            "success": True
        }
    
    def get_priority_analytics(self, days_back: int = 7) -> Dict[str, Any]:
        """Get comprehensive priority analytics for the specified time period."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Get all agents and their messages
        agents = self.mailbox.get_agents()
        all_messages = []
        
        for agent in agents:
            messages = self.mailbox.get_messages(agent.name, unread_only=False, limit=500)
            # Filter by date
            recent_messages = [
                msg for msg in messages 
                if msg.timestamp.replace(tzinfo=timezone.utc) >= cutoff_date
            ]
            all_messages.extend(recent_messages)
        
        # Analyze trends
        daily_priorities = defaultdict(lambda: defaultdict(int))
        resolution_times = defaultdict(list)
        
        for message in all_messages:
            day = message.timestamp.date().isoformat()
            daily_priorities[day][message.priority] += 1
            
            if message.read:
                # Calculate resolution time (approximation)
                resolution_hours = 24  # Placeholder - would need read timestamp in real implementation
                resolution_times[message.priority].append(resolution_hours)
        
        # Calculate average resolution times
        avg_resolution_times = {
            priority: round(sum(times) / len(times), 1) if times else 0
            for priority, times in resolution_times.items()
        }
        
        # Identify trends
        trends = self._analyze_priority_trends(daily_priorities)
        
        return {
            "analysis_period_days": days_back,
            "total_messages_analyzed": len(all_messages),
            "daily_priority_breakdown": dict(daily_priorities),
            "average_resolution_times_hours": avg_resolution_times,
            "priority_trends": trends,
            "recommendations": self._generate_analytics_recommendations(trends, avg_resolution_times)
        }
    
    def _analyze_priority_trends(self, daily_priorities: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """Analyze trends in priority distribution over time."""
        if not daily_priorities:
            return {}
        
        # Calculate overall trends
        total_by_priority = defaultdict(int)
        for day_data in daily_priorities.values():
            for priority, count in day_data.items():
                total_by_priority[priority] += count
        
        total_messages = sum(total_by_priority.values())
        
        trends = {
            "overall_distribution": {
                priority: round((count / total_messages) * 100, 1) if total_messages > 0 else 0
                for priority, count in total_by_priority.items()
            },
            "daily_averages": {
                priority: round(count / len(daily_priorities), 1) if daily_priorities else 0
                for priority, count in total_by_priority.items()
            }
        }
        
        # Identify concerning patterns
        urgent_percentage = trends["overall_distribution"].get('urgent', 0)
        if urgent_percentage > 15:
            trends["alerts"] = [f"High urgent message percentage: {urgent_percentage}%"]
        else:
            trends["alerts"] = []
        
        return trends
    
    def _generate_analytics_recommendations(
        self, 
        trends: Dict[str, Any], 
        resolution_times: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations based on analytics."""
        recommendations = []
        
        # Resolution time recommendations
        urgent_resolution = resolution_times.get('urgent', 0)
        if urgent_resolution > 4:
            recommendations.append(f"⚠️ Urgent messages taking {urgent_resolution:.1f}h to resolve - target <2h")
        
        high_resolution = resolution_times.get('high', 0)
        if high_resolution > 12:
            recommendations.append(f"📊 High priority messages taking {high_resolution:.1f}h - target <8h")
        
        # Trend-based recommendations
        if trends.get("alerts"):
            recommendations.extend(trends["alerts"])
        
        # Distribution recommendations
        distribution = trends.get("overall_distribution", {})
        if distribution.get('low', 0) > 40:
            recommendations.append("📈 Consider auto-processing some low priority messages")
        
        if distribution.get('normal', 0) < 20:
            recommendations.append("⚖️ Low normal priority percentage - review escalation policies")
        
        return recommendations
