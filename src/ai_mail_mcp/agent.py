"""
Agent identification and naming utilities.
"""

import logging
import os
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
                return value.strip()
        
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
                    return arg.split('=', 1)[1]
                elif arg.startswith('--agent='):
                    return arg.split('=', 1)[1]
        except Exception as e:
            logger.debug(f"Could not detect agent from command line: {e}")
        
        # Fallback to hostname-based naming
        hostname = socket.gethostname()
        return f"agent-{hostname}"
    
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
            
        # Check for valid characters (alphanumeric, dash, underscore)
        if not name.replace('-', '').replace('_', '').replace('.', '').isalnum():
            return False
            
        # Can't start or end with dash/underscore
        if name.startswith(('-', '_')) or name.endswith(('-', '_')):
            return False
            
        return True

    @staticmethod
    def suggest_agent_names(base_name: str, existing_names: Set[str], count: int = 5) -> list:
        """Suggest alternative agent names if the preferred one is taken."""
        suggestions = []
        
        # Clean the base name
        base_name = base_name.strip().lower()
        
        # Try numbered variants
        for i in range(1, count + 1):
            candidate = f"{base_name}-{i}"
            if candidate not in existing_names:
                suggestions.append(candidate)
                
        # Try with suffixes
        suffixes = ['ai', 'bot', 'agent', 'assistant', 'worker']
        for suffix in suffixes:
            candidate = f"{base_name}-{suffix}"
            if candidate not in existing_names and len(suggestions) < count:
                suggestions.append(candidate)
                
        return suggestions[:count]
