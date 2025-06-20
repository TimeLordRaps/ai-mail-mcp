#!/usr/bin/env python3
"""
AI Mail MCP Setup and Diagnostic Script

This script helps diagnose and fix common issues with the AI Mail MCP project.
Run this script to:
- Verify project structure
- Install missing dependencies  
- Fix configuration issues
- Test basic functionality
- Prepare for deployment
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

def run_command(cmd: str, description: str, check: bool = True) -> bool:
    """Run a command and return success status."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"⚠️ {description} completed with issues")
            if result.stderr.strip():
                print(f"   Error: {result.stderr.strip()}")
            return not check
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return not check

def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✅ {description} exists")
        return True
    else:
        print(f"❌ {description} missing")
        return False

def diagnose_project_structure() -> Tuple[bool, List[str]]:
    """Diagnose the project structure and return status and missing files."""
    print("🔍 Diagnosing project structure...")
    
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
        (".github/workflows/ci-cd-robust.yml", "Robust CI/CD workflow"),
    ]
    
    missing_files = []
    all_exist = True
    
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            missing_files.append(filepath)
            all_exist = False
    
    return all_exist, missing_files

def fix_python_dependencies() -> bool:
    """Install and fix Python dependencies."""
    print("\n🐍 Fixing Python dependencies...")
    
    # Update pip and essential tools
    if not run_command("python -m pip install --upgrade pip setuptools wheel", "Updating pip and tools", check=False):
        print("⚠️ Could not update pip")
    
    # Install build tools
    if not run_command("pip install build twine", "Installing build tools", check=False):
        print("⚠️ Could not install build tools")
    
    # Install core dependencies manually
    core_deps = ["pydantic>=2.0.0", "psutil>=5.8.0", "aiofiles>=0.8.0"]
    for dep in core_deps:
        if not run_command(f"pip install '{dep}'", f"Installing {dep}", check=False):
            print(f"⚠️ Could not install {dep}")
    
    # Install development dependencies
    dev_deps = ["pytest>=7.0.0", "pytest-asyncio>=0.21.0", "pytest-cov>=4.0.0", 
               "black>=23.0.0", "isort>=5.12.0", "flake8>=6.0.0", "mypy>=1.0.0"]
    for dep in dev_deps:
        if not run_command(f"pip install '{dep}'", f"Installing {dep}", check=False):
            print(f"⚠️ Could not install {dep}")
    
    # Try to install MCP
    mcp_options = ["mcp>=0.1.0", "model-context-protocol"]
    mcp_installed = False
    for mcp_pkg in mcp_options:
        if run_command(f"pip install '{mcp_pkg}'", f"Installing {mcp_pkg}", check=False):
            mcp_installed = True
            break
    
    if not mcp_installed:
        print("⚠️ Could not install MCP package - may need manual installation")
    
    return True

def test_imports() -> bool:
    """Test that core modules can be imported."""
    print("\n🧪 Testing Python imports...")
    
    import_tests = [
        ("from src.ai_mail_mcp.models import Message", "Message model"),
        ("from src.ai_mail_mcp.mailbox import MailboxManager", "Mailbox manager"),
        ("from src.ai_mail_mcp.agent import AgentIdentifier", "Agent identifier"),
    ]
    
    all_passed = True
    for import_cmd, description in import_tests:
        try:
            exec(import_cmd)
            print(f"✅ {description} import successful")
        except Exception as e:
            print(f"❌ {description} import failed: {e}")
            all_passed = False
    
    return all_passed

def test_basic_functionality() -> bool:
    """Test basic AI Mail MCP functionality."""
    print("\n🔧 Testing basic functionality...")
    
    try:
        import tempfile
        sys.path.insert(0, 'src')
        
        from ai_mail_mcp.models import Message
        from ai_mail_mcp.mailbox import MailboxManager
        from ai_mail_mcp.agent import AgentIdentifier
        from datetime import datetime, timezone
        
        # Test agent detection
        agent_name = AgentIdentifier.detect_agent_name()
        print(f"✅ Agent name detected: {agent_name}")
        
        # Test mailbox with temporary database
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'test.db'
            mailbox = MailboxManager(db_path)
            print("✅ Mailbox manager created")
            
            # Test agent registration
            mailbox.register_agent(agent_name, {"diagnostic_test": True})
            agents = mailbox.get_agents()
            print(f"✅ Agent registered, found {len(agents)} agents")
            
            # Test message creation and sending
            message = Message(
                id='diagnostic-test-001',
                sender=agent_name,
                recipient='diagnostic-recipient',
                subject='Diagnostic Test Message',
                body='This is a diagnostic test to verify functionality.',
                timestamp=datetime.now(timezone.utc),
                tags=['diagnostic', 'test']
            )
            
            msg_id = mailbox.send_message(message)
            print(f"✅ Message sent with ID: {msg_id}")
            
            # Test message retrieval
            messages = mailbox.get_messages('diagnostic-recipient')
            print(f"✅ Retrieved {len(messages)} messages")
            
            # Test statistics
            stats = mailbox.get_message_stats(agent_name)
            print(f"✅ Statistics retrieved: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_nodejs_functionality() -> bool:
    """Test Node.js and NPX functionality."""
    print("\n🟢 Testing Node.js functionality...")
    
    # Check if Node.js is available
    if not run_command("node --version", "Checking Node.js", check=False):
        print("⚠️ Node.js not available - NPX functionality will be limited")
        return False
    
    # Check if NPM is available
    if not run_command("npm --version", "Checking NPM", check=False):
        print("⚠️ NPM not available")
        return False
    
    # Validate package.json
    if not run_command("node -e \"JSON.parse(require('fs').readFileSync('package.json', 'utf8'))\"", 
                      "Validating package.json", check=False):
        print("⚠️ package.json is invalid")
        return False
    
    # Test bin script if it exists
    if Path("bin/ai-mail-server.js").exists():
        if run_command("node bin/ai-mail-server.js --help", "Testing bin script", check=False):
            print("✅ Bin script working")
        else:
            print("⚠️ Bin script has issues")
    
    return True

def generate_diagnostic_report() -> str:
    """Generate a comprehensive diagnostic report."""
    report = []
    report.append("# AI Mail MCP Diagnostic Report")
    report.append(f"Generated: {datetime.now().isoformat()}")
    report.append("")
    
    # System info
    report.append("## System Information")
    report.append(f"- Python: {sys.version}")
    report.append(f"- Platform: {sys.platform}")
    report.append(f"- Working Directory: {os.getcwd()}")
    report.append("")
    
    # Project structure
    all_exist, missing = diagnose_project_structure()
    report.append("## Project Structure")
    if all_exist:
        report.append("✅ All required files present")
    else:
        report.append("❌ Missing files:")
        for file in missing:
            report.append(f"  - {file}")
    report.append("")
    
    # Dependencies
    report.append("## Dependencies")
    try:
        import pydantic
        report.append(f"✅ Pydantic: {pydantic.__version__}")
    except ImportError:
        report.append("❌ Pydantic: Not installed")
    
    try:
        import psutil
        report.append(f"✅ Psutil: {psutil.__version__}")
    except ImportError:
        report.append("❌ Psutil: Not installed")
    
    try:
        import aiofiles
        report.append(f"✅ Aiofiles: Available")
    except ImportError:
        report.append("❌ Aiofiles: Not installed")
    
    report.append("")
    
    # Recommendations
    report.append("## Recommendations")
    if not all_exist:
        report.append("1. Run this diagnostic script to fix missing files")
    
    if missing:
        report.append("2. Check repository integrity - some files may need to be restored")
    
    report.append("3. Run 'python setup-and-fix.py' to attempt automatic fixes")
    report.append("4. Run tests with 'python test-node.js' for Node.js functionality")
    report.append("")
    
    return "\n".join(report)

def main():
    """Main diagnostic and setup function."""
    print("🚀 AI Mail MCP Setup and Diagnostic Tool")
    print("=" * 50)
    
    # Change to project directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    success_count = 0
    total_checks = 6
    
    # 1. Diagnose project structure
    print("\n" + "="*20 + " DIAGNOSIS " + "="*20)
    all_exist, missing = diagnose_project_structure()
    if all_exist:
        success_count += 1
        print("✅ Project structure is complete")
    else:
        print(f"⚠️ Missing {len(missing)} files")
    
    # 2. Fix Python dependencies
    print("\n" + "="*20 + " PYTHON SETUP " + "="*20)
    if fix_python_dependencies():
        success_count += 1
    
    # 3. Test imports
    print("\n" + "="*20 + " IMPORT TESTS " + "="*20)
    if test_imports():
        success_count += 1
    
    # 4. Test basic functionality
    print("\n" + "="*20 + " FUNCTIONALITY TESTS " + "="*20)
    if test_basic_functionality():
        success_count += 1
    
    # 5. Test Node.js functionality
    print("\n" + "="*20 + " NODE.JS TESTS " + "="*20)
    if test_nodejs_functionality():
        success_count += 1
    
    # 6. Generate report
    print("\n" + "="*20 + " DIAGNOSTIC REPORT " + "="*20)
    report = generate_diagnostic_report()
    
    # Save report to file
    try:
        with open("diagnostic_report.md", "w") as f:
            f.write(report)
        print("✅ Diagnostic report saved to diagnostic_report.md")
        success_count += 1
    except Exception as e:
        print(f"❌ Could not save diagnostic report: {e}")
    
    # Summary
    print("\n" + "="*50)
    print(f"📊 Setup Summary: {success_count}/{total_checks} checks passed")
    
    if success_count >= 4:
        print("🎉 AI Mail MCP is in good condition!")
        print("\n🚀 Next steps:")
        print("   • Run: python test-node.js")
        print("   • Run: python quick_test.py (when available)")
        print("   • Test: node bin/ai-mail-server.js --help")
        print("   • Deploy: npm start or uvx ai-mail-mcp")
        return True
    else:
        print("⚠️ AI Mail MCP needs attention")
        print("\n🔧 Troubleshooting:")
        print("   • Check missing files in diagnostic report")
        print("   • Ensure Python 3.8+ is installed")
        print("   • Install missing dependencies manually")
        print("   • Check repository integrity")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
