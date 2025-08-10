# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies.
RUN apt-get update && \
    apt-get install -y curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install the 'uv' CLI.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# Install uv in build stage
RUN pip install --no-cache-dir uv

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN uv pip install --no-cache --system -r requirements.txt

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy necessary files from mcp-server folder
COPY server.py .


# Ensure uv is in PATH
ENV PATH=/usr/local/bin:$PATH

# Expose port 4200 for the FastMCP server
EXPOSE 4200

# Run the server with uv
CMD ["uv", "run", "server.py"]