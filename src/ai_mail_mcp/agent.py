"""
Agent identification and naming utilities.
"""

import logging
import os
import re
import socket
from typing import Set

try:
    import psutil
except ImportError:
    psutil = None

from .mailbox import MailboxManager

logger = logging.getLogger(__name__)


class AgentIdentifier:
    """Manages agent identification and naming."""
    
    @staticmethod
    def detect_agent_name() -> str:
        """Attempt to detect the current agent's name from environment and process info."""
        
        # Check environment variables for common agent identifiers
        env_vars = [
            'AI_AGENT_NAME',
            'AGENT_NAME', 
            'MCP_CLIENT_NAME',
            'VSCODE_AGENT_NAME',
            'CURSOR_AGENT_NAME',
            'CLAUDE_AGENT_NAME',
            'GPT_AGENT_NAME'
        ]
        
        for var in env_vars:
            value = os.getenv(var)
            if value:
                return AgentIdentifier.sanitize_agent_name(value.strip())
        
        # Try to detect from process information
        if psutil:
            try:
                current_process = psutil.Process()
                parent = current_process.parent()
                
                if parent:
                    parent_name = parent.name().lower()
                    
                    # Common agent process names
                    agent_mappings = {
                        'code': 'vscode-copilot',
                        'cursor': 'cursor-ai',
                        'zed': 'zed-ai',
                        'claude': 'claude-desktop',
                        'chatgpt': 'chatgpt-desktop',
                        'python': 'python-agent',
                        'node': 'node-agent',
                        'npm': 'npm-agent',
                        'yarn': 'yarn-agent'
                    }
                    
                    for process_name, agent_name in agent_mappings.items():
                        if process_name in parent_name:
                            return agent_name
                            
            except Exception as e:
                logger.debug(f"Could not detect agent from process: {e}")
        
        # Try to get from command line arguments
        try:
            import sys
            for arg in sys.argv:
                if arg.startswith('--agent-name='):
                    name = arg.split('=', 1)[1]
                    return AgentIdentifier.sanitize_agent_name(name)
                elif arg.startswith('--agent='):
                    name = arg.split('=', 1)[1]
                    return AgentIdentifier.sanitize_agent_name(name)
        except Exception as e:
            logger.debug(f"Could not detect agent from command line: {e}")
        
        # Fallback to hostname-based naming
        hostname = socket.gethostname()
        return AgentIdentifier.sanitize_agent_name(f"agent-{hostname}")
    
    @staticmethod
    def sanitize_agent_name(name: str) -> str:
        """Sanitize an agent name to make it valid."""
        if not name:
            return "default-agent"
        
        # Convert to lowercase and strip whitespace
        name = name.lower().strip()
        
        # Replace invalid characters with dashes
        name = re.sub(r'[^a-z0-9\-_.]', '-', name)
        
        # Remove multiple consecutive dashes
        name = re.sub(r'-+', '-', name)
        
        # Remove leading/trailing dashes or underscores
        name = name.strip('-_.')
        
        # Ensure minimum length
        if len(name) < 2:
            name = f"agent-{name}" if name else "default-agent"
        
        # Ensure maximum length
        if len(name) > 64:
            name = name[:64].rstrip('-_.')
        
        # Ensure it doesn't start or end with invalid characters
        if name.startswith(('-', '_', '.')):
            name = 'agent-' + name.lstrip('-_.')
        
        if name.endswith(('-', '_', '.')):
            name = name.rstrip('-_.') + '-agent'
        
        return name
    
    @staticmethod
    def ensure_unique_name(mailbox: MailboxManager, preferred_name: str) -> str:
        """Ensure the agent name is unique by adding a suffix if needed."""
        agents = mailbox.get_agents()
        existing_names: Set[str] = {agent.name for agent in agents}
        
        if preferred_name not in existing_names:
            return preferred_name
        
        # Extract base name and find next available number
        if preferred_name.endswith(tuple(f'-{i}' for i in range(1, 100))):
            base_name = '-'.join(preferred_name.split('-')[:-1])
        else:
            base_name = preferred_name
        
        counter = 1
        while f"{base_name}-{counter}" in existing_names:
            counter += 1
            
        return f"{base_name}-{counter}"

    @staticmethod
    def validate_agent_name(name: str) -> bool:
        """Validate that an agent name is acceptable."""
        if not name or not name.strip():
            return False
            
        name = name.strip()
        
        # Check length
        if len(name) < 2 or len(name) > 64:
            return False
            
        # Check for valid characters (alphanumeric, dash, underscore, dot)
        if not re.match(r'^[a-zA-Z0-9\-_.]+$', name):
            return False
            
        # Can't start or end with dash/underscore/dot
        if name.startswith(('-', '_', '.')) or name.endswith(('-', '_', '.')):
            return False
            
        # Must contain at least one letter or number
        if not re.search(r'[a-zA-Z0-9]', name):
            return False
            
        return True

    @staticmethod
    def suggest_agent_names(base_name: str, existing_names: Set[str], count: int = 5) -> list:
        """Suggest alternative agent names if the preferred one is taken."""
        suggestions = []
        
        # Clean the base name
        base_name = AgentIdentifier.sanitize_agent_name(base_name)
        
        # Try numbered variants
        counter = 2  # Start from 2 since base_name might be taken
        while len(suggestions) < count:
            candidate = f"{base_name}-{counter}"
            if candidate not in existing_names:
                suggestions.append(candidate)
            counter += 1
            
            # Prevent infinite loop
            if counter > 1000:
                break
                
        # Try with suffixes if we need more suggestions
        if len(suggestions) < count:
            suffixes = ['ai', 'bot', 'agent', 'assistant', 'worker', 'helper', 'client']
            for suffix in suffixes:
                candidate = f"{base_name}-{suffix}"
                if candidate not in existing_names and candidate not in suggestions:
                    suggestions.append(candidate)
                    if len(suggestions) >= count:
                        break
                        
        return suggestions[:count]
