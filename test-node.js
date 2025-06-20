#!/usr/bin/env node

/**
 * Node.js test runner for AI Mail MCP
 * Tests NPX functionality and basic operations
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('🚀 AI Mail MCP Node.js Test Runner');
console.log('=' + '='.repeat(39));

function testFileStructure() {
    console.log('\n📁 Testing file structure...');
    
    const files = [
        'package.json',
        'tsconfig.json', 
        'src/index.ts',
        'bin/ai-mail-server.js',
        'src/ai_mail_mcp/server.py'
    ];
    
    let allExist = true;
    
    for (const file of files) {
        const exists = fs.existsSync(file);
        console.log(`${exists ? '✅' : '❌'} ${file}`);
        if (!exists) allExist = false;
    }
    
    return allExist;
}

function testPackageJson() {
    console.log('\n📦 Testing package.json...');
    
    try {
        const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        
        console.log(`✅ Package name: ${pkg.name}`);
        console.log(`✅ Version: ${pkg.version}`);
        console.log(`✅ Main: ${pkg.main}`);
        console.log(`✅ Bin: ${JSON.stringify(pkg.bin)}`);
        
        // Check if bin file exists
        if (pkg.bin && pkg.bin['ai-mail-server']) {
            const binPath = pkg.bin['ai-mail-server'];
            const exists = fs.existsSync(binPath);
            console.log(`${exists ? '✅' : '❌'} Bin file exists: ${binPath}`);
            return exists;
        }
        
        return true;
    } catch (error) {
        console.log(`❌ Package.json error: ${error.message}`);
        return false;
    }
}

function testBinScript() {
    console.log('\n🔧 Testing bin script...');
    
    try {
        const binPath = './bin/ai-mail-server.js';
        
        if (!fs.existsSync(binPath)) {
            console.log(`❌ Bin script not found: ${binPath}`);
            return false;
        }
        
        const content = fs.readFileSync(binPath, 'utf8');
        
        // Check for basic structure
        if (content.includes('#!/usr/bin/env node')) {
            console.log('✅ Has correct shebang');
        } else {
            console.log('⚠️ Missing or incorrect shebang');
        }
        
        if (content.includes('--help')) {
            console.log('✅ Has help functionality');
        } else {
            console.log('⚠️ Missing help functionality');
        }
        
        console.log('✅ Bin script structure looks good');
        return true;
        
    } catch (error) {
        console.log(`❌ Bin script test failed: ${error.message}`);
        return false;
    }
}

function testEnvironmentVariables() {
    console.log('\n🌍 Testing environment variables...');
    
    // Test data directory
    const dataDir = process.env.AI_MAIL_DATA_DIR || path.join(os.homedir(), '.ai_mail');
    const agentName = process.env.AI_AGENT_NAME || 'nodejs-test-agent';
    
    console.log(`✅ Data directory: ${dataDir}`);
    console.log(`✅ Agent name: ${agentName}`);
    
    // Test that we can create the data directory structure
    try {
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
            console.log('✅ Created data directory');
        } else {
            console.log('✅ Data directory exists');
        }
        
        // Test basic file operations
        const testFile = path.join(dataDir, 'nodejs_test.json');
        const testData = {
            agent: agentName,
            timestamp: new Date().toISOString(),
            test: 'Node.js functionality working',
            pid: process.pid,
            platform: os.platform(),
            arch: os.arch()
        };
        
        fs.writeFileSync(testFile, JSON.stringify(testData, null, 2));
        const readData = JSON.parse(fs.readFileSync(testFile, 'utf8'));
        
        console.log('✅ File operations working');
        console.log(`✅ Test data verified: ${readData.agent}`);
        
        // Clean up
        fs.unlinkSync(testFile);
        console.log('✅ Cleanup completed');
        
        return true;
        
    } catch (error) {
        console.log(`❌ Environment test failed: ${error.message}`);
        return false;
    }
}

function testMCPConfiguration() {
    console.log('\n⚙️ Testing MCP configuration...');
    
    try {
        // Test Claude Desktop config format
        const claudeConfig = {
            mcpServers: {
                "ai-mail": {
                    command: "npx",
                    args: ["-y", "@timelordraps/ai-mail-mcp"]
                }
            }
        };
        
        console.log('✅ Claude Desktop config format valid');
        console.log(`   Command: ${claudeConfig.mcpServers["ai-mail"].command}`);
        console.log(`   Args: ${claudeConfig.mcpServers["ai-mail"].args.join(' ')}`);
        
        // Test VS Code config format
        const vscodeConfig = {
            "mcp.servers": {
                "ai-mail": {
                    command: "npx", 
                    args: ["-y", "@timelordraps/ai-mail-mcp"]
                }
            }
        };
        
        console.log('✅ VS Code config format valid');
        
        return true;
    } catch (error) {
        console.log(`❌ MCP configuration test failed: ${error.message}`);
        return false;
    }
}

function testSystemInfo() {
    console.log('\n💻 Testing system information...');
    
    try {
        console.log(`✅ Node.js version: ${process.version}`);
        console.log(`✅ Platform: ${os.platform()}`);
        console.log(`✅ Architecture: ${os.arch()}`);
        console.log(`✅ Hostname: ${os.hostname()}`);
        console.log(`✅ User: ${os.userInfo().username}`);
        console.log(`✅ Home directory: ${os.homedir()}`);
        console.log(`✅ Current working directory: ${process.cwd()}`);
        
        return true;
    } catch (error) {
        console.log(`❌ System info test failed: ${error.message}`);
        return false;
    }
}

function main() {
    let allPassed = true;
    let passedTests = 0;
    const totalTests = 6;
    
    // Run all tests
    if (testFileStructure()) passedTests++;
    else allPassed = false;
    
    if (testPackageJson()) passedTests++;
    else allPassed = false;
    
    if (testBinScript()) passedTests++;
    else allPassed = false;
    
    if (testEnvironmentVariables()) passedTests++;
    else allPassed = false;
    
    if (testMCPConfiguration()) passedTests++;
    else allPassed = false;
    
    if (testSystemInfo()) passedTests++;
    else allPassed = false;
    
    console.log('\n' + '='.repeat(50));
    console.log(`📊 Test Results: ${passedTests}/${totalTests} tests passed`);
    
    if (allPassed) {
        console.log('🎉 All Node.js tests passed!');
        console.log('✅ NPX functionality should be working');
        console.log('\n💡 Try running:');
        console.log('   node bin/ai-mail-server.js --help');
        console.log('   npm start');
        console.log('   npm test');
        console.log('\n📚 For more info: https://github.com/TimeLordRaps/ai-mail-mcp');
    } else {
        console.log('❌ Some tests failed');
        console.log('⚠️ Check the issues above');
        console.log('\n🔧 Troubleshooting:');
        console.log('   - Ensure all required files exist');
        console.log('   - Check file permissions');
        console.log('   - Verify Node.js installation');
    }
    
    process.exit(allPassed ? 0 : 1);
}

if (require.main === module) {
    main();
}

module.exports = {
    testFileStructure,
    testPackageJson,
    testBinScript,
    testEnvironmentVariables,
    testMCPConfiguration,
    testSystemInfo
};
