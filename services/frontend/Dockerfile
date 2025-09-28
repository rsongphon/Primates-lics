# Multi-stage build for Next.js Frontend Service
# Based on Documentation.md Section 11.3 - Docker Optimization with Multi-Stage Builds

# Build stage with full toolchain
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files for dependency installation
COPY package*.json ./

# Install dependencies with npm ci for faster, reliable, reproducible builds
RUN npm ci --only=production --ignore-scripts

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Runtime stage with minimal image
FROM node:20-alpine AS runner

# Create non-root user for security (Documentation.md Section 11.3)
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Set working directory
WORKDIR /app

# Copy necessary files from builder stage
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next

# Set user to non-root
USER nextjs

# Expose port
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# Start the application
CMD ["node", "server.js"]