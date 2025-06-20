"""
Message Summary Engine for AI Mail MCP Orchestrator.

Creates intelligent summaries for agents with large message volumes,
focusing on actionable insights and priority organization.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import re

from ..mailbox import MailboxManager
from ..models import Message

logger = logging.getLogger(__name__)


class MessageSummaryEngine:
    """
    Generates intelligent summaries for overwhelmed agents.
    
    Focuses on:
    - Priority-based organization
    - Actionable item extraction  
    - Context preservation for critical items
    - Breadth-first approach for equal priority tasks
    - Clear next-action recommendations
    """
    
    def __init__(self, mailbox: MailboxManager):
        self.mailbox = mailbox
        
        # Summary configuration
        self.priority_weights = {
            'urgent': 1.0,
            'high': 0.8,
            'normal': 0.5,
            'low': 0.2
        }
        
        # Action keywords for extracting actionable items
        self.action_keywords = [
            'please', 'request', 'need', 'require', 'must', 'should',
            'action required', 'please review', 'please confirm', 
            'deadline', 'due', 'asap', 'urgent', 'complete', 'finish',
            'respond', 'reply', 'feedback', 'approval', 'decision'
        ]
        
        # Question indicators
        self.question_indicators = ['?', 'what', 'when', 'where', 'who', 'why', 'how']
        
        # Category keywords for message classification
        self.category_keywords = {
            'task_assignment': ['task', 'assignment', 'project', 'deliverable', 'work on'],
            'code_review': ['review', 'code', 'pull request', 'merge', 'feedback'],
            'meeting_coordination': ['meeting', 'schedule', 'calendar', 'time', 'availability'],
            'status_update': ['status', 'update', 'progress', 'completed', 'finished'],
            'question': ['question', 'clarification', 'help', 'how to', 'what is'],
            'decision_needed': ['decision', 'approval', 'choose', 'decide', 'option'],
            'escalation': ['escalation', 'issue', 'problem', 'blocker', 'stuck'],
            'information_sharing': ['fyi', 'information', 'heads up', 'notice', 'announcement']
        }
    
    def create_comprehensive_summary(
        self, 
        agent_name: str, 
        max_messages: int = 50,
        focus_mode: str = "balanced"  # "urgent_first", "breadth_first", "balanced"
    ) -> str:
        """
        Create a comprehensive summary for an agent with many messages.
        
        Args:
            agent_name: Target agent name
            max_messages: Maximum messages to analyze
            focus_mode: Summary focus strategy
        """
        # Get messages for analysis
        all_messages = self.mailbox.get_messages(agent_name, unread_only=False, limit=max_messages)
        unread_messages = [msg for msg in all_messages if not msg.read]
        
        if not unread_messages:
            return "✅ **ORCHESTRATOR SUMMARY**: No unread messages found. All caught up!"
        
        # Analyze and categorize messages
        analysis = self._analyze_message_batch(unread_messages)
        
        # Generate summary based on focus mode
        if focus_mode == "urgent_first":
            summary = self._create_urgent_first_summary(analysis, unread_messages)
        elif focus_mode == "breadth_first":
            summary = self._create_breadth_first_summary(analysis, unread_messages)
        else:  # balanced
            summary = self._create_balanced_summary(analysis, unread_messages)
        
        return summary
    
    def _analyze_message_batch(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze a batch of messages for summary generation."""
        analysis = {
            "total_count": len(messages),
            "priority_breakdown": defaultdict(int),
            "category_breakdown": defaultdict(int),
            "sender_breakdown": defaultdict(int),
            "actionable_items": [],
            "questions": [],
            "urgent_items": [],
            "recent_threads": defaultdict(list),
            "stale_messages": [],
            "key_topics": []
        }
        
        now = datetime.now(timezone.utc)
        
        for message in messages:
            # Priority analysis
            analysis["priority_breakdown"][message.priority] += 1
            
            # Sender analysis
            analysis["sender_breakdown"][message.sender] += 1
            
            # Category classification
            category = self._classify_message(message)
            analysis["category_breakdown"][category] += 1
            
            # Age analysis
            age_hours = (now - message.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            
            if age_hours > 48:  # Older than 2 days
                analysis["stale_messages"].append({
                    "id": message.id,
                    "sender": message.sender,
                    "subject": message.subject,
                    "age_hours": round(age_hours, 1),
                    "priority": message.priority
                })
            
            # Thread analysis
            if message.thread_id:
                analysis["recent_threads"][message.thread_id].append(message)
            
            # Content analysis
            if self._is_actionable(message):
                action_item = self._extract_action_item(message)
                analysis["actionable_items"].append(action_item)
            
            if self._contains_question(message):
                question = self._extract_question(message)
                analysis["questions"].append(question)
            
            # Urgent items (urgent priority or critical keywords)
            if message.priority == 'urgent' or self._is_critical_content(message):
                analysis["urgent_items"].append({
                    "id": message.id,
                    "sender": message.sender, 
                    "subject": message.subject,
                    "priority": message.priority,
                    "urgency_reason": self._explain_urgency(message),
                    "age_hours": round(age_hours, 1)
                })
        
        # Extract key topics
        analysis["key_topics"] = self._extract_key_topics(messages)
        
        return analysis
    
    def _classify_message(self, message: Message) -> str:
        """Classify message into a category."""
        content = f"{message.subject} {message.body}".lower()
        
        # Score each category
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content)
            if score > 0:
                category_scores[category] = score
        
        # Check tags for category hints
        if message.tags:
            tag_content = " ".join(message.tags).lower()
            for category, keywords in self.category_keywords.items():
                additional_score = sum(1 for keyword in keywords if keyword in tag_content)
                category_scores[category] = category_scores.get(category, 0) + additional_score * 2
        
        # Return highest scoring category or default
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        else:
            return 'general_communication'
    
    def _is_actionable(self, message: Message) -> bool:
        """Determine if message contains actionable items."""
        content = f"{message.subject} {message.body}".lower()
        
        # Check for action keywords
        action_score = sum(1 for keyword in self.action_keywords if keyword in content)
        
        # Check for imperative language patterns
        imperative_patterns = [
            r'\bplease\s+\w+',
            r'\bneed\s+to\s+\w+',
            r'\bmust\s+\w+',
            r'\brequire\s+\w+',
            r'\baction\s+required',
            r'\bdeadline\b',
            r'\bdue\s+\w+'
        ]
        
        pattern_matches = sum(1 for pattern in imperative_patterns if re.search(pattern, content))
        
        return action_score > 0 or pattern_matches > 0
    
    def _extract_action_item(self, message: Message) -> Dict[str, Any]:
        """Extract actionable item details from message."""
        content = f"{message.subject} {message.body}"
        
        # Find action phrases
        action_phrases = []
        for keyword in self.action_keywords:
            if keyword.lower() in content.lower():
                # Extract sentence containing the keyword
                sentences = content.split('.')
                for sentence in sentences:
                    if keyword.lower() in sentence.lower():
                        action_phrases.append(sentence.strip())
                        break
        
        return {
            "message_id": message.id,
            "sender": message.sender,
            "subject": message.subject,
            "priority": message.priority,
            "action_phrases": action_phrases[:2],  # Top 2 action phrases
            "deadline_mentioned": self._extract_deadline(message),
            "category": self._classify_message(message)
        }
    
    def _contains_question(self, message: Message) -> bool:
        """Check if message contains questions."""
        content = f"{message.subject} {message.body}"
        
        # Look for question marks
        if '?' in content:
            return True
        
        # Look for question words at sentence beginnings
        sentences = content.split('.')
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if any(sentence.startswith(word) for word in ['what', 'when', 'where', 'who', 'why', 'how']):
                return True
        
        return False
    
    def _extract_question(self, message: Message) -> Dict[str, Any]:
        """Extract question details from message."""
        content = f"{message.subject} {message.body}"
        
        # Find sentences with questions
        questions = []
        sentences = content.split('.')
        
        for sentence in sentences:
            if '?' in sentence or any(sentence.strip().lower().startswith(word) for word in ['what', 'when', 'where', 'who', 'why', 'how']):
                questions.append(sentence.strip())
        
        return {
            "message_id": message.id,
            "sender": message.sender,
            "subject": message.subject,
            "priority": message.priority,
            "questions": questions[:2],  # Top 2 questions
            "urgency": message.priority in ['urgent', 'high']
        }
    
    def _is_critical_content(self, message: Message) -> bool:
        """Check if message contains critical content keywords."""
        critical_keywords = [
            'critical', 'emergency', 'urgent', 'immediate', 'crisis',
            'failure', 'down', 'broken', 'error', 'issue', 'problem'
        ]
        
        content = f"{message.subject} {message.body}".lower()
        return any(keyword in content for keyword in critical_keywords)
    
    def _explain_urgency(self, message: Message) -> str:
        """Explain why a message is considered urgent."""
        reasons = []
        
        if message.priority == 'urgent':
            reasons.append("Marked as urgent priority")
        
        content = f"{message.subject} {message.body}".lower()
        
        critical_keywords = ['critical', 'emergency', 'immediate', 'crisis', 'failure', 'down']
        found_keywords = [kw for kw in critical_keywords if kw in content]
        
        if found_keywords:
            reasons.append(f"Contains critical keywords: {', '.join(found_keywords)}")
        
        if 'deadline' in content or 'due' in content:
            reasons.append("Mentions deadline")
        
        return "; ".join(reasons) if reasons else "Content analysis"
    
    def _extract_deadline(self, message: Message) -> Optional[str]:
        """Extract deadline information from message."""
        content = f"{message.subject} {message.body}".lower()
        
        # Look for deadline patterns
        deadline_patterns = [
            r'deadline\s+(\w+\s+\w+)',
            r'due\s+(\w+\s+\w+)',
            r'by\s+(\w+day)',
            r'before\s+(\w+\s+\w+)'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_key_topics(self, messages: List[Message]) -> List[str]:
        """Extract key topics from message batch."""
        # Combine all subject lines and extract common themes
        all_subjects = " ".join([msg.subject for msg in messages])
        all_tags = []
        for msg in messages:
            all_tags.extend(msg.tags)
        
        # Count word frequency in subjects (excluding common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        words = re.findall(r'\b\w+\b', all_subjects.lower())
        word_freq = Counter([w for w in words if len(w) > 3 and w not in common_words])
        
        # Get most common tags
        tag_freq = Counter(all_tags)
        
        # Combine and return top topics
        topics = []
        topics.extend([word for word, count in word_freq.most_common(5) if count > 1])
        topics.extend([tag for tag, count in tag_freq.most_common(3) if count > 1])
        
        return topics[:6]  # Return top 6 topics
    
    def _create_urgent_first_summary(self, analysis: Dict[str, Any], messages: List[Message]) -> str:
        """Create summary prioritizing urgent items first."""
        summary_parts = []
        
        # Header
        summary_parts.append("🚨 **ORCHESTRATOR PRIORITY SUMMARY** - Urgent First Approach")
        summary_parts.append(f"📊 **Total Unread**: {analysis['total_count']} messages")
        summary_parts.append("")
        
        # Urgent items first
        if analysis["urgent_items"]:
            summary_parts.append("🔥 **IMMEDIATE ACTION REQUIRED** (Handle First):")
            for i, item in enumerate(analysis["urgent_items"][:5], 1):
                summary_parts.append(f"   **{i}.** From {item['sender']} ({item['age_hours']:.1f}h ago)")
                summary_parts.append(f"       Subject: {item['subject']}")
                summary_parts.append(f"       Urgency: {item['urgency_reason']}")
            summary_parts.append("")
        
        # High priority actionable items
        high_priority_actions = [item for item in analysis["actionable_items"] if item["priority"] == "high"]
        if high_priority_actions:
            summary_parts.append("⚡ **HIGH PRIORITY ACTIONS**:")
            for i, item in enumerate(high_priority_actions[:5], 1):
                summary_parts.append(f"   **{i}.** {item['sender']}: {item['subject']}")
                if item["action_phrases"]:
                    summary_parts.append(f"       Action: {item['action_phrases'][0]}")
                if item["deadline_mentioned"]:
                    summary_parts.append(f"       Deadline: {item['deadline_mentioned']}")
            summary_parts.append("")
        
        # Critical questions needing answers
        urgent_questions = [q for q in analysis["questions"] if q["urgency"]]
        if urgent_questions:
            summary_parts.append("❓ **URGENT QUESTIONS** (Need Response):")
            for i, q in enumerate(urgent_questions[:3], 1):
                summary_parts.append(f"   **{i}.** From {q['sender']}: {q['subject']}")
                if q["questions"]:
                    summary_parts.append(f"       Q: {q['questions'][0]}")
            summary_parts.append("")
        
        # Stale high-priority items
        stale_important = [msg for msg in analysis["stale_messages"] if msg["priority"] in ["urgent", "high"]]
        if stale_important:
            summary_parts.append("⏰ **OVERDUE ITEMS** (>48h old):")
            for i, item in enumerate(stale_important[:3], 1):
                summary_parts.append(f"   **{i}.** {item['sender']}: {item['subject']} ({item['age_hours']:.1f}h)")
            summary_parts.append("")
        
        # Normal priority summary (condensed)
        normal_count = analysis["priority_breakdown"]["normal"]
        if normal_count > 0:
            summary_parts.append(f"📋 **NORMAL PRIORITY**: {normal_count} messages (review after urgent items)")
            
            # Show top senders for normal priority
            normal_messages = [msg for msg in messages if msg.priority == "normal"]
            sender_counts = Counter([msg.sender for msg in normal_messages])
            top_senders = sender_counts.most_common(3)
            
            if top_senders:
                summary_parts.append("   Top senders: " + ", ".join([f"{sender} ({count})" for sender, count in top_senders]))
            summary_parts.append("")
        
        # Next actions
        summary_parts.append("🎯 **RECOMMENDED ACTION SEQUENCE**:")
        summary_parts.append("1. Handle all urgent items immediately")
        summary_parts.append("2. Respond to urgent questions")
        summary_parts.append("3. Address overdue high-priority items")
        summary_parts.append("4. Process high-priority actions")
        summary_parts.append("5. Review normal priority in sender groups")
        
        return "\n".join(summary_parts)
    
    def _create_breadth_first_summary(self, analysis: Dict[str, Any], messages: List[Message]) -> str:
        """Create summary using breadth-first approach for equal priority tasks."""
        summary_parts = []
        
        # Header
        summary_parts.append("📋 **ORCHESTRATOR BREADTH SUMMARY** - Equal Priority Distribution")
        summary_parts.append(f"📊 **Total Unread**: {analysis['total_count']} messages")
        summary_parts.append("")
        
        # Priority distribution
        summary_parts.append("⚖️ **PRIORITY DISTRIBUTION**:")
        for priority in ["urgent", "high", "normal", "low"]:
            count = analysis["priority_breakdown"][priority]
            if count > 0:
                summary_parts.append(f"   • {priority.title()}: {count} messages")
        summary_parts.append("")
        
        # Category-based organization (breadth-first)
        summary_parts.append("🗂️ **BY CATEGORY** (Process in parallel):")
        
        category_priority = [
            ("task_assignment", "📋 Task Assignments"),
            ("decision_needed", "⚖️ Decisions Needed"),
            ("question", "❓ Questions"),
            ("code_review", "👁️ Code Reviews"),
            ("escalation", "🚨 Escalations"),
            ("status_update", "📊 Status Updates"),
            ("meeting_coordination", "📅 Meeting Coordination"),
            ("information_sharing", "📢 Information Sharing")
        ]
        
        for category, display_name in category_priority:
            count = analysis["category_breakdown"][category]
            if count > 0:
                # Get messages in this category
                category_messages = [msg for msg in messages if self._classify_message(msg) == category]
                
                summary_parts.append(f"**{display_name}** ({count} messages):")
                
                # Group by sender for breadth-first processing
                sender_groups = defaultdict(list)
                for msg in category_messages[:10]:  # Limit to 10 per category
                    sender_groups[msg.sender].append(msg)
                
                for sender, sender_messages in list(sender_groups.items())[:3]:  # Top 3 senders
                    summary_parts.append(f"   • {sender}: {len(sender_messages)} messages")
                    if len(sender_messages) == 1:
                        summary_parts.append(f"     → {sender_messages[0].subject}")
                    else:
                        summary_parts.append(f"     → Latest: {sender_messages[0].subject}")
                
                summary_parts.append("")
        
        # Thread-based grouping
        if analysis["recent_threads"]:
            summary_parts.append("🧵 **ACTIVE CONVERSATIONS** (Process by thread):")
            for thread_id, thread_messages in list(analysis["recent_threads"].items())[:5]:
                latest_msg = max(thread_messages, key=lambda m: m.timestamp)
                summary_parts.append(f"   • Thread with {latest_msg.sender}: {len(thread_messages)} messages")
                summary_parts.append(f"     → Latest: {latest_msg.subject}")
            summary_parts.append("")
        
        # Sender-based grouping for efficiency
        summary_parts.append("👥 **BY SENDER** (Batch process):")
        sender_counts = Counter([msg.sender for msg in messages])
        for sender, count in sender_counts.most_common(5):
            summary_parts.append(f"   • {sender}: {count} messages")
        summary_parts.append("")
        
        # Breadth-first processing strategy
        summary_parts.append("🎯 **BREADTH-FIRST PROCESSING STRATEGY**:")
        summary_parts.append("1. **Quick triage**: Scan all urgent/high priority items first")
        summary_parts.append("2. **Category rotation**: Spend 15-20 min per category")
        summary_parts.append("3. **Sender batching**: Process all messages from one sender together")
        summary_parts.append("4. **Thread completion**: Finish entire conversation threads")
        summary_parts.append("5. **Time boxing**: Set fixed time limits to prevent getting stuck")
        summary_parts.append("")
        summary_parts.append("💡 **Tip**: This approach ensures progress across all areas rather than deep-diving into one.")
        
        return "\n".join(summary_parts)
    
    def _create_balanced_summary(self, analysis: Dict[str, Any], messages: List[Message]) -> str:
        """Create balanced summary combining urgent-first with breadth-first elements."""
        summary_parts = []
        
        # Header
        summary_parts.append("⚖️ **ORCHESTRATOR BALANCED SUMMARY** - Smart Prioritization")
        summary_parts.append(f"📊 **Total Unread**: {analysis['total_count']} messages")
        summary_parts.append("")
        
        # Critical items first (but limited)
        if analysis["urgent_items"]:
            summary_parts.append("🚨 **CRITICAL ITEMS** (Handle immediately):")
            for i, item in enumerate(analysis["urgent_items"][:3], 1):  # Limit to top 3
                summary_parts.append(f"   **{i}.** {item['sender']}: {item['subject']} ({item['age_hours']:.1f}h)")
            summary_parts.append("")
        
        # Priority overview with actionable breakdown
        summary_parts.append("📈 **PRIORITY OVERVIEW**:")
        for priority in ["urgent", "high", "normal", "low"]:
            count = analysis["priority_breakdown"][priority]
            if count > 0:
                # Get actionable items for this priority
                priority_actions = [item for item in analysis["actionable_items"] if item["priority"] == priority]
                action_count = len(priority_actions)
                
                summary_parts.append(f"   • **{priority.title()}**: {count} total ({action_count} actionable)")
        summary_parts.append("")
        
        # Smart grouping by efficiency
        summary_parts.append("🎯 **SMART GROUPING** (Optimized for efficiency):")
        
        # Quick wins (easy actions)
        quick_actions = [item for item in analysis["actionable_items"] 
                        if len(item.get("action_phrases", [""])[0]) < 100 and item["priority"] in ["normal", "high"]]
        if quick_actions:
            summary_parts.append(f"⚡ **Quick Actions** ({len(quick_actions)} items - 5-10 min each):")
            for item in quick_actions[:4]:
                summary_parts.append(f"   • {item['sender']}: {item['subject']}")
            summary_parts.append("")
        
        # Questions needing responses
        if analysis["questions"]:
            summary_parts.append(f"❓ **Questions** ({len(analysis['questions'])} items - batch respond):")
            for q in analysis["questions"][:3]:
                summary_parts.append(f"   • {q['sender']}: {q['subject']}")
            summary_parts.append("")
        
        # Collaboration opportunities (threads)
        if analysis["recent_threads"]:
            summary_parts.append(f"🤝 **Active Threads** ({len(analysis['recent_threads'])} conversations):")
            for thread_id, thread_messages in list(analysis["recent_threads"].items())[:3]:
                latest = max(thread_messages, key=lambda m: m.timestamp)
                summary_parts.append(f"   • {latest.sender}: {len(thread_messages)} messages in thread")
            summary_parts.append("")
        
        # Stale items needing attention
        if analysis["stale_messages"]:
            summary_parts.append(f"⏰ **Stale Items** ({len(analysis['stale_messages'])} overdue):")
            for item in analysis["stale_messages"][:3]:
                summary_parts.append(f"   • {item['sender']}: {item['subject']} ({item['age_hours']:.1f}h)")
            summary_parts.append("")
        
        # Category insights
        top_categories = sorted(analysis["category_breakdown"].items(), key=lambda x: x[1], reverse=True)[:3]
        if top_categories:
            summary_parts.append("📊 **Top Categories**:")
            for category, count in top_categories:
                summary_parts.append(f"   • {category.replace('_', ' ').title()}: {count} messages")
            summary_parts.append("")
        
        # Key topics
        if analysis["key_topics"]:
            summary_parts.append(f"🔑 **Key Topics**: {', '.join(analysis['key_topics'][:5])}")
            summary_parts.append("")
        
        # Balanced processing strategy
        summary_parts.append("🎯 **BALANCED PROCESSING STRATEGY**:")
        summary_parts.append("**Phase 1 (30 min)**: Handle all critical items + quick actions")
        summary_parts.append("**Phase 2 (45 min)**: Process high-priority items + respond to questions")  
        summary_parts.append("**Phase 3 (30 min)**: Address stale items + active threads")
        summary_parts.append("**Phase 4 (Ongoing)**: Batch process normal priority by category")
        summary_parts.append("")
        summary_parts.append("💡 **Focus**: Complete urgent work first, then maintain momentum with mixed priority levels")
        
        return "\n".join(summary_parts)
    
    def create_daily_digest(self, agent_name: str) -> str:
        """Create a daily digest summary for an agent."""
        # Get messages from last 24 hours
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        messages = self.mailbox.get_messages(agent_name, unread_only=False, limit=200)
        
        recent_messages = [
            msg for msg in messages 
            if msg.timestamp.replace(tzinfo=timezone.utc) >= yesterday
        ]
        
        if not recent_messages:
            return f"📅 **DAILY DIGEST** for {agent_name}\n\nNo new messages in the last 24 hours. All caught up! ✅"
        
        # Analyze recent activity
        analysis = self._analyze_message_batch(recent_messages)
        
        digest_parts = []
        digest_parts.append(f"📅 **DAILY DIGEST** for {agent_name}")
        digest_parts.append(f"📊 **Last 24 hours**: {len(recent_messages)} messages")
        digest_parts.append("")
        
        # Activity summary
        digest_parts.append("📈 **Activity Summary**:")
        digest_parts.append(f"   • Total messages: {len(recent_messages)}")
        digest_parts.append(f"   • Unread: {len([m for m in recent_messages if not m.read])}")
        digest_parts.append(f"   • Urgent: {analysis['priority_breakdown']['urgent']}")
        digest_parts.append(f"   • Actionable items: {len(analysis['actionable_items'])}")
        digest_parts.append("")
        
        # Top senders
        sender_counts = Counter([msg.sender for msg in recent_messages])
        if sender_counts:
            digest_parts.append("👥 **Most Active Senders**:")
            for sender, count in sender_counts.most_common(3):
                digest_parts.append(f"   • {sender}: {count} messages")
            digest_parts.append("")
        
        # Key topics
        if analysis["key_topics"]:
            digest_parts.append(f"🔑 **Trending Topics**: {', '.join(analysis['key_topics'][:4])}")
            digest_parts.append("")
        
        # Action needed
        unread_count = len([m for m in recent_messages if not m.read])
        if unread_count > 0:
            digest_parts.append(f"🎯 **Action Needed**: {unread_count} unread messages require attention")
        else:
            digest_parts.append("✅ **Status**: All messages processed - great work!")
        
        return "\n".join(digest_parts)
