# Use Node.js LTS slim version as base image
FROM node:22.16-slim

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install pnpm and project dependencies
RUN npm install

# Copy the rest of the application code
# In development, we'll mount the local directory as a volume,
# but having this here helps when building the image without a volume
COPY . .

# Expose Vite development server port
EXPOSE 5000

# Set environment variable to indicate development environment
ENV NODE_ENV=development

# Start Vite dev server with host set to 0.0.0.0 to allow external access
CMD ["npm", "run", "dev"]
