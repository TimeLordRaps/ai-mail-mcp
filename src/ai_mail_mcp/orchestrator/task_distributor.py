"""
Task Distribution Manager for AI Mail MCP Orchestrator.

Handles intelligent task distribution and workload balancing
across AI agents in the local system.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter

from ..mailbox import MailboxManager
from ..models import Message, AgentInfo

logger = logging.getLogger(__name__)


class TaskDistributor:
    """
    Manages task distribution and workload balancing across AI agents.
    
    Responsibilities:
    - Analyze agent capabilities and current workloads
    - Redistribute tasks from overwhelmed agents
    - Suggest optimal task assignments
    - Monitor distribution effectiveness
    - Provide load balancing recommendations
    """
    
    def __init__(self, mailbox: MailboxManager):
        self.mailbox = mailbox
        
        # Distribution configuration
        self.distribution_criteria = {
            'equal_distribution': self._equal_distribution_strategy,
            'capability_based': self._capability_based_strategy,
            'workload_balanced': self._workload_balanced_strategy,
            'priority_focused': self._priority_focused_strategy
        }
        
        # Agent capability inference (can be enhanced with explicit metadata)
        self.capability_keywords = {
            'code': ['code', 'programming', 'development', 'review', 'debug', 'fix'],
            'documentation': ['docs', 'documentation', 'writing', 'readme', 'guide'],
            'analysis': ['analyze', 'analysis', 'data', 'research', 'investigate'],
            'coordination': ['coordinate', 'manage', 'schedule', 'meeting', 'plan'],
            'support': ['support', 'help', 'assist', 'customer', 'user'],
            'testing': ['test', 'testing', 'qa', 'quality', 'validation']
        }
        
        # Workload thresholds for distribution decisions
        self.workload_thresholds = {
            'overwhelmed': 50,    # Messages requiring redistribution
            'high_load': 30,      # Messages indicating high workload
            'normal_load': 15,    # Balanced workload
            'low_load': 5,        # Available for more tasks
            'idle': 0             # No current workload
        }
    
    def redistribute_workload(
        self, 
        overloaded_agent: str, 
        target_agents: Optional[List[str]] = None,
        criteria: str = "workload_balanced"
    ) -> Dict[str, Any]:
        """
        Redistribute workload from an overloaded agent to others.
        
        Args:
            overloaded_agent: Agent with too many messages
            target_agents: Specific agents to redistribute to (optional)
            criteria: Distribution strategy to use
        
        Returns:
            Dictionary with redistribution results and recommendations
        """
        # Get current workload status
        overloaded_workload = self._analyze_agent_workload(overloaded_agent)
        
        if overloaded_workload['unread_count'] < self.workload_thresholds['high_load']:
            return {
                "redistribution_needed": False,
                "reason": f"Agent {overloaded_agent} workload is manageable ({overloaded_workload['unread_count']} messages)",
                "current_workload": overloaded_workload
            }
        
        # Find suitable target agents
        if not target_agents:
            target_agents = self._find_available_agents(overloaded_agent)
        
        if not target_agents:
            return {
                "redistribution_needed": True,
                "redistribution_possible": False,
                "reason": "No available agents found for redistribution",
                "recommendation": "Consider generating summary for overwhelmed agent",
                "current_workload": overloaded_workload
            }
        
        # Apply distribution strategy
        distribution_strategy = self.distribution_criteria.get(criteria, self._workload_balanced_strategy)
        redistribution_plan = distribution_strategy(overloaded_agent, target_agents, overloaded_workload)
        
        # Calculate impact metrics
        impact_analysis = self._analyze_redistribution_impact(overloaded_agent, redistribution_plan)
        
        return {
            "redistribution_needed": True,
            "redistribution_possible": True,
            "overloaded_agent": overloaded_agent,
            "target_agents": target_agents,
            "strategy_used": criteria,
            "current_workload": overloaded_workload,
            "redistribution_plan": redistribution_plan,
            "impact_analysis": impact_analysis,
            "recommendations": self._generate_redistribution_recommendations(redistribution_plan)
        }
    
    def _analyze_agent_workload(self, agent_name: str) -> Dict[str, Any]:
        """Analyze an agent's current workload and characteristics."""
        # Get basic statistics
        stats = self.mailbox.get_message_stats(agent_name)
        messages = self.mailbox.get_messages(agent_name, unread_only=False, limit=200)
        unread_messages = [msg for msg in messages if not msg.read]
        
        # Analyze message characteristics
        priority_breakdown = defaultdict(int)
        category_breakdown = defaultdict(int)
        sender_diversity = set()
        age_distribution = {'fresh': 0, 'moderate': 0, 'stale': 0}
        
        now = datetime.now(timezone.utc)
        
        for msg in unread_messages:
            priority_breakdown[msg.priority] += 1
            sender_diversity.add(msg.sender)
            
            # Categorize by age
            age_hours = (now - msg.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            if age_hours < 8:
                age_distribution['fresh'] += 1
            elif age_hours < 48:
                age_distribution['moderate'] += 1
            else:
                age_distribution['stale'] += 1
            
            # Infer category from content
            category = self._infer_message_category(msg)
            category_breakdown[category] += 1
        
        # Determine workload status
        unread_count = len(unread_messages)
        if unread_count >= self.workload_thresholds['overwhelmed']:
            status = 'overwhelmed'
        elif unread_count >= self.workload_thresholds['high_load']:
            status = 'high_load'
        elif unread_count >= self.workload_thresholds['normal_load']:
            status = 'normal_load'
        elif unread_count >= self.workload_thresholds['low_load']:
            status = 'low_load'
        else:
            status = 'idle'
        
        return {
            'agent_name': agent_name,
            'unread_count': unread_count,
            'total_messages': stats['total_received'],
            'status': status,
            'priority_breakdown': dict(priority_breakdown),
            'category_breakdown': dict(category_breakdown),
            'sender_diversity': len(sender_diversity),
            'age_distribution': age_distribution,
            'inferred_capabilities': self._infer_agent_capabilities(messages),
            'recent_activity': stats['recent_activity']
        }
    
    def _find_available_agents(self, exclude_agent: str) -> List[str]:
        """Find agents available for task redistribution."""
        agents = self.mailbox.get_agents()
        available_agents = []
        
        for agent in agents:
            if agent.name == exclude_agent or agent.name.startswith('system-'):
                continue
                
            workload = self._analyze_agent_workload(agent.name)
            
            # Consider agents with normal or lower workload as available
            if workload['status'] in ['idle', 'low_load', 'normal_load']:
                available_agents.append({
                    'name': agent.name,
                    'workload': workload,
                    'capacity_score': self._calculate_capacity_score(workload)
                })
        
        # Sort by capacity (highest capacity first)
        available_agents.sort(key=lambda x: x['capacity_score'], reverse=True)
        
        return [agent['name'] for agent in available_agents[:5]]  # Return top 5 candidates
    
    def _calculate_capacity_score(self, workload: Dict[str, Any]) -> float:
        """Calculate an agent's capacity to take on additional work."""
        base_capacity = {
            'idle': 1.0,
            'low_load': 0.8,
            'normal_load': 0.5,
            'high_load': 0.2,
            'overwhelmed': 0.0
        }
        
        status_score = base_capacity.get(workload['status'], 0.0)
        
        # Adjust based on recent activity (lower activity = higher capacity)
        activity_factor = max(0.1, 1.0 - (workload['recent_activity'] / 50))
        
        # Adjust based on message age distribution (more fresh messages = less capacity)
        fresh_ratio = workload['age_distribution']['fresh'] / max(workload['unread_count'], 1)
        age_factor = max(0.1, 1.0 - fresh_ratio * 0.5)
        
        return status_score * activity_factor * age_factor
    
    def _infer_message_category(self, message: Message) -> str:
        """Infer message category from content and tags."""
        content = f"{message.subject} {message.body}".lower()
        
        # Check tags first (explicit categorization)
        if message.tags:
            tag_content = " ".join(message.tags).lower()
            for category, keywords in self.capability_keywords.items():
                if any(keyword in tag_content for keyword in keywords):
                    return category
        
        # Infer from content
        category_scores = {}
        for category, keywords in self.capability_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            return 'general'
    
    def _infer_agent_capabilities(self, messages: List[Message]) -> List[str]:
        """Infer an agent's capabilities from their message history."""
        capability_scores = defaultdict(int)
        
        # Analyze sent and received messages for capability indicators
        for msg in messages[-50:]:  # Look at recent 50 messages
            content = f"{msg.subject} {msg.body}".lower()
            
            for capability, keywords in self.capability_keywords.items():
                score = sum(1 for keyword in keywords if keyword in content)
                capability_scores[capability] += score
        
        # Return capabilities with significant evidence
        threshold = 2  # At least 2 keyword matches
        return [cap for cap, score in capability_scores.items() if score >= threshold]
    
    def _equal_distribution_strategy(
        self, 
        overloaded_agent: str, 
        target_agents: List[str], 
        workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Distribute tasks equally among available agents."""
        messages_to_redistribute = min(workload['unread_count'] // 2, 20)  # Redistribute up to half or 20 messages
        messages_per_agent = messages_to_redistribute // len(target_agents)
        remainder = messages_to_redistribute % len(target_agents)
        
        distribution = {}
        for i, agent in enumerate(target_agents):
            allocation = messages_per_agent + (1 if i < remainder else 0)
            if allocation > 0:
                distribution[agent] = {
                    'message_count': allocation,
                    'criteria': 'equal_distribution',
                    'priority_focus': 'any'
                }
        
        return {
            'strategy': 'equal_distribution',
            'total_redistributed': sum(d['message_count'] for d in distribution.values()),
            'distribution': distribution,
            'rationale': 'Distribute workload equally among all available agents'
        }
    
    def _capability_based_strategy(
        self, 
        overloaded_agent: str, 
        target_agents: List[str], 
        workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Distribute tasks based on agent capabilities and message types."""
        # Analyze what types of messages need redistribution
        messages = self.mailbox.get_messages(overloaded_agent, unread_only=True, limit=50)
        category_counts = defaultdict(int)
        
        for msg in messages:
            category = self._infer_message_category(msg)
            category_counts[category] += 1
        
        # Get capabilities of target agents
        agent_capabilities = {}
        for agent in target_agents:
            agent_workload = self._analyze_agent_workload(agent)
            agent_capabilities[agent] = agent_workload['inferred_capabilities']
        
        # Match categories to agents based on capabilities
        distribution = {}
        for category, count in category_counts.items():
            # Find agents with this capability
            capable_agents = [agent for agent, caps in agent_capabilities.items() if category in caps]
            
            if not capable_agents:
                capable_agents = target_agents  # Fall back to any available agent
            
            # Distribute this category's messages among capable agents
            messages_per_agent = count // len(capable_agents)
            remainder = count % len(capable_agents)
            
            for i, agent in enumerate(capable_agents):
                allocation = messages_per_agent + (1 if i < remainder else 0)
                if allocation > 0:
                    if agent not in distribution:
                        distribution[agent] = {'message_count': 0, 'categories': [], 'criteria': 'capability_based'}
                    
                    distribution[agent]['message_count'] += allocation
                    distribution[agent]['categories'].append(category)
        
        return {
            'strategy': 'capability_based',
            'total_redistributed': sum(d['message_count'] for d in distribution.values()),
            'distribution': distribution,
            'rationale': 'Match message types to agents with relevant capabilities'
        }
    
    def _workload_balanced_strategy(
        self, 
        overloaded_agent: str, 
        target_agents: List[str], 
        workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Distribute tasks to balance workloads across agents."""
        # Get current workloads of target agents
        agent_workloads = {}
        for agent in target_agents:
            agent_workloads[agent] = self._analyze_agent_workload(agent)
        
        # Sort agents by current workload (lowest first)
        sorted_agents = sorted(agent_workloads.items(), key=lambda x: x[1]['unread_count'])
        
        # Distribute more messages to agents with lower workloads
        total_to_redistribute = min(workload['unread_count'] // 2, 25)
        distribution = {}
        
        # Weight distribution inversely to current workload
        total_weight = sum(1.0 / max(w['unread_count'] + 1, 1) for _, w in sorted_agents)
        
        for agent, agent_workload in sorted_agents:
            weight = 1.0 / max(agent_workload['unread_count'] + 1, 1)
            allocation = int((weight / total_weight) * total_to_redistribute)
            
            if allocation > 0:
                distribution[agent] = {
                    'message_count': allocation,
                    'current_workload': agent_workload['unread_count'],
                    'criteria': 'workload_balanced',
                    'priority_focus': 'balanced'
                }
        
        return {
            'strategy': 'workload_balanced',
            'total_redistributed': sum(d['message_count'] for d in distribution.values()),
            'distribution': distribution,
            'rationale': 'Balance workloads by giving more tasks to less busy agents'
        }
    
    def _priority_focused_strategy(
        self, 
        overloaded_agent: str, 
        target_agents: List[str], 
        workload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Redistribute based on message priorities and agent capacity for urgent work."""
        # Prioritize redistribution of high and urgent messages
        priority_order = ['urgent', 'high', 'normal', 'low']
        distribution = {}
        
        # Get agents with highest capacity scores (best for urgent work)
        agent_capacities = {}
        for agent in target_agents:
            agent_workload = self._analyze_agent_workload(agent)
            agent_capacities[agent] = self._calculate_capacity_score(agent_workload)
        
        # Sort by capacity (highest first)
        sorted_agents = sorted(agent_capacities.items(), key=lambda x: x[1], reverse=True)
        
        # Redistribute by priority level
        for priority in priority_order:
            priority_count = workload['priority_breakdown'].get(priority, 0)
            if priority_count == 0:
                continue
            
            # For urgent/high priority, use highest capacity agents
            if priority in ['urgent', 'high']:
                target_subset = sorted_agents[:2]  # Top 2 agents
            else:
                target_subset = sorted_agents  # All available agents
            
            # Distribute this priority level
            if target_subset:
                messages_per_agent = priority_count // len(target_subset)
                remainder = priority_count % len(target_subset)
                
                for i, (agent, capacity) in enumerate(target_subset):
                    allocation = messages_per_agent + (1 if i < remainder else 0)
                    if allocation > 0:
                        if agent not in distribution:
                            distribution[agent] = {
                                'message_count': 0, 
                                'priorities': {}, 
                                'criteria': 'priority_focused'
                            }
                        
                        distribution[agent]['message_count'] += allocation
                        distribution[agent]['priorities'][priority] = allocation
        
        return {
            'strategy': 'priority_focused',
            'total_redistributed': sum(d['message_count'] for d in distribution.values()),
            'distribution': distribution,
            'rationale': 'Distribute high-priority messages to highest-capacity agents'
        }
    
    def _analyze_redistribution_impact(
        self, 
        overloaded_agent: str, 
        redistribution_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the expected impact of the redistribution plan."""
        total_redistributed = redistribution_plan.get('total_redistributed', 0)
        current_workload = self.mailbox.get_message_stats(overloaded_agent)['unread']
        
        # Calculate workload reduction
        remaining_workload = current_workload - total_redistributed
        reduction_percentage = (total_redistributed / current_workload) * 100 if current_workload > 0 else 0
        
        # Predict new status
        if remaining_workload >= self.workload_thresholds['overwhelmed']:
            new_status = 'overwhelmed'
        elif remaining_workload >= self.workload_thresholds['high_load']:
            new_status = 'high_load'
        elif remaining_workload >= self.workload_thresholds['normal_load']:
            new_status = 'normal_load'
        else:
            new_status = 'manageable'
        
        # Analyze impact on target agents
        target_impact = {}
        for agent, allocation in redistribution_plan.get('distribution', {}).items():
            current_target_workload = self.mailbox.get_message_stats(agent)['unread']
            new_target_workload = current_target_workload + allocation['message_count']
            
            target_impact[agent] = {
                'current_workload': current_target_workload,
                'additional_messages': allocation['message_count'],
                'new_workload': new_target_workload,
                'workload_increase_pct': (allocation['message_count'] / max(current_target_workload, 1)) * 100
            }
        
        return {
            'overloaded_agent_impact': {
                'current_workload': current_workload,
                'messages_redistributed': total_redistributed,
                'remaining_workload': remaining_workload,
                'workload_reduction_pct': round(reduction_percentage, 1),
                'predicted_new_status': new_status
            },
            'target_agents_impact': target_impact,
            'overall_effectiveness': self._calculate_effectiveness_score(
                reduction_percentage, new_status, target_impact
            )
        }
    
    def _calculate_effectiveness_score(
        self, 
        reduction_pct: float, 
        new_status: str, 
        target_impact: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate the overall effectiveness of the redistribution."""
        # Base score from workload reduction
        reduction_score = min(reduction_pct / 50, 1.0)  # Normalize to 0-1 (50% reduction = full score)
        
        # Status improvement score
        status_scores = {
            'manageable': 1.0,
            'normal_load': 0.8,
            'high_load': 0.5,
            'overwhelmed': 0.2
        }
        status_score = status_scores.get(new_status, 0.0)
        
        # Check if any target agents become overloaded
        overload_penalty = 0.0
        for agent, impact in target_impact.items():
            if impact['new_workload'] > self.workload_thresholds['high_load']:
                overload_penalty += 0.3
        
        # Calculate overall score
        overall_score = (reduction_score * 0.4 + status_score * 0.6) * (1.0 - min(overload_penalty, 0.5))
        
        # Determine effectiveness rating
        if overall_score >= 0.8:
            rating = "Highly Effective"
        elif overall_score >= 0.6:
            rating = "Effective"
        elif overall_score >= 0.4:
            rating = "Moderately Effective"
        else:
            rating = "Low Effectiveness"
        
        return {
            'score': round(overall_score, 2),
            'rating': rating,
            'reduction_score': round(reduction_score, 2),
            'status_score': round(status_score, 2),
            'overload_penalty': round(overload_penalty, 2)
        }
    
    def _generate_redistribution_recommendations(self, redistribution_plan: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on the redistribution plan."""
        recommendations = []
        
        total_redistributed = redistribution_plan.get('total_redistributed', 0)
        strategy = redistribution_plan.get('strategy', 'unknown')
        
        if total_redistributed > 0:
            recommendations.append(f"✅ Redistribute {total_redistributed} messages using {strategy} strategy")
            
            # Strategy-specific recommendations
            if strategy == 'capability_based':
                recommendations.append("💡 Match message types to agent expertise for better efficiency")
            elif strategy == 'workload_balanced':
                recommendations.append("⚖️ Monitor workload balance after redistribution")
            elif strategy == 'priority_focused':
                recommendations.append("🚨 Ensure high-priority messages get immediate attention")
            
            # General recommendations
            recommendations.append("📊 Generate summary for overloaded agent before redistribution")
            recommendations.append("🔄 Follow up in 2-4 hours to assess redistribution effectiveness")
            recommendations.append("📈 Consider preventive measures to avoid future overload")
        else:
            recommendations.append("ℹ️ No redistribution possible - focus on summary generation")
            recommendations.append("🔍 Consider if agent needs additional support or training")
        
        return recommendations
    
    def get_load_balancing_recommendations(self) -> Dict[str, Any]:
        """Generate system-wide load balancing recommendations."""
        agents = self.mailbox.get_agents()
        agent_workloads = []
        
        # Analyze all agent workloads
        for agent in agents:
            if not agent.name.startswith('system-'):
                workload = self._analyze_agent_workload(agent.name)
                agent_workloads.append(workload)
        
        if not agent_workloads:
            return {"recommendations": ["No active agents found"]}
        
        # Categorize agents by workload
        overwhelmed = [w for w in agent_workloads if w['status'] == 'overwhelmed']
        high_load = [w for w in agent_workloads if w['status'] == 'high_load']
        normal_load = [w for w in agent_workloads if w['status'] == 'normal_load']
        low_load = [w for w in agent_workloads if w['status'] in ['low_load', 'idle']]
        
        recommendations = []
        
        # High-level recommendations
        if overwhelmed:
            recommendations.append(f"🚨 {len(overwhelmed)} agents overwhelmed - immediate redistribution needed")
            for agent in overwhelmed:
                recommendations.append(f"   → {agent['agent_name']}: {agent['unread_count']} unread messages")
        
        if high_load and low_load:
            recommendations.append(f"⚖️ Load imbalance detected: {len(high_load)} high-load vs {len(low_load)} low-load agents")
            recommendations.append("   → Consider proactive task redistribution")
        
        if len(low_load) / len(agent_workloads) > 0.5:
            recommendations.append("💡 Many agents have low workload - opportunities for additional task assignment")
        
        # Specific redistribution opportunities
        redistribution_opportunities = []
        for overloaded_agent in overwhelmed + high_load:
            available_agents = [w['agent_name'] for w in low_load + normal_load]
            if available_agents:
                redistribution_opportunities.append({
                    'from_agent': overloaded_agent['agent_name'],
                    'to_agents': available_agents[:3],
                    'message_count': overloaded_agent['unread_count'],
                    'recommended_strategy': 'workload_balanced'
                })
        
        # Capability gaps analysis
        all_categories = set()
        agent_capabilities = {}
        for workload in agent_workloads:
            all_categories.update(workload['category_breakdown'].keys())
            agent_capabilities[workload['agent_name']] = workload['inferred_capabilities']
        
        coverage_analysis = {}
        for category in all_categories:
            capable_agents = [name for name, caps in agent_capabilities.items() if category in caps]
            coverage_analysis[category] = {
                'capable_agents': len(capable_agents),
                'coverage_percentage': (len(capable_agents) / len(agent_workloads)) * 100
            }
        
        # Identify capability gaps
        low_coverage_categories = [cat for cat, analysis in coverage_analysis.items() 
                                 if analysis['coverage_percentage'] < 50]
        
        if low_coverage_categories:
            recommendations.append(f"🎯 Capability gaps in: {', '.join(low_coverage_categories)}")
            recommendations.append("   → Consider agent training or specialization")
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system_overview': {
                'total_agents': len(agent_workloads),
                'overwhelmed': len(overwhelmed),
                'high_load': len(high_load),
                'normal_load': len(normal_load),
                'low_load': len(low_load)
            },
            'workload_distribution': [
                {
                    'agent': w['agent_name'],
                    'unread_count': w['unread_count'],
                    'status': w['status'],
                    'capabilities': w['inferred_capabilities']
                }
                for w in agent_workloads
            ],
            'redistribution_opportunities': redistribution_opportunities,
            'capability_coverage': coverage_analysis,
            'recommendations': recommendations
        }
