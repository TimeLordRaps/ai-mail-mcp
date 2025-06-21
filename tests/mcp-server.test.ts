/**
 * TypeScript tests for AI Mail MCP Server
 */

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';
import * as fs from 'fs';
import * as path from 'os';
import * as os from 'os';
import Database from 'better-sqlite3';
import { v4 as uuidv4 } from 'uuid';

// Mock dependencies
jest.mock('better-sqlite3');
jest.mock('node-machine-id', () => ({
  machineIdSync: () => 'test-machine-id'
}));
jest.mock('@modelcontextprotocol/sdk/server/index.js', () => ({
  Server: jest.fn().mockImplementation(() => ({
    setRequestHandler: jest.fn(),
    connect: jest.fn()
  }))
}));
jest.mock('@modelcontextprotocol/sdk/server/stdio.js', () => ({
  StdioServerTransport: jest.fn()
}));

// Test interfaces matching the server
interface Message {
  id: string;
  sender: string;
  recipient: string;
  subject: string;
  body: string;
  priority: 'urgent' | 'high' | 'normal' | 'low';
  tags: string[];
  reply_to?: string;
  thread_id: string;
  timestamp: string;
  read: boolean;
  archived: boolean;
}

interface Agent {
  name: string;
  last_seen: string;
  status: 'online' | 'offline';
  machine_id: string;
  process_info?: string;
}

describe('AI Mail MCP Server', () => {
  let mockDb: any;
  let testDataDir: string;

  beforeEach(() => {
    // Setup mock database
    const mockPrepare = jest.fn();
    const mockExec = jest.fn();
    const mockGet = jest.fn();
    const mockAll = jest.fn();
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

    // Setup test environment
    testDataDir = '/tmp/ai-mail-test';
    process.env.AI_MAIL_DATA_DIR = testDataDir;
    process.env.AI_AGENT_NAME = 'test-agent';

    // Clear any existing environment
    delete process.env.NODE_ENV;
    process.env.NODE_ENV = 'test';
  });

  afterEach(() => {
    jest.clearAllMocks();
    delete process.env.AI_MAIL_DATA_DIR;
    delete process.env.AI_AGENT_NAME;
  });

  describe('Database Initialization', () => {
    test('should create database tables on initialization', () => {
      // Import here to trigger constructor after mocks are set up
      const { AIMailServer } = require('../src/index');
      new AIMailServer();

      expect(mockDb.exec).toHaveBeenCalledWith(expect.stringContaining('CREATE TABLE IF NOT EXISTS messages'));
      expect(mockDb.exec).toHaveBeenCalledWith(expect.stringContaining('CREATE TABLE IF NOT EXISTS agents'));
      expect(mockDb.exec).toHaveBeenCalledWith(expect.stringContaining('CREATE INDEX'));
    });

    test('should handle database initialization errors gracefully', () => {
      mockDb.exec.mockImplementation(() => {
        throw new Error('Database error');
      });

      expect(() => {
        const { AIMailServer } = require('../src/index');
        new AIMailServer();
      }).toThrow('Database error');
    });
  });

  describe('Agent Detection and Registration', () => {
    test('should detect agent name from environment variable', () => {
      process.env.AI_AGENT_NAME = 'custom-agent';
      
      const { AIMailServer } = require('../src/index');
      const server = new AIMailServer();
      
      expect(server.agentName).toBe('custom-agent');
    });

    test('should detect agent name from process information', () => {
      delete process.env.AI_AGENT_NAME;
      process.env.TERM_PROGRAM = 'claude';
      
      const { AIMailServer } = require('../src/index');
      const server = new AIMailServer();
      
      expect(server.agentName).toContain('claude');
    });

    test('should ensure unique agent names', () => {
      const mockGet = jest.fn()
        .mockReturnValueOnce({ name: 'test-agent' }) // First call returns existing
        .mockReturnValueOnce(null); // Second call returns nothing

      mockDb.prepare.mockReturnValue({ get: mockGet, run: jest.fn() });

      const { AIMailServer } = require('../src/index');
      const server = new AIMailServer();
      
      expect(mockGet).toHaveBeenCalledWith('test-agent', 'test-machine-id');
      expect(mockGet).toHaveBeenCalledWith('test-agent-2', 'test-machine-id');
    });

    test('should register agent in database', () => {
      const mockRun = jest.fn();
      mockDb.prepare.mockReturnValue({ 
        get: jest.fn().mockReturnValue(null),
        run: mockRun 
      });

      const { AIMailServer } = require('../src/index');
      new AIMailServer();

      expect(mockRun).toHaveBeenCalledWith(
        'test-agent',
        expect.any(String), // timestamp
        'online',
        'test-machine-id',
        expect.any(String) // process info
      );
    });
  });

  describe('Message Handling', () => {
    let server: any;

    beforeEach(() => {
      const mockGet = jest.fn().mockReturnValue(null);
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValue({ get: mockGet, run: mockRun, all: jest.fn() });

      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();
    });

    test('should send mail successfully', async () => {
      // Mock recipient exists
      mockDb.prepare.mockReturnValueOnce({
        get: jest.fn().mockReturnValue({ name: 'recipient-agent' })
      });
      
      // Mock message insertion
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValueOnce({ run: mockRun });

      const result = await server.handleSendMail({
        recipient: 'recipient-agent',
        subject: 'Test Message',
        body: 'Test body',
        priority: 'normal',
        tags: ['test']
      });

      expect(result.content[0].text).toContain('Message sent successfully');
      expect(mockRun).toHaveBeenCalledWith(
        expect.any(String), // message ID
        'test-agent', // sender
        'recipient-agent',
        'Test Message',
        'Test body',
        'normal',
        '["test"]',
        null, // reply_to
        expect.any(String), // thread_id
        expect.any(String) // timestamp
      );
    });

    test('should fail when recipient does not exist', async () => {
      mockDb.prepare.mockReturnValueOnce({
        get: jest.fn().mockReturnValue(null) // No recipient found
      });

      await expect(server.handleSendMail({
        recipient: 'nonexistent-agent',
        subject: 'Test',
        body: 'Test'
      })).rejects.toThrow("Recipient agent 'nonexistent-agent' not found");
    });

    test('should handle message threading correctly', async () => {
      // Mock recipient exists
      mockDb.prepare.mockReturnValueOnce({
        get: jest.fn().mockReturnValue({ name: 'recipient-agent' })
      });
      
      // Mock thread lookup for reply
      mockDb.prepare.mockReturnValueOnce({
        get: jest.fn().mockReturnValue({ thread_id: 'existing-thread-123' })
      });

      // Mock message insertion
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValueOnce({ run: mockRun });

      await server.handleSendMail({
        recipient: 'recipient-agent',
        subject: 'Re: Test Message',
        body: 'Reply body',
        reply_to: 'original-message-id'
      });

      expect(mockRun).toHaveBeenCalledWith(
        expect.any(String), // message ID
        'test-agent',
        'recipient-agent',
        'Re: Test Message',
        'Reply body',
        'normal',
        '[]',
        'original-message-id',
        'existing-thread-123', // Should use existing thread ID
        expect.any(String)
      );
    });

    test('should check mail and return formatted messages', async () => {
      const testMessages: Message[] = [
        {
          id: 'msg-1',
          sender: 'sender-agent',
          recipient: 'test-agent',
          subject: 'Urgent Task',
          body: 'This is an urgent message that needs immediate attention',
          priority: 'urgent',
          tags: ['task', 'urgent'],
          thread_id: 'thread-1',
          timestamp: new Date().toISOString(),
          read: false,
          archived: false
        },
        {
          id: 'msg-2',
          sender: 'another-agent',
          recipient: 'test-agent',
          subject: 'Normal Update',
          body: 'Just a regular update message',
          priority: 'normal',
          tags: ['update'],
          thread_id: 'thread-2',
          timestamp: new Date().toISOString(),
          read: false,
          archived: false
        }
      ];

      mockDb.prepare.mockReturnValue({
        all: jest.fn().mockReturnValue(testMessages)
      });

      const result = await server.handleCheckMail({
        unread_only: true,
        limit: 10
      });

      expect(result.content[0].text).toContain('Found 2 message(s)');
      expect(result.content[0].text).toContain('🚨'); // Urgent emoji
      expect(result.content[0].text).toContain('📧'); // Normal emoji
      expect(result.content[0].text).toContain('Urgent Task');
      expect(result.content[0].text).toContain('Normal Update');
    });

    test('should return empty message when no mail found', async () => {
      mockDb.prepare.mockReturnValue({
        all: jest.fn().mockReturnValue([])
      });

      const result = await server.handleCheckMail({ unread_only: true });

      expect(result.content[0].text).toBe('📭 No new messages');
    });

    test('should read and mark message as read', async () => {
      const testMessage: Message = {
        id: 'msg-1',
        sender: 'sender-agent',
        recipient: 'test-agent',
        subject: 'Test Message',
        body: 'Test message content',
        priority: 'normal',
        tags: ['test'],
        thread_id: 'thread-1',
        timestamp: new Date().toISOString(),
        read: false,
        archived: false
      };

      const mockGet = jest.fn().mockReturnValue(testMessage);
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      
      mockDb.prepare
        .mockReturnValueOnce({ get: mockGet })  // Get message
        .mockReturnValueOnce({ run: mockRun }); // Mark as read

      const result = await server.handleReadMessage({ message_id: 'msg-1' });

      expect(mockRun).toHaveBeenCalledWith('msg-1');
      expect(result.content[0].text).toContain('Test Message');
      expect(result.content[0].text).toContain('Test message content');
    });

    test('should search messages by content', async () => {
      const searchResults: Message[] = [
        {
          id: 'msg-1',
          sender: 'sender-agent',
          recipient: 'test-agent',
          subject: 'Important Task',
          body: 'This task is important',
          priority: 'high',
          tags: ['task'],
          thread_id: 'thread-1',
          timestamp: new Date().toISOString(),
          read: false,
          archived: false
        }
      ];

      mockDb.prepare.mockReturnValue({
        all: jest.fn().mockReturnValue(searchResults)
      });

      const result = await server.handleSearchMessages({
        query: 'important',
        limit: 20
      });

      expect(result.content[0].text).toContain('Found 1 message(s) matching "important"');
      expect(result.content[0].text).toContain('Important Task');
    });
  });

  describe('Agent Management', () => {
    let server: any;

    beforeEach(() => {
      const mockGet = jest.fn().mockReturnValue(null);
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValue({ get: mockGet, run: mockRun, all: jest.fn() });

      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();
    });

    test('should list all agents', async () => {
      const testAgents: Agent[] = [
        {
          name: 'test-agent',
          last_seen: new Date().toISOString(),
          status: 'online',
          machine_id: 'test-machine-id'
        },
        {
          name: 'other-agent',
          last_seen: new Date(Date.now() - 60000).toISOString(),
          status: 'offline',
          machine_id: 'other-machine-id'
        }
      ];

      mockDb.prepare.mockReturnValue({
        all: jest.fn().mockReturnValue(testAgents)
      });

      const result = await server.handleListAgents({ active_only: false });

      expect(result.content[0].text).toContain('Available agents (2)');
      expect(result.content[0].text).toContain('test-agent');
      expect(result.content[0].text).toContain('(YOU)'); // Current agent indicator
      expect(result.content[0].text).toContain('other-agent');
      expect(result.content[0].text).toContain('🟢'); // Online status
      expect(result.content[0].text).toContain('🔴'); // Offline status
    });

    test('should filter active agents only', async () => {
      const activeAgents: Agent[] = [
        {
          name: 'active-agent',
          last_seen: new Date().toISOString(),
          status: 'online',
          machine_id: 'active-machine-id'
        }
      ];

      mockDb.prepare.mockReturnValue({
        all: jest.fn().mockReturnValue(activeAgents)
      });

      const result = await server.handleListAgents({ active_only: true });

      expect(result.content[0].text).toContain('Available agents (1)');
      expect(result.content[0].text).toContain('active-agent');
    });
  });

  describe('Message Operations', () => {
    let server: any;

    beforeEach(() => {
      const mockGet = jest.fn().mockReturnValue(null);
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValue({ get: mockGet, run: mockRun, all: jest.fn() });

      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();
    });

    test('should mark multiple messages as read', async () => {
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValue({ run: mockRun });

      const result = await server.handleMarkRead({
        message_ids: ['msg-1', 'msg-2', 'msg-3']
      });

      expect(mockRun).toHaveBeenCalledTimes(3);
      expect(result.content[0].text).toBe('✅ Marked 3 message(s) as read');
    });

    test('should archive message', async () => {
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValue({ run: mockRun });

      const result = await server.handleArchiveMessage({
        message_id: 'msg-1'
      });

      expect(mockRun).toHaveBeenCalledWith('msg-1', 'test-agent');
      expect(result.content[0].text).toBe('📦 Message archived successfully');
    });

    test('should delete message permanently', async () => {
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValue({ run: mockRun });

      const result = await server.handleDeleteMessage({
        message_id: 'msg-1'
      });

      expect(mockRun).toHaveBeenCalledWith('msg-1', 'test-agent');
      expect(result.content[0].text).toBe('🗑️ Message deleted permanently');
    });

    test('should get thread messages', async () => {
      const threadMessages: Message[] = [
        {
          id: 'msg-1',
          sender: 'agent-a',
          recipient: 'test-agent',
          subject: 'Original Message',
          body: 'Start of conversation',
          priority: 'normal',
          tags: [],
          thread_id: 'thread-1',
          timestamp: new Date().toISOString(),
          read: true,
          archived: false
        },
        {
          id: 'msg-2',
          sender: 'test-agent',
          recipient: 'agent-a',
          subject: 'Re: Original Message',
          body: 'Reply to conversation',
          priority: 'normal',
          tags: [],
          reply_to: 'msg-1',
          thread_id: 'thread-1',
          timestamp: new Date().toISOString(),
          read: true,
          archived: false
        }
      ];

      mockDb.prepare.mockReturnValue({
        all: jest.fn().mockReturnValue(threadMessages)
      });

      const result = await server.handleGetThread({
        thread_id: 'thread-1'
      });

      expect(result.content[0].text).toContain('Thread thread-1 (2 messages)');
      expect(result.content[0].text).toContain('Original Message');
      expect(result.content[0].text).toContain('Re: Original Message');
      expect(result.content[0].text).toContain('#1');
      expect(result.content[0].text).toContain('#2');
    });

    test('should get mailbox statistics', async () => {
      const stats = {
        total_messages: 10,
        unread_messages: 3,
        urgent_messages: 1,
        agents_count: 5,
        threads_count: 7
      };

      const mockGet = jest.fn()
        .mockReturnValueOnce({ count: stats.total_messages })
        .mockReturnValueOnce({ count: stats.unread_messages })
        .mockReturnValueOnce({ count: stats.urgent_messages })
        .mockReturnValueOnce({ count: stats.agents_count })
        .mockReturnValueOnce({ count: stats.threads_count });

      mockDb.prepare.mockReturnValue({ get: mockGet });

      const result = await server.handleGetMailboxStats({});

      expect(result.content[0].text).toContain('Mailbox Statistics for test-agent');
      expect(result.content[0].text).toContain('Total messages: 10');
      expect(result.content[0].text).toContain('Unread messages: 3');
      expect(result.content[0].text).toContain('Urgent unread: 1');
      expect(result.content[0].text).toContain('Active agents: 5');
      expect(result.content[0].text).toContain('Message threads: 7');
    });
  });

  describe('Error Handling', () => {
    let server: any;

    beforeEach(() => {
      const mockGet = jest.fn().mockReturnValue(null);
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValue({ get: mockGet, run: mockRun, all: jest.fn() });

      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();
    });

    test('should handle database errors gracefully', async () => {
      mockDb.prepare.mockImplementation(() => {
        throw new Error('Database connection failed');
      });

      await expect(server.handleCheckMail({})).rejects.toThrow('Database connection failed');
    });

    test('should handle message not found errors', async () => {
      mockDb.prepare.mockReturnValue({
        get: jest.fn().mockReturnValue(null)
      });

      await expect(server.handleReadMessage({
        message_id: 'nonexistent-msg'
      })).rejects.toThrow('Message nonexistent-msg not found or not addressed to you');
    });

    test('should handle failed message operations', async () => {
      mockDb.prepare.mockReturnValue({
        run: jest.fn().mockReturnValue({ changes: 0 })
      });

      await expect(server.handleDeleteMessage({
        message_id: 'msg-1'
      })).rejects.toThrow('Message not found or not addressed to you');
    });
  });

  describe('MCP Tool Registration', () => {
    let server: any;

    beforeEach(() => {
      const mockGet = jest.fn().mockReturnValue(null);
      const mockRun = jest.fn().mockReturnValue({ changes: 1 });
      mockDb.prepare.mockReturnValue({ get: mockGet, run: mockRun, all: jest.fn() });

      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();
    });

    test('should register all expected MCP tools', () => {
      const tools = server.getTools();
      
      const expectedTools = [
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

      const toolNames = tools.map((tool: any) => tool.name);
      
      expectedTools.forEach(expectedTool => {
        expect(toolNames).toContain(expectedTool);
      });
    });

    test('should have proper tool schemas', () => {
      const tools = server.getTools();
      const sendMailTool = tools.find((tool: any) => tool.name === 'send_mail');
      
      expect(sendMailTool).toBeDefined();
      expect(sendMailTool.description).toContain('Send a mail message');
      expect(sendMailTool.inputSchema.properties).toHaveProperty('recipient');
      expect(sendMailTool.inputSchema.properties).toHaveProperty('subject');
      expect(sendMailTool.inputSchema.properties).toHaveProperty('body');
      expect(sendMailTool.inputSchema.required).toEqual(['recipient', 'subject', 'body']);
    });
  });

  describe('UUID and Timestamp Validation', () => {
    test('should generate valid UUIDs for messages', async () => {
      const uuid = uuidv4();
      expect(uuid).toBeValidUUID();
    });

    test('should generate timestamps within reasonable range', () => {
      const start = new Date();
      const timestamp = new Date().toISOString();
      const end = new Date();
      
      expect(new Date(timestamp)).toBeWithinTimeRange(start, end);
    });
  });
});
