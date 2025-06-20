# Troubleshooting Guide

Common issues and solutions for AI Mail MCP.

## 🚨 Quick Fixes

### Problem: Server won't start
```bash
# Try these in order:
ai-mail-server --help                    # Check if installed
pip install --upgrade ai-mail-mcp       # Update to latest
export AI_MAIL_DATA_DIR="./mail_data"   # Use local directory
ai-mail-server --agent-name=test-agent  # Set custom name
```

### Problem: Messages not appearing
```bash
# Check agent registration
ai-mail-server --list-agents

# Verify database health
python -m ai_mail_mcp.scripts.health_check --integrity-only

# Check permissions
ls -la ~/.ai_mail/
```

### Problem: Permission denied
```bash
# Use local directory
mkdir ./ai_mail_data
export AI_MAIL_DATA_DIR="./ai_mail_data"
ai-mail-server
```

## 📋 Detailed Troubleshooting

### Installation Issues

#### "Command not found: ai-mail-server"

**Symptoms:**
```bash
$ ai-mail-server
bash: ai-mail-server: command not found
```

**Root Cause:** Package not installed correctly or not in PATH

**Solutions:**
```bash
# 1. Verify installation
pip show ai-mail-mcp

# 2. Check if script exists
find ~/.local -name "ai-mail-server" 2>/dev/null

# 3. Add to PATH (Linux/Mac)
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# 4. Use full path temporarily
python -m ai_mail_mcp.server

# 5. Reinstall if needed
pip uninstall ai-mail-mcp
pip install ai-mail-mcp
```

#### "No module named 'ai_mail_mcp'"

**Symptoms:**
```bash
ModuleNotFoundError: No module named 'ai_mail_mcp'
```

**Root Cause:** Package not installed or wrong Python environment

**Solutions:**
```bash
# 1. Check Python environment
which python
which pip

# 2. Install in correct environment
pip install ai-mail-mcp

# 3. If using virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install ai-mail-mcp

# 4. Use pip3 if needed
pip3 install ai-mail-mcp
```

### Database Issues

#### "Permission denied" when creating database

**Symptoms:**
```bash
PermissionError: [Errno 13] Permission denied: '/home/user/.ai_mail/mailbox.db'
```

**Root Cause:** No write permissions to default directory

**Solutions:**
```bash
# 1. Use writable directory
export AI_MAIL_DATA_DIR="./my_mail"
ai-mail-server

# 2. Fix permissions
chmod 755 ~/.ai_mail
chmod 644 ~/.ai_mail/mailbox.db

# 3. Use temporary directory
export AI_MAIL_DATA_DIR="/tmp/ai_mail_$(whoami)"
ai-mail-server

# 4. Run with specific permissions
mkdir -p ~/Documents/ai_mail
export AI_MAIL_DATA_DIR="~/Documents/ai_mail"
ai-mail-server
```

#### "Database is locked"

**Symptoms:**
```bash
sqlite3.OperationalError: database is locked
```

**Root Cause:** Multiple server instances or corruption

**Solutions:**
```bash
# 1. Stop all instances
pkill -f ai-mail-server

# 2. Check for lock files
ls ~/.ai_mail/mailbox.db*
rm ~/.ai_mail/mailbox.db-wal ~/.ai_mail/mailbox.db-shm

# 3. Check database integrity
sqlite3 ~/.ai_mail/mailbox.db "PRAGMA integrity_check;"

# 4. Backup and recreate if needed
cp ~/.ai_mail/mailbox.db ~/.ai_mail/mailbox.db.backup
python -c "
import sqlite3
conn = sqlite3.connect('~/.ai_mail/mailbox_new.db')
conn.execute('PRAGMA journal_mode=WAL')
conn.close()
"
```

### Agent Detection Issues

#### Agent name conflicts

**Symptoms:**
```bash
🚀 AI Mail server starting as agent: claude-desktop-2
```

**Root Cause:** Multiple agents with same detected name

**Solutions:**
```bash
# 1. Set unique name explicitly
ai-mail-server --agent-name=my-unique-agent

# 2. Use environment variable
export AI_AGENT_NAME="my-custom-name"
ai-mail-server

# 3. Check existing agents
ai-mail-server --list-agents

# 4. Clear old agents if needed
python -c "
from ai_mail_mcp.mailbox import MailboxManager
from pathlib import Path
mb = MailboxManager(Path('~/.ai_mail/mailbox.db').expanduser())
agents = mb.get_agents()
print([a.name for a in agents])
"
```

#### Wrong agent name detected

**Symptoms:**
```bash
🚀 AI Mail server starting as agent: agent-hostname
```

**Root Cause:** Auto-detection fallback to hostname

**Solutions:**
```bash
# 1. Set environment variable
export AI_AGENT_NAME="preferred-name"

# 2. Use command line argument
ai-mail-server --agent-name=preferred-name

# 3. Set in MCP client config
{
  "mcpServers": {
    "ai-mail": {
      "command": "ai-mail-server",
      "env": {
        "AI_AGENT_NAME": "my-agent"
      }
    }
  }
}
```

### Performance Issues

#### Slow message operations

**Symptoms:** Long delays when sending/receiving messages

**Diagnosis:**
```bash
# Run performance benchmark
python scripts/benchmark.py

# Check database size
du -h ~/.ai_mail/mailbox.db

# Analyze database
python scripts/health_check.py --full-check
```

**Solutions:**
```bash
# 1. Optimize database
python scripts/health_check.py --optimize

# 2. Clean up old messages
python scripts/health_check.py --cleanup 30

# 3. Rebuild indexes
sqlite3 ~/.ai_mail/mailbox.db "REINDEX;"

# 4. Enable WAL mode
sqlite3 ~/.ai_mail/mailbox.db "PRAGMA journal_mode=WAL;"
```

#### High memory usage

**Symptoms:** AI Mail server using excessive memory

**Diagnosis:**
```bash
# Check memory usage
ps aux | grep ai-mail-server

# Monitor with script
python scripts/monitor.py --once
```

**Solutions:**
```bash
# 1. Restart server periodically
pkill -f ai-mail-server
ai-mail-server

# 2. Limit message history
export AI_MAIL_MAX_MESSAGES=1000
ai-mail-server

# 3. Clean up regularly
python scripts/health_check.py --cleanup 7

# 4. Use monitoring
python scripts/monitor.py --daemon
```

### Network and Connectivity Issues

#### MCP client can't connect

**Symptoms:** Client reports connection errors

**Diagnosis:**
```bash
# Check if server is running
ps aux | grep ai-mail-server

# Check server logs
tail -f ~/.ai_mail/logs/server.log

# Test server manually
python -c "
import asyncio
from ai_mail_mcp.server import server
asyncio.run(server.run())
"
```

**Solutions:**
```bash
# 1. Restart server
pkill -f ai-mail-server
ai-mail-server

# 2. Check configuration
cat ~/.config/claude/claude_desktop_config.json

# 3. Verify command path
which ai-mail-server

# 4. Use full path in config
{
  "mcpServers": {
    "ai-mail": {
      "command": "/full/path/to/ai-mail-server"
    }
  }
}
```

### Message Issues

#### Messages not being delivered

**Symptoms:** send_mail succeeds but recipient doesn't see messages

**Diagnosis:**
```bash
# Check if recipient exists
python -c "
from ai_mail_mcp.mailbox import MailboxManager
from pathlib import Path
mb = MailboxManager(Path('~/.ai_mail/mailbox.db').expanduser())
agents = [a.name for a in mb.get_agents()]
print('Available agents:', agents)
"

# Check database directly
sqlite3 ~/.ai_mail/mailbox.db "SELECT sender, recipient, subject FROM messages ORDER BY timestamp DESC LIMIT 10;"
```

**Solutions:**
```bash
# 1. Verify agent names match exactly
ai-mail-server --list-agents

# 2. Check message was actually sent
sqlite3 ~/.ai_mail/mailbox.db "SELECT COUNT(*) FROM messages WHERE sender='your-agent';"

# 3. Restart both agents
pkill -f ai-mail-server
# Start both agents

# 4. Check database permissions
ls -la ~/.ai_mail/mailbox.db
```

#### Search not finding messages

**Symptoms:** search_messages returns no results for known content

**Diagnosis:**
```bash
# Check if messages exist
sqlite3 ~/.ai_mail/mailbox.db "SELECT COUNT(*), MAX(timestamp) FROM messages;"

# Check search terms
sqlite3 ~/.ai_mail/mailbox.db "SELECT subject, body FROM messages WHERE subject LIKE '%search_term%' OR body LIKE '%search_term%';"
```

**Solutions:**
```bash
# 1. Use broader search terms
# Instead of "authentication module" try "authentication"

# 2. Check date range
# Use days_back parameter: search_messages(query="term", days_back=90)

# 3. Rebuild search indexes
sqlite3 ~/.ai_mail/mailbox.db "REINDEX;"

# 4. Check for special characters
# Escape SQL special characters in search terms
```

## 🔧 Diagnostic Tools

### Health Check Script
```bash
# Full system health check
python scripts/health_check.py --full-check

# Quick integrity check
python scripts/health_check.py --integrity-only

# Performance analysis
python scripts/health_check.py --performance
```

### Monitoring Script
```bash
# One-time monitoring
python scripts/monitor.py --once

# Continuous monitoring
python scripts/monitor.py --daemon --interval=300
```

### Manual Database Inspection
```bash
# Connect to database
sqlite3 ~/.ai_mail/mailbox.db

# Useful queries
.schema                              # Show table structure
SELECT COUNT(*) FROM messages;      # Total messages
SELECT COUNT(*) FROM agents;        # Total agents
SELECT * FROM agents;               # List all agents
SELECT sender, recipient, subject, timestamp FROM messages ORDER BY timestamp DESC LIMIT 10;

# Check for corruption
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

### Log Analysis
```bash
# Check system logs (Linux/Mac)
tail -f /var/log/system.log | grep ai-mail

# Check Python logs
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Then run your ai-mail operations
"

# Enable debug mode
export AI_MAIL_DEBUG=1
ai-mail-server
```

## 🆘 Emergency Recovery

### Complete Reset
```bash
# 1. Stop all instances
pkill -f ai-mail-server

# 2. Backup existing data
cp -r ~/.ai_mail ~/.ai_mail.backup.$(date +%Y%m%d_%H%M%S)

# 3. Remove old installation
pip uninstall ai-mail-mcp

# 4. Clean directories
rm -rf ~/.ai_mail

# 5. Fresh install
pip install ai-mail-mcp

# 6. Start fresh
ai-mail-server
```

### Data Recovery
```bash
# 1. Check backup files
ls -la ~/.ai_mail/*.backup*

# 2. Restore from backup
cp ~/.ai_mail/mailbox.db.backup ~/.ai_mail/mailbox.db

# 3. Or export/import messages
sqlite3 ~/.ai_mail.backup/mailbox.db ".dump" | sqlite3 ~/.ai_mail/mailbox.db

# 4. Verify recovery
python scripts/health_check.py --integrity-only
```

## 📞 Getting Help

If these solutions don't work:

1. **Check GitHub Issues**: [Known issues and solutions](https://github.com/TimeLordRaps/ai-mail-mcp/issues)
2. **Create New Issue**: Provide logs, error messages, and system info
3. **Enable Debug Mode**: `export AI_MAIL_DEBUG=1` before running
4. **Collect System Info**: 
   ```bash
   python --version
   pip show ai-mail-mcp
   uname -a  # Linux/Mac
   systeminfo  # Windows
   ```

### Issue Template
When reporting issues, include:
```
**Environment:**
- OS: [e.g., Ubuntu 20.04, Windows 10, macOS 12.0]
- Python: [version]
- AI Mail MCP: [version]
- MCP Client: [e.g., Claude Desktop, VS Code]

**Problem:**
[Clear description of what's not working]

**Expected:**
[What should happen]

**Steps to Reproduce:**
1. [First step]
2. [Second step]
3. [Error occurs]

**Error Messages:**
```
[Full error output]
```

**Additional Context:**
[Any other relevant information]
```

---

**Remember:** Most issues are solved by ensuring proper installation, correct permissions, and unique agent names. When in doubt, try a fresh installation!
