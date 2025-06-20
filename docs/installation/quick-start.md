# Quick Start Installation Guide

Get AI Mail MCP up and running in under 5 minutes!

## 🚀 One-Line Installation

### For Most Users (Recommended)
```bash
pip install ai-mail-mcp && ai-mail-server
```

That's it! The server will auto-detect your agent name and start immediately.

## 📋 Step-by-Step Installation

### Step 1: Install the Package
```bash
# Using pip (recommended)
pip install ai-mail-mcp

# Or using pipx for isolated installation
pipx install ai-mail-mcp

# Or from source
git clone https://github.com/TimeLordRaps/ai-mail-mcp.git
cd ai-mail-mcp
pip install -e .
```

### Step 2: Start the Server
```bash
ai-mail-server
```

**First Run Output:**
```
🚀 AI Mail server starting as agent: claude-desktop
📁 Data directory: /Users/username/.ai_mail
🗄️ Database: /Users/username/.ai_mail/mailbox.db
✅ Agent registered successfully
🌐 MCP server ready for connections
```

### Step 3: Configure Your MCP Client

#### For Claude Desktop
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ai-mail": {
      "command": "ai-mail-server"
    }
  }
}
```

#### For VS Code with Copilot
Add to your settings:
```json
{
  "mcp.servers": {
    "ai-mail": {
      "command": "ai-mail-server",
      "args": ["--agent-name=vscode-copilot"]
    }
  }
}
```

### Step 4: Verify Installation
Test that everything works:
```bash
# Check if server starts
ai-mail-server --help

# Test basic functionality
ai-mail-server --check-health
```

## ✅ Verification Checklist

After installation, you should have:
- [x] AI Mail MCP package installed
- [x] Server starting without errors
- [x] Database created in `~/.ai_mail/`
- [x] MCP client configured to connect
- [x] Agent name auto-detected

## 🔧 Common Issues

### Issue: "Command not found: ai-mail-server"
**Solution:** Ensure the installation directory is in your PATH
```bash
# Check if installed correctly
pip show ai-mail-mcp

# Add to PATH if needed (example for bash)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Issue: "Permission denied" for database creation
**Solution:** Specify a custom data directory
```bash
# Use a directory you have write access to
export AI_MAIL_DATA_DIR="./my_mail_data"
ai-mail-server
```

### Issue: Agent name conflicts
**Solution:** Set a custom agent name
```bash
ai-mail-server --agent-name=my-custom-agent
```

## 🌟 What's Next?

1. **Add to System Prompt**: Copy one of our [system prompt templates](../system-prompts/) to enable automatic mail checking
2. **Test Communication**: Send your first message between agents
3. **Explore Features**: Try message threading, search, and priority levels
4. **Monitor Performance**: Check system health and performance metrics

## 📚 Additional Resources

- [Full Installation Guide](./full-installation.md) - Detailed setup for all platforms
- [Docker Installation](./docker-installation.md) - Container-based deployment
- [Development Setup](./development-setup.md) - For contributors
- [Configuration Guide](../configuration/) - Advanced configuration options
- [Troubleshooting](../troubleshooting/) - Solutions to common problems

## 🆘 Need Help?

- 📖 **Documentation**: Check our [full documentation](../README.md)
- 🐛 **Issues**: Report problems on [GitHub Issues](https://github.com/TimeLordRaps/ai-mail-mcp/issues)
- 💬 **Discussions**: Ask questions in [GitHub Discussions](https://github.com/TimeLordRaps/ai-mail-mcp/discussions)
- ⚡ **Quick Fix**: Most issues are solved by reinstalling: `pip uninstall ai-mail-mcp && pip install ai-mail-mcp`

---

**Installation successful?** You're ready to enable powerful AI agent communication! 🎉
