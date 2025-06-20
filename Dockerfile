# Multi-stage Dockerfile for AI Mail MCP Server
# This creates a production-ready Docker image with minimal size and security

# Build stage
FROM python:3.8-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml .
COPY src/ src/

# Install Python dependencies
RUN pip install --user --no-cache-dir -e .

# Production stage
FROM python:3.8-slim as production

# Add labels for better container management
LABEL maintainer="TimeLordRaps <timelordraps@example.com>"
LABEL description="AI Mail MCP Server - Inter-agent communication system"
LABEL version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/TimeLordRaps/ai-mail-mcp"

# Create non-root user for security
RUN groupadd -r aimail && useradd -r -g aimail aimail

# Set up directories
WORKDIR /app
RUN mkdir -p /data /logs && chown -R aimail:aimail /app /data /logs

# Copy from builder stage
COPY --from=builder /root/.local /home/aimail/.local
COPY --from=builder /app/src /app/src

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set environment variables
ENV PATH="/home/aimail/.local/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV AI_MAIL_DATA_DIR="/data"
ENV AI_MAIL_LOG_DIR="/logs"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER aimail

# Create entrypoint script
COPY --chown=aimail:aimail <<EOF /app/entrypoint.sh
#!/bin/bash
set -e

# Initialize data directory if needed
if [ ! -f /data/mailbox.db ]; then
    echo "Initializing AI Mail database..."
    python -c "from ai_mail_mcp.mailbox import MailboxManager; from pathlib import Path; MailboxManager(Path('/data/mailbox.db'))"
fi

# Start the server with provided arguments
exec python -m ai_mail_mcp.server "\$@"
EOF

RUN chmod +x /app/entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; conn = sqlite3.connect('/data/mailbox.db'); conn.execute('SELECT 1').fetchone(); conn.close()" || exit 1

# Expose data and log volumes
VOLUME ["/data", "/logs"]

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["--help"]

# Metadata
EXPOSE 0
