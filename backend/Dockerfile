# Multi-architecture build
# Supports: linux/amd64, linux/arm64, linux/arm/v7
FROM node:20-alpine

WORKDIR /app

# Install Python (needed for MCP server)
RUN apk add --no-cache python3 py3-pip

# Copy Python MCP server and dependencies
COPY pantrybot_mcp_server.py /app/
COPY pantry_tools.py /app/
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy backend package files
COPY backend/package*.json ./

# Install Node dependencies
RUN npm ci --only=production

# Copy backend source
COPY backend/tsconfig.json ./
COPY backend/src ./src

# Build TypeScript
RUN npm install -D typescript tsx
RUN npm run build

# Create recipes directory
RUN mkdir -p /app/recipes

# Expose port
EXPOSE 8080

# Run the server
CMD ["node", "dist/index.js"]
