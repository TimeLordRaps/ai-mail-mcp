#!/usr/bin/env node

/**
 * NPX wrapper for AI Mail MCP Server
 * This allows running the Python MCP server via NPX
 */

const { spawn } = require('child_process');
const path = require('path');

// Try to run with uvx first, fallback to python
function runServer() {
  const args = process.argv.slice(2);
  
  // Try uvx first (modern uv tool runner)
  const uvx = spawn('uvx', ['ai-mail-mcp', ...args], {
    stdio: 'inherit',
    shell: true
  });

  uvx.on('error', (err) => {
    if (err.code === 'ENOENT') {
      // Fallback to direct python execution
      console.log('uvx not found, trying direct python execution...');
      
      const pythonPath = path.join(__dirname, '..', 'src', 'ai_mail_server.py');
      const python = spawn('python', [pythonPath, ...args], {
        stdio: 'inherit',
        shell: true
      });

      python.on('error', (pythonErr) => {
        console.error('Failed to start AI Mail server:', pythonErr.message);
        process.exit(1);
      });

      python.on('exit', (code) => {
        process.exit(code);
      });
    } else {
      console.error('Failed to start AI Mail server:', err.message);
      process.exit(1);
    }
  });

  uvx.on('exit', (code) => {
    process.exit(code);
  });
}

// Print help if requested
if (process.argv.includes('--help') || process.argv.includes('-h')) {
  console.log(`
AI Mail MCP Server - Local mailbox for AI agent communication

Usage:
  npx @timelordraps/ai-mail-mcp [options]

Options:
  --help, -h          Show this help message
  --list-agents       List all registered agents
  --stats             Show mailbox statistics
  --cleanup           Clean up old data

Environment Variables:
  AI_AGENT_NAME       Override agent name detection
  AI_MAIL_DATA_DIR    Custom data directory

Examples:
  npx @timelordraps/ai-mail-mcp
  npx @timelordraps/ai-mail-mcp --list-agents
  AI_AGENT_NAME=my-agent npx @timelordraps/ai-mail-mcp

For more information, visit: https://github.com/TimeLordRaps/ai-mail-mcp
`);
  process.exit(0);
}

runServer();
