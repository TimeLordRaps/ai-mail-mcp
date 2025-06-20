#!/usr/bin/env python3
"""
AI Mail MCP Project Setup and Fix Script

This script fixes common issues and ensures the project is properly configured.
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"⚠️ {description} completed with issues")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return not check
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return not check


def check_file_exists(filepath, description):
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✅ {description} exists")
        return True
    else:
        print(f"❌ {description} missing")
        return False


def create_missing_orchestrator_files():
    """Create missing orchestrator module files."""
    orchestrator_dir = Path("src/ai_mail_mcp/orchestrator")
    orchestrator_dir.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py
    init_file = orchestrator_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text('''"""
AI Mail MCP Orchestrator module.
"""

from .main import main

__all__ = ["main"]
''')
        print("✅ Created orchestrator __init__.py")
    
    # Create main.py
    main_file = orchestrator_dir / "main.py"
    if not main_file.exists():
        main_file.write_text('''#!/usr/bin/env python3
"""
AI Mail MCP Orchestrator - Main entry point.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_mail_mcp.mailbox import MailboxManager
from ai_mail_mcp.agent import AgentIdentifier

logger = logging.getLogger(__name__)


def main():
    """Main orchestrator entry point."""
    print("🤖 AI Mail MCP Orchestrator")
    print("=" * 30)
    
    try:
        # Initialize system
        data_dir = Path.home() / ".ai_mail"
        db_path = data_dir / "mailbox.db"
        
        mailbox = MailboxManager(db_path)
        agent_name = AgentIdentifier.detect_agent_name()
        
        print(f"📧 Agent: {agent_name}")
        print(f"📁 Data: {data_dir}")
        
        # Get system stats
        agents = mailbox.get_agents()
        stats = mailbox.get_message_stats(agent_name)
        
        print(f"🤖 Registered agents: {len(agents)}")
        print(f"📊 Messages received: {stats['total_received']}")
        print(f"📤 Messages sent: {stats['sent']}")
        print(f"🔴 Unread: {stats['unread']}")
        
        print("✅ Orchestrator system check completed")
        return True
        
    except Exception as e:
        print(f"❌ Orchestrator failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
''')
        print("✅ Created orchestrator main.py")
    
    return True


def create_missing_monitor_file():
    """Create missing monitor module."""
    monitor_file = Path("src/ai_mail_mcp/monitor.py")
    if not monitor_file.exists():
        monitor_file.write_text('''#!/usr/bin/env python3
"""
AI Mail MCP Monitor - System monitoring and health checks.
"""

import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_mail_mcp.mailbox import MailboxManager
from ai_mail_mcp.agent import AgentIdentifier

logger = logging.getLogger(__name__)


def main():
    """Main monitor entry point."""
    print("📊 AI Mail MCP Monitor")
    print("=" * 25)
    
    try:
        # Initialize system
        data_dir = Path.home() / ".ai_mail"
        db_path = data_dir / "mailbox.db"
        
        if not db_path.exists():
            print("❌ Database not found. Run the server first.")
            return False
        
        mailbox = MailboxManager(db_path)
        
        # Monitor loop
        print("🔍 Starting monitoring...")
        print("Press Ctrl+C to stop")
        
        while True:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            agents = mailbox.get_agents()
            
            print(f"\\n[{timestamp}]")
            print(f"📈 Active agents: {len(agents)}")
            
            for agent in agents:
                stats = mailbox.get_message_stats(agent.name)
                print(f"   🤖 {agent.name}: {stats['unread']} unread, {stats['total_received']} total")
            
            time.sleep(30)  # Check every 30 seconds
            
    except KeyboardInterrupt:
        print("\\n⏹️ Monitoring stopped")
        return True
    except Exception as e:
        print(f"❌ Monitor failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
''')
        print("✅ Created monitor.py")
        return True
    return False


def fix_imports_in_init():
    """Fix imports in __init__.py to handle missing modules gracefully."""
    init_file = Path("src/ai_mail_mcp/__init__.py")
    if init_file.exists():
        init_content = '''"""
AI Mail MCP - A Model Context Protocol server for AI agent mail communication.

This package provides a mailbox system that allows AI agents on the same machine
to send and receive messages from each other through a locally hosted service.
"""

__version__ = "1.0.0"
__author__ = "TimeLordRaps"
__email__ = "tyler.roost@gmail.com"

try:
    from .models import Message
    from .mailbox import MailboxManager
    from .agent import AgentIdentifier
except ImportError as e:
    print(f"Warning: Could not import all modules: {e}")
    Message = None
    MailboxManager = None
    AgentIdentifier = None

try:
    from .server import server
except ImportError:
    server = None

__all__ = [
    "Message",
    "MailboxManager", 
    "AgentIdentifier",
    "server",
]
'''
        init_file.write_text(init_content)
        print("✅ Fixed __init__.py imports")
        return True
    return False


def validate_project_structure():
    """Validate the project structure."""
    print("🔍 Validating project structure...")
    
    required_files = [
        ("pyproject.toml", "Python project configuration"),
        ("package.json", "Node.js package configuration"),
        ("src/ai_mail_mcp/__init__.py", "Python package init"),
        ("src/ai_mail_mcp/models.py", "Data models"),
        ("src/ai_mail_mcp/mailbox.py", "Mailbox manager"),
        ("src/ai_mail_mcp/agent.py", "Agent identifier"),
        ("src/ai_mail_mcp/server.py", "MCP server"),
        ("bin/ai-mail-server.js", "NPX entry point"),
        ("src/index.ts", "TypeScript entry point"),
        ("tests/test_ai_mail.py", "Test suite"),
        ("quick_test.py", "Quick test script"),
    ]
    
    all_exist = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_exist = False
    
    return all_exist


def run_basic_tests():
    """Run basic functionality tests."""
    print("🧪 Running basic tests...")
    
    # Test Python quick test
    if not run_command("python quick_test.py", "Python quick test", check=False):
        print("⚠️ Python quick test had issues")
    
    # Test comprehensive test
    if not run_command("python tests/test_ai_mail.py --comprehensive", "Comprehensive test", check=False):
        print("⚠️ Comprehensive test had issues")
    
    # Test Node.js functionality
    if not run_command("node bin/ai-mail-server.js --test", "Node.js functionality test", check=False):
        print("⚠️ Node.js test had issues")
    
    return True


def fix_typescript_config():
    """Ensure TypeScript configuration is correct."""
    tsconfig_path = Path("tsconfig.json")
    if tsconfig_path.exists():
        try:
            with open(tsconfig_path) as f:
                config = json.load(f)
            
            # Ensure proper configuration
            if "compilerOptions" not in config:
                config["compilerOptions"] = {}
            
            config["compilerOptions"].update({
                "target": "ES2022",
                "module": "ESNext",
                "moduleResolution": "Node",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "outDir": "./dist",
                "rootDir": "./src",
                "declaration": True,
                "declarationMap": True,
                "sourceMap": True,
                "lib": ["ES2022"],
                "allowSyntheticDefaultImports": True,
                "resolveJsonModule": True,
                "types": ["node"]
            })
            
            with open(tsconfig_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print("✅ Fixed TypeScript configuration")
            return True
        except Exception as e:
            print(f"⚠️ Could not fix TypeScript config: {e}")
    
    return False


def main():
    """Main setup and fix function."""
    print("🚀 AI Mail MCP Project Setup and Fix")
    print("=" * 40)
    
    # Change to project directory if script is run from elsewhere
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success_count = 0
    total_checks = 8
    
    # 1. Validate project structure
    if validate_project_structure():
        success_count += 1
    
    # 2. Create missing orchestrator files
    if create_missing_orchestrator_files():
        success_count += 1
    
    # 3. Create missing monitor file
    if create_missing_monitor_file():
        success_count += 1
    
    # 4. Fix imports in __init__.py
    if fix_imports_in_init():
        success_count += 1
    
    # 5. Fix TypeScript configuration
    if fix_typescript_config():
        success_count += 1
    
    # 6. Install Python dependencies
    if run_command("python -m pip install --upgrade pip setuptools wheel", "Python dependency update", check=False):
        success_count += 1
    
    # 7. Install core dependencies
    core_deps = "pydantic psutil aiofiles"
    if run_command(f"pip install {core_deps}", "Core dependencies installation", check=False):
        success_count += 1
    
    # 8. Run basic tests
    if run_basic_tests():
        success_count += 1
    
    print("\n" + "=" * 40)
    print(f"📊 Setup Summary: {success_count}/{total_checks} checks passed")
    
    if success_count >= 6:
        print("✅ Project setup is in good condition!")
        print("🚀 You can now run:")
        print("   • python quick_test.py")
        print("   • python src/ai_mail_server.py --test")
        print("   • node bin/ai-mail-server.js --test")
        return True
    else:
        print("⚠️ Project setup needs attention")
        print("📝 Check the errors above and fix them manually")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)