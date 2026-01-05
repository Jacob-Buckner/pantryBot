FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared tools and HTTP bridge
COPY pantry_tools.py .
COPY mcp_http_bridge.py .
COPY claude_chat_handler.py .

# Create recipes directory
RUN mkdir -p /app/recipes

# Expose HTTP port (internal - map to any port you want with -p)
EXPOSE 8000

# Run the HTTP bridge (wraps the MCP server)
CMD ["python", "mcp_http_bridge.py"]
