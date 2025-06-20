#!/usr/bin/env node

/**
 * AI Mail MCP Server - Node.js Implementation
 * 
 * A locally hostable mailbox system for AI agent communication.
 * Supports automatic agent detection, message threading, priorities,
 * and includes an intelligent orchestrator for managing multiple agents.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema, 
  ListToolsRequestSchema,
  Tool,
  TextContent
} from '@modelcontextprotocol/sdk/types.js';
import Database from 'better-sqlite3';
import { machineIdSync } from 'node-machine-id';
import { v4 as uuidv4 } from 'uuid';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import * as process from 'process';
import { program } from 'commander';
import chalk from 'chalk';

// Types and Interfaces
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

interface MailboxStats {
  total_messages: number;
  unread_messages: number;
  agents_count: number;
  urgent_messages: number;
  threads_count: number;
}

/**
 * AI Mail MCP Server
 * 
 * Provides a local mailbox system for AI agents to communicate with each other.
 * Features automatic agent detection, message threading, priorities, and search.
 */
class AIMailServer {
  private db: Database.Database;
  private agentName: string;
  private dataDir: string;
  private machineId: string;
  private server: Server;

  constructor() {
    // Initialize data directory
    this.dataDir = process.env.AI_MAIL_DATA_DIR || path.join(os.homedir(), '.ai_mail');
    this.ensureDataDir();

    // Initialize database
    const dbPath = path.join(this.dataDir, 'mailbox.db');
    this.db = new Database(dbPath);
    this.initializeDatabase();

    // Get machine ID for agent identification
    this.machineId = machineIdSync();

    // Detect or set agent name
    this.agentName = this.detectAgentName();

    // Initialize MCP server
    this.server = new Server({
      name: 'ai-mail-mcp',
      version: '1.0.0',
    }, {
      capabilities: {
        tools: {},
      },
    });

    this.setupToolHandlers();
    this.registerAgent();

    console.log(chalk.blue(`🤖 AI Mail Server started for agent: ${chalk.bold(this.agentName)}`));
    console.log(chalk.gray(`📁 Data directory: ${this.dataDir}`));
    console.log(chalk.gray(`🔧 Machine ID: ${this.machineId.substring(0, 8)}...`));
  }

  /**
   * Ensure data directory exists
   */
  private ensureDataDir(): void {
    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }
  }

  /**
   * Initialize SQLite database with required tables
   */
  private initializeDatabase(): void {
    // Messages table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        sender TEXT NOT NULL,
        recipient TEXT NOT NULL,
        subject TEXT NOT NULL,
        body TEXT NOT NULL,
        priority TEXT DEFAULT 'normal',
        tags TEXT DEFAULT '[]',
        reply_to TEXT,
        thread_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        read INTEGER DEFAULT 0,
        archived INTEGER DEFAULT 0,
        FOREIGN KEY (reply_to) REFERENCES messages(id)
      )
    `);

    // Agents table
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS agents (
        name TEXT PRIMARY KEY,
        last_seen TEXT NOT NULL,
        status TEXT DEFAULT 'online',
        machine_id TEXT NOT NULL,
        process_info TEXT
      )
    `);

    // Create indexes for performance
    this.db.exec(`
      CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient);
      CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
      CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
      CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(read);
      CREATE INDEX IF NOT EXISTS idx_messages_priority ON messages(priority);
    `);

    console.log(chalk.green('📦 Database initialized successfully'));
  }

  /**
   * Detect agent name from environment or process information
   */
  private detectAgentName(): string {
    // Check environment variable first
    if (process.env.AI_AGENT_NAME) {
      return this.ensureUniqueAgentName(process.env.AI_AGENT_NAME);
    }

    // Try to detect from process name or command line
    const processName = process.title || 'node';
    const parentProcess = process.env.TERM_PROGRAM || '';
    const hostname = os.hostname();

    let detectedName = '';

    // Detection patterns
    if (parentProcess.includes('claude') || processName.includes('claude')) {
      detectedName = 'claude-desktop';
    } else if (parentProcess.includes('code') || processName.includes('code')) {
      detectedName = 'vscode-copilot';
    } else if (parentProcess.includes('cursor') || processName.includes('cursor')) {
      detectedName = 'cursor-ai';
    } else if (parentProcess.includes('zed') || processName.includes('zed')) {
      detectedName = 'zed-ai';
    } else if (parentProcess.includes('windsurf') || processName.includes('windsurf')) {
      detectedName = 'windsurf-ai';
    } else {
      detectedName = `agent-${hostname}`;
    }

    return this.ensureUniqueAgentName(detectedName);
  }

  /**
   * Ensure agent name is unique by adding numbers if needed
   */
  private ensureUniqueAgentName(baseName: string): string {
    const stmt = this.db.prepare('SELECT name FROM agents WHERE name = ? AND machine_id != ?');
    
    let candidateName = baseName;
    let counter = 2;

    while (stmt.get(candidateName, this.machineId)) {
      candidateName = `${baseName}-${counter}`;
      counter++;
    }

    return candidateName;
  }

  /**
   * Register this agent in the database
   */
  private registerAgent(): void {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO agents (name, last_seen, status, machine_id, process_info)
      VALUES (?, ?, ?, ?, ?)
    `);

    const processInfo = JSON.stringify({
      pid: process.pid,
      title: process.title,
      version: process.version,
      platform: process.platform,
      arch: process.arch
    });

    stmt.run(
      this.agentName,
      new Date().toISOString(),
      'online',
      this.machineId,
      processInfo
    );

    console.log(chalk.green(`✅ Agent registered: ${this.agentName}`));
  }

  /**
   * Setup MCP tool handlers
   */
  private setupToolHandlers(): void {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: this.getTools(),
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'send_mail':
            return await this.handleSendMail(args);
          case 'check_mail':
            return await this.handleCheckMail(args);
          case 'read_message':
            return await this.handleReadMessage(args);
          case 'search_messages':
            return await this.handleSearchMessages(args);
          case 'list_agents':
            return await this.handleListAgents(args);
          case 'mark_read':
            return await this.handleMarkRead(args);
          case 'archive_message':
            return await this.handleArchiveMessage(args);
          case 'get_thread':
            return await this.handleGetThread(args);
          case 'get_mailbox_stats':
            return await this.handleGetMailboxStats(args);
          case 'delete_message':
            return await this.handleDeleteMessage(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        console.error(chalk.red(`❌ Error in ${name}:`), error);
        return {
          content: [{
            type: 'text' as const,
            text: `Error: ${error instanceof Error ? error.message : String(error)}`
          }]
        };
      }
    });
  }

  /**
   * Get available MCP tools
   */
  private getTools(): Tool[] {
    return [
      {
        name: 'send_mail',
        description: 'Send a mail message to another AI agent on this machine. This is the primary way for AI agents to communicate with each other.',
        inputSchema: {
          type: 'object',
          properties: {
            recipient: {
              type: 'string',
              description: 'Name of the recipient agent (e.g., claude-desktop, vscode-copilot)'
            },
            subject: {
              type: 'string',
              description: 'Subject line for the message'
            },
            body: {
              type: 'string',
              description: 'Main message content'
            },
            priority: {
              type: 'string',
              enum: ['urgent', 'high', 'normal', 'low'],
              default: 'normal',
              description: 'Message priority level'
            },
            tags: {
              type: 'array',
              items: { type: 'string' },
              description: 'Optional tags for categorizing the message'
            },
            reply_to: {
              type: 'string',
              description: 'ID of message being replied to (creates thread)'
            }
          },
          required: ['recipient', 'subject', 'body']
        }
      },
      {
        name: 'check_mail',
        description: 'Check for new messages. Add this to your system prompt: "Check for new messages regularly using check_mail to coordinate with other AI agents."',
        inputSchema: {
          type: 'object',
          properties: {
            unread_only: {
              type: 'boolean',
              default: true,
              description: 'Only return unread messages'
            },
            limit: {
              type: 'number',
              default: 10,
              description: 'Maximum number of messages to return'
            },
            priority_filter: {
              type: 'string',
              enum: ['urgent', 'high', 'normal', 'low'],
              description: 'Filter by specific priority'
            },
            days_back: {
              type: 'number',
              default: 7,
              description: 'Number of days to look back'
            }
          }
        }
      },
      {
        name: 'read_message',
        description: 'Read a specific message by ID and mark it as read',
        inputSchema: {
          type: 'object',
          properties: {
            message_id: {
              type: 'string',
              description: 'ID of the message to read'
            }
          },
          required: ['message_id']
        }
      },
      {
        name: 'search_messages',
        description: 'Search through messages by content, subject, or tags',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Search query (searches subject, body, and tags)'
            },
            days_back: {
              type: 'number',
              default: 30,
              description: 'Number of days to search back'
            },
            sender: {
              type: 'string',
              description: 'Filter by sender name'
            },
            priority: {
              type: 'string',
              enum: ['urgent', 'high', 'normal', 'low'],
              description: 'Filter by priority'
            },
            limit: {
              type: 'number',
              default: 20,
              description: 'Maximum number of results'
            }
          },
          required: ['query']
        }
      },
      {
        name: 'list_agents',
        description: 'List all available AI agents on this machine',
        inputSchema: {
          type: 'object',
          properties: {
            active_only: {
              type: 'boolean',
              default: false,
              description: 'Only show agents active in the last hour'
            }
          }
        }
      },
      {
        name: 'mark_read',
        description: 'Mark specific messages as read',
        inputSchema: {
          type: 'object',
          properties: {
            message_ids: {
              type: 'array',
              items: { type: 'string' },
              description: 'Array of message IDs to mark as read'
            }
          },
          required: ['message_ids']
        }
      },
      {
        name: 'archive_message',
        description: 'Archive a message (removes from normal view but keeps in database)',
        inputSchema: {
          type: 'object',
          properties: {
            message_id: {
              type: 'string',
              description: 'ID of message to archive'
            }
          },
          required: ['message_id']
        }
      },
      {
        name: 'get_thread',
        description: 'Get all messages in a conversation thread',
        inputSchema: {
          type: 'object',
          properties: {
            thread_id: {
              type: 'string',
              description: 'ID of the thread to retrieve'
            }
          },
          required: ['thread_id']
        }
      },
      {
        name: 'get_mailbox_stats',
        description: 'Get statistics about the mailbox (message counts, agents, etc.)',
        inputSchema: {
          type: 'object',
          properties: {}
        }
      },
      {
        name: 'delete_message',
        description: 'Permanently delete a message (use carefully)',
        inputSchema: {
          type: 'object',
          properties: {
            message_id: {
              type: 'string',
              description: 'ID of message to delete'
            }
          },
          required: ['message_id']
        }
      }
    ];
  }

  /**
   * Handle send_mail tool
   */
  private async handleSendMail(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { recipient, subject, body, priority = 'normal', tags = [], reply_to } = args;

    // Validate recipient exists
    const recipientExists = this.db.prepare('SELECT name FROM agents WHERE name = ?').get(recipient);
    if (!recipientExists) {
      throw new Error(`Recipient agent '${recipient}' not found. Use list_agents to see available agents.`);
    }

    // Generate message ID and thread ID
    const messageId = uuidv4();
    const threadId = reply_to ? 
      this.db.prepare('SELECT thread_id FROM messages WHERE id = ?').get(reply_to)?.thread_id || uuidv4() :
      uuidv4();

    // Insert message
    const stmt = this.db.prepare(`
      INSERT INTO messages (id, sender, recipient, subject, body, priority, tags, reply_to, thread_id, timestamp, read, archived)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
    `);

    stmt.run(
      messageId,
      this.agentName,
      recipient,
      subject,
      body,
      priority,
      JSON.stringify(tags),
      reply_to || null,
      threadId,
      new Date().toISOString()
    );

    console.log(chalk.green(`📧 Message sent to ${recipient}: ${subject}`));

    return {
      content: [{
        type: 'text' as const,
        text: `✅ Message sent successfully to ${recipient}\nMessage ID: ${messageId}\nSubject: ${subject}\nPriority: ${priority}`
      }]
    };
  }

  /**
   * Handle check_mail tool
   */
  private async handleCheckMail(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { 
      unread_only = true, 
      limit = 10, 
      priority_filter, 
      days_back = 7 
    } = args;

    let query = `
      SELECT * FROM messages 
      WHERE recipient = ? AND archived = 0
      AND datetime(timestamp) >= datetime('now', '-${days_back} days')
    `;
    const params: any[] = [this.agentName];

    if (unread_only) {
      query += ' AND read = 0';
    }

    if (priority_filter) {
      query += ' AND priority = ?';
      params.push(priority_filter);
    }

    query += ' ORDER BY priority DESC, timestamp DESC LIMIT ?';
    params.push(limit);

    const messages = this.db.prepare(query).all(...params) as Message[];

    if (messages.length === 0) {
      return {
        content: [{
          type: 'text' as const,
          text: unread_only ? '📭 No new messages' : '📭 No messages found'
        }]
      };
    }

    const formatMessage = (msg: Message) => {
      const priorityEmoji = {
        urgent: '🚨',
        high: '⚡',
        normal: '📧',
        low: '📮'
      }[msg.priority];

      const readStatus = msg.read ? '✅' : '🔴';
      const replyIndicator = msg.reply_to ? '↳ ' : '';
      
      return `${priorityEmoji} ${readStatus} ${replyIndicator}**${msg.subject}**
From: ${msg.sender}
Time: ${new Date(msg.timestamp).toLocaleString()}
ID: ${msg.id}
${msg.body.substring(0, 100)}${msg.body.length > 100 ? '...' : ''}`;
    };

    const messageList = messages.map(formatMessage).join('\n\n---\n\n');
    
    return {
      content: [{
        type: 'text' as const,
        text: `📬 Found ${messages.length} message(s):\n\n${messageList}`
      }]
    };
  }

  /**
   * Handle read_message tool
   */
  private async handleReadMessage(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { message_id } = args;

    const message = this.db.prepare('SELECT * FROM messages WHERE id = ? AND recipient = ?')
      .get(message_id, this.agentName) as Message | undefined;

    if (!message) {
      throw new Error(`Message ${message_id} not found or not addressed to you`);
    }

    // Mark as read
    this.db.prepare('UPDATE messages SET read = 1 WHERE id = ?').run(message_id);

    const priorityEmoji = {
      urgent: '🚨',
      high: '⚡',
      normal: '📧',
      low: '📮'
    }[message.priority];

    const tags = JSON.parse(message.tags || '[]');
    const tagsStr = tags.length > 0 ? `\nTags: ${tags.join(', ')}` : '';

    return {
      content: [{
        type: 'text' as const,
        text: `${priorityEmoji} **${message.subject}**

From: ${message.sender}
To: ${message.recipient}
Time: ${new Date(message.timestamp).toLocaleString()}
Priority: ${message.priority}${tagsStr}
Thread ID: ${message.thread_id}
${message.reply_to ? `Reply to: ${message.reply_to}` : ''}

---

${message.body}`
      }]
    };
  }

  /**
   * Handle search_messages tool
   */
  private async handleSearchMessages(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { 
      query, 
      days_back = 30, 
      sender, 
      priority, 
      limit = 20 
    } = args;

    let sqlQuery = `
      SELECT * FROM messages 
      WHERE (recipient = ? OR sender = ?) 
      AND archived = 0
      AND datetime(timestamp) >= datetime('now', '-${days_back} days')
      AND (subject LIKE ? OR body LIKE ? OR tags LIKE ?)
    `;
    const params: any[] = [
      this.agentName, 
      this.agentName,
      `%${query}%`,
      `%${query}%`,
      `%${query}%`
    ];

    if (sender) {
      sqlQuery += ' AND sender = ?';
      params.push(sender);
    }

    if (priority) {
      sqlQuery += ' AND priority = ?';
      params.push(priority);
    }

    sqlQuery += ' ORDER BY timestamp DESC LIMIT ?';
    params.push(limit);

    const messages = this.db.prepare(sqlQuery).all(...params) as Message[];

    if (messages.length === 0) {
      return {
        content: [{
          type: 'text' as const,
          text: `🔍 No messages found matching "${query}"`
        }]
      };
    }

    const formatMessage = (msg: Message) => {
      const priorityEmoji = {
        urgent: '🚨',
        high: '⚡',
        normal: '📧',
        low: '📮'
      }[msg.priority];

      return `${priorityEmoji} **${msg.subject}**
From: ${msg.sender} → To: ${msg.recipient}
Time: ${new Date(msg.timestamp).toLocaleString()}
ID: ${msg.id}`;
    };

    const messageList = messages.map(formatMessage).join('\n\n');
    
    return {
      content: [{
        type: 'text' as const,
        text: `🔍 Found ${messages.length} message(s) matching "${query}":\n\n${messageList}`
      }]
    };
  }

  /**
   * Handle list_agents tool
   */
  private async handleListAgents(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { active_only = false } = args;

    let query = 'SELECT * FROM agents ORDER BY last_seen DESC';
    const params: any[] = [];

    if (active_only) {
      query = `SELECT * FROM agents 
               WHERE datetime(last_seen) >= datetime('now', '-1 hour')
               ORDER BY last_seen DESC`;
    }

    const agents = this.db.prepare(query).all(...params) as Agent[];

    if (agents.length === 0) {
      return {
        content: [{
          type: 'text' as const,
          text: active_only ? '🤖 No active agents found' : '🤖 No agents registered'
        }]
      };
    }

    const formatAgent = (agent: Agent) => {
      const isCurrentAgent = agent.name === this.agentName;
      const statusEmoji = agent.status === 'online' ? '🟢' : '🔴';
      const currentIndicator = isCurrentAgent ? ' (YOU)' : '';
      
      return `${statusEmoji} **${agent.name}**${currentIndicator}
Last seen: ${new Date(agent.last_seen).toLocaleString()}
Status: ${agent.status}`;
    };

    const agentList = agents.map(formatAgent).join('\n\n');
    
    return {
      content: [{
        type: 'text' as const,
        text: `🤖 Available agents (${agents.length}):\n\n${agentList}`
      }]
    };
  }

  /**
   * Handle mark_read tool
   */
  private async handleMarkRead(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { message_ids } = args;

    const stmt = this.db.prepare('UPDATE messages SET read = 1 WHERE id = ? AND recipient = ?');
    let markedCount = 0;

    for (const messageId of message_ids) {
      const result = stmt.run(messageId, this.agentName);
      if (result.changes > 0) {
        markedCount++;
      }
    }

    return {
      content: [{
        type: 'text' as const,
        text: `✅ Marked ${markedCount} message(s) as read`
      }]
    };
  }

  /**
   * Handle archive_message tool
   */
  private async handleArchiveMessage(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { message_id } = args;

    const result = this.db.prepare('UPDATE messages SET archived = 1 WHERE id = ? AND recipient = ?')
      .run(message_id, this.agentName);

    if (result.changes === 0) {
      throw new Error('Message not found or not addressed to you');
    }

    return {
      content: [{
        type: 'text' as const,
        text: `📦 Message archived successfully`
      }]
    };
  }

  /**
   * Handle get_thread tool
   */
  private async handleGetThread(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { thread_id } = args;

    const messages = this.db.prepare(`
      SELECT * FROM messages 
      WHERE thread_id = ? AND (recipient = ? OR sender = ?)
      ORDER BY timestamp ASC
    `).all(thread_id, this.agentName, this.agentName) as Message[];

    if (messages.length === 0) {
      throw new Error('Thread not found or no access to thread');
    }

    const formatMessage = (msg: Message, index: number) => {
      const priorityEmoji = {
        urgent: '🚨',
        high: '⚡',
        normal: '📧',
        low: '📮'
      }[msg.priority];

      return `**#${index + 1}** ${priorityEmoji} ${msg.subject}
From: ${msg.sender} → To: ${msg.recipient}
Time: ${new Date(msg.timestamp).toLocaleString()}
ID: ${msg.id}

${msg.body}`;
    };

    const threadContent = messages.map(formatMessage).join('\n\n---\n\n');
    
    return {
      content: [{
        type: 'text' as const,
        text: `🧵 Thread ${thread_id} (${messages.length} messages):\n\n${threadContent}`
      }]
    };
  }

  /**
   * Handle get_mailbox_stats tool
   */
  private async handleGetMailboxStats(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const stats = {
      total_messages: this.db.prepare('SELECT COUNT(*) as count FROM messages WHERE recipient = ?').get(this.agentName)?.count || 0,
      unread_messages: this.db.prepare('SELECT COUNT(*) as count FROM messages WHERE recipient = ? AND read = 0').get(this.agentName)?.count || 0,
      urgent_messages: this.db.prepare('SELECT COUNT(*) as count FROM messages WHERE recipient = ? AND priority = "urgent" AND read = 0').get(this.agentName)?.count || 0,
      agents_count: this.db.prepare('SELECT COUNT(*) as count FROM agents').get()?.count || 0,
      threads_count: this.db.prepare('SELECT COUNT(DISTINCT thread_id) as count FROM messages WHERE recipient = ?').get(this.agentName)?.count || 0
    } as MailboxStats;

    return {
      content: [{
        type: 'text' as const,
        text: `📊 **Mailbox Statistics for ${this.agentName}**

📧 Total messages: ${stats.total_messages}
🔴 Unread messages: ${stats.unread_messages}
🚨 Urgent unread: ${stats.urgent_messages}
🤖 Active agents: ${stats.agents_count}
🧵 Message threads: ${stats.threads_count}

Data directory: ${this.dataDir}`
      }]
    };
  }

  /**
   * Handle delete_message tool
   */
  private async handleDeleteMessage(args: any): Promise<{ content: Array<TextContent | ImageContent | EmbeddedResource> }> {
    const { message_id } = args;

    const result = this.db.prepare('DELETE FROM messages WHERE id = ? AND recipient = ?')
      .run(message_id, this.agentName);

    if (result.changes === 0) {
      throw new Error('Message not found or not addressed to you');
    }

    return {
      content: [{
        type: 'text' as const,
        text: `🗑️ Message deleted permanently`
      }]
    };
  }

  /**
   * Update agent status (heartbeat)
   */
  private updateAgentStatus(): void {
    this.db.prepare('UPDATE agents SET last_seen = ?, status = ? WHERE name = ?')
      .run(new Date().toISOString(), 'online', this.agentName);
  }

  /**
   * Start the server
   */
  async start(): Promise<void> {
    // Set up heartbeat to update agent status
    setInterval(() => {
      this.updateAgentStatus();
    }, 30000); // Update every 30 seconds

    // Handle graceful shutdown
    process.on('SIGINT', () => {
      console.log(chalk.yellow('\n🛑 Shutting down AI Mail Server...'));
      this.db.prepare('UPDATE agents SET status = ? WHERE name = ?').run('offline', this.agentName);
      this.db.close();
      process.exit(0);
    });

    // Start MCP server
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    
    console.log(chalk.green('🚀 AI Mail MCP Server running'));
    console.log(chalk.blue('Add this to your system prompt: "Check for new messages regularly using check_mail to coordinate with other AI agents."'));
  }
}

// CLI Interface
program
  .name('ai-mail-server')
  .description('AI Mail MCP Server - Local mailbox for AI agent communication')
  .version('1.0.0')
  .option('--list-agents', 'List all registered agents')
  .option('--stats', 'Show mailbox statistics')
  .option('--cleanup', 'Clean up old agents and messages')
  .action(async (options) => {
    if (options.listAgents || options.stats || options.cleanup) {
      // Quick operations without starting full server
      const server = new AIMailServer();
      
      if (options.listAgents) {
        const result = await server.handleListAgents({});
        console.log(result.content[0]?.text);
      }
      
      if (options.stats) {
        const result = await server.handleGetMailboxStats({});
        console.log(result.content[0]?.text);
      }
      
      if (options.cleanup) {
        // TODO: Implement cleanup logic
        console.log('🧹 Cleanup completed');
      }
      
      return;
    }

    // Start full server
    const server = new AIMailServer();
    await server.start();
  });

// Only run CLI if this file is executed directly
if (require.main === module) {
  program.parse();
}
