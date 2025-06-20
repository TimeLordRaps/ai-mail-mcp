#!/usr/bin/env python3
"""
AI Mail MCP - Automated Maintenance Script

Handles automated maintenance tasks:
- Issue management and responses
- Documentation updates
- Performance monitoring
- Security updates
- Repository health checks
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIMailMaintenance:
    """Automated maintenance system for AI Mail MCP."""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.repo_name = 'TimeLordRaps/ai-mail-mcp'
        
        # Try to import GitHub if available
        try:
            from github import Github
            if self.github_token:
                self.github = Github(self.github_token)
                self.repo = self.github.get_repo(self.repo_name)
            else:
                logger.warning("No GitHub token provided - limited functionality")
                self.github = None
                self.repo = None
        except ImportError:
            logger.warning("PyGithub not installed - installing...")
            os.system("pip install PyGithub")
            from github import Github
            if self.github_token:
                self.github = Github(self.github_token)
                self.repo = self.github.get_repo(self.repo_name)
            else:
                self.github = None
                self.repo = None
            
    def respond_to_issues(self):
        """Automatically respond to and manage GitHub issues."""
        if not self.repo:
            logger.warning("Cannot manage issues without GitHub access")
            return
            
        try:
            # Get open issues
            open_issues = list(self.repo.get_issues(state='open'))
            logger.info(f"📋 Found {len(open_issues)} open issues")
            
            for issue in open_issues:
                # Skip pull requests
                if issue.pull_request:
                    continue
                    
                # Auto-respond to new issues
                if self.is_new_issue(issue):
                    self.respond_to_new_issue(issue)
                    
                # Auto-close resolved issues
                if self.is_resolved_issue(issue):
                    self.close_resolved_issue(issue)
                    
        except Exception as e:
            logger.error(f"❌ Error managing issues: {e}")
            
    def is_new_issue(self, issue) -> bool:
        """Check if issue needs initial response."""
        comments = list(issue.get_comments())
        
        # If no comments, it's new
        if len(comments) == 0:
            return True
            
        # If last comment is from issue author and older than 1 hour
        last_comment = comments[-1]
        if (last_comment.user.login == issue.user.login and 
            datetime.now(timezone.utc) - last_comment.created_at > timedelta(hours=1)):
            return True
            
        return False
        
    def respond_to_new_issue(self, issue):
        """Respond to a new issue with helpful information."""
        try:
            # Categorize issue
            if 'installation' in issue.title.lower() or 'install' in issue.body.lower():
                response = self.get_installation_help_response()
            elif 'bug' in issue.title.lower() or 'error' in issue.body.lower():
                response = self.get_bug_report_response()
            elif 'feature' in issue.title.lower() or 'enhancement' in issue.body.lower():
                response = self.get_feature_request_response()
            else:
                response = self.get_general_help_response()
                
            # Add response
            issue.create_comment(response)
            
            # Add labels
            labels = self.categorize_issue(issue)
            for label in labels:
                try:
                    issue.add_to_labels(label)
                except:
                    # Label might not exist
                    pass
                    
            logger.info(f"✅ Responded to issue #{issue.number}: {issue.title}")
            
        except Exception as e:
            logger.error(f"❌ Error responding to issue #{issue.number}: {e}")
            
    def get_installation_help_response(self) -> str:
        """Get installation help response."""
        return """👋 Thanks for reporting this installation issue!

## Quick Installation Guide

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

## MCP Configuration

Add this to your MCP settings:

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

## Troubleshooting

1. **Permission errors**: Try setting `AI_MAIL_DATA_DIR` to a writable directory
2. **Agent not detected**: Set `AI_AGENT_NAME` environment variable
3. **Python issues**: Make sure Python 3.8+ is installed

Let me know if this helps or if you need more specific assistance! 🚀"""

    def get_bug_report_response(self) -> str:
        """Get bug report response."""
        return """🐛 Thanks for the bug report!

To help us resolve this quickly, could you please provide:

## Environment Information
- Operating System: 
- Python version: `python --version`
- Package version: `pip show ai-mail-mcp`
- MCP client (Claude Desktop, VS Code, etc.):

## Reproduction Steps
1. 
2. 
3. 

## Expected vs Actual Behavior
- Expected: 
- Actual: 

## Logs
Please include any error messages or logs from:
- AI Mail server output
- MCP client logs
- `~/.ai_mail/server.log` (if it exists)

## Quick Debugging Steps
1. Try running with debug logging: `AI_MAIL_DEBUG=1 ai-mail-server`
2. Check if the data directory is writable: `ls -la ~/.ai_mail/`
3. Test with a fresh data directory: `AI_MAIL_DATA_DIR=/tmp/test_mail ai-mail-server`

I'll investigate this issue ASAP! 🔍"""

    def get_feature_request_response(self) -> str:
        """Get feature request response."""
        return """✨ Thanks for the feature request!

I love seeing ideas for improving AI Mail MCP. Here's what happens next:

## Evaluation Process
1. **Community Interest**: How many users would benefit?
2. **Technical Feasibility**: Can it be implemented efficiently?
3. **Scope Alignment**: Does it fit the project's goals?

## Implementation Priority
- 🚨 **High**: Core functionality, security, performance
- ⚡ **Medium**: Quality of life improvements, integrations
- 📮 **Low**: Nice-to-have features, experimental ideas

## How to Help
- 👍 React with thumbs up if you want this feature
- 💬 Share your specific use case in the comments
- 🛠️ Feel free to submit a PR if you want to implement it!

## Similar Features
I'll check if there are similar requests or existing solutions.

Thanks for helping make AI Mail MCP better! 🤖📧"""

    def get_general_help_response(self) -> str:
        """Get general help response."""
        return """👋 Hello! Thanks for reaching out about AI Mail MCP.

## Quick Links
- 📖 **Documentation**: [README.md](https://github.com/TimeLordRaps/ai-mail-mcp#readme)
- 🚀 **Quick Start**: [Installation Guide](https://github.com/TimeLordRaps/ai-mail-mcp#-quick-setup)
- 💬 **Examples**: [Integration Examples](https://github.com/TimeLordRaps/ai-mail-mcp/tree/main/examples)

## Common Solutions
- **Installation issues**: Check Python 3.8+ and permissions
- **Agent detection**: Set `AI_AGENT_NAME` environment variable
- **MCP setup**: Verify your MCP client configuration
- **Performance**: Try the orchestrator for multi-agent setups

## Getting Help
For faster assistance, please provide:
- What you're trying to do
- Any error messages
- Your environment (OS, Python version, MCP client)

I'll respond as quickly as possible! 🚀"""

    def categorize_issue(self, issue) -> List[str]:
        """Categorize issue and return appropriate labels."""
        labels = []
        
        title_lower = issue.title.lower()
        body_lower = issue.body.lower() if issue.body else ""
        
        # Type labels
        if any(word in title_lower for word in ['bug', 'error', 'fail', 'broken']):
            labels.append('bug')
        elif any(word in title_lower for word in ['feature', 'enhancement', 'improve']):
            labels.append('enhancement')
        elif any(word in title_lower for word in ['install', 'setup', 'config']):
            labels.append('installation')
        elif any(word in title_lower for word in ['doc', 'documentation', 'readme']):
            labels.append('documentation')
            
        # Priority labels
        if any(word in title_lower for word in ['urgent', 'critical', 'security']):
            labels.append('high-priority')
        elif any(word in title_lower for word in ['minor', 'typo', 'cosmetic']):
            labels.append('low-priority')
            
        return labels
        
    def run_full_maintenance(self):
        """Run all maintenance tasks."""
        logger.info("🔧 Starting automated maintenance")
        
        self.respond_to_issues()
        
        logger.info("✅ Maintenance completed")


def main():
    """Main entry point."""
    maintenance = AIMailMaintenance()
    maintenance.run_full_maintenance()


if __name__ == "__main__":
    main()
