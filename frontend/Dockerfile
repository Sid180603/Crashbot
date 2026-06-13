# ============================================
# PHASE 4: Frontend Dockerfile
# Multi-stage build for production
# ============================================

FROM node:18-alpine as base

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Set build-time environment variable
ARG NEXT_PUBLIC_API_URL=http://localhost:8002
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Build for production
RUN npm run build

# Expose port
EXPOSE 3002

# Run application
CMD ["npm", "start"]


# ============================================
# Development stage
# ============================================
FROM base as development

CMD ["npm", "run", "dev"]
