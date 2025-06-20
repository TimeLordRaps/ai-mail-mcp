#!/usr/bin/env node

/**
 * Quick test script for Node.js functionality
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('🚀 AI Mail MCP Node.js Quick Test');
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

function testSimpleServer() {
    console.log('\n🤖 Testing simple server functionality...');
    
    try {
        // Create simple data structure
        const dataDir = process.env.AI_MAIL_DATA_DIR || path.join(os.homedir(), '.ai_mail');
        const agentName = process.env.AI_AGENT_NAME || 'test-agent';
        
        console.log(`✅ Data directory: ${dataDir}`);
        console.log(`✅ Agent name: ${agentName}`);
        
        // Test that we can create the data directory structure
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
            console.log('✅ Created data directory');
        } else {
            console.log('✅ Data directory exists');
        }
        
        // Test basic file operations
        const testFile = path.join(dataDir, 'node_test.json');
        const testData = {
            agent: agentName,
            timestamp: new Date().toISOString(),
            test: 'Node.js functionality working'
        };
        
        fs.writeFileSync(testFile, JSON.stringify(testData, null, 2));
        const readData = JSON.parse(fs.readFileSync(testFile, 'utf8'));
        
        console.log('✅ File operations working');
        console.log(`✅ Test data: ${JSON.stringify(readData, null, 2)}`);
        
        // Clean up
        fs.unlinkSync(testFile);
        console.log('✅ Cleanup completed');
        
        return true;
        
    } catch (error) {
        console.log(`❌ Simple server test failed: ${error.message}`);
        return false;
    }
}

function main() {
    let allPassed = true;
    
    // Run all tests
    if (!testFileStructure()) allPassed = false;
    if (!testPackageJson()) allPassed = false;
    if (!testBinScript()) allPassed = false;
    if (!testSimpleServer()) allPassed = false;
    
    console.log('\n' + '='.repeat(40));
    
    if (allPassed) {
        console.log('🎉 All Node.js tests passed!');
        console.log('✅ NPX functionality should be working');
        console.log('\n💡 Try running:');
        console.log('   node bin/ai-mail-server.js --help');
        console.log('   npm start');
    } else {
        console.log('❌ Some tests failed');
        console.log('⚠️ Check the issues above');
    }
    
    process.exit(allPassed ? 0 : 1);
}

if (require.main === module) {
    main();
}