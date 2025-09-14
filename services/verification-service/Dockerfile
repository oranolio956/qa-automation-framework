FROM node:20-alpine AS deps
WORKDIR /srv
COPY package.json package-lock.json* .npmrc* ./
RUN npm ci --ignore-scripts

FROM node:20-alpine AS builder
WORKDIR /srv
COPY --from=deps /srv/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /srv
ENV NODE_ENV=production
COPY --from=builder /srv/dist ./dist
COPY --from=builder /srv/package.json ./package.json
COPY --from=builder /srv/node_modules ./node_modules
EXPOSE 4007
CMD ["node", "dist/index.js"]

