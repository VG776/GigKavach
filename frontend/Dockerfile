FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
# Increase npm timeout and add retries
RUN npm ci --legacy-peer-deps --include=optional --maxsockets=5 --timeout=120000
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host"]