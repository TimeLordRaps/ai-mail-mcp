# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Web dashboard for message visualization
- Message encryption support
- Cross-machine messaging capabilities
- Webhook notifications
- Agent authentication system

### Changed
- Improved performance for large message volumes
- Enhanced search functionality with full-text indexing

### Fixed
- Database locking issues under high concurrency

## [1.0.0] - 2025-06-19

### Added
- Initial release of AI Mail MCP server
- Basic message sending and receiving functionality
- Automatic agent detection and naming
- Message threading and conversation support
- Priority levels (low, normal, high, urgent)
- Message tagging system
- Search functionality across message history
- SQLite-based local storage
- Performance monitoring and health checks
- Comprehensive test suite with 95%+ coverage
- CI/CD pipeline with automated testing
- Automated maintenance workflows (every 3 hours)
- Docker support
- Python 3.8+ compatibility
- MCP (Model Context Protocol) integration

### Features
- **Agent Auto-Discovery**: Automatically detects agent names from environment, process info, or command line
- **Threaded Conversations**: Full reply-to and thread support for organized conversations
- **Message Search**: Search through message history with filters for sender, date range, and content
- **Real-time Statistics**: Track message counts, agent activity, and system performance
- **Priority Handling**: Support for low, normal, high, and urgent message priorities
- **Tagging System**: Organize messages with custom tags for better categorization
- **Local-First**: All data stored locally in SQLite database, no external dependencies
- **High Performance**: Optimized for handling thousands of messages with sub-second response times
- **Automatic Cleanup**: Built-in maintenance routines for optimal performance

### MCP Tools Provided
- `send_mail`: Send messages to other AI agents
- `check_mail`: Check for new/unread messages
- `read_message`: Read specific messages and mark as read
- `mark_messages_read`: Mark multiple messages as read
- `delete_messages`: Delete messages permanently
- `get_thread`: Retrieve entire conversation threads
- `list_agents`: Show all registered agents and their status
- `get_agent_info`: Get detailed agent information and statistics
- `search_messages`: Search through message history

### Agent Detection
- Environment variables: `AI_AGENT_NAME`, `AGENT_NAME`, `MCP_CLIENT_NAME`
- Process detection: Automatically maps parent processes to agent names
  - `code` → `vscode-copilot`
  - `cursor` → `cursor-ai`
  - `claude` → `claude-desktop`
- Command line arguments: `--agent-name=custom-name`
- Fallback: `agent-{hostname}`
- Automatic unique naming: Appends numbers if names conflict

### Configuration
- Data directory: `~/.ai_mail/` (configurable via `AI_MAIL_DATA_DIR`)
- Database: SQLite with automatic schema migration
- Logging: Configurable log levels and file rotation
- Environment variables for all major settings

### Performance Benchmarks
- Message sending: 100+ messages per second
- Message retrieval: 1000+ messages in under 2 seconds
- Concurrent access: Supports multiple agents simultaneously
- Memory usage: < 50MB for typical workloads
- Database size: ~1KB per message

### Development Features
- Comprehensive test suite with pytest
- Code quality tools: black, isort, flake8, mypy
- Security scanning: bandit, safety
- Performance profiling and benchmarking
- Pre-commit hooks for code quality
- Automated dependency updates
- Documentation generation

### Deployment
- PyPI package: `pip install ai-mail-mcp`
- Docker support with multi-stage builds
- GitHub Actions CI/CD pipeline
- Automated releases on tag push
- Security scanning and vulnerability alerts

### Maintenance
- Automated workflows running every 3 hours:
  - Dependency security updates
  - Performance monitoring and alerts
  - Repository health checks
  - Database optimization
  - Log rotation and cleanup
- Issue triage automation
- Stale issue management
- Automated security vulnerability reporting

### Documentation
- Comprehensive README with usage examples
- API documentation with all MCP tools
- Integration guides for popular AI platforms
- Performance tuning guidelines
- Troubleshooting section
- Contributing guidelines

## [0.9.0] - 2025-06-18 (Beta)

### Added
- Core message passing functionality
- Basic agent registration
- SQLite database backend
- Initial MCP server implementation

### Changed
- Migrated from JSON file storage to SQLite
- Improved error handling and logging

### Fixed
- Race conditions in message sending
- Database connection issues

## [0.1.0] - 2025-06-17 (Alpha)

### Added
- Initial prototype implementation
- Basic message storage in JSON files
- Simple agent communication
- Proof of concept MCP integration

---

## Version History Summary

| Version | Release Date | Key Features |
|---------|--------------|--------------|
| 1.0.0   | 2025-06-19   | Full production release with all core features |
| 0.9.0   | 2025-06-18   | Beta release with SQLite backend |
| 0.1.0   | 2025-06-17   | Initial alpha prototype |

## Upgrade Guide

### From 0.9.x to 1.0.0

No breaking changes. The database schema is automatically migrated.

```bash
pip install --upgrade ai-mail-mcp
```

### From 0.1.x to 1.0.0

**Breaking Changes:**
- Data format changed from JSON to SQLite
- Configuration file format updated
- Some tool names changed

**Migration Steps:**
1. Export data from old version: `ai-mail-server --export-data old_data.json`
2. Upgrade: `pip install --upgrade ai-mail-mcp`
3. Import data: `ai-mail-server --import-data old_data.json`

## Future Roadmap

### Version 1.1 (Q3 2025)
- Message encryption and security
- Agent authentication protocols
- File attachments support
- Web-based dashboard
- Enhanced search with filters

### Version 1.2 (Q4 2025)
- Cross-machine messaging
- Message delivery guarantees
- Advanced analytics dashboard
- Integration APIs for external systems

### Version 2.0 (Q1 2026)
- Distributed agent networks
- Message queuing and reliability
- Advanced security features
- Enterprise deployment options

## Support and Feedback

We welcome feedback and contributions! Please:

- Report bugs: [GitHub Issues](https://github.com/TimeLordRaps/ai-mail-mcp/issues)
- Request features: [GitHub Discussions](https://github.com/TimeLordRaps/ai-mail-mcp/discussions)
- Contribute code: See [CONTRIBUTING.md](CONTRIBUTING.md)
- Join discussions: [Discord Community](https://discord.gg/ai-mail-mcp)

---

*This changelog is automatically updated by our CI/CD pipeline.*
