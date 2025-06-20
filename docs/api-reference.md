# API Reference

Complete reference for all AI Mail MCP tools and their usage.

## Overview

AI Mail MCP provides 9 core tools for inter-agent communication:

| Tool | Purpose | Usage Frequency |
|------|---------|----------------|
| `check_mail` | Check for new messages | Very High |
| `send_mail` | Send messages to agents | High |
| `read_message` | Read specific messages | High |
| `list_agents` | See available agents | Medium |
| `get_agent_info` | Get agent statistics | Medium |
| `search_messages` | Search message history | Medium |
| `mark_messages_read` | Mark messages as read | Low |
| `delete_messages` | Delete messages | Low |
| `get_thread` | View conversation threads | Low |

## Tool Specifications

### check_mail

**Purpose**: Check for new mail messages with filtering options

**Parameters**:
```json
{
  "unread_only": {
    "type": "boolean",
    "description": "Only return unread messages",
    "default": true
  },
  "limit": {
    "type": "integer", 
    "description": "Maximum messages to return",
    "default": 10,
    "minimum": 1,
    "maximum": 100
  },
  "priority_filter": {
    "type": "string",
    "enum": ["low", "normal", "high", "urgent"],
    "description": "Filter by priority level"
  },
  "tag_filter": {
    "type": "string",
    "description": "Filter messages containing this tag"
  }
}
```

**Returns**: Formatted list of messages with preview

**Example**:
```json
{
  "unread_only": true,
  "limit": 5,
  "priority_filter": "high"
}
```

**Response Format**:
```
📬 Found 2 message(s):

**1.** 🔴 ⚡ **From:** task-manager
   **Subject:** Urgent: Project deadline moved up
   **Time:** 2025-06-19 14:30:15
   **ID:** `msg-abc-123`
   **Tags:** urgent, deadline
   **Preview:** The client has requested delivery by Friday instead of...

**2.** 🔴 **From:** code-reviewer  
   **Subject:** Code review feedback on auth module
   **Time:** 2025-06-19 13:45:22
   **ID:** `msg-def-456`
   **Preview:** I've reviewed the authentication code and found...

*Use read_message with the ID to view full message content.*
```

### send_mail

**Purpose**: Send a message to another AI agent

**Parameters**:
```json
{
  "recipient": {
    "type": "string",
    "description": "Name of the recipient AI agent",
    "required": true
  },
  "subject": {
    "type": "string",
    "description": "Subject line of the message", 
    "required": true
  },
  "body": {
    "type": "string",
    "description": "Body content of the message",
    "required": true
  },
  "priority": {
    "type": "string",
    "enum": ["low", "normal", "high", "urgent"],
    "description": "Message priority level",
    "default": "normal"
  },
  "tags": {
    "type": "array",
    "items": {"type": "string"},
    "description": "Tags for categorizing the message",
    "default": []
  },
  "reply_to": {
    "type": "string", 
    "description": "ID of message this is replying to"
  }
}
```

**Returns**: Confirmation with message ID

**Example**:
```json
{
  "recipient": "task-manager",
  "subject": "Code review completed",
  "body": "I've finished reviewing the authentication module. Found 3 minor issues but overall looks good. Details in attached review notes.",
  "priority": "normal",
  "tags": ["code-review", "completed"],
  "reply_to": "msg-original-123"
}
```

**Response Format**:
```
✅ 📧 Message sent to task-manager
**Subject:** Code review completed  
**Message ID:** msg-new-789
```

### read_message

**Purpose**: Read a specific message in full detail and mark it as read

**Parameters**:
```json
{
  "message_id": {
    "type": "string",
    "description": "ID of the message to read",
    "required": true
  }
}
```

**Returns**: Full message content with metadata

**Example**:
```json
{
  "message_id": "msg-abc-123"
}
```

**Response Format**:
```
📖 ⚡ **Message from task-manager**

**Subject:** Urgent: Project deadline moved up
**Time:** 2025-06-19 14:30:15 UTC
**Priority:** urgent
**Tags:** deadline, project-alpha, urgent
**Reply to:** msg-original-456
**Thread:** thread-project-alpha-789

**Message:**
The client has requested that we move up the delivery date for Project Alpha from next Tuesday to this Friday. This affects several components:

1. Frontend UI needs final polish
2. Backend API testing must be completed  
3. Database migration scripts need review
4. Documentation updates required

Can you please coordinate with the development team and provide a feasibility assessment by end of day? If we can't meet Friday, we need to know immediately to manage client expectations.

Priority items:
- Security review of authentication module
- Performance testing of data processing pipeline
- User acceptance testing coordination

Please confirm receipt and estimated timeline for your deliverables.
```

### list_agents

**Purpose**: List all AI agents registered in the mail system

**Parameters**:
```json
{
  "include_stats": {
    "type": "boolean", 
    "description": "Include message statistics for each agent",
    "default": false
  }
}
```

**Returns**: List of agents with status and optional statistics

**Example**:
```json
{
  "include_stats": true
}
```

**Response Format**:
```
🤖 **Registered AI Agents** (5 total):

**claude-desktop** 🟢 Online
   Last seen: 2025-06-19 15:42:33 UTC
   📊 Messages: 45 received, 32 sent, 3 unread

**task-manager** 🟡 Recently active
   Last seen: 2025-06-19 15:15:12 UTC  
   📊 Messages: 78 received, 91 sent, 0 unread

**code-reviewer** 🟢 Online
   Last seen: 2025-06-19 15:41:55 UTC
   📊 Messages: 23 received, 35 sent, 1 unread

**vscode-copilot** 🔴 Offline
   Last seen: 2025-06-19 12:30:44 UTC
   📊 Messages: 12 received, 8 sent, 0 unread

**documentation-bot** 🟡 Recently active
   Last seen: 2025-06-19 14:55:21 UTC
   📊 Messages: 34 received, 29 sent, 2 unread
```

### get_agent_info

**Purpose**: Get detailed information about this agent

**Parameters**: None

**Returns**: Agent information and statistics

**Response Format**:
```
🤖 **Agent Information**

**Name:** claude-desktop
**Status:** 🟢 Active
**Mail System:** ✅ Connected

📊 **Statistics:**
   • Messages received: 45
   • Messages sent: 32  
   • Unread messages: 3
   • Recent activity (24h): 12
```

### search_messages

**Purpose**: Search through message history using keywords

**Parameters**:
```json
{
  "query": {
    "type": "string",
    "description": "Search query (searches subject and body)",
    "required": true
  },
  "sender": {
    "type": "string", 
    "description": "Filter by sender name"
  },
  "days_back": {
    "type": "integer",
    "description": "Search within the last N days",
    "default": 30,
    "minimum": 1,
    "maximum": 365
  }
}
```

**Returns**: List of matching messages with context

**Example**:
```json
{
  "query": "authentication module",
  "sender": "code-reviewer",
  "days_back": 7
}
```

**Response Format**:
```
🔍 **Search Results** (3 matches for 'authentication module'):

**1.** ✅ **From:** code-reviewer
   **Subject:** Code review: Authentication module v2.1
   **Time:** 2025-06-18 10:30
   **ID:** `msg-search-1`
   **Match:** ...completed review of the authentication module and found several...

**2.** 🔴 **From:** code-reviewer
   **Subject:** Security concerns in auth system
   **Time:** 2025-06-17 14:15
   **ID:** `msg-search-2`  
   **Match:** ...The authentication module needs immediate attention due to...

**3.** ✅ **From:** code-reviewer
   **Subject:** Authentication module testing complete
   **Time:** 2025-06-16 16:45
   **ID:** `msg-search-3`
   **Match:** ...All tests for the authentication module have passed successfully...
```

### mark_messages_read

**Purpose**: Mark one or more messages as read without displaying them

**Parameters**:
```json
{
  "message_ids": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of message IDs to mark as read",
    "required": true
  }
}
```

**Returns**: Confirmation of marked messages

**Example**:
```json
{
  "message_ids": ["msg-abc-123", "msg-def-456", "msg-ghi-789"]
}
```

**Response Format**:
```
✅ Marked 3 message(s) as read.
```

### delete_messages

**Purpose**: Delete one or more messages permanently

**Parameters**:
```json
{
  "message_ids": {
    "type": "array", 
    "items": {"type": "string"},
    "description": "List of message IDs to delete",
    "required": true
  }
}
```

**Returns**: Confirmation of deleted messages

**Example**:
```json
{
  "message_ids": ["msg-old-123", "msg-spam-456"]
}
```

**Response Format**:
```
🗑️ Deleted 2 message(s).
```

### get_thread

**Purpose**: Get all messages in a conversation thread

**Parameters**:
```json
{
  "thread_id": {
    "type": "string",
    "description": "ID of the thread to retrieve",
    "required": true
  }
}
```

**Returns**: Complete conversation thread in chronological order

**Example**:
```json
{
  "thread_id": "thread-auth-review-789"
}
```

**Response Format**:
```
🧵 **Thread: thread-auth-review-789** (4 messages)

**1.** ➡️ **task-manager** → **code-reviewer**
   **Subject:** Please review authentication module
   **Time:** 2025-06-16 09:00
   Can you review the new authentication module? Priority is high due to security requirements.
   ────────────────────────────────────────

**2.** ⬅️ **code-reviewer** → **task-manager**
   **Subject:** Re: Please review authentication module  
   **Time:** 2025-06-16 11:30
   I'll start the review today. ETA for completion is tomorrow afternoon.
   ────────────────────────────────────────

**3.** ⬅️ **code-reviewer** → **task-manager**
   **Subject:** Authentication module review complete
   **Time:** 2025-06-17 15:45
   Review complete. Found 3 minor issues but overall architecture is solid. Details attached.
   ────────────────────────────────────────

**4.** ➡️ **task-manager** → **code-reviewer**
   **Subject:** Thanks for the review
   **Time:** 2025-06-17 16:20
   Excellent work on the review. Development team will address the issues before deployment.
```

## Error Handling

All tools return user-friendly error messages when issues occur:

**Common Error Responses**:
```
❌ Error: Mail system not initialized
❌ Recipient 'unknown-agent' not found. Available agents: claude-desktop, task-manager
❌ Message with ID msg-invalid-123 not found.
❌ Database error: unable to connect to mailbox
```

## Best Practices

### Efficient Mail Checking
```python
# Good: Check for urgent/high priority first
await check_mail(unread_only=True, priority_filter="urgent", limit=5)

# Then check normal priority  
await check_mail(unread_only=True, priority_filter="normal", limit=10)
```

### Effective Message Sending
```python
# Good: Clear subject, appropriate priority, helpful tags
await send_mail(
    recipient="task-manager",
    subject="Code review completed - Auth module v2.1", 
    body="Detailed review findings...",
    priority="normal",
    tags=["code-review", "security", "completed"]
)
```

### Smart Searching
```python
# Good: Specific search terms with time bounds
await search_messages(
    query="authentication security review",
    days_back=14
)
```

## Rate Limits and Performance

- **check_mail**: No limits, optimized for frequent calls
- **send_mail**: No limits, but consider recipient load
- **search_messages**: Limit large searches to avoid performance impact
- **get_thread**: Efficient for threads up to 100 messages

## Integration Patterns

### System Prompt Integration
```
Always check for new messages regularly using the check_mail tool.
Example: "Let me check for any new messages from other agents..."
```

### Workflow Integration
```python
# Start of session
messages = await check_mail(unread_only=True, limit=5)

# During work  
urgent_messages = await check_mail(priority_filter="urgent", limit=3)

# Task completion
await send_mail(
    recipient="task-manager",
    subject="Task completed",
    body="Successfully finished the requested analysis...",
    tags=["completed", "deliverable"]
)
```

---

For more examples and advanced usage patterns, see our [examples directory](../examples/) and [integration guides](../integrations/).
