/**
 * Integration tests for AI Mail MCP Server
 * Tests the actual MCP protocol integration and end-to-end workflows
 */

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import Database from 'better-sqlite3';

// Mock dependencies for integration tests
jest.mock('better-sqlite3');
jest.mock('node-machine-id', () => ({
  machineIdSync: () => 'integration-test-machine-id'
}));

describe('AI Mail MCP Server Integration Tests', () => {
  let tempDir: string;
  let mockDb: any;
  let server: any;

  beforeEach(async () => {
    // Create temporary directory for integration tests
    tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'ai-mail-integration-'));
    
    // Setup mock database
    const mockPrepare = jest.fn();
    const mockExec = jest.fn();
    const mockGet = jest.fn().mockReturnValue(null);
    const mockAll = jest.fn().mockReturnValue([]);
    const mockRun = jest.fn().mockReturnValue({ changes: 1 });
    const mockClose = jest.fn();

    mockDb = {
      prepare: mockPrepare.mockReturnValue({
        get: mockGet,
        all: mockAll,
        run: mockRun
      }),
      exec: mockExec,
      close: mockClose
    };

    (Database as jest.MockedClass<typeof Database>).mockReturnValue(mockDb);

    // Set environment for integration tests
    process.env.AI_MAIL_DATA_DIR = tempDir;
    process.env.AI_AGENT_NAME = 'integration-test-agent';
    process.env.NODE_ENV = 'test';
  });

  afterEach(async () => {
    // Cleanup
    if (server) {
      server = null;
    }
    
    // Remove temporary directory
    await fs.promises.rm(tempDir, { recursive: true, force: true });
    
    delete process.env.AI_MAIL_DATA_DIR;
    delete process.env.AI_AGENT_NAME;
    
    jest.clearAllMocks();
  });

  describe('MCP Protocol Compliance', () => {
    test('should properly initialize MCP server', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();
      
      expect(server.server).toBeDefined();
      expect(server.agentName).toBe('integration-test-agent');
    });

    test('should register all required MCP tools', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();
      
      const tools = server.getTools();
      const requiredTools = [
        'send_mail',
        'check_mail',
        'read_message',
        'search_messages',
        'list_agents',
        'mark_read',
        'archive_message',
        'get_thread',
        'get_mailbox_stats',
        'delete_message'
      ];

      requiredTools.forEach(toolName => {
        const tool = tools.find((t: any) => t.name === toolName);
        expect(tool).toBeDefined();
        expect(tool.inputSchema).toBeDefined();
        expect(tool.description).toBeDefined();
      });
    });

    test('should handle MCP tool requests properly', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Mock successful agent lookup
      mockDb.prepare.mockReturnValueOnce({
        get: jest.fn().mockReturnValue({ name: 'test-recipient' })
      });
      
      // Mock message insertion
      mockDb.prepare.mockReturnValueOnce({
        run: jest.fn().mockReturnValue({ changes: 1 })
      });

      const result = await server.handleSendMail({
        recipient: 'test-recipient',
        subject: 'Integration Test',
        body: 'This is an integration test message',
        priority: 'normal'
      });

      expect(result).toBeDefined();
      expect(result.content).toBeDefined();
      expect(result.content[0].text).toContain('Message sent successfully');
    });
  });

  describe('Multi-Agent Communication Workflows', () => {
    test('should handle complete message exchange workflow', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Scenario: Agent A sends message to Agent B, Agent B replies
      
      // Step 1: Send initial message
      mockDb.prepare.mockReturnValueOnce({
        get: jest.fn().mockReturnValue({ name: 'agent-b' })
      });
      mockDb.prepare.mockReturnValueOnce({
        run: jest.fn().mockReturnValue({ changes: 1 })
      });

      const sendResult = await server.handleSendMail({
        recipient: 'agent-b',
        subject: 'Project Assignment',
        body: 'Can you handle the authentication module?',
        priority: 'high',
        tags: ['project', 'auth']
      });

      expect(sendResult.content[0].text).toContain('Message sent successfully');

      // Step 2: Agent B checks mail
      const testMessage = {
        id: 'msg-001',
        sender: 'integration-test-agent',
        recipient: 'agent-b',
        subject: 'Project Assignment',
        body: 'Can you handle the authentication module?',
        priority: 'high',
        tags: ['project', 'auth'],
        thread_id: 'thread-001',
        timestamp: new Date().toISOString(),
        read: false,
        archived: false
      };

      mockDb.prepare.mockReturnValueOnce({
        all: jest.fn().mockReturnValue([testMessage])
      });

      const checkResult = await server.handleCheckMail({
        unread_only: true,
        limit: 10
      });

      expect(checkResult.content[0].text).toContain('Found 1 message(s)');
      expect(checkResult.content[0].text).toContain('Project Assignment');

      // Step 3: Agent B reads and replies
      mockDb.prepare.mockReturnValueOnce({
        get: jest.fn().mockReturnValue(testMessage)
      });
      mockDb.prepare.mockReturnValueOnce({
        run: jest.fn().mockReturnValue({ changes: 1 })
      });

      const readResult = await server.handleReadMessage({
        message_id: 'msg-001'
      });

      expect(readResult.content[0].text).toContain('Project Assignment');
      expect(readResult.content[0].text).toContain('authentication module');
    });

    test('should handle message threading correctly', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Create a thread with multiple messages
      const threadMessages = [
        {
          id: 'msg-1',
          sender: 'agent-a',
          recipient: 'integration-test-agent',
          subject: 'Original Message',
          body: 'Starting a conversation',
          priority: 'normal',
          tags: [],
          thread_id: 'thread-abc123',
          timestamp: '2024-01-01T10:00:00Z',
          read: true,
          archived: false
        },
        {
          id: 'msg-2',
          sender: 'integration-test-agent',
          recipient: 'agent-a',
          subject: 'Re: Original Message',
          body: 'Thanks for starting this conversation',
          priority: 'normal',
          tags: [],
          reply_to: 'msg-1',
          thread_id: 'thread-abc123',
          timestamp: '2024-01-01T10:05:00Z',
          read: true,
          archived: false
        },
        {
          id: 'msg-3',
          sender: 'agent-a',
          recipient: 'integration-test-agent',
          subject: 'Re: Original Message',
          body: 'No problem! Let me know if you need anything',
          priority: 'normal',
          tags: [],
          reply_to: 'msg-2',
          thread_id: 'thread-abc123',
          timestamp: '2024-01-01T10:10:00Z',
          read: false,
          archived: false
        }
      ];

      mockDb.prepare.mockReturnValueOnce({
        all: jest.fn().mockReturnValue(threadMessages)
      });

      const threadResult = await server.handleGetThread({
        thread_id: 'thread-abc123'
      });

      expect(threadResult.content[0].text).toContain('Thread thread-abc123 (3 messages)');
      expect(threadResult.content[0].text).toContain('Original Message');
      expect(threadResult.content[0].text).toContain('Thanks for starting');
      expect(threadResult.content[0].text).toContain('No problem!');
      expect(threadResult.content[0].text).toContain('#1');
      expect(threadResult.content[0].text).toContain('#2');
      expect(threadResult.content[0].text).toContain('#3');
    });
  });

  describe('Priority and Tag Management', () => {
    test('should handle priority-based message filtering', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const urgentMessages = [
        {
          id: 'urgent-1',
          sender: 'emergency-agent',
          recipient: 'integration-test-agent',
          subject: 'URGENT: Server Down',
          body: 'Production server is down, need immediate attention',
          priority: 'urgent',
          tags: ['emergency', 'production'],
          thread_id: 'urgent-thread-1',
          timestamp: new Date().toISOString(),
          read: false,
          archived: false
        }
      ];

      mockDb.prepare.mockReturnValueOnce({
        all: jest.fn().mockReturnValue(urgentMessages)
      });

      const result = await server.handleCheckMail({
        unread_only: true,
        priority_filter: 'urgent',
        limit: 10
      });

      expect(result.content[0].text).toContain('Found 1 message(s)');
      expect(result.content[0].text).toContain('🚨'); // Urgent emoji
      expect(result.content[0].text).toContain('URGENT: Server Down');
    });

    test('should handle tag-based message search', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const taggedMessages = [
        {
          id: 'tagged-1',
          sender: 'project-manager',
          recipient: 'integration-test-agent',
          subject: 'Weekly Sprint Review',
          body: 'Time to review our sprint progress',
          priority: 'normal',
          tags: ['sprint', 'review', 'weekly'],
          thread_id: 'sprint-thread-1',
          timestamp: new Date().toISOString(),
          read: false,
          archived: false
        }
      ];

      mockDb.prepare.mockReturnValueOnce({
        all: jest.fn().mockReturnValue(taggedMessages)
      });

      const result = await server.handleSearchMessages({
        query: 'sprint',
        limit: 20
      });

      expect(result.content[0].text).toContain('Found 1 message(s) matching "sprint"');
      expect(result.content[0].text).toContain('Weekly Sprint Review');
    });
  });

  describe('Database Integration', () => {
    test('should properly initialize database schema', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Verify database initialization calls
      expect(mockDb.exec).toHaveBeenCalledWith(expect.stringContaining('CREATE TABLE IF NOT EXISTS messages'));
      expect(mockDb.exec).toHaveBeenCalledWith(expect.stringContaining('CREATE TABLE IF NOT EXISTS agents'));
      expect(mockDb.exec).toHaveBeenCalledWith(expect.stringContaining('CREATE INDEX'));
    });

    test('should handle database transaction errors gracefully', async () => {
      // Simulate database error
      mockDb.prepare.mockImplementation(() => {
        throw new Error('Database connection lost');
      });

      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      await expect(server.handleCheckMail({})).rejects.toThrow('Database connection lost');
    });
  });

  describe('Agent Management Integration', () => {
    test('should handle multi-agent registration and discovery', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const registeredAgents = [
        {
          name: 'integration-test-agent',
          last_seen: new Date().toISOString(),
          status: 'online',
          machine_id: 'integration-test-machine-id'
        },
        {
          name: 'claude-desktop',
          last_seen: new Date(Date.now() - 30000).toISOString(),
          status: 'online',
          machine_id: 'other-machine-id'
        },
        {
          name: 'vscode-copilot',
          last_seen: new Date(Date.now() - 120000).toISOString(),
          status: 'offline',
          machine_id: 'third-machine-id'
        }
      ];

      mockDb.prepare.mockReturnValueOnce({
        all: jest.fn().mockReturnValue(registeredAgents)
      });

      const result = await server.handleListAgents({ active_only: false });

      expect(result.content[0].text).toContain('Available agents (3)');
      expect(result.content[0].text).toContain('integration-test-agent');
      expect(result.content[0].text).toContain('(YOU)');
      expect(result.content[0].text).toContain('claude-desktop');
      expect(result.content[0].text).toContain('vscode-copilot');
      expect(result.content[0].text).toContain('🟢'); // Online status
      expect(result.content[0].text).toContain('🔴'); // Offline status
    });
  });

  describe('Performance and Load Testing', () => {
    test('should handle bulk message operations efficiently', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Simulate bulk message handling
      const bulkMessages = Array.from({ length: 100 }, (_, i) => ({
        id: `bulk-msg-${i}`,
        sender: `sender-${i % 10}`,
        recipient: 'integration-test-agent',
        subject: `Bulk Message ${i}`,
        body: `This is bulk message number ${i}`,
        priority: i % 4 === 0 ? 'urgent' : 'normal',
        tags: [`bulk`, `batch-${Math.floor(i / 10)}`],
        thread_id: `thread-${i}`,
        timestamp: new Date(Date.now() - i * 1000).toISOString(),
        read: i % 3 === 0,
        archived: false
      }));

      mockDb.prepare.mockReturnValueOnce({
        all: jest.fn().mockReturnValue(bulkMessages)
      });

      const startTime = Date.now();
      const result = await server.handleCheckMail({
        unread_only: false,
        limit: 100
      });
      const duration = Date.now() - startTime;

      expect(result.content[0].text).toContain('Found 100 message(s)');
      expect(duration).toBeLessThan(1000); // Should complete within 1 second
    });

    test('should handle concurrent operations', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Simulate concurrent message operations
      const concurrentPromises = Array.from({ length: 10 }, async (_, i) => {
        mockDb.prepare.mockReturnValue({
          get: jest.fn().mockReturnValue({ name: `agent-${i}` }),
          run: jest.fn().mockReturnValue({ changes: 1 })
        });

        return server.handleSendMail({
          recipient: `agent-${i}`,
          subject: `Concurrent Message ${i}`,
          body: `This is concurrent message ${i}`,
          priority: 'normal'
        });
      });

      const startTime = Date.now();
      const results = await Promise.all(concurrentPromises);
      const duration = Date.now() - startTime;

      expect(results).toHaveLength(10);
      results.forEach((result, i) => {
        expect(result.content[0].text).toContain('Message sent successfully');
      });
      expect(duration).toBeLessThan(2000); // Should complete within 2 seconds
    });
  });

  describe('Error Recovery and Resilience', () => {
    test('should recover from temporary database failures', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // First call fails
      mockDb.prepare.mockImplementationOnce(() => {
        throw new Error('Temporary database error');
      });

      await expect(server.handleCheckMail({})).rejects.toThrow('Temporary database error');

      // Second call succeeds
      mockDb.prepare.mockReturnValueOnce({
        all: jest.fn().mockReturnValue([])
      });

      const result = await server.handleCheckMail({});
      expect(result.content[0].text).toBe('📭 No new messages');
    });

    test('should handle malformed message data gracefully', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const malformedMessage = {
        id: 'malformed-1',
        sender: null, // Invalid sender
        recipient: 'integration-test-agent',
        subject: undefined, // Invalid subject
        body: 'Test body',
        priority: 'invalid-priority', // Invalid priority
        tags: 'not-an-array', // Invalid tags format
        thread_id: 'thread-1',
        timestamp: 'invalid-date', // Invalid timestamp
        read: 'yes', // Invalid boolean
        archived: false
      };

      mockDb.prepare.mockReturnValueOnce({
        get: jest.fn().mockReturnValue(malformedMessage)
      });

      // Should handle gracefully without crashing
      await expect(server.handleReadMessage({
        message_id: 'malformed-1'
      })).resolves.toBeDefined();
    });
  });
});
