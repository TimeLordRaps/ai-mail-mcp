# AI Mail MCP 📧🤖

**Simple local mailbox system for AI agent communication**

> Enable AI agents on the same machine to send messages to each other

**GitHub**: https://github.com/TimeLordRaps/ai-mail-mcp

## 🚀 Quick Setup

### For NPX users (recommended):
```bash
npx @timelordraps/ai-mail-mcp
```

### For UV users:
```bash
uvx ai-mail-mcp
```

### For pip users:
```bash
pip install ai-mail-mcp
ai-mail-server
```

### 2. Add to MCP Configuration

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "ai-mail": {
      "command": "npx",
      "args": ["-y", "@timelordraps/ai-mail-mcp"]
    }
  }
}
```

**VS Code** (`settings.json`):
```json
{
  "mcp.servers": {
    "ai-mail": {
      "command": "npx",
      "args": ["-y", "@timelordraps/ai-mail-mcp"]
    }
  }
}
```

### 3. Done! 

Your agents can now:
- `check_mail()` - Check for new messages
- `send_mail()` - Send messages to other agents  
- `list_agents()` - See available agents

## ✨ Features

- **🏠 Local only** - No external services, works offline
- **🤖 Auto-detect agents** - Finds `claude-desktop`, `vscode-copilot`, etc.
- **🧵 Threaded conversations** - Full reply chains
- **📊 Priorities** - Urgent, high, normal, low
- **🔍 Search** - Find messages by content
- **⚡ Fast** - 100+ messages/sec, SQLite backend

## 📝 System Prompt

Add this to your agent's system prompt:

```
You have access to an AI agent mail system. Check for new messages regularly using check_mail and send messages to coordinate with other AI agents on this machine.
```

## 🛠️ Agent Names

The system automatically detects agent names:
- `claude-desktop` (Claude Desktop)
- `vscode-copilot` (VS Code)  
- `cursor-ai` (Cursor)
- `zed-ai` (Zed)
- `agent-{hostname}` (fallback)

If names conflict, it adds numbers: `claude-desktop-2`

## 📧 Basic Usage

```python
# Check for messages
await check_mail(unread_only=True, limit=10)

# Send a message
await send_mail(
    recipient="vscode-copilot",
    subject="Need help with Python code",
    body="Can you review this function?",
    priority="normal"
)

# Read a specific message  
await read_message(message_id="msg-123")

# Search messages
await search_messages(query="python", days_back=7)
```

## 🏗️ How It Works

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Claude      │    │ VS Code     │    │ Cursor      │
│ Desktop     │    │ Copilot     │    │ AI          │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       │    MCP Tools     │    MCP Tools     │
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
              ┌───────────▼───────────┐
              │   AI Mail MCP Server  │
              │   (Local SQLite DB)   │
              └───────────────────────┘
```

## 🔧 Configuration

**Environment Variables**:
- `AI_AGENT_NAME` - Override agent name
- `AI_MAIL_DATA_DIR` - Data directory (default: `~/.ai_mail`)

**Data Location**: `~/.ai_mail/mailbox.db`

## 📊 Advanced Features

### Message Priorities
- `urgent` 🚨 - Critical, handle immediately  
- `high` ⚡ - Important, handle soon
- `normal` 📧 - Standard priority
- `low` 📮 - When convenient

### Message Threads
Reply to messages to create conversation threads:
```python
await send_mail(
    recipient="other-agent",
    subject="Re: Previous topic",
    body="Continuing our discussion...",
    reply_to="msg-original-123"  # Creates thread
)
```

### Search & Filter
```python
# Filter by priority
await check_mail(priority_filter="urgent")

# Search with tags
await send_mail(
    recipient="agent",
    subject="Task",
    body="Work item",
    tags=["project-alpha", "urgent"]
)
```

## 🤖 Orchestrator (Advanced)

For teams with many agents, the system includes an intelligent orchestrator:

- **Smart Summaries** - Automatically summarizes messages for overwhelmed agents
- **Priority Management** - Escalates old messages, optimizes priorities  
- **Task Distribution** - Balances workload across agents
- **Urgent Notices** - System-wide alerts

## 🔄 Automated Maintenance

The system maintains itself every 3 hours:
- Security updates
- Performance monitoring  
- Database optimization
- Issue management

## 🐛 Troubleshooting

**Agent not detected?**
```bash
export AI_AGENT_NAME="my-agent"
ai-mail-server
```

**Permission errors?**
```bash
export AI_MAIL_DATA_DIR="./my_mail"
ai-mail-server  
```

**Test the system:**
```bash
ai-mail-server --list-agents
```

## 📚 More Information

- **Issues**: [GitHub Issues](https://github.com/TimeLordRaps/ai-mail-mcp/issues)
- **Documentation**: [Full Docs](https://github.com/TimeLordRaps/ai-mail-mcp/tree/main/docs)
- **Examples**: [Integration Examples](https://github.com/TimeLordRaps/ai-mail-mcp/tree/main/examples)

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

**Made with ❤️ for AI agent collaboration**

*Install → Configure → Communicate* 🤖📧
