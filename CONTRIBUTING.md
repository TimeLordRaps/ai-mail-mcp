# Contributing to AI Mail MCP 🤝

Thank you for your interest in contributing to AI Mail MCP! This guide will help you get started with contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Issue Guidelines](#issue-guidelines)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Code Style](#code-style)
- [Documentation](#documentation)
- [Release Process](#release-process)
- [Community](#community)

## 📜 Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code. Please report unacceptable behavior to [timelordraps@example.com](mailto:timelordraps@example.com).

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of:
- Age, body size, disability, ethnicity, gender identity and expression
- Level of experience, nationality, personal appearance, race, religion
- Sexual identity and orientation

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of MCP (Model Context Protocol)
- Familiarity with SQLite and async Python

### First Contribution

1. **Find an Issue**: Look for issues labeled `good first issue` or `help wanted`
2. **Ask Questions**: Don't hesitate to ask for clarification on issues
3. **Start Small**: Begin with documentation fixes or small feature additions
4. **Learn the Codebase**: Read through the existing code to understand the architecture

## 🛠️ Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ai-mail-mcp.git
cd ai-mail-mcp

# Add the original repository as upstream
git remote add upstream https://github.com/TimeLordRaps/ai-mail-mcp.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

### 3. Verify Setup

```bash
# Run tests to ensure everything works
pytest

# Run linting
flake8 src tests
black --check src tests
isort --check-only src tests
mypy src

# Start the server to test basic functionality
python -m ai_mail_mcp.server
```

## ✏️ Making Changes

### 1. Create a Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
# or for bug fixes:
git checkout -b fix/issue-description
```

### 2. Development Workflow

```bash
# Make your changes
# Edit files, add features, fix bugs

# Add tests for your changes
# Tests should be in tests/ directory

# Run tests frequently
pytest tests/

# Run code quality checks
pre-commit run --all-files
```

### 3. Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Format: <type>[optional scope]: <description>
git commit -m "feat: add message encryption support"
git commit -m "fix: resolve database locking issue"
git commit -m "docs: update installation instructions"
git commit -m "test: add performance benchmarks"
```

**Commit Types:**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_mailbox.py

# Run with coverage
pytest --cov=ai_mail_mcp --cov-report=html

# Run performance tests (slower)
pytest -m slow

# Run without slow tests
pytest -m "not slow"
```

### Writing Tests

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **Performance Tests**: Benchmark critical operations
- **End-to-End Tests**: Test complete workflows

```python
# Example test structure
def test_feature_description():
    """Test that the feature works as expected."""
    # Arrange
    setup_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

### Test Requirements

- All new features must have tests
- Bug fixes must include regression tests
- Maintain minimum 90% test coverage
- Performance tests for critical paths

## 📤 Submitting Changes

### 1. Pre-Submission Checklist

- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`black`, `isort`)
- [ ] No linting errors (`flake8`, `mypy`)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (for significant changes)
- [ ] Commit messages follow conventions

### 2. Push Changes

```bash
# Push your branch to your fork
git push origin feature/your-feature-name
```

### 3. Create Pull Request

1. Go to GitHub and create a Pull Request
2. Use the Pull Request template
3. Link related issues
4. Add reviewers if you know who should review

## 🐛 Issue Guidelines

### Reporting Bugs

Use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md):

```markdown
**Bug Description**
Clear description of what the bug is.

**Steps to Reproduce**
1. Step one
2. Step two
3. See error

**Expected Behavior**
What you expected to happen.

**Environment**
- OS: [e.g., Windows 10, Ubuntu 20.04]
- Python version: [e.g., 3.9.0]
- AI Mail MCP version: [e.g., 1.0.0]
- MCP Client: [e.g., Claude Desktop, VS Code]
```

### Feature Requests

Use the [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md):

```markdown
**Feature Description**
Clear description of what you want to add.

**Use Case**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How you envision this working.

**Alternatives Considered**
Other approaches you've considered.
```

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements to docs
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention is needed
- `priority-high`: High priority issues
- `performance`: Performance related
- `security`: Security related

## 🔍 Pull Request Guidelines

### PR Requirements

- **Clear Title**: Descriptive title following conventional commit format
- **Description**: Explain what changes were made and why
- **Link Issues**: Reference related issues with "Fixes #123" or "Closes #456"
- **Tests**: Include tests for new functionality
- **Documentation**: Update relevant documentation

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] All new and existing tests pass

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
```

### Review Process

1. **Automated Checks**: CI/CD runs tests and checks
2. **Code Review**: Maintainers review the code
3. **Feedback**: Address any requested changes
4. **Approval**: Get approval from at least one maintainer
5. **Merge**: Maintainer merges the PR

## 🎨 Code Style

### Python Style

We use several tools to maintain code quality:

```bash
# Code formatting
black src tests

# Import sorting
isort src tests

# Linting
flake8 src tests

# Type checking
mypy src
```

### Style Guidelines

- **Line Length**: 88 characters (Black default)
- **Imports**: Sorted with isort, grouped by standard/third-party/local
- **Type Hints**: Use type hints for all public functions
- **Docstrings**: Google style docstrings for all public APIs
- **Comments**: Clear, concise comments for complex logic

### Example Code Style

```python
"""Module docstring describing the module's purpose."""

import os
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from ai_mail_mcp.models import Message


class ExampleClass:
    """Example class with proper styling.
    
    Attributes:
        name: The name of the example.
        value: An optional value.
    """
    
    def __init__(self, name: str, value: Optional[int] = None) -> None:
        """Initialize the example.
        
        Args:
            name: The name for this example.
            value: Optional value parameter.
        """
        self.name = name
        self.value = value
    
    def process_data(self, items: List[str]) -> List[str]:
        """Process a list of items.
        
        Args:
            items: List of strings to process.
            
        Returns:
            Processed list of strings.
            
        Raises:
            ValueError: If items list is empty.
        """
        if not items:
            raise ValueError("Items list cannot be empty")
        
        # Process each item
        return [item.upper() for item in items]
```

## 📚 Documentation

### Documentation Requirements

- **API Documentation**: All public functions must have docstrings
- **README Updates**: Update README.md for new features
- **Examples**: Provide usage examples for new functionality
- **CHANGELOG**: Update for significant changes

### Documentation Structure

```
docs/
├── api/              # API documentation
├── guides/           # User guides
├── examples/         # Code examples
├── architecture/     # Architecture documentation
└── troubleshooting/  # Common issues and solutions
```

### Writing Guidelines

- **Clear and Concise**: Use simple language
- **Examples**: Include code examples
- **Cross-References**: Link to related documentation
- **Up-to-Date**: Keep documentation current with code changes

## 🚢 Release Process

### Version Numbers

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes (2.0.0)
- **MINOR**: Backwards-compatible functionality (1.1.0)
- **PATCH**: Backwards-compatible bug fixes (1.0.1)

### Release Workflow

1. **Feature Freeze**: Stop adding new features
2. **Testing**: Comprehensive testing phase
3. **Documentation**: Update all documentation
4. **CHANGELOG**: Update with all changes
5. **Tag Release**: Create release tag
6. **Automated Deployment**: CI/CD handles PyPI publishing

### Pre-Release Checklist

- [ ] All tests pass
- [ ] Documentation is updated
- [ ] CHANGELOG.md is current
- [ ] Version numbers are bumped
- [ ] Performance benchmarks are acceptable
- [ ] Security scan passes

## 🤔 Getting Help

### Communication Channels

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Discord**: Real-time chat (coming soon)
- **Email**: Direct contact for sensitive issues

### Maintainer Response Times

- **Issues**: 24-48 hours for initial response
- **Pull Requests**: 48-72 hours for initial review
- **Security Issues**: 24 hours or less

### Office Hours

Maintainers are generally available:
- **Weekdays**: 9 AM - 5 PM EST
- **Weekends**: Limited availability

## 🏆 Recognition

### Contributors

All contributors are recognized in:
- GitHub contributors page
- CONTRIBUTORS.md file
- Release notes for significant contributions

### Types of Contributions

We value all types of contributions:
- 🐛 **Bug Reports**: Help us identify issues
- 💡 **Feature Ideas**: Suggest improvements
- 📝 **Documentation**: Improve clarity
- 🧪 **Testing**: Increase coverage and reliability
- 🎨 **Design**: UI/UX improvements
- 🔧 **Code**: Implementation of features and fixes
- 📢 **Community**: Help others and spread the word

## 📈 Project Stats

Current status:
- **Contributors**: Growing community
- **Issues**: Actively triaged and resolved
- **Pull Requests**: Reviewed within 72 hours
- **Test Coverage**: >90%
- **Performance**: Continuously monitored

## 🔮 Future Plans

### Upcoming Features
- Message encryption
- Cross-machine communication
- Web dashboard
- Enhanced security

### Long-term Vision
- Distributed agent networks
- Enterprise features
- Advanced analytics
- AI-powered message routing

---

Thank you for contributing to AI Mail MCP! Your efforts help make AI agent communication better for everyone. 🚀

*Questions? Feel free to open a discussion or reach out to the maintainers!*
