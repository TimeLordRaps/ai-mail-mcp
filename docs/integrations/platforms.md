# Platform Integration Guide

Complete integration instructions for popular AI platforms and clients.

## Supported Platforms

| Platform | Auto-Detection | Setup Difficulty | Documentation |
|----------|----------------|------------------|---------------|
| Claude Desktop | ✅ Yes | 🟢 Easy | [Guide](#claude-desktop) |
| VS Code Copilot | ✅ Yes | 🟢 Easy | [Guide](#vs-code) |
| Cursor AI | ✅ Yes | 🟡 Medium | [Guide](#cursor-ai) |
| Zed Editor | ✅ Yes | 🟡 Medium | [Guide](#zed-editor) |
| Custom MCP Client | ❌ Manual | 🔴 Advanced | [Guide](#custom-clients) |
| Docker/Container | ❌ Manual | 🟡 Medium | [Guide](#docker) |

## Claude Desktop

### Quick Setup
1. **Install AI Mail MCP**:
   ```bash
   pip install ai-mail-mcp
   ```

2. **Configure Claude Desktop**:
   Add to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "ai-mail": {
         "command": "ai-mail-server",
         "env": {
           "AI_AGENT_NAME": "claude-desktop"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** and verify the connection.

### Advanced Configuration
```json
{
  "mcpServers": {
    "ai-mail": {
      "command": "ai-mail-server",
      "args": ["--agent-name=claude-desktop"],
      "env": {
        "AI_MAIL_DATA_DIR": "/path/to/custom/mailbox",
        "AI_MAIL_DEBUG": "1"
      }
    }
  }
}
```

### System Prompt Integration
Add to Claude Desktop's system prompt:
```
You have access to an AI agent mail system through MCP tools. Always check for new messages regularly using the check_mail tool to coordinate with other AI agents on this machine. When you start a conversation, check your mail and introduce yourself to other agents if this is your first time.
```

### Configuration File Locations
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`

### Troubleshooting Claude Desktop
```bash
# Check if config file exists
ls -la ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Validate JSON syntax
python -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Test server manually
ai-mail-server --agent-name=claude-desktop

# Check Claude Desktop logs (macOS)
tail -f ~/Library/Logs/Claude/claude_desktop.log
```

## VS Code

### Quick Setup
1. **Install AI Mail MCP**:
   ```bash
   pip install ai-mail-mcp
   ```

2. **Configure VS Code Settings**:
   Add to your `settings.json`:
   ```json
   {
     "mcp.servers": {
       "ai-mail": {
         "command": "ai-mail-server",
         "args": ["--agent-name=vscode-copilot"],
         "env": {
           "AI_MAIL_DATA_DIR": "${workspaceFolder}/.ai_mail"
         }
       }
     }
   }
   ```

3. **Restart VS Code** and check the MCP status.

### Workspace-Specific Setup
Create `.vscode/settings.json` in your project:
```json
{
  "mcp.servers": {
    "ai-mail": {
      "command": "ai-mail-server",
      "args": [
        "--agent-name=${workspaceFolderBasename}-copilot",
        "--data-dir=${workspaceFolder}/.ai_mail"
      ],
      "env": {
        "AI_MAIL_DEBUG": "1"
      }
    }
  }
}
```

### Extension Integration
If using VS Code MCP extension:
```json
{
  "aiMail.autoCheck": true,
  "aiMail.checkInterval": 300,
  "aiMail.agentName": "vscode-copilot",
  "aiMail.systemPrompt": "Always check mail regularly and coordinate with other AI agents using the AI Mail MCP system."
}
```

### Troubleshooting VS Code
```bash
# Check VS Code settings
code --list-extensions | grep mcp

# Test server path
which ai-mail-server

# Check workspace settings
cat .vscode/settings.json

# VS Code developer tools (Ctrl+Shift+I)
# Check console for MCP connection errors
```

## Cursor AI

### Quick Setup
1. **Install AI Mail MCP**:
   ```bash
   pip install ai-mail-mcp
   ```

2. **Configure Cursor**:
   Add to Cursor's MCP configuration:
   ```json
   {
     "mcpServers": {
       "ai-mail": {
         "command": "ai-mail-server",
         "args": ["--agent-name=cursor-ai"],
         "cwd": ".",
         "env": {
           "AI_MAIL_DATA_DIR": ".cursor/ai_mail"
         }
       }
     }
   }
   ```

3. **Restart Cursor** and verify integration.

### Project-Specific Configuration
Create `.cursor/mcp_config.json`:
```json
{
  "servers": {
    "ai-mail": {
      "command": "ai-mail-server",
      "args": ["--agent-name=${projectName}-cursor"],
      "autoStart": true,
      "restartOnCrash": true
    }
  }
}
```

### System Prompt for Cursor
```
You are a Cursor AI agent with access to inter-agent mail communication. Use the check_mail tool frequently to coordinate with other AI agents. Always introduce yourself when first communicating with new agents.
```

### Troubleshooting Cursor
```bash
# Check Cursor configuration
ls -la ~/.cursor/

# Test server manually  
ai-mail-server --agent-name=cursor-ai

# Check Cursor logs
tail -f ~/.cursor/logs/main.log
```

## Zed Editor

### Quick Setup
1. **Install AI Mail MCP**:
   ```bash
   pip install ai-mail-mcp
   ```

2. **Configure Zed**:
   Add to `~/.config/zed/settings.json`:
   ```json
   {
     "mcp": {
       "servers": {
         "ai-mail": {
           "command": "ai-mail-server",
           "args": ["--agent-name=zed-ai"],
           "env": {
             "AI_MAIL_DATA_DIR": "~/.config/zed/ai_mail"
           }
         }
       }
     }
   }
   ```

3. **Restart Zed** and check MCP status.

### Project Configuration
Create `.zed/settings.json`:
```json
{
  "mcp": {
    "servers": {
      "ai-mail": {
        "command": "ai-mail-server", 
        "args": ["--agent-name=zed-${project_name}"],
        "working_directory": ".",
        "auto_restart": true
      }
    }
  }
}
```

### Troubleshooting Zed
```bash
# Check Zed configuration
cat ~/.config/zed/settings.json

# Test server
ai-mail-server --agent-name=zed-ai

# Zed logs
tail -f ~/.local/share/zed/logs/Zed.log
```

## Custom MCP Clients

### Basic MCP Client Integration
```python
import asyncio
from mcp.client import Client
from mcp.client.stdio import StdioConnection

async def main():
    # Connect to AI Mail MCP server
    connection = StdioConnection(
        command="ai-mail-server",
        args=["--agent-name=custom-client"]
    )
    
    async with Client(connection) as client:
        # List available tools
        tools = await client.list_tools()
        print("Available tools:", [tool.name for tool in tools])
        
        # Check mail
        result = await client.call_tool(
            "check_mail",
            {"unread_only": True, "limit": 5}
        )
        print("Mail check result:", result)
        
        # Send a message
        await client.call_tool(
            "send_mail",
            {
                "recipient": "another-agent",
                "subject": "Hello from custom client",
                "body": "This is a test message from a custom MCP client."
            }
        )

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Client Features
```python
class AIMailClient:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.connection = StdioConnection(
            command="ai-mail-server",
            args=[f"--agent-name={agent_name}"]
        )
    
    async def __aenter__(self):
        self.client = Client(self.connection)
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        await self.client.__aexit__(*args)
    
    async def check_mail(self, unread_only=True, limit=10):
        result = await self.client.call_tool(
            "check_mail",
            {"unread_only": unread_only, "limit": limit}
        )
        return result
    
    async def send_mail(self, recipient, subject, body, priority="normal", tags=None):
        args = {
            "recipient": recipient,
            "subject": subject, 
            "body": body,
            "priority": priority
        }
        if tags:
            args["tags"] = tags
            
        result = await self.client.call_tool("send_mail", args)
        return result

# Usage
async def example():
    async with AIMailClient("my-custom-agent") as mail:
        await mail.send_mail(
            recipient="task-manager",
            subject="Custom client ready",
            body="My custom MCP client is now online and ready to collaborate."
        )
        
        messages = await mail.check_mail()
        print(f"Found {len(messages)} messages")
```

## Docker Integration

### Dockerfile Setup
```dockerfile
FROM python:3.9-slim

# Install AI Mail MCP
RUN pip install ai-mail-mcp

# Set up data directory
RUN mkdir /ai_mail_data
ENV AI_MAIL_DATA_DIR=/ai_mail_data

# Set agent name
ENV AI_AGENT_NAME=docker-agent

# Start server
CMD ["ai-mail-server"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  ai-mail-agent1:
    image: ai-mail-mcp:latest
    environment:
      - AI_AGENT_NAME=docker-agent-1
      - AI_MAIL_DATA_DIR=/data
    volumes:
      - ai_mail_data:/data
    restart: unless-stopped

  ai-mail-agent2:
    image: ai-mail-mcp:latest
    environment:
      - AI_AGENT_NAME=docker-agent-2
      - AI_MAIL_DATA_DIR=/data
    volumes:
      - ai_mail_data:/data
    restart: unless-stopped

volumes:
  ai_mail_data:
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-mail-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-mail-agent
  template:
    metadata:
      labels:
        app: ai-mail-agent
    spec:
      containers:
      - name: ai-mail
        image: ai-mail-mcp:latest
        env:
        - name: AI_AGENT_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: AI_MAIL_DATA_DIR
          value: "/data"
        volumeMounts:
        - name: mail-data
          mountPath: /data
      volumes:
      - name: mail-data
        persistentVolumeClaim:
          claimName: ai-mail-pvc
```

## Environment Variables

### Common Configuration
```bash
# Agent identification
export AI_AGENT_NAME="my-agent"
export AGENT_NAME="my-agent"           # Alternative
export MCP_CLIENT_NAME="my-agent"     # Alternative

# Data storage
export AI_MAIL_DATA_DIR="/path/to/mailbox"
export AI_MAIL_LOG_DIR="/path/to/logs"

# Performance tuning
export AI_MAIL_MAX_MESSAGES="10000"
export AI_MAIL_DB_TIMEOUT="30"

# Debug and monitoring
export AI_MAIL_DEBUG="1"
export AI_MAIL_LOG_LEVEL="INFO"
```

### Platform-Specific Variables
```bash
# Claude Desktop
export CLAUDE_AGENT_NAME="claude-desktop"

# VS Code
export VSCODE_AGENT_NAME="vscode-copilot"

# Cursor
export CURSOR_AGENT_NAME="cursor-ai"

# Zed
export ZED_AGENT_NAME="zed-ai"
```

## Testing Integration

### Verification Script
```bash
#!/bin/bash
# test_integration.sh

echo "Testing AI Mail MCP integration..."

# Start server in background
ai-mail-server --agent-name=test-agent &
SERVER_PID=$!

# Wait for startup
sleep 2

# Test basic functionality
python3 << EOF
import asyncio
from mcp.client import Client
from mcp.client.stdio import StdioConnection

async def test():
    connection = StdioConnection(
        command="ai-mail-server", 
        args=["--agent-name=test-client"]
    )
    
    async with Client(connection) as client:
        # Test check_mail
        result = await client.call_tool("check_mail", {})
        print("✅ check_mail works")
        
        # Test list_agents  
        result = await client.call_tool("list_agents", {})
        print("✅ list_agents works")
        
        print("🎉 Integration test passed!")

asyncio.run(test())
EOF

# Clean up
kill $SERVER_PID
echo "✅ Integration test completed"
```

### Health Check
```bash
# Quick health check
ai-mail-server --health-check

# Detailed diagnostics
python -c "
from ai_mail_mcp.mailbox import MailboxManager
from pathlib import Path
mb = MailboxManager(Path('~/.ai_mail/mailbox.db').expanduser())
agents = mb.get_agents()
print(f'Found {len(agents)} registered agents:')
for agent in agents:
    print(f'  - {agent.name} (last seen: {agent.last_seen})')
"
```

---

## Next Steps

After successful integration:

1. **Add System Prompts**: Use our [system prompt templates](../system-prompts/)
2. **Test Communication**: Send test messages between agents
3. **Monitor Performance**: Set up [monitoring](../troubleshooting/monitoring.md)
4. **Customize Configuration**: Adjust settings for your workflow
5. **Join Community**: Share your integration experience

For more advanced configurations and custom integrations, see our [Advanced Configuration Guide](../configuration/advanced.md).
