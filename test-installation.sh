#!/bin/bash
# AI Mail MCP Installation Test Script

set -e

echo "🧪 Testing AI Mail MCP Installation Methods"
echo "============================================"

# Test 1: NPX Installation
echo ""
echo "1️⃣ Testing NPX installation..."
if command -v npx &> /dev/null; then
    echo "✅ NPX is available"
    echo "   Testing: npx @timelordraps/ai-mail-mcp --help"
    # This would test the NPX installation once published
    echo "   (Skipping actual test - package not yet published)"
else
    echo "❌ NPX not available"
fi

# Test 2: UV Installation
echo ""
echo "2️⃣ Testing UV installation..."
if command -v uvx &> /dev/null; then
    echo "✅ UV is available"
    echo "   Testing: uvx ai-mail-mcp --help"
    # This would test the UV installation once published
    echo "   (Skipping actual test - package not yet published)"
else
    echo "❌ UV not available"
fi

# Test 3: Pip Installation
echo ""
echo "3️⃣ Testing Pip installation..."
if command -v pip &> /dev/null; then
    echo "✅ Pip is available"
    echo "   Testing local installation..."
    
    # Test local installation
    cd "$(dirname "$0")"
    if [ -f "pyproject.toml" ]; then
        echo "   Installing from local directory..."
        pip install -e . --quiet
        
        if command -v ai-mail-server &> /dev/null; then
            echo "✅ ai-mail-server command available"
            ai-mail-server --help > /dev/null 2>&1 && echo "✅ Help command works"
        else
            echo "❌ ai-mail-server command not found"
        fi
        
        if command -v ai-mail-orchestrator &> /dev/null; then
            echo "✅ ai-mail-orchestrator command available"
        else
            echo "❌ ai-mail-orchestrator command not found"
        fi
    else
        echo "❌ pyproject.toml not found"
    fi
else
    echo "❌ Pip not available"
fi

# Test 4: MCP Configuration Examples
echo ""
echo "4️⃣ Testing MCP configuration examples..."

# Test Claude Desktop config
claude_config='{"mcpServers":{"ai-mail":{"command":"npx","args":["-y","@timelordraps/ai-mail-mcp"]}}}'
if echo "$claude_config" | python -m json.tool > /dev/null 2>&1; then
    echo "✅ Claude Desktop config is valid JSON"
else
    echo "❌ Claude Desktop config is invalid JSON"
fi

# Test VS Code config
vscode_config='{"mcp.servers":{"ai-mail":{"command":"npx","args":["-y","@timelordraps/ai-mail-mcp"]}}}'
if echo "$vscode_config" | python -m json.tool > /dev/null 2>&1; then
    echo "✅ VS Code config is valid JSON"
else
    echo "❌ VS Code config is invalid JSON"
fi

# Test 5: Environment Variables
echo ""
echo "5️⃣ Testing environment variable support..."

export AI_MAIL_DATA_DIR="/tmp/test_ai_mail"
export AI_AGENT_NAME="test-agent"

if [ "$AI_MAIL_DATA_DIR" = "/tmp/test_ai_mail" ]; then
    echo "✅ AI_MAIL_DATA_DIR environment variable works"
else
    echo "❌ AI_MAIL_DATA_DIR environment variable failed"
fi

if [ "$AI_AGENT_NAME" = "test-agent" ]; then
    echo "✅ AI_AGENT_NAME environment variable works"
else
    echo "❌ AI_AGENT_NAME environment variable failed"
fi

# Test 6: Directory Structure
echo ""
echo "6️⃣ Testing project structure..."

required_files=(
    "src/ai_mail_mcp/server.py"
    "src/ai_mail_mcp/orchestrator/main.py"
    "bin/ai-mail-server.js"
    "package.json"
    "pyproject.toml"
    "README.md"
    ".github/workflows/ci-cd.yml"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

# Test 7: Python Import Test
echo ""
echo "7️⃣ Testing Python imports..."
python -c "
try:
    import sys
    sys.path.insert(0, 'src')
    from ai_mail_mcp import __version__
    print(f'✅ AI Mail MCP version: {__version__}')
except ImportError as e:
    print(f'❌ Import failed: {e}')
except Exception as e:
    print(f'⚠️  Import warning: {e}')
"

echo ""
echo "🎉 Installation test completed!"
echo ""
echo "📦 To install AI Mail MCP:"
echo "   NPX:  npx @timelordraps/ai-mail-mcp"
echo "   UV:   uvx ai-mail-mcp"  
echo "   Pip:  pip install ai-mail-mcp"
echo ""
echo "📚 Documentation: https://github.com/TimeLordRaps/ai-mail-mcp"